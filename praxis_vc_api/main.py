"""v0.6 P2:PRAXIS-VirtualCell 本地 FastAPI 服务。

科学决策全由确定性 runtime 完成;本服务只做 HTTP 适配 + job 持久化。默认 offline。
启动:praxis-vc serve  或  uvicorn praxis_vc_api.main:app
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from praxis_vc_api.models.api_schema import (
    HealthOut,
    JobIn,
    JobOut,
    PackCompatibilityIn,
    ParseIn,
    ParseOut,
)
from praxis_vc_api.services import data_portal_service as data_portal
from praxis_vc_api.services import runtime_service as svc
from praxis_virtualcell import __version__
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.pack_product import (
    PackIndexError,
    PackNotFound,
    PackUnavailable,
)

logger = logging.getLogger(__name__)


class _UploadBodyTooLarge(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=413, detail="upload_too_large")


class UploadBodyLimitMiddleware:
    """Bound chunked upload bodies before multipart parsing can spool them."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] != "/api/data-uploads"
        ):
            await self.app(scope, receive, send)
            return

        received = 0
        max_body_bytes = data_portal.upload_body_limit()

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_body_bytes:
                    raise _UploadBodyTooLarge()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _UploadBodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"detail": "upload_too_large"},
                headers={"Connection": "close"},
            )
            await response(scope, receive, send)


app = FastAPI(title="PRAXIS-VirtualCell Local API", version=__version__)

# CORS:仅放行本地 Vite dev(5173)。前端只读展示,不影响后端科学决策。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(UploadBodyLimitMiddleware)


@app.middleware("http")
async def protect_data_upload(request: Request, call_next):
    """Reject disabled/unauthorized uploads before multipart body parsing."""
    if request.method == "POST" and request.url.path == "/api/data-uploads":
        try:
            data_portal.authorize_upload(request.headers.get("authorization"))
            data_portal.validate_upload_content_length(
                request.headers.get("content-length")
            )
        except data_portal.UploadRejected as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
    return await call_next(request)


@app.get("/api/health", response_model=HealthOut)
def health():
    return svc.health()


@app.post("/api/parse", response_model=ParseOut)
def parse(body: ParseIn):
    """自然语言 → candidate_request + 校验(不执行)。offline 不调 LLM。"""
    return svc.parse(body.text, body.mode)


@app.get("/api/options")
def options():
    """前端下拉选项(只读):物种/扰动类型/任务的权威枚举 + cell_type 常见示例。"""
    return svc.options()


@app.get("/api/modules")
def modules():
    """八模块目录(只读):M1–M8 的 id/code/display_name/engines/pillars。单一真相源 modules.py。"""
    return svc.modules()


@app.get("/api/packs")
def packs():
    """Return revalidated Pack records and declared model capabilities."""
    try:
        return svc.packs()
    except PackIndexError as exc:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from exc


@app.post("/api/packs/compatibility")
def pack_compatibility(body: PackCompatibilityIn):
    """Read-only request/Pack/model compatibility planning; never execute."""
    try:
        return svc.pack_compatibility(
            body.request,
            body.pack_id,
            body.pack_version,
        )
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail="invalid_request") from exc
    except PackNotFound as exc:
        raise HTTPException(status_code=404, detail="pack_not_found") from exc
    except PackUnavailable as exc:
        raise HTTPException(status_code=409, detail="pack_unavailable") from exc
    except PackIndexError as exc:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from exc


@app.get("/api/packs/{pack_id}/{pack_version}")
def pack(pack_id: str, pack_version: str):
    """Return one revalidated Pack record from the read-only product index."""
    try:
        return svc.pack(pack_id, pack_version)
    except PackNotFound as exc:
        raise HTTPException(status_code=404, detail="pack_not_found") from exc
    except PackIndexError as exc:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from exc


@app.get("/api/packs/{pack_id}/{pack_version}/validate")
def validate_pack(pack_id: str, pack_version: str):
    """Re-run full asset/data validation for a registered Pack."""
    try:
        return svc.validate_registered_pack(pack_id, pack_version)
    except PackNotFound as exc:
        raise HTTPException(status_code=404, detail="pack_not_found") from exc
    except PackIndexError as exc:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from exc


@app.get("/api/data-catalog")
def data_catalog(species: str | None = None):
    """Strict public omics metadata; source files remain download-only."""
    try:
        return data_portal.catalog_payload(species)
    except data_portal.UnsupportedSpecies as exc:
        raise HTTPException(status_code=400, detail="unsupported_species") from exc
    except data_portal.DataPortalConfigError as exc:
        raise HTTPException(status_code=503, detail="data_catalog_invalid") from exc


