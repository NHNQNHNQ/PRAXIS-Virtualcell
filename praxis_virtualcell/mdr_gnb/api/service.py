"""服务层:纯函数,把 run_mdr_query + registry + evidence_tiers 组装成 API 可返回的 dict。
不含 FastAPI 依赖,便于单测。所有输出确定性(同输入逐字相等)。
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from praxis_virtualcell.mdr_gnb.coordinator.active_learning import build_amr_learning_queue
from praxis_virtualcell.mdr_gnb.coordinator.evidence_level import attach_evidence_level
from praxis_virtualcell.mdr_gnb.coordinator.fusion import load_evidence_tiers
from praxis_virtualcell.mdr_gnb.coordinator.task_parser import require_exactly_one_drug_entry
from praxis_virtualcell.mdr_gnb.governance_snapshot import (
    GovernanceExecutionContext,
    build_governance_execution_context,
)
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query

# 10 物种框架(与 run_mdr_query._AGENTS 一致):5 有模型 + 5 fail-closed。
# 顺序固定 → /species 输出确定性。
SPECIES_FRAMEWORK: tuple[str, ...] = (
    "escherichia_coli",
    "klebsiella_pneumoniae",
    "pseudomonas_aeruginosa",
    "acinetobacter_baumannii",
    "salmonella_enterica",
    "enterobacter_cloacae",
    "serratia_marcescens",
    "stenotrophomonas_maltophilia",
    "proteus_mirabilis",
    "morganella_morganii",
)

# 固有耐药/折点极少物种(与 mdr_router._INTRINSIC 一致)
INTRINSIC_SPECIES: frozenset[str] = frozenset({
    "stenotrophomonas_maltophilia", "serratia_marcescens",
    "proteus_mirabilis", "morganella_morganii",
})

# Bump only when a scientific safety/routing policy changes.  This is separate
# from the raw request identity and from the immutable catalog digest so cached
# decisions cannot silently survive a policy change.
RUNTIME_POLICY_VERSION = "mdr-readiness-v4-sidecar-context"
_RESPONSE_ADVISORY_TRACE_SCHEMA = "mdr-response-advisory-v1"
# The advisory is not a scientific/routing decision, so it has an independent
# semantic version.  A changed queue/evidence presentation must not be served
# from a cache entry built by the preceding advisory policy.
ADVISORY_POLICY_VERSION = "mdr-response-advisory-policy-v1"
_RUNTIME_MODEL_PREFLIGHT_FAILURE_SCHEMA = "mdr-runtime-model-context-v2"


@dataclass(frozen=True)
class RuntimeModelPreflight:
    """Private model-context capture plus its cache-safe public identity."""

    context: Any | None
    lifecycle_identity: dict[str, Any]
    requested_model_integrity: dict[str, Any]
    cacheable: bool


def _runtime_request_coordinates(raw: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Normalize only routing coordinates; never retain biological request fields."""
    from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import requested_output_kinds

    drug_entry = require_exactly_one_drug_entry(raw.get("drug_panel"))
    return (
        str(raw.get("species", "") or ""),
        drug_entry["drug"],
        requested_output_kinds(raw),
    )


def _unavailable_runtime_model_identity(raw: dict[str, Any]) -> dict[str, Any]:
    """A non-cacheable receipt for a failed preflight without exposing raw inputs."""
    _species, _drug, output_kinds = _runtime_request_coordinates(raw)
    payload = {
        "schema_version": _RUNTIME_MODEL_PREFLIGHT_FAILURE_SCHEMA,
        "state": "catalog_unavailable",
        "requested_output_kinds": sorted(set(output_kinds)),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": _RUNTIME_MODEL_PREFLIGHT_FAILURE_SCHEMA,
        "catalog_version": None,
        "catalog_digest": None,
        "requested_readiness_digest": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        "requested_capability_count": 0,
        "preflight_state": "catalog_unavailable",
    }


