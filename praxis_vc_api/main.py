"""Local FastAPI adapter for PRAXIS-VirtualCell.

The deterministic runtime makes scientific decisions; this service adapts
HTTP requests and persists jobs. Offline mode is the default.
Start with praxis-vc serve or uvicorn praxis_vc_api.main:app.
"""

from __future__ import annotations

import hashlib
import json
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
    ResearchTaskDescriptor,
    ResearchTaskExecutionIn,
)
from praxis_vc_api.services import data_portal_service as data_portal
from praxis_vc_api.services import runtime_service as svc
from praxis_virtualcell import __version__
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.data_packs.errors import PackRegistryError
from praxis_virtualcell.pack_factory import PackFactoryError
from praxis_virtualcell.pack_product import (
    PackIndexError,
    PackNotFound,
    PackUnavailable,
)
from praxis_virtualcell.workflows.runtime_builder import DirectV2RuntimeFactory
from praxis_virtualcell.workflows.submit_job import DirectV2FactoryUnconfigured

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
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/data-uploads":
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
app.state.direct_v2_factory = None
app.state.research_tasks = ()


def configure_direct_v2_factory(
    factory: DirectV2RuntimeFactory | None,
    *,
    research_tasks: tuple[ResearchTaskDescriptor | dict, ...] = (),
) -> None:
    """Explicitly attach a direct-v2 composition root to this ASGI host.

    The base API intentionally has no default factory: selecting a direct-v2
    submission without one must fail closed rather than auto-discovering a
    model, Pack, adapter, or domain plugin.
    """

    if factory is not None and not isinstance(factory, DirectV2RuntimeFactory):
        raise TypeError("direct_v2_factory must be DirectV2RuntimeFactory or None")
    if not isinstance(research_tasks, tuple):
        raise TypeError("research_tasks must be a tuple")
    tasks = tuple(
        ResearchTaskDescriptor.model_validate(
            _research_task_descriptor_payload(task) if isinstance(task, ResearchTaskDescriptor) else task
        )
        for task in research_tasks
    )
    if len({task.task_id for task in tasks}) != len(tasks):
        raise ValueError("research task IDs must be unique")
    app.state.direct_v2_factory = factory
    app.state.research_tasks = tasks


def _research_task_descriptor_payload(task: ResearchTaskDescriptor) -> dict:
    payload = task.model_dump(mode="json")
    payload["request"] = task.request.to_dict()
    return payload


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _research_task(task_id: str) -> ResearchTaskDescriptor:
    task = next(
        (candidate for candidate in app.state.research_tasks if candidate.task_id == task_id),
        None,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="research_task_not_found")
    return task


def _validate_research_task_plan(task: ResearchTaskDescriptor, plan: dict) -> None:
    reports = plan.get("reports")
    steps = plan.get("steps")
    if not (
        plan.get("pack_id") == task.pack_id
        and plan.get("pack_version") == task.pack_version
        and isinstance(reports, list)
        and len(reports) == 1
        and reports[0].get("model_name") == task.model_name
        and reports[0].get("model_version") == task.model_version
        and reports[0].get("research_execution_scope") == task.execution_scope
        and reports[0].get("scientifically_validated") is task.scientifically_validated
        and isinstance(steps, list)
        and all(
            step.get("model_name") == task.model_name and step.get("model_version") == task.model_version
            for step in steps
        )
    ):
        raise ValueError("research task descriptor does not bind the direct-v2 plan")


def _research_task_compatibility_payload(task: ResearchTaskDescriptor, plan: dict) -> dict:
    descriptor = _research_task_descriptor_payload(task)
    descriptor_fingerprint = _fingerprint(descriptor)
    return {
        "schema_version": "vc.research-task-compatibility.v1",
        "task_id": task.task_id,
        "descriptor_fingerprint": descriptor_fingerprint,
        "compatibility_fingerprint": _fingerprint(
            {
                "descriptor_fingerprint": descriptor_fingerprint,
                "execution_plan": plan,
            }
        ),
        "execution_plan": plan,
    }


def _run_job(
    request: dict,
    mode: str,
    enable_llm_report: bool,
    pack_id: str | None,
    pack_version: str | None,
    *,
    submission_contract: str,
    direct_v2_factory: DirectV2RuntimeFactory | None,
) -> dict:
    try:
        return svc.run_job(
            request,
            mode,
            enable_llm_report,
            pack_id,
            pack_version,
            submission_contract=submission_contract,
            direct_v2_factory=direct_v2_factory,
        )
    except DirectV2FactoryUnconfigured as exc:
        raise HTTPException(status_code=503, detail="direct_v2_factory_unconfigured") from exc
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail="invalid_request") from exc
    except PackNotFound as exc:
        raise HTTPException(status_code=404, detail="pack_not_found") from exc
    except PackUnavailable as exc:
        raise HTTPException(status_code=409, detail="pack_unavailable") from exc
    except PackIndexError as exc:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="job_already_exists") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("job execution failed")
        raise HTTPException(status_code=500, detail="job_execution_failed") from exc


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
            data_portal.validate_upload_content_length(request.headers.get("content-length"))
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
    """Parse and validate a candidate without execution. Offline mode makes no LLM calls."""
    return svc.parse(body.text, body.mode)


