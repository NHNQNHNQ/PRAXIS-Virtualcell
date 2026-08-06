"""v0.6 P2:API 与核心 runtime/服务层之间的薄适配。所有科学决策仍由确定性 runtime 完成。"""
from __future__ import annotations

import hashlib
import json
import os

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.io.job_store import JobStore
from praxis_virtualcell.pack_factory import factory_catalog_payload
from praxis_virtualcell.pack_product import (
    PackIndex,
    compatibility_payload,
    pack_catalog_payload,
    run_pack_query,
    virtual_experiment_payload,
)
from praxis_virtualcell.version import (
    API_PROTOCOL_VERSION,
    LEGACY_RUNTIME_VERSION,
    PRODUCT_VERSION,
    RUNTIME_PROTOCOL_VERSION,
    git_sha,
)
from praxis_virtualcell.workflows.run_virtualcell_query import (
    SUPPORTED_PERTURBATION,
    SUPPORTED_SPECIES,
    SUPPORTED_TASKS,
    parse_query,
    run_query,
    validate_candidate,
)

RUNS_DIR = os.environ.get("PRAXIS_VC_RUNS", "runs")

# UI 辅助:cell_type 后端不做枚举校验(自由字符串),这里仅给常见示例供前端下拉,
# 允许自由填写。物种/扰动类型的合法值直接复用 runtime 白名单(单一真相源)。
_CELL_TYPE_EXAMPLES = [
    "K562", "HEK293T", "A549", "Jurkat", "HeLa", "THP-1",
    "iPSC", "T cell", "B cell", "macrophage", "fibroblast", "hepatocyte",
]


def config_for(mode: str) -> RuntimeConfig:
    """mode=llm_assisted 时从 env 取 key(无 key 自动 fallback);否则强制 offline。"""
    if mode in ("llm_assisted", "llm-assisted"):
        os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"
        return RuntimeConfig.from_env()
    return RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)


def health() -> dict:
    cfg = RuntimeConfig.from_env()
    return {
        "status": "ok",
        "mode": cfg.mode.value,
        "llm_enabled": cfg.llm_enabled,
        "product_version": PRODUCT_VERSION,
        "api_protocol_version": API_PROTOCOL_VERSION,
        "runtime_protocol_version": RUNTIME_PROTOCOL_VERSION,
        "runtime_version": LEGACY_RUNTIME_VERSION,
        "git_sha": git_sha(),
    }


def parse(text: str, mode: str) -> dict:
    return parse_query(text, config=config_for(mode))


def options() -> dict:
    """暴露后端权威枚举供前端下拉(只读)。cell_type 后端不限制,仅给示例可自由填。
    cell_presets 是只读展示层(catalog),不引入新词汇/治理权威。"""
    from praxis_virtualcell.catalogs import load_cell_presets
    return {
        "species": sorted(SUPPORTED_SPECIES),
        "perturbation_type": sorted(SUPPORTED_PERTURBATION),
        "task_type": sorted(SUPPORTED_TASKS),
        "cell_type_examples": list(_CELL_TYPE_EXAMPLES),
        "cell_type_free_text": True,
        "cell_presets": load_cell_presets(),
    }


def modules() -> dict:
    """八模块目录(只读展示)。单一真相源 = biological_modules.modules,前端 module_context 步消费。"""
    from praxis_virtualcell.biological_modules import modules as M
    return {"modules": [
        {"id": mid, "code": M.MODULES[mid]["code"],
         "display_name": M.MODULES[mid]["display_name"],
         "engines": list(M.MODULES[mid]["engines"]),
         "pillars": list(M.MODULES[mid]["pillars"])}
        for mid in M.MODULE_ORDER
    ]}


def _job_id(
    request: dict,
    pack_id: str | None = None,
    pack_version: str | None = None,
) -> str:
    identity = {
        "request": request,
        "pack_id": pack_id,
        "pack_version": pack_version,
    }
    h = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:8]
    store = JobStore(RUNS_DIR)
    return f"vc_{len(store.list_jobs()) + 1:04d}_{h}"