def runtime_model_execution_context(raw: dict[str, Any]) -> RuntimeModelPreflight:
    """Capture selected model readiness before a response-cache lookup.

    An unavailable catalog is deliberately *not* cacheable: the caller must not
    replay an earlier successful response merely because this process could not
    observe the current model state.  API/CLI callers reject this preflight
    explicitly instead of executing under an unbound model observation.
    """
    from praxis_virtualcell.model_zoo.runtime_manifest import (
        capture_runtime_model_execution_context,
    )

    species, drug, output_kinds = _runtime_request_coordinates(raw)
    try:
        context = capture_runtime_model_execution_context(
            species=species,
            drug=drug,
            output_kinds=output_kinds,
        )
    except Exception:  # noqa: BLE001 - cache admission must fail closed
        identity = _unavailable_runtime_model_identity(raw)
        return RuntimeModelPreflight(
            context=None,
            lifecycle_identity={"catalog_version": None, "catalog_digest": None},
            requested_model_integrity=identity,
            cacheable=False,
        )
    return RuntimeModelPreflight(
        context=context,
        lifecycle_identity=context.lifecycle_identity,
        requested_model_integrity=dict(context.public_identity),
        cacheable=True,
    )


def requested_model_integrity_identity(raw: dict[str, Any]) -> dict[str, Any]:
    """Public cache/provenance receipt for the current requested model units."""
    return dict(runtime_model_execution_context(raw).requested_model_integrity)


def supported_species() -> set[str]:
    """Species with at least one live-ready, routeable catalog model.

    Evidence-tier rows remain scientific evidence metadata; they are not evidence
    that a local runtime artifact can currently execute.
    """
    return {
        species
        for species, counts in _species_model_lifecycle().items()
        if counts["ready"] > 0
    }


def _sm_activity_evidence() -> dict[str, Any] | None:
    """线B 化合物活性模型的验证层证据(E1-E5),读已产 artifact;缺则 None(fail-soft)。

    与 SIR 侧 evidence_tiers 暴露对齐:让 /models 能查到化合物活性模型爬到证据阶梯哪一级。
    路径经 __file__ 解析(抗 CWD;裸相对路径在生产 ASGI/Docker 非 repo 根 CWD 下会静默丢失)。
    """
    # service.py: praxis_virtualcell/mdr_gnb/api/ → parents[3] = 仓库根
    repo_root = Path(__file__).resolve().parents[3]
    p = repo_root / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "sm_activity_evidence" / "sm_activity_evidence.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _inspect_catalog_model(manifest: Any, model_id: str) -> Any:
    """Return the runtime state for one catalog model.

    SIR entries deliberately go through ``inspect_sir`` rather than the generic
    lookup: it also verifies that the batch manifest used to generate the runtime
    catalog is still pinned to the catalog's recorded digest.
    """
    if model_id.startswith("sir/"):
        _prefix, species, drug_id = model_id.split("/", maxsplit=2)
        return manifest.inspect_sir(species, drug_id, probe=True)
    return manifest.inspect(model_id, probe=True)


def model_lifecycle_summary(manifest: Any | None = None) -> dict[str, Any]:
    """Expose declared, runtime-ready, and scientifically validated separately.

    ``declared`` comes from the versioned catalog, while ``ready`` is a live
    SHA/dependency/deserialization/schema-probe result.  ``validated`` is never
    inferred from a successful runtime probe: it is true only when the catalog
    explicitly records a completed scientific validation *and* the exact artifact
    is ready.  This is intentionally more conservative than the legacy registry
    capability count, which remains below for backward compatibility.
    """
    if manifest is None:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        manifest = get_runtime_manifest()

    entries: list[dict[str, Any]] = []
    for model_id, model in sorted(manifest.models.items()):
        readiness = _inspect_catalog_model(manifest, model_id)
        capability = dict(model.get("capability") or {})
        lifecycle = dict(model.get("lifecycle") or {})
        validation = dict(model.get("validation") or {})
        asset = dict(model.get("asset") or {})
        entries.append({
            "id": model_id,
            "execution": model.get("execution"),
            "capability": capability,
            # Catalog declaration is intentionally independent from runtime
            # availability; a stale source/artifact must not erase its audit trail.
            "declared": bool(lifecycle.get("declared")),
            "ready": bool(readiness.ready),
            "validated": bool(readiness.validated),
            "validation_status": readiness.validation_status,
            "reason_code": readiness.reason_code,
            "routeable_when_ready": bool(lifecycle.get("routeable_when_ready")),
            "artifact_path": asset.get("path"),
            "expected_sha256": asset.get("sha256"),
            "validation": validation,
        })

    validation_status = Counter(str(entry["validation_status"]) for entry in entries)
    return {
        "catalog_version": manifest.doc.get("catalog_version"),
        "catalog_digest": manifest.catalog_digest,
        "readiness_check": "artifact_sha256_dependency_deserialization_schema_probe",
        "declared": sum(entry["declared"] for entry in entries),
        "ready": sum(entry["ready"] for entry in entries),
        "validated": sum(entry["validated"] for entry in entries),
        "routeable_when_ready": sum(entry["routeable_when_ready"] for entry in entries),
        "validation_status": dict(sorted(validation_status.items())),
        "orphaned_evidence": list(manifest.doc.get("orphaned_evidence") or []),
        "models": entries,
    }


