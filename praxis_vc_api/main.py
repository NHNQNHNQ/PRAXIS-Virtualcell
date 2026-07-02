"""v0.6 P2:PRAXIS-VirtualCell 本地 FastAPI 服务。

科学决策全由确定性 runtime 完成;本服务只做 HTTP 适配 + job 持久化。默认 offline。
启动:praxis-vc serve  或  uvicorn praxis_vc_api.main:app
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from praxis_vc_api.models.api_schema import HealthOut, JobIn, JobOut, ParseIn, ParseOut
from praxis_vc_api.services import runtime_service as svc

app = FastAPI(title="PRAXIS-VirtualCell Local API", version="0.6")

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


@app.post("/api/jobs", response_model=JobOut)
def create_job(body: JobIn):
    """已确认的 request → 离线 runtime 执行 → 落盘 job。"""
    try:
        return svc.run_job(body.request, body.mode, body.enable_llm_report)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


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