def run_job(
    request: dict,
    mode: str,
    enable_llm_report: bool,
    pack_id: str | None = None,
    pack_version: str | None = None,
) -> dict:
    if request.get("schema_version") == "vc.request.v2":
        if not all(
            isinstance(value, str) and value and value.strip() == value
            for value in (pack_id, pack_version)
        ):
            raise InputValidationError(
                "vc.request.v2 requires exact pack_id and pack_version"
            )
        try:
            validated_request = VirtualCellRequestV2.from_dict(request).to_dict()
        except (TypeError, ValueError) as exc:
            raise InputValidationError("invalid vc.request.v2") from exc
        out = virtual_experiment_payload(
            validated_request,
            pack_id=pack_id,
            pack_version=pack_version,
        )
        job_id = _job_id(validated_request, pack_id, pack_version)
        JobStore(RUNS_DIR).save(job_id, request=validated_request, result=out)
        return {"job_id": job_id, "status": "done"}

    cfg = config_for(mode)
    validation = validate_candidate(request)
    if not validation["schema_valid"]:
        raise InputValidationError(
            "confirmed_request_invalid:"
            f"missing={validation['missing_fields']} errors={validation['errors']}"
        )
    normalized = validation["normalized"]
    # API 运行与落盘只消费 validator normalized 的顶层请求；metadata 响应安全扩展 key
    # 可保留，但 requested_outputs/assumptions 等控制字段已清洗，且不把原始请求混回去。
    validated_request = dict(normalized)
    if pack_id is None:
        out = run_query(
            validated_request,
            config=cfg,
            enable_llm_report=enable_llm_report,
        )
    else:
        out = run_pack_query(
            validated_request,
            pack_id=pack_id,
            pack_version=pack_version,
            config=cfg,
            enable_llm_report=enable_llm_report,
        )
    job_id = _job_id(validated_request, pack_id, pack_version)
    JobStore(RUNS_DIR).save(job_id, request=validated_request, result=out)
    return {"job_id": job_id, "status": "done"}


def packs() -> dict:
    return pack_catalog_payload()


def pack_factory_catalog() -> dict:
    """Read-only, root-free P19 lifecycle projection; never creates or mutates a store."""
    return factory_catalog_payload()


def pack(pack_id: str, pack_version: str) -> dict:
    return PackIndex().get_record(pack_id, pack_version)


def validate_registered_pack(pack_id: str, pack_version: str) -> dict:
    return PackIndex().get_record(pack_id, pack_version)


def pack_compatibility(
    request: dict,
    pack_id: str,
    pack_version: str,
) -> dict:
    return compatibility_payload(
        request,
        pack_id=pack_id,
        pack_version=pack_version,
    )


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
        execution_identity = j.get("execution_identity") or {}
        pack_identity = execution_identity.get("pack") or {}
        out.append({
            "job_id": jid,
            "status": j.get("status", "unknown"),
            "species": req.get("species"),
            "perturbation_targets": req.get("perturbation_targets", []),
            "abstain": rep.get("abstain"),
            "reliability": rep.get("reliability"),
            "pack_id": pack_identity.get("pack_id"),
            "pack_version": pack_identity.get("pack_version"),
            "pack_fingerprint": pack_identity.get("fingerprint"),
        })
    return out


def report_markdown(job_id: str) -> str:
    """返回该 job 的确定性 report.md(优先读落盘,缺则现场重渲染)。只读。"""
    job = JobStore(RUNS_DIR).load(job_id)   # 缺失抛 FileNotFoundError
    md = job.get("report_md")
    if md:
        return md
    from praxis_virtualcell.io.report_markdown import render_report_md
    return render_report_md(job)


def module_plan(job_id: str) -> dict:
    """从落盘 job 的 structured_report.provenance 提取 module_plan(只读)。
    缺失(abstain/不可路由 job)→ 空 dict,fail-closed 不重算。job 不存在 → FileNotFoundError。"""
    job = JobStore(RUNS_DIR).load(job_id)   # 缺 → FileNotFoundError
    report = job.get("report") or {}
    prov = report.get("provenance") or job.get("provenance") or {}
    return {"module_plan": prov.get("module_plan") or {}}