def model_lifecycle_identity() -> dict[str, Any]:
    """Small reproducibility handle suitable for every prediction response."""
    from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

    manifest = get_runtime_manifest()
    return {
        "catalog_version": manifest.doc.get("catalog_version"),
        "catalog_digest": manifest.catalog_digest,
    }


def governance_execution_context() -> GovernanceExecutionContext:
    """Capture one private governance context for a cache-keyed execution."""
    return build_governance_execution_context()


def governance_snapshot_identity() -> dict[str, Any]:
    """Return only the public identity for compatibility/read-only callers."""
    return governance_execution_context().snapshot


def _species_model_lifecycle() -> dict[str, dict[str, int]]:
    """Live declared/ready/validated coverage by catalog species.

    Only entries allowed to route once ready are counted.  Stubs, wildcard
    declarations and experimental GEMs remain visible in `/models` but must not
    make a species look production-supported.
    """
    counts = {
        species: {"declared": 0, "ready": 0, "validated": 0}
        for species in SPECIES_FRAMEWORK
    }
    for entry in model_lifecycle_summary()["models"]:
        capability = entry["capability"]
        species = capability.get("species")
        if species not in counts or not entry["routeable_when_ready"]:
            continue
        counts[species]["declared"] += int(bool(entry["declared"]))
        counts[species]["ready"] += int(bool(entry["ready"]))
        counts[species]["validated"] += int(bool(entry["validated"]))
    return counts


def catalog_declared_routeable_species(manifest: Any | None = None) -> set[str]:
    """Cheap declared-coverage view for a single prediction response.

    Exact readiness for the requested unit is recorded in report provenance.  The
    expensive all-artifact live probe is reserved for `/models`, `/species`, and
    `/health`, rather than making every prediction scan all 129 joblib files.
    """
    if manifest is None:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        manifest = get_runtime_manifest()
    return {
        str((model.get("capability") or {}).get("species"))
        for model in manifest.models.values()
        if bool((model.get("lifecycle") or {}).get("routeable_when_ready"))
        and str((model.get("capability") or {}).get("species")) in SPECIES_FRAMEWORK
    }