@app.get("/api/options")
def options():
    """Return authoritative request enums and editable cell-type examples."""
    return svc.options()


@app.get("/api/modules")
def modules():
    """Return the read-only M1-M8 catalog from biological_modules.modules."""
    return svc.modules()


@app.get("/api/research-tasks")
def research_tasks():
    """Return only explicitly configured, path-free research task descriptors."""
    return {"tasks": [_research_task_descriptor_payload(task) for task in app.state.research_tasks]}


@app.post("/api/research-tasks/{task_id}/compatibility")
def research_task_compatibility(task_id: str):
    """Plan one configured task through its exact direct-v2 factory; never execute."""
    task = _research_task(task_id)
    factory = app.state.direct_v2_factory
    if factory is None:
        raise HTTPException(status_code=503, detail="direct_v2_factory_unconfigured")
    try:
        plan = factory.compatibility(task.request, task.pack_id, task.pack_version)
        _validate_research_task_plan(task, plan)
    except (InputValidationError, PackRegistryError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="research_task_unavailable") from exc
    return _research_task_compatibility_payload(task, plan)


@app.post("/api/research-tasks/{task_id}/execute", response_model=JobOut)
def execute_research_task(task_id: str, body: ResearchTaskExecutionIn):
    """Execute only while the current exact plan matches the confirmed preview."""
    task = _research_task(task_id)
    factory = app.state.direct_v2_factory
    if factory is None:
        raise HTTPException(status_code=503, detail="direct_v2_factory_unconfigured")
    try:
        with factory.compatibility_guard(task.request, task.pack_id, task.pack_version) as plan:
            _validate_research_task_plan(task, plan)
            compatibility = _research_task_compatibility_payload(task, plan)
            if compatibility["compatibility_fingerprint"] != body.compatibility_fingerprint:
                raise HTTPException(status_code=409, detail="research_task_compatibility_stale")
            if plan.get("executable") is not True:
                raise HTTPException(status_code=409, detail="research_task_unavailable")
            return _run_job(
                task.request.to_dict(),
                "offline",
                False,
                task.pack_id,
                task.pack_version,
                submission_contract="vc.direct-v2-execution.v1",
                direct_v2_factory=factory,
            )
    except HTTPException:
        raise
    except (InputValidationError, PackRegistryError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="research_task_unavailable") from exc


@app.get("/api/packs")
def packs():
    """Return revalidated Pack records and declared model capabilities."""
    try:
        return svc.packs()
    except PackIndexError as exc:
        raise HTTPException(status_code=503, detail="pack_index_invalid") from exc


@app.get("/api/pack-factory")
def pack_factory_catalog():
    """Read-only receipt/candidate/registration projection; no HTTP write route exists."""
    try:
        return svc.pack_factory_catalog()
    except PackFactoryError as exc:
        raise HTTPException(status_code=503, detail="pack_factory_store_invalid") from exc


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
        raise HTTPException(status_code=404, detail="dataset_file_not_found") from exc
    except data_portal.DatasetFileUnavailable as exc:
        raise HTTPException(status_code=404, detail="dataset_file_unavailable") from exc
    except data_portal.DatasetIntegrityError as exc:
        raise HTTPException(status_code=409, detail="dataset_integrity_failed") from exc
    except data_portal.DataPortalConfigError as exc:
        raise HTTPException(status_code=503, detail="data_catalog_invalid") from exc
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
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except data_portal.DataPortalConfigError as exc:
        raise HTTPException(status_code=503, detail="uploads_disabled") from exc


@app.post("/api/jobs", response_model=JobOut)
def create_job(body: JobIn):
    """Execute a confirmed request through the offline runtime and persist the job."""
    return _run_job(
        body.request,
        body.mode,
        body.enable_llm_report,
        body.pack_id,
        body.pack_version,
        submission_contract=body.submission_contract,
        direct_v2_factory=app.state.direct_v2_factory,
    )


@app.get("/api/jobs")
def list_jobs():
    """List saved job summaries through JobStore.list_jobs."""
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
    return {
        "structured_report": j.get("report", {}),
        "narrative_report": j.get("narrative"),
        "trace_url": f"/api/reports/{job_id}/trace",
        "provenance_url": f"/api/reports/{job_id}/provenance",
        "markdown_url": f"/api/reports/{job_id}/markdown",
        "llm_used_for_prediction": False,
    }


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
    """Read the stored routing plan; unroutable jobs return an empty plan without recomputation."""
    try:
        return svc.module_plan(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e


@app.get("/api/reports/{job_id}/markdown", response_class=PlainTextResponse)
def report_markdown(job_id: str):
    """Return deterministic Markdown, rendering it from the saved artifact when missing."""
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


_REACT_DIST = _react_dist()
if _REACT_DIST is not None:
    app.mount("/", StaticFiles(directory=str(_REACT_DIST), html=True), name="react")
