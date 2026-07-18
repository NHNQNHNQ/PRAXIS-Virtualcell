"""v0.6 P2:PRAXIS-VirtualCell 本地 FastAPI 服务。

科学决策全由确定性 runtime 完成;本服务只做 HTTP 适配 + job 持久化。默认 offline。
启动:praxis-vc serve  或  uvicorn praxis_vc_api.main:app
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from praxis_vc_api.models.api_schema import HealthOut, JobIn, JobOut, ParseIn, ParseOut
from praxis_vc_api.services import runtime_service as svc
from praxis_virtualcell import __version__

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


@app.post("/api/jobs", response_model=JobOut)
def create_job(body: JobIn):
    """已确认的 request → 离线 runtime 执行 → 落盘 job。"""
    try:
        return svc.run_job(body.request, body.mode, body.enable_llm_report)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        return {"provenance": svc.get_job(job_id).get("provenance", {}),
                "llm_meta": svc.get_job(job_id).get("llm_meta", {})}
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