def models_summary() -> dict[str, Any]:
    """Legacy registry/evidence summary plus the authoritative runtime lifecycle.

    ``registry`` remains a declaration-level compatibility view.  Consumers that
    need to decide whether a model can run must use ``model_lifecycle`` instead.
    """
    from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry

    specs = build_default_registry().all_specs()
    by_output_kind: Counter[str] = Counter(s.output_kind for s in specs)

    tiers = load_evidence_tiers()
    by_tier: Counter[str] = Counter(v.get("tier") for v in tiers.values())
    by_level: Counter[str] = Counter(v.get("evidence_level") for v in tiers.values())
    by_species: Counter[str] = Counter(sp for (sp, _d) in tiers.keys())

    # strong 组合明细(前端 baseline 对比要用),按 (species, drug) 排序确定
    strong = []
    for (sp, drug), v in sorted(tiers.items()):
        if v.get("tier") != "strong":
            continue
        strong.append({
            "species": sp, "drug": drug,
            "evidence_level": v.get("evidence_level"),
            "delta_vme": v.get("delta_vme"),
            "p_value": v.get("p_value"),
            "auc_R": v.get("auc_R"),
            "per_st_vme_fusion": v.get("per_st_vme_fusion"),
            "per_st_vme_rule": v.get("per_st_vme_rule"),
            "me_fusion": v.get("me_fusion"),
            "n_R_ST": v.get("n_R_ST"),
        })

    return {
        "registry": {
            "n_specs": len(specs),
            "by_output_kind": dict(sorted(by_output_kind.items())),
        },
        "evidence_tiers": {
            "total": len(tiers),
            "by_tier": dict(sorted(by_tier.items())),
            "by_evidence_level": dict(sorted(by_level.items())),
            "by_species": dict(sorted(by_species.items())),
            "strong_combos": strong,
        },
        # 线B:化合物活性模型验证层(E1-E5),fail-soft(artifact 缺则 None)
        "compound_activity_evidence": _sm_activity_evidence(),
        # P1:唯一运行时目录。declared/ready/validated 不可互相推断。
        "model_lifecycle": model_lifecycle_summary(),
    }


def canonical_task_id(raw: dict[str, Any]) -> str:
    """内容寻址 task_id:同 raw → 同 id(与字段顺序无关)。保证 /predict 幂等 + 可 replay。"""
    blob = json.dumps(raw, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "mdr-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def execution_cache_key(
    raw: dict[str, Any],
    *,
    lifecycle_identity: dict[str, Any] | None = None,
    governance_snapshot: dict[str, Any] | None = None,
    requested_model_integrity: dict[str, Any] | None = None,
) -> str:
    """Namespace a cached response by selected model state, governance and policies.

    ``task_id`` deliberately remains raw-input identity for replay and user-facing
    URLs.  Cache identity is stricter: the same request must be recomputed when
    the SHA-locked model catalog, a mutable fusion/brain source, or runtime safety
    policy changes.  The response also contains a non-scientific advisory, so
    its independent policy version belongs to this identity even though it does
    not alter the core report or raw-request ``task_id``.
    """
    requested_integrity = dict(
        requested_model_integrity or requested_model_integrity_identity(raw)
    )
    identity = dict(lifecycle_identity or model_lifecycle_identity())
    governance = dict(governance_snapshot or governance_snapshot_identity())
    payload = {
        "task_id": canonical_task_id(raw),
        "catalog_digest": identity["catalog_digest"],
        # This is a request-scoped receipt (not merely a catalog version).  It
        # changes when a selected artifact/source/dependency/probe state changes,
        # so a cache hit cannot bypass readiness that a cache miss would enforce.
        "requested_readiness_digest": requested_integrity["requested_readiness_digest"],
        "governance_digest": governance["governance_digest"],
        "policy_version": RUNTIME_POLICY_VERSION,
        "advisory_policy_version": ADVISORY_POLICY_VERSION,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "mdr-exec-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def cache_response_matches_execution(
    response: Any,
    *,
    execution_id: str,
    lifecycle_identity: dict[str, Any],
    governance_snapshot: dict[str, Any],
    requested_model_integrity: dict[str, Any],
) -> bool:
    """Return whether a cached public response belongs to this exact execution.

    The response cache is an availability optimization, not an authority.  A
    shared-cache payload must therefore repeat the public facts used to namespace
    its key before an API handler can replay it.  This validates cache semantics;
    it is not a substitute for Redis ACL/TLS, immutable artifact releases, or a
    distributed rollout protocol.
    """
    if not isinstance(response, dict):
        return False
    try:
        expected_governance = {
            "schema_version": governance_snapshot["schema_version"],
            "governance_digest": governance_snapshot["governance_digest"],
        }
    except (KeyError, TypeError):
        return False
    return (
        response.get("execution_id") == execution_id
        and response.get("model_lifecycle") == dict(lifecycle_identity)
        and response.get("requested_model_integrity") == dict(requested_model_integrity)
        and response.get("governance_snapshot") == expected_governance
        and response.get("runtime_policy_version") == RUNTIME_POLICY_VERSION
    )


