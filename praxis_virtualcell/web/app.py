from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from uuid import UUID, uuid4
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from praxis_virtualcell.settings import LLMSettings

Modality = Literal["genome", "transcriptome", "proteome"]


class AnalysisRequest(BaseModel):
    profile_id: str | None = None
    smiles: str = Field(min_length=1, max_length=10000)
    candidate_id: str = Field(default="candidate-001", max_length=200)
    max_turns: int = Field(default=8, ge=1, le=20)
    max_output_tokens: int | None = Field(default=None, ge=1024, le=131072)
    reasoning_effort: Literal["low", "high", "max"] | None = None
    modalities: list[Modality] | None = Field(default=None, min_length=1, max_length=3)


class GeneRequest(BaseModel):
    gene_ids: list[str] = Field(max_length=100)
    modality: Modality | None = None


class FeatureRequest(BaseModel):
    feature_ids: list[str] = Field(max_length=100)
    modality: Modality


def create_app(*, data_root=None, env_file=None, report_root=None, analyzer=None, knowledge_catalog_path=None) -> FastAPI:
    from praxis_virtualcell.omics import list_profiles, load_profile
    from praxis_virtualcell.llm_prediction import analyze_with_agents, render_report
    from praxis_virtualcell.llm_prediction.workflow import DEFAULT_PROFILE
    from praxis2.llm.client import LLMClient

    app = FastAPI(title="PRAXIS VirtualCell", version="2.1.0")
    settings = LLMSettings.load(env_file)
    destination = Path(report_root or "reports/llm_live/web")
    run = analyzer or analyze_with_agents
    gate = asyncio.Semaphore(1)

    def profile_choices():
        return sorted((item for item in list_profiles(data_root=data_root)
                       if item.get("input_role") != "species_reference"), key=lambda item: (
            item.get("input_role") != "strain_reference", item.get("input_role") == "species_reference",
            item.get("label") or item.get("name") or item["profile_id"],
        ))

    def default_profile_id(choices):
        if any(item["profile_id"] == DEFAULT_PROFILE and item.get("input_role") == "strain_reference"
               for item in choices):
            return DEFAULT_PROFILE
        return next((item["profile_id"] for item in choices if item.get("input_role") == "strain_reference"),
                    next((item["profile_id"] for item in choices
                          if item.get("input_role") != "species_reference" and item.get("strain")), None))

    def profile(profile_id):
        try:
            return load_profile(profile_id, data_root=data_root)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            raise HTTPException(404, "Profile unavailable or invalid") from exc

    def selected_profile(profile_id, modalities=None):
        loaded = profile(profile_id)
        if modalities is None:
            return loaded
        try:
            return loaded.select_modalities(modalities)
        except ValueError as exc:
            raise HTTPException(422, "Requested modalities are unavailable or invalid for this profile") from exc

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/api/health")
    async def health():
        choices = profile_choices()
        return {"status": "ok", "inference": "llm_only", "model": settings.model,
                "workflow": "planning_analysis_review_revision",
                "credential_configured": bool(settings.api_key),
                "profile_count": len(choices), "default_profile_id": default_profile_id(choices)}

    @app.get("/api/profiles")
    async def profiles():
        choices = profile_choices()
        return {"profiles": choices, "default_profile_id": default_profile_id(choices)}

    @app.get("/api/profiles/{profile_id}")
    async def overview(profile_id: str, modalities: list[Modality] | None = Query(default=None)):
        return selected_profile(profile_id, modalities).overview()

    @app.post("/api/profiles/{profile_id}/genes")
    async def genes(profile_id: str, request: GeneRequest):
        loaded = selected_profile(profile_id, [request.modality] if request.modality else None)
        return loaded.query_genes(request.gene_ids)

    @app.post("/api/profiles/{profile_id}/features")
    async def features(profile_id: str, request: FeatureRequest):
        loaded = selected_profile(profile_id, [request.modality])
        try:
            return loaded.query_features(request.modality, request.feature_ids)
        except ValueError as exc:
            raise HTTPException(422, "Invalid feature query for the selected modality") from exc

    @app.get("/api/profiles/{profile_id}/features")
    async def search_features(profile_id: str, query: str, modality: Modality):
        if not query.strip() or len(query) > 200:
            raise HTTPException(422, "Provide a short feature search term")
        loaded = selected_profile(profile_id, [modality])
        try:
            return loaded.search_features(modality, query)
        except ValueError as exc:
            raise HTTPException(422, "Invalid feature query for the selected modality") from exc

    @app.get("/api/profiles/{profile_id}/annotations")
    async def annotations(profile_id: str, query: str, modality: Modality | None = None):
        if not query.strip() or len(query) > 200:
            raise HTTPException(422, "Provide a short annotation search term")
        loaded = selected_profile(profile_id, [modality] if modality else None)
        return loaded.search_annotations(query)

    @app.post("/api/analyze")
    async def analyze(request: AnalysisRequest):
        chosen_id = request.profile_id or default_profile_id(profile_choices())
        if chosen_id is None:
            raise HTTPException(422, "Select an explicit strain profile; species references are not selected by default")
        loaded = selected_profile(chosen_id, request.modalities)
        if loaded.overview().get("input_role") == "species_reference":
            raise HTTPException(422, "New analysis requires an explicit strain; species references remain readable as historical context")
        if not settings.api_key:
            raise HTTPException(503, "Configure DEEPSEEK_API_KEY locally")
        async with gate:
            client = LLMClient(settings.api_key, settings.base_url, timeout_s=180)
            def progress(event):
                logging.getLogger("uvicorn.error").info("Analysis progress: %s", json.dumps(
                    {"candidate_id": request.candidate_id, **event}, ensure_ascii=False))
            try:
                selection = {"modalities": request.modalities} if request.modalities is not None else {}
                if knowledge_catalog_path is not None:
                    selection["knowledge_catalog_path"] = knowledge_catalog_path
                result = await run(request.smiles, chosen_id, client=client,
                                   model=settings.model, data_root=data_root,
                                   max_turns=request.max_turns, candidate_id=request.candidate_id,
                                   on_progress=progress,
                                   max_output_tokens=request.max_output_tokens or settings.max_output_tokens,
                                   reasoning_effort=request.reasoning_effort or settings.reasoning_effort,
                                   **selection)
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
