"""v0.6 P2:API 与核心 runtime/服务层之间的薄适配。所有科学决策仍由确定性 runtime 完成。"""
from __future__ import annotations

import hashlib
import json
import os

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.workflows.run_virtualcell_query import parse_query, run_query

RUNS_DIR = os.environ.get("PRAXIS_VC_RUNS", "runs")
RUNTIME_VERSION = "v0.3"


def config_for(mode: str) -> RuntimeConfig:
    """mode=llm_assisted 时从 env 取 key(无 key 自动 fallback);否则强制 offline。"""
    if mode in ("llm_assisted", "llm-assisted"):
        os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"
        return RuntimeConfig.from_env()
    return RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


def health() -> dict:
    cfg = RuntimeConfig.from_env()
    return {"status": "ok", "mode": cfg.mode.value, "llm_enabled": cfg.llm_enabled,
            "runtime_version": RUNTIME_VERSION}


def parse(text: str, mode: str) -> dict:
    return parse_query(text, config=config_for(mode))


def _job_id(request: dict) -> str:
    h = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]
    store = JobStore(RUNS_DIR)
    return f"vc_{len(store.list_jobs()) + 1:04d}_{h}"


def run_job(request: dict, mode: str, enable_llm_report: bool) -> dict:
    cfg = config_for(mode)
    out = run_query(request, config=cfg, enable_llm_report=enable_llm_report)
    job_id = _job_id(request)
    JobStore(RUNS_DIR).save(job_id, request=request, result=out)
    return {"job_id": job_id, "status": "done"}


def get_job(job_id: str) -> dict:
    return JobStore(RUNS_DIR).load(job_id)


def list_jobs() -> list[dict]:
    """列出 runs/ 下所有 job(带简要信息,供前端 Jobs 列表)。只读,不做任何科学判断。"""
    store = JobStore(RUNS_DIR)
    out: list[dict] = []
    for jid in store.list_jobs():
        try:
            j = store.load(jid)
        except FileNotFoundError:
            continue
        req = j.get("request", {}) or {}
        rep = j.get("report", {}) or {}
        out.append({
            "job_id": jid,
            "status": j.get("status", "unknown"),
            "species": req.get("species"),
            "perturbation_targets": req.get("perturbation_targets", []),
            "abstain": rep.get("abstain"),
            "reliability": rep.get("reliability"),
        })
    return out