def _serialize_trace(trace: list) -> list[dict[str, Any]]:
    """AgentMessage → JSON 友好 dict(确定性)。"""
    out = []
    for m in trace:
        out.append({
            "message_id": m.message_id,
            "sender": m.sender,
            "receiver": m.receiver,
            "message_type": m.message_type,
            "timestamp": m.timestamp,
            "parent_message_id": m.parent_message_id,
            "payload": m.payload,
        })
    return out


def _canonical_sha256(value: Any) -> str:
    """Hash a public, JSON-compatible trace payload deterministically."""
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _advisory_timestamp(parent_timestamp: str) -> str:
    """Advance the deterministic core clock spelling without owning its clock."""
    if parent_timestamp.startswith("t") and parent_timestamp[1:].isdigit():
        return f"t{int(parent_timestamp[1:]) + 1:04d}"
    return f"{parent_timestamp}:response-advisory"


def _append_response_advisory_trace_event(
    trace: list[dict[str, Any]],
    *,
    runtime_evidence_level: dict[str, Any] | None,
    active_learning: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Append an API-only, content-addressed advisory after the core report.

    ``run_mdr_query`` remains the sole owner of scientific/routing decisions and
    the core report hash.  This API-layer event makes already-public runtime
    evidence and active-learning advice durable and replayable without adding
    either field to the scientific report.
    """
    if not trace or trace[-1].get("message_type") != "report_built":
        raise RuntimeError(
            "response advisory requires report_built to remain the final core trace event"
        )
    parent = trace[-1]
    parent_message_id = str(parent["message_id"])
    advisory_payload = {
        "schema_version": _RESPONSE_ADVISORY_TRACE_SCHEMA,
        "advisory_policy_version": ADVISORY_POLICY_VERSION,
        "advisory_only": True,
        "runtime_evidence_level": runtime_evidence_level,
        "active_learning": active_learning,
    }
    payload_sha256 = _canonical_sha256(advisory_payload)
    event = {
        "message_id": f"{parent_message_id}:response-advisory",
        "sender": "APIService",
        "receiver": "AuditTrail",
        "message_type": "response_advisory_built",
        "timestamp": _advisory_timestamp(str(parent["timestamp"])),
        "parent_message_id": parent_message_id,
        "payload": {**advisory_payload, "payload_sha256": payload_sha256},
    }
    metadata = {
        "schema_version": _RESPONSE_ADVISORY_TRACE_SCHEMA,
        "advisory_policy_version": ADVISORY_POLICY_VERSION,
        "message_id": event["message_id"],
        "parent_message_id": parent_message_id,
        "payload_sha256": payload_sha256,
    }
    return [*trace, event], metadata


def _evidence_for(
    species: str,
    drug: str,
    *,
    tiers: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """(species, drug) 的证据分层明细(前端 baseline 对比 + 门控标注)。无收录返回 None。"""
    source = tiers if tiers is not None else load_evidence_tiers()
    v = source.get((species, drug))
    if v is None:
        return None
    # 返回拷贝,避免调用方改到缓存
    return dict(v)


def _warnings(report: dict[str, Any], *, supported: bool, species: str,
             evidence: dict[str, Any] | None) -> list[str]:
    """证据分层门控 UI 文案(如实标注,不夸大)。确定性顺序。"""
    w: list[str] = []
    if not supported:
        w.append(f"species_not_supported: {species} 无训练模型,fail-closed 不预测")
    if report.get("abstained"):
        reasons = ",".join(report.get("abstain_reasons", []) or [])
        w.append(f"abstained: {reasons}" if reasons else "abstained")
    fusion = (report.get("provenance", {}) or {}).get("fusion") or {}
    tier = (evidence or {}).get("tier") or fusion.get("evidence_tier")
    if tier == "practical":
        w.append("practical_tier: 融合不劣于规则但未达统计显著,谨慎解读")
    elif tier == "no_baseline":
        w.append("no_baseline: 冻结规则表未收录该药,无对照基线")
    elif tier in ("unevaluated", None) and supported and not report.get("abstained"):
        w.append("unevaluated: 未评估是否优于规则")
    return w


def predict(
    raw: dict[str, Any],
    *,
    lifecycle_identity: dict[str, Any] | None = None,
    governance_snapshot: dict[str, Any] | None = None,
    governance_context: GovernanceExecutionContext | None = None,
    runtime_model_preflight: RuntimeModelPreflight | None = None,
) -> dict[str, Any]:
    """包 run_mdr_query,组装 API 响应。确定性:同 raw 逐字相等。
    不重算科学;fusion/evidence 只读暴露;fail-closed 不伪造。"""
    drug_entry = require_exactly_one_drug_entry(raw.get("drug_panel"))
    task_id = canonical_task_id(raw)
    runtime_model_preflight = runtime_model_preflight or runtime_model_execution_context(raw)
    if runtime_model_preflight.context is None:
        raise ValueError("runtime_model_preflight_unavailable")
    captured_lifecycle = dict(runtime_model_preflight.lifecycle_identity)
    if (
        lifecycle_identity is not None
        and dict(lifecycle_identity) != captured_lifecycle
    ):
        raise ValueError(
            "lifecycle_identity must match the captured runtime model context; "
            "identity-only overrides are unsafe for execution"
        )
    lifecycle_identity = captured_lifecycle
    requested_model_integrity = dict(
        runtime_model_preflight.requested_model_integrity
    )
    governance_context = governance_context or governance_execution_context()
    governance_identity = dict(governance_context.snapshot)
    if (governance_snapshot is not None
            and governance_snapshot.get("governance_digest")
            != governance_identity.get("governance_digest")):
        raise ValueError(
            "governance_snapshot must match governance_context; "
            "identity-only overrides are unsafe for execution"
        )
    out = run_mdr_query(
        raw,
        seed_task_id=task_id,
        governance_context=governance_context,
        runtime_manifest=runtime_model_preflight.context,
    )
    report = out["report"]
    route = out["route"]
    trace_governance = (out.get("trace_metadata") or {}).get("governance_snapshot")
    if trace_governance is not None:
        governance_identity = dict(trace_governance)
    execution_id = execution_cache_key(
        raw,
        lifecycle_identity=lifecycle_identity,
        governance_snapshot=governance_identity,
        requested_model_integrity=requested_model_integrity,
    )

    species = raw.get("species", "") or ""
    drug = report.get("drug", "") or ""
    captured_manifest = (
        runtime_model_preflight.context.manifest
        if runtime_model_preflight.context is not None
        else None
    )
    supported = species in catalog_declared_routeable_species(captured_manifest)
    evidence = _evidence_for(
        species,
        drug,
        tiers=governance_context.evidence_tiers,
    )
    fusion = (report.get("provenance", {}) or {}).get("fusion")
    # 有预测 = 未弃权且有主结果(SIR / 线B 小分子 activity / 线B 肽 peptide_activity)
    prediction_available = (not report.get("abstained")) and (
        report.get("sir") is not None
        or report.get("activity") is not None
        or report.get("peptide_activity") is not None)

    # P18:运行时证据层(E0-E5)+ 主动学习队列。advisory——只加响应顶层键,**不写回 report**
    # (保 report/trace/fixture 字节不变);两函数均纯确定性(spike 已证)。与顶层 evidence(验证层
    # tier)并列,二者别混:运行时读弃权/OOD/分歧信号,验证层记模型爬到证据阶梯哪级。
    _req_view = {"species": species, "drug_class": drug_entry.get("drug_class", "")}
    _ev_level = attach_evidence_level(
        report, disagreement=out["disagreement"], request=_req_view)["provenance"]["evidence_level"]
    # 守卫:无预测(无模型物种/弃权)不显自信运行时级——map_evidence_level 只读 abstained,
    # 无模型「无预测结果」分支(abstained=False)会误给 E3,故按 prediction_available 兜 None。
    runtime_evidence_level = _ev_level if prediction_available else None
    # 主动学习刻意用**未 guard 的** _ev_level(真实运行时级)排优先级——它是「该测什么」的内部
    # 依据,与守卫②压制的「对外显示的自信级」是两回事;故无模型物种可能 runtime_evidence_level=None
    # 但 active_learning.drivers 里含 evidence_E3(非矛盾:前者是展示,后者是优先级信号)。
    active_learning = build_amr_learning_queue(
        report, evidence_level=_ev_level, request=_req_view,
        disagreement=out["disagreement"]).to_dict()

    response = {
        "task_id": task_id,
        "species": species,
        "drug": drug,
        "report": report,
        "route": {"disposition": route.get("disposition"),
                  "reason": route.get("reason"),
                  "caution_flags": route.get("caution_flags", [])},
        "fusion": fusion,
        "evidence": evidence,
        "prediction_available": prediction_available,
        "supported_species": supported,
        # P18 advisory(顶层键,不进 report):运行时置信 + 该测什么。runtime 与验证层 evidence 别混
        "runtime_evidence_level": runtime_evidence_level,
        "active_learning": active_learning,
        "warnings": _warnings(report, supported=supported, species=species, evidence=evidence),
        # Compact catalog identity: replay/audit can bind this response to the
        # exact model declaration without altering task_id, DB schema, or report.
        "model_lifecycle": dict(lifecycle_identity),
        # Request-scoped readiness receipt: safe to expose because it contains
        # only model/catalog facts, never AMR profile, SMILES or sequence.
        "requested_model_integrity": requested_model_integrity,
        "governance_snapshot": {
            "schema_version": governance_identity["schema_version"],
            "governance_digest": governance_identity["governance_digest"],
        },
        "execution_id": execution_id,
        "runtime_policy_version": RUNTIME_POLICY_VERSION,
        # LLM 不裁决:三 flag 恒 False(offline 默认亦显式钉住;LLM 只进 provenance)
        "llm": {"mode": "offline", "modify_disposition": False,
                "override_abstain": False, "change_breakpoint": False,
                "note": "LLM 仅进 provenance,不裁决"},
    }
    trace, advisory_metadata = _append_response_advisory_trace_event(
        _serialize_trace(out["trace"]),
        runtime_evidence_level=runtime_evidence_level,
        active_learning=active_learning,
    )
    trace_metadata = dict(out.get("trace_metadata") or {})
    trace_metadata["response_advisory"] = advisory_metadata
    trace_metadata["requested_model_integrity"] = requested_model_integrity
    trace_record = {
        "task_id": task_id,
        "trace": trace,
        "trace_metadata": trace_metadata,
        "route": response["route"],
        "disagreement": out["disagreement"],
        # input manifest:完整 canonical raw,供 DB 落库回放(可复现)
        "input_manifest": raw,
        "model_lifecycle": dict(lifecycle_identity),
        "requested_model_integrity": requested_model_integrity,
        "governance_snapshot": dict(governance_identity),
        "execution_id": execution_id,
        "runtime_policy_version": RUNTIME_POLICY_VERSION,
        "capability": (report.get("provenance", {}) or {}).get("capability"),
    }
    return {"response": response, "trace_record": trace_record}


def species_status() -> list[dict[str, Any]]:
    """10-species framework plus live catalog coverage and separate evidence rows."""
    tiers = load_evidence_tiers()
    per_species_combos: Counter[str] = Counter(sp for (sp, _d) in tiers.keys())
    per_species_strong: Counter[str] = Counter(
        sp for (sp, _d), v in tiers.items() if v.get("tier") == "strong")
    coverage = _species_model_lifecycle()
    out: list[dict[str, Any]] = []
    for sp in SPECIES_FRAMEWORK:
        out.append({
            "name": sp,
            "supported": coverage[sp]["ready"] > 0,
            "intrinsic_resistance": sp in INTRINSIC_SPECIES,
            "n_declared_models": coverage[sp]["declared"],
            "n_ready_models": coverage[sp]["ready"],
            "n_validated_models": coverage[sp]["validated"],
            "n_evidence_combos": int(per_species_combos.get(sp, 0)),
            "n_strong": int(per_species_strong.get(sp, 0)),
        })
    return out