@app.get("/api/data-catalog/{dataset_id}/files/{file_id}/download")
def download_dataset_file(dataset_id: str, file_id: str):
    """Serve only a catalog-declared file after path, size, and hash checks."""
    try:
        path, catalog_file = data_portal.resolve_download(dataset_id, file_id)
    except data_portal.DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail="dataset_not_found") from exc
    except data_portal.DatasetFileNotFound as exc:
        raise HTTPException(
            status_code=404, detail="dataset_file_not_found"
        ) from exc
    except data_portal.DatasetFileUnavailable as exc:
        raise HTTPException(
            status_code=404, detail="dataset_file_unavailable"
        ) from exc
    except data_portal.DatasetIntegrityError as exc:
        raise HTTPException(
            status_code=409, detail="dataset_integrity_failed"
        ) from exc
    except data_portal.DataPortalConfigError as exc:
        raise HTTPException(
            status_code=503, detail="data_catalog_invalid"
        ) from exc
    return FileResponse(
        path,
        media_type=catalog_file.media_type,
        filename=catalog_file.filename,
    )


@app.post("/api/data-uploads", status_code=201)
def upload_data_file(
    species: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
):
    """Store exact user bytes in quarantine; never unpack or register here."""
    try:
        return data_portal.store_upload(
            filename=file.filename or "",
            species=species,
            content_type=file.content_type,
            stream=file.file,
        )
    except data_portal.UploadRejected as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.detail
        ) from exc
    except data_portal.DataPortalConfigError as exc:
        raise HTTPException(status_code=503, detail="uploads_disabled") from exc


@app.post("/api/jobs", response_model=JobOut)
def create_job(body: JobIn):
    """已确认的 request → 离线 runtime 执行 → 落盘 job。"""
    try:
        return svc.run_job(
            body.request,
            body.mode,
            body.enable_llm_report,
            body.pack_id,
            body.pack_version,
        )
    except InputValidationError as e:
        raise HTTPException(status_code=400, detail="invalid_request") from e
    except PackNotFound as e:
        raise HTTPException(status_code=404, detail="pack_not_found") from e
    except PackUnavailable as e:
        raise HTTPException(status_code=409, detail="pack_unavailable") from e
    except PackIndexError as e:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from e
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail="job_already_exists") from e
    except Exception as e:  # noqa: BLE001
        logger.exception("job execution failed")
        raise HTTPException(status_code=500, detail="job_execution_failed") from e


@app.get("/api/jobs")
def list_jobs():
    """列出历史 job(只读)。供前端 Jobs 列表复用 JobStore.list_jobs。"""
    return {"jobs": svc.list_jobs()}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    try:
        j = svc.get_job(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e
    return {"job_id": job_id, "status": j.get("status", "unknown")}


@app.get("/api/reports/{job_id}")
def report(job_id: str):
    try:
        j = svc.get_job(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e
    return {"structured_report": j.get("report", {}), "narrative_report": j.get("narrative"),
            "trace_url": f"/api/reports/{job_id}/trace",
            "provenance_url": f"/api/reports/{job_id}/provenance",
            "markdown_url": f"/api/reports/{job_id}/markdown",
            "llm_used_for_prediction": False}


@app.get("/api/reports/{job_id}/trace")
def trace(job_id: str):
    try:
        return {"trace": svc.get_job(job_id).get("trace", [])}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e


@app.get("/api/reports/{job_id}/provenance")
def provenance(job_id: str):
    try:
        job = svc.get_job(job_id)
        return {
            "provenance": job.get("provenance", {}),
            "llm_meta": job.get("llm_meta", {}),
            "execution_identity": job.get("execution_identity", {}),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e


@app.get("/api/reports/{job_id}/module-plan")
def module_plan(job_id: str):
    """该 job 的实际模块路由结果(只读):primary/secondary/entries/overall_verdict。
    不可路由 job 返回空 module_plan,不重算。"""
    try:
        return svc.module_plan(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e


@app.get("/api/reports/{job_id}/markdown", response_class=PlainTextResponse)
def report_markdown(job_id: str):
    """确定性 report.md(text/markdown)。历史 job 缺 .md 时现场重渲染。"""
    try:
        return PlainTextResponse(svc.report_markdown(job_id), media_type="text/markdown")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e


def _react_dist() -> Path | None:
    """Resolve explicit, packaged, then source-checkout static assets."""
    configured = os.environ.get("PRAXIS_VC_STATIC_ROOT")
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_dir():
            raise RuntimeError(f"PRAXIS_VC_STATIC_ROOT is not a directory: {path}")
        return path

    package_static = Path(__file__).resolve().parent / "static"
    if package_static.is_dir():
        return package_static

    checkout_dist = Path(__file__).resolve().parent.parent / "praxis_vc_react" / "dist"
    return checkout_dist if checkout_dist.is_dir() else None


# 必须在所有 /api 路由声明之后 mount，API 路由优先匹配。release wheel 使用包内
# static；开发 checkout 回退到 Vite dist；容器也可显式设置 PRAXIS_VC_STATIC_ROOT。
_REACT_DIST = _react_dist()
if _REACT_DIST is not None:
    app.mount("/", StaticFiles(directory=str(_REACT_DIST), html=True), name="react")
