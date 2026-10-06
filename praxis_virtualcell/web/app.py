from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from praxis_virtualcell.settings import LLMSettings


class AnalysisRequest(BaseModel):
    profile_id: str = "AB5075-AZI000"
    smiles: str = Field(min_length=1, max_length=10000)
    candidate_id: str = Field(default="candidate-001", max_length=200)
    max_turns: int = Field(default=8, ge=1, le=20)


class GeneRequest(BaseModel):
    gene_ids: list[str] = Field(max_length=100)


def create_app(*, data_root=None, env_file=None, report_root=None, analyzer=None) -> FastAPI:
    from praxis_virtualcell.omics import list_profiles, load_profile
    from praxis_virtualcell.llm_prediction import analyze_candidate, render_report
    from praxis2.llm.client import LLMClient

    app = FastAPI(title="PRAXIS VirtualCell", version="2.1.0")
    settings = LLMSettings.load(env_file)
    destination = Path(report_root or "reports/llm_live/web")
    run = analyzer or analyze_candidate
    gate = asyncio.Semaphore(1)

    def profile(profile_id):
        try:
            return load_profile(profile_id, data_root=data_root)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            raise HTTPException(404, "Profile unavailable or invalid") from exc

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "inference": "llm_only", "model": settings.model,
                "credential_configured": bool(settings.api_key),
                "profile_count": len(list_profiles(data_root=data_root))}

    @app.get("/api/profiles")
    async def profiles():
        return {"profiles": list_profiles(data_root=data_root)}

    @app.get("/api/profiles/{profile_id}")
    async def overview(profile_id: str):
        return profile(profile_id).overview()

    @app.post("/api/profiles/{profile_id}/genes")
    async def genes(profile_id: str, request: GeneRequest):
        return profile(profile_id).query_genes(request.gene_ids)

    @app.get("/api/profiles/{profile_id}/annotations")
    async def annotations(profile_id: str, query: str):
        if not query.strip() or len(query) > 200:
            raise HTTPException(422, "Provide a short annotation search term")
        return profile(profile_id).search_annotations(query)

    @app.post("/api/analyze")
    async def analyze(request: AnalysisRequest):
        profile(request.profile_id)
        if not settings.api_key:
            raise HTTPException(503, "Configure DEEPSEEK_API_KEY locally")
        async with gate:
            client = LLMClient(settings.api_key, settings.base_url, timeout_s=180)
            def progress(event):
                logging.getLogger("uvicorn.error").info("Analysis progress: %s", json.dumps(
                    {"candidate_id": request.candidate_id, **event}, ensure_ascii=False))
            try:
                result = await run(request.smiles, request.profile_id, client=client,
                                   model=settings.model, data_root=data_root,
                                   max_turns=request.max_turns, candidate_id=request.candidate_id,
                                   on_progress=progress)
            except Exception as exc:
                raise HTTPException(502, "LLM analysis failed; no prediction was substituted") from exc
            finally:
                await client.aclose()
        report_id = str(uuid4())
        destination.mkdir(parents=True, exist_ok=True)
        payload = {**result, "report_id": report_id}
        (destination / f"{report_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown = render_report(result)
        (destination / f"{report_id}.md").write_text(markdown, encoding="utf-8")
        return {**payload, "report_markdown": markdown}

    @app.get("/api/reports/{report_id}")
    async def report(report_id: str, format: str = "json"):
        try:
            UUID(report_id)
        except ValueError as exc:
            raise HTTPException(404, "Report not found") from exc
        if format not in {"json", "md"}:
            raise HTTPException(422, "Supported formats: json, md")
        path = destination / f"{report_id}.{format}"
        if not path.is_file():
            raise HTTPException(404, "Report not found")
        if format == "md":
            return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))

    return app
