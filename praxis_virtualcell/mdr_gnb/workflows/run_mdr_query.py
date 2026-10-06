"""端到端 MDR-GNB 确定性链，产出可审计的局部 replay trace。

``MessageBus`` 用于物种 agent 的 brain 检索和相关 trace，不是 route/predict 等阶段的
唯一运行时通道；这些阶段目前大多为显式函数调用。时间戳/ID 经每次新建的
``Clock``/``IdGen``（固定起点）产出，使同输入的 trace 可稳定比较。

实际顺序：parse_task → governance capture → SpeciesAgent（检索 captured brain）→ route_mdr → 候选 predict
→ ensembler.aggregate → pre-fusion abstain（硬规则）→ 可选 mechanism sidecar
→ rule-first fusion（仅非 abstain SIR）→ critic（审最终 fusion）→ build_report。
LLM 若启仅在 parse_task,assert_llm_boundaries 守卫防越权。

磁盘 model artifact 缺失、预测器执行失败或输入不足时，predict 闭包 fail-closed 返回 abstained →
该候选记 failed、不进 ensemble（避免伪造 MIC）；若请求输出却无任何成功预测器，核心报告以
`no_successful_predictor` 硬弃权，并保留具体失败机器码。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.mdr_gnb.abstain import AbstainContext, evaluate_abstain
from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import route_mdr
from praxis_virtualcell.mdr_gnb.coordinator.report_builder import build_report
from praxis_virtualcell.mdr_gnb.coordinator.task_parser import (
    parse_task,
    require_exactly_one_drug_entry,
)
from praxis_virtualcell.mdr_gnb.critic import CriticInput, check_invariants
from praxis_virtualcell.mdr_gnb.ensembler import MDRPredictorResult, aggregate
from praxis_virtualcell.mdr_gnb.governance_snapshot import (
    GovernanceExecutionContext,
    build_governance_execution_context,
)
from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry

# 物种名 → agent 类(全景铺开:全 10 物种,retrieve-before-predict 经各自 brain)
from praxis_virtualcell.mdr_gnb.agents.escherichia_coli.agent import EColiAgent
from praxis_virtualcell.mdr_gnb.agents.klebsiella_pneumoniae.agent import KpnAgent
from praxis_virtualcell.mdr_gnb.agents.pseudomonas_aeruginosa.agent import PaeAgent
from praxis_virtualcell.mdr_gnb.agents.acinetobacter_baumannii.agent import AbaAgent
from praxis_virtualcell.mdr_gnb.agents.salmonella_enterica.agent import SenAgent
from praxis_virtualcell.mdr_gnb.agents.enterobacter_cloacae.agent import EclAgent
from praxis_virtualcell.mdr_gnb.agents.serratia_marcescens.agent import SmaeAgent
from praxis_virtualcell.mdr_gnb.agents.stenotrophomonas_maltophilia.agent import SmaAgent
from praxis_virtualcell.mdr_gnb.agents.proteus_mirabilis.agent import PmiAgent
from praxis_virtualcell.mdr_gnb.agents.morganella_morganii.agent import MmoAgent

_AGENTS = {
    "escherichia_coli": EColiAgent, "klebsiella_pneumoniae": KpnAgent,
    "pseudomonas_aeruginosa": PaeAgent, "acinetobacter_baumannii": AbaAgent,
    "salmonella_enterica": SenAgent, "enterobacter_cloacae": EclAgent,
    "serratia_marcescens": SmaeAgent, "stenotrophomonas_maltophilia": SmaAgent,
    "proteus_mirabilis": PmiAgent, "morganella_morganii": MmoAgent,
}

_TRACE_SCHEMA_VERSION = "mdr-trace-v1"
_CRITIC_POLICY_VERSION = "mdr-critic-v2-final-fusion"


def _canonical_sha256(value: Any) -> str:
    """稳定序列化的 SHA256，用于 trace 中绑定输入、provenance 与最终报告。"""
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _brain_root():
    from pathlib import Path
    import praxis_virtualcell.mdr_gnb.agents as agents_pkg
    return Path(agents_pkg.__file__).resolve().parent


def _default_resolve(identifier: str) -> dict[str, Any]:
    """默认化合物标识符解析(经 PubChem;裸 SMILES 本地规范化)。

    测试可 monkeypatch 本函数或给 run_mdr_query 传 resolve= 注入,保证确定性不联网。
    """
    from praxis_virtualcell.mdr_gnb.drug_agent.compound_resolver import resolve_compound
    return resolve_compound(identifier)


def _default_fuse_mechanism(
    species: str,
    drug: str,
    *,
    runtime_manifest: Any | None = None,
) -> dict[str, Any]:
    """Default mechanism fusion under the request's captured model manifest.

    ``RuntimeModelExecutionContext`` owns a private ``manifest``; bare-core
    callers may still provide a manifest directly.  Injected ``fuse_mech`` hooks
    retain their historical two-argument contract and never receive this keyword.
    """
    from praxis_virtualcell.mdr_gnb.coordinator.mechanism_fusion import fuse_mechanism

    sidecar_manifest = getattr(runtime_manifest, "manifest", runtime_manifest)
    return fuse_mechanism(species, drug, sidecar_manifest=sidecar_manifest)


def run_mdr_query(
    raw: dict[str, Any],
    *,
    seed_task_id: str,
    registry=None,
    runtime_manifest: Any | None = None,
    resolve=None,
    fuse_mech=None,
    governance_snapshot: dict[str, Any] | None = None,
    governance_context: GovernanceExecutionContext | None = None,
) -> dict[str, Any]:
    # Validate before observing a model catalog or constructing any legacy
    # execution component.  A panel is not an execution instruction: this path
    # accepts exactly one non-empty drug and never selects a first panel entry.
    msg = parse_task(raw, task_id=seed_task_id)
    drug_entry = require_exactly_one_drug_entry(msg.drug_panel)
    drug = drug_entry["drug"]
    drug_class = drug_entry.get("drug_class", "")

    # The API may provide a request-scoped catalog observation captured before
    # response-cache lookup.  Keep routing, readiness provenance and adapter
    # loading on that same manifest so an in-process catalog rotation cannot
    # make the cache key describe different bytes from the executed predictor.
    # A normal bare-core execution still needs a manifest to construct the
    # default registry.  A caller supplying a custom registry keeps the older
    # lazy provenance path below: catalog failure must become an explicit
    # ``missing_provenance`` critic finding, not an exception before routing.
    if runtime_manifest is None and registry is None:
        from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

        runtime_manifest = get_runtime_manifest()
    registry = registry or build_default_registry(runtime_manifest=runtime_manifest)
    clock, idg = Clock(), IdGen()
    bus = MessageBus()

    governance_context = governance_context or build_governance_execution_context()
    captured_snapshot = dict(governance_context.snapshot)
    if (governance_snapshot is not None
            and governance_snapshot.get("governance_digest")
            != captured_snapshot.get("governance_digest")):
        raise ValueError(
            "governance_snapshot must match the captured execution context; "
            "pass governance_context instead of an identity-only override"
        )
    governance_snapshot = captured_snapshot
    parsed_message = AgentMessage(
        idg.next(), "Parser", "Coordinator", "task_parsed",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "task_id": msg.task_id,
            "input_sha256": _canonical_sha256(raw),
            "requested_outputs": list(msg.requested_outputs),
            "parser_boundaries": list(msg.boundaries),
        },
        clock.now(),
    )
    bus.send(parsed_message)
    trace_parent_id = parsed_message.message_id

    # Bind before any brain/rule/evidence consumer runs.  The same parsed
    # documents are injected below, so the public digest is an identity of the
    # inputs actually consumed rather than merely a pre-execution observation.
    governance_message = AgentMessage(
        idg.next(),
        "Coordinator",
        "PredictorHub",
        "governance_snapshot_bound",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            **governance_snapshot,
        },
        clock.now(),
        parent_message_id=trace_parent_id,
    )
    bus.send(governance_message)
    trace_parent_id = governance_message.message_id

    # An API/CLI execution can supply a model context captured before response
    # cache admission.  Record its safe receipt on the same parent spine so the
    # later route/load provenance is auditable as one observation.  Bare core
    # callers retain compatibility and simply omit this API-level preflight node.
    runtime_model_preflight = dict(
        getattr(runtime_manifest, "public_identity", {}) or {}
    )
    if runtime_model_preflight:
        model_preflight_message = AgentMessage(
            idg.next(),
            "Coordinator",
            "PredictorHub",
            "runtime_model_preflight_bound",
            {
                "schema_version": _TRACE_SCHEMA_VERSION,
                "model_context": runtime_model_preflight,
            },
            clock.now(),
            parent_message_id=trace_parent_id,
        )
        bus.send(model_preflight_message)
        trace_parent_id = model_preflight_message.message_id

    # --- 化合物标识符解析(B2 输入层):compound→smiles;裸 smiles 直用不联网;失败→诚实 fail-closed ---
    smiles = msg.smiles
    compound_resolution_code = None
    if msg.compound and not smiles:
        res = (resolve or _default_resolve)(msg.compound)
        if res.get("ok"):
            smiles = res["smiles"]                    # 解析成功:canonical SMILES 进核心
        else:
            # 无网/查不到/解析失败 → 不伪造 SMILES,置码后经报告级弃权(见下)
            compound_resolution_code = "compound_resolution_failed"

    # --- species agent 经 bus 检索 brain(retrieve-before-predict)---
    agent_cls = _AGENTS.get(msg.species)
    brain_context: dict[str, Any] = {"species": msg.species, "rules_referenced": [],
                                     "species_specific_breakpoints": {}}
    if agent_cls is not None:
        agent = agent_cls(
            brain_root=_brain_root(),
            clock=clock,
            idgen=idg,
            brain=governance_context.brain_for_species(msg.species),
            brain_available=governance_context.brain_available.get(msg.species, False),
            rules_referenced=list(
                governance_context.brain_references.get(msg.species, ())
            ),
        )
        task = AgentMessage(idg.next(), "Coordinator", agent.name, "mdr_task",
                            {"request": {"species": msg.species,
                                         "amr_profile": msg.amr_profile, "drug": drug}},
                            clock.now(), parent_message_id=trace_parent_id)
        bus.send(task)
        agent.handle(bus.get_messages(agent.name)[-1], bus)
        brain_message = bus.latest("brain_retrieved")
        assert brain_message is not None
        brain_context = brain_message.payload["brain_context"]
        trace_parent_id = brain_message.message_id

    # --- 路由 ---
    route = route_mdr({"species": msg.species, "drug": drug, "drug_class": drug_class,
                       "requested_outputs": msg.requested_outputs,
                       "amr_profile": msg.amr_profile}, registry)
    route_message = AgentMessage(
        idg.next(), "Coordinator", "PredictorHub", "route_decided",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "disposition": route.disposition,
            "reason": route.reason,
            "requested_kinds": list(route.requested_kinds),
            "candidate_names": [spec.name for spec in route.candidates],
            "unready_reason_codes": sorted({
                str(item["reason_code"])
                for item in route.unready_candidates if item.get("reason_code")
            }),
        },
        clock.now(), parent_message_id=trace_parent_id,
    )
    bus.send(route_message)

    # P1: the report must bind a decision to exact executable catalog units, not
    # merely broad registry declarations or an evidence tier.  This snapshot is
    # derived from the same manifest used by readiness callbacks.  If the catalog
    # itself cannot be read, retain an explicit failure state instead of guessing.
    try:
        if runtime_manifest is None:
            from praxis_virtualcell.model_zoo.runtime_manifest import get_runtime_manifest

            runtime_manifest = get_runtime_manifest()
        requested_capabilities = runtime_manifest.inspect_request_capabilities(
            species=msg.species,
            drug=drug,
            output_kinds=route.requested_kinds,
            probe=True,
        )
        capability_provenance: dict[str, Any] = {
            "catalog_digest": runtime_manifest.catalog_digest,
            "requested": [status.as_dict() for status in requested_capabilities],
            "catalog_reason_code": "catalog_loaded",
            "route_unready_candidates": list(route.unready_candidates),
        }
    except Exception:  # noqa: BLE001 - provenance failure must remain fail-closed
        requested_capabilities = []
        capability_provenance = {
            "catalog_digest": None,
            "requested": [],
            "catalog_reason_code": "catalog_unavailable",
            "route_unready_candidates": list(route.unready_candidates),
        }
    capability_by_kind = dict(
        zip(sorted(set(route.requested_kinds)), requested_capabilities, strict=False)
    )
    catalog_spec_kinds = {
        "genotype_to_sir": "sir_class",
        "sm_activity_model": "sm_activity",
        "peptide_activity_model": "peptide_activity",
    }

    # --- 跑候选 predict → predictor_result(记 trace,供 critic retrieve-first)---
    results: list[MDRPredictorResult] = []
    failed_reason_codes: list[str] = []
    ctx = {"species": msg.species, "drug": drug, "amr_profile": msg.amr_profile,
           "assay_context": msg.assay_context, "features": msg.amr_profile,
           "smiles": smiles,                          # 线B:化合物结构输入(compound 已解析成 smiles)
           "sequence": msg.sequence}                  # 线B B5:抗菌肽序列输入
    chem_ood = False                                  # 化合物/肽落在训练(化学/序列)空间外(→ abstain)
    # sm_activity/peptide_activity 非 OOD 的 fail-closed 机器码(诚实透出);解析失败优先(比"缺 smiles"更准)
    activity_abstain_code = compound_resolution_code
    # 活性类 output_kind(小分子/肽),共享 OOD→abstain + 非 OOD→报告级弃权的 fail-closed 处理
    _ACTIVITY_KINDS = ("sm_activity", "peptide_activity")
    for spec in route.candidates:
        if spec.output_kind not in ("mic_scalar", "sir_class", "synergy", *_ACTIVITY_KINDS):
            continue  # mechanism_state 不进 SIR/MIC/活性 ensemble
        predictor_input_sha256 = _canonical_sha256({
            "spec": {
                "name": spec.name,
                "version": spec.version,
                "output_kind": spec.output_kind,
            },
            "context": ctx,
        })
        catalog_status = None
        if catalog_spec_kinds.get(spec.name) == spec.output_kind:
            catalog_status = capability_by_kind.get(spec.output_kind)
        catalog_trace = None
        if catalog_status is not None:
            catalog_trace = {
                "model_id": catalog_status.model_id,
                "catalog_digest": catalog_status.catalog_digest,
                "artifact_path": catalog_status.artifact_path,
                "artifact_sha256": catalog_status.expected_sha256,
                "declared": catalog_status.declared,
                "ready": catalog_status.ready,
                "validated": catalog_status.validated,
                "validation_status": catalog_status.validation_status,
                "reason_code": catalog_status.reason_code,
            }
        # This records the verified readiness contract immediately before a
        # predictor closure is invoked.  It is intentionally not called
        # ``artifact_loaded``: closures may use a cache, and the generic trace
        # cannot honestly assert a fresh deserialization on every request.
        predictor_contract_message = AgentMessage(
            idg.next(),
            "PredictorHub",
            spec.name,
            "predictor_contract_checked",
            {
                "schema_version": _TRACE_SCHEMA_VERSION,
                "spec": spec.name,
                "version": spec.version,
                "output_kind": spec.output_kind,
                "artifact_path": spec.artifact_path,
                "predictor_input_sha256": predictor_input_sha256,
                "contract_status": (
                    "catalog_verified"
                    if catalog_trace is not None
                    else "unmanaged_test_or_legacy_spec"
                ),
                "catalog": catalog_trace,
            },
            clock.now(),
            parent_message_id=route_message.message_id,
        )
        bus.send(predictor_contract_message)
        try:
            pred = spec.predict(ctx) if spec.predict else None
        except Exception:
            # fail-closed:predict 抛任何异常(如无 rdkit 环境 featurize 抛 ImportError)也不崩管线
            pred = None
            failure_reason_code = "predictor_execution_failed"
        else:
            failure_reason_code = None
        # fail-closed:predict 返回 abstained(artifact 缺 / OOD / invalid)或 None → 记 failed 不进 ensemble
        if pred is None or pred.get("abstained"):
            if pred and pred.get("reason_code"):
                failure_reason_code = str(pred["reason_code"])
            if failure_reason_code and failure_reason_code not in failed_reason_codes:
                failed_reason_codes.append(failure_reason_code)
            if spec.output_kind in _ACTIVITY_KINDS:
                if pred and pred.get("ood"):
                    chem_ood = True                   # 化学/序列 OOD:走 drug_in_training_dist 通道弃权
                elif activity_abstain_code is None:
                    # 非 OOD 失败(缺输入/缺 artifact/invalid/predict 崩)→ 诚实机器码,供报告级弃权
                    activity_abstain_code = ((pred or {}).get("reason_code")
                                                or "activity_prediction_failed")
            status, pred = "failed", None
        else:
            status = "success"
        trace_payload: dict[str, Any] = {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "spec": spec.name,
            "status": status,
            "reason_code": failure_reason_code,
            "predictor_input_sha256": predictor_input_sha256,
            "predictor_result_sha256": _canonical_sha256({
                "status": status,
                "prediction": pred,
                "reason_code": failure_reason_code,
            }),
        }
        result_provenance: dict[str, Any] = {
            "artifact": spec.artifact_path,
            "version": spec.version,
        }
        if catalog_trace is not None:
            trace_payload["catalog"] = catalog_trace
            # ``capability.selected`` is a stable API/report summary that
            # predates the richer trace event.  Keep that public shape narrow;
            # the complete contract lives in predictor_contract_checked and
            # predictor_result trace payloads.
            result_provenance["catalog"] = {
                key: catalog_trace[key]
                for key in (
                    "model_id",
                    "catalog_digest",
                    "artifact_sha256",
                    "ready",
                )
            }
        if failure_reason_code:
            result_provenance["failure_reason_code"] = failure_reason_code
        bus.send(AgentMessage(idg.next(), spec.name, "Ensembler", "predictor_result",
                              trace_payload, clock.now(),
                              parent_message_id=predictor_contract_message.message_id))
        results.append(MDRPredictorResult(
            agent_name=spec.name, status=status, output_kind=spec.output_kind,
            prediction=pred, uncertainty=(pred or {}).get("uncertainty", {"sigma": 0.5}),
            provenance=result_provenance))

    capability_provenance["selected"] = [
        result.provenance["catalog"]
        for result in results
        if result.status == "success" and "catalog" in result.provenance
    ]

    # 同 kind 才聚合:取**有 success 结果**的主 kind(优先 mic_scalar,否则 sir_class);
    # 避免 mic_regressor 恒 fail-closed 却占位 mic_scalar 导致 sir_class 成功预测被忽略。
    success_kinds = {r.output_kind for r in results if r.status == "success"}
    successful_predictor_count = sum(r.status == "success" for r in results)
    if "mic_scalar" in success_kinds:
        primary = "mic_scalar"
    elif "sm_activity" in success_kinds:
        primary = "sm_activity"
    elif "peptide_activity" in success_kinds:
        primary = "peptide_activity"
    elif "sir_class" in success_kinds:
        primary = "sir_class"
    else:
        primary = None
    ens = aggregate([r for r in results if r.output_kind == primary]) if primary else aggregate([])
    ensemble_parent = bus.trace[-1].message_id if bus.trace else route_message.message_id
    ensemble_message = AgentMessage(
        idg.next(), "Ensembler", "Reliability", "ensemble_done",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "output_kind": ens.output_kind,
            "models_used": list(ens.models_used),
            "successful_predictor_count": successful_predictor_count,
        },
        clock.now(), parent_message_id=ensemble_parent,
    )
    bus.send(ensemble_message)

    # --- abstain 硬规则 ---
    ab = evaluate_abstain(AbstainContext(
        species=msg.species,
        species_confident=bool(msg.species) and route.disposition != "abstain",
        genome_quality_ok=True,
        drug=drug,
        # 化合物落在训练化学空间外(sm_activity OOD)= 该"药"不在训练分布 → 弃权(不伪造 OOD 数字)
        drug_in_training_dist=bool(route.candidates) and not chem_ood,
        mechanism_conflict=False,
        n_mic_samples=(200 if ens.output_kind == "mic_scalar" else 999),
        # model_disagreement 语义=**模型间分歧**,仅多模型才有意义;单模型时 sir_class 的
        # 类别熵(预测不确定性)不是模型分歧,不得据此 abstain(否则越靠折点越被拦,反噬临床价值)。
        model_disagreement=((ens.disagreement.get("score") or 0.0)
                            if len(ens.models_used) > 1 else 0.0),
        combo_gate_status=("excluded" if route.disposition == "abstain" else "pass"),
    ))
    # 请求了活性(小分子/肽)但无对应成功结果(非 OOD 的 fail-closed:缺输入/缺 artifact/invalid/
    # predict 崩)→ 报告级诚实弃权,不返回"空但标称未弃权"的误导结果。仅作用于活性查询,
    # 不改既有 SIR/MIC 语义。OOD 已由 drug_in_training_dist 通道处理,故此处只补非 OOD 失败。
    # primary is None 守卫:混合查询里 SIR 成功、活性失败时,不因活性失败压掉成功的 SIR。
    _activity_requested = any(k in route.requested_kinds for k in ("sm_activity", "peptide_activity"))
    _activity_success = any(k in success_kinds for k in ("sm_activity", "peptide_activity"))
    activity_unresolved = (_activity_requested and not _activity_success
                           and primary is None
                           and activity_abstain_code is not None)
    # P0:声明式 route=accept/caution 只表示候选存在；若运行时没有任何成功预测器，
    # 核心报告必须硬弃权，不能让 API 的 prediction_available 充当展示层补丁。
    no_successful_predictor = successful_predictor_count == 0
    abstain = (ab.abstain or route.disposition == "abstain" or activity_unresolved
               or no_successful_predictor)
    abstain_reasons = list(ab.reasons)
    if route.reason == "no_ready_capability":
        # Route-level readiness failures happen before a predictor is allowed to
        # execute, so they otherwise would disappear behind the generic P0 reason.
        abstain_reasons.append("no_ready_capability")
        for item in route.unready_candidates:
            reason_code = item.get("reason_code")
            if reason_code and reason_code not in abstain_reasons:
                abstain_reasons.append(reason_code)
    if no_successful_predictor and "no_successful_predictor" not in abstain_reasons:
        abstain_reasons.append("no_successful_predictor")
    if no_successful_predictor:
        for reason_code in failed_reason_codes:
            if reason_code not in abstain_reasons:
                abstain_reasons.append(reason_code)
    if activity_unresolved:
        if activity_abstain_code not in abstain_reasons:
            abstain_reasons.append(activity_abstain_code)

    abstain_message = AgentMessage(
        idg.next(), "Reliability", "RuleFusion", "abstain_decided",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "abstained": abstain,
            "reasons": list(abstain_reasons),
            "successful_predictor_count": successful_predictor_count,
        },
        clock.now(), parent_message_id=ensemble_message.message_id,
    )
    bus.send(abstain_message)

    # --- B4 机制融合:化合物查询(sm_activity)且非弃权时跑 GEM/FBA 出机制段,与 activity 分栏 ---
    #     非化合物查询(SIR/MIC)/弃权/drug 为空 → 不加 mechanism(零污染、省 GEM 载入)。
    #     fuse_mech 可注入(测试不跑 cobra);fail-closed:融合抛异常也不崩管线,降级 mechanism=None。
    mechanism_requested = "sm_activity" in route.requested_kinds and bool(drug)
    mechanism_attempted = mechanism_requested and not abstain
    mechanism = None
    if mechanism_attempted:
        try:
            if fuse_mech is None:
                mechanism = _default_fuse_mechanism(
                    msg.species,
                    drug,
                    runtime_manifest=runtime_manifest,
                )
            else:
                mechanism = fuse_mech(msg.species, drug)
        except Exception:
            mechanism = None
    # 从机制结果派生 critic 输入:mechanism_claim 非 None=声称机制,g3_gate.status==passed=G3 过。
    # 让 critic 不变量#7(mechanism_claim_without_g3)对 B4 兜底(默认路径恒不触发,融合回归才抓)。
    mechanism_claimed = bool(mechanism and mechanism.get("mechanism_claim") is not None)
    g3_passed = bool(mechanism and (mechanism.get("g3_gate") or {}).get("status") == "passed")
    final_decision_parent_id = abstain_message.message_id
    if mechanism_requested:
        mechanism_payload = {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "attempted": mechanism_attempted,
            "available": bool(mechanism and mechanism.get("available")),
            "mechanism_claimed": mechanism_claimed,
            "g3_status": (mechanism or {}).get("g3_gate", {}).get("status"),
        }
        sidecar_contract = (mechanism or {}).get("sidecar_contract")
        if isinstance(sidecar_contract, dict):
            mechanism_payload["sidecar_contract"] = dict(sidecar_contract)
        mechanism_message = AgentMessage(
            idg.next(), "MechanismFusion", "RuleFusion", "mechanism_evaluated",
            mechanism_payload,
            clock.now(), parent_message_id=final_decision_parent_id,
        )
        bus.send(mechanism_message)
        final_decision_parent_id = mechanism_message.message_id

    # --- rule-first 融合 + 证据分层(G2R 落地;有意改 SIR:融合验证过 VME≤规则,确定性,
    #     rule=R 永不翻 S;仅非 abstain 的 sir_class 生效,fail-closed/abstain 路径不碰)---
    fusion_prov = None
    if not abstain and ens.output_kind == "sir_class" and ens.ensemble:
        from praxis_virtualcell.mdr_gnb.coordinator.fusion import fuse_sir
        from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR

        frozen_rule = RuleBaselineSIR(
            db_version="2024-01-frozen",
            rules_doc=governance_context.rule_document(),
        )
        fused = fuse_sir(
            {"output_kind": "sir_class", "abstained": False,
             "sir": ens.ensemble.get("sir"), "sir_prob": ens.ensemble.get("sir_prob")},
            species=msg.species, drug=drug, amr_profile=msg.amr_profile,
            tiers=governance_context.evidence_tiers,
            rule=frozen_rule,
            use_tuned_threshold=True)   # EC+KP 机制重训模型用 tuned t*(无 t_star 组合自动回退 0.5)
        ens.ensemble = {**ens.ensemble, "sir": fused["sir"]}   # 覆盖为融合 SIR
        fusion_prov = fused.get("fusion")

    final_sir = None
    if not abstain and ens.output_kind == "sir_class" and ens.ensemble:
        final_sir = ens.ensemble.get("sir")
    fusion_message = AgentMessage(
        idg.next(), "RuleFusion", "Critic", "rule_fusion_done",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "applied": fusion_prov is not None,
            "output_kind": ens.output_kind,
            "final_sir": final_sir,
            "fusion": fusion_prov,
        },
        clock.now(), parent_message_id=final_decision_parent_id,
    )
    bus.send(fusion_message)

    # --- critic 七不变量 ---
    # 关键顺序：critic 只能看到 rule-first 融合后的最终结论和实际 provenance，不能以
    # 空 conclusion_sir 或预融合 ML 值代替最终用户裁决。
    bp = brain_context.get("species_specific_breakpoints", {}) or {}
    bp_source = (bp.get(drug, {}) or {}).get("source", "EUCAST v14.0")
    conclusion_sir = ({drug: final_sir}
                      if drug and final_sir in {"S", "I", "R"} else {})
    critic_provenance = {
        "route": route.disposition,
        "route_reason": route.reason,
        "capability": capability_provenance,
        "governance_snapshot": governance_snapshot,
        "trace_schema_version": _TRACE_SCHEMA_VERSION,
        "critic_policy_version": _CRITIC_POLICY_VERSION,
        **({"fusion": fusion_prov} if fusion_prov else {}),
    }
    critic = check_invariants(CriticInput(
        trace_types=[m.message_type for m in bus.trace],
        abstain=abstain, reasons=abstain_reasons,
        models_used=ens.models_used,
        # Pass the pre-abstain ensemble to the critic too.  The report remains
        # abstained, but otherwise guard #3 could never detect a regressing
        # upstream stage that retained a prediction together with abstention.
        ensemble=ens.ensemble,
        rules_referenced=brain_context.get("rules_referenced", []),
        breakpoint_sources=({drug: bp_source} if not abstain else {}),
        request_breakpoint_version="EUCAST v14.0",
        genotype=msg.amr_profile, conclusion_sir=conclusion_sir,
        provenance=critic_provenance,
        mechanism_claimed=mechanism_claimed, g3_passed=g3_passed,
    ))
    critic_message = AgentMessage(
        idg.next(), "Critic", "ReportBuilder", "critic_checked",
        {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "policy_version": _CRITIC_POLICY_VERSION,
            "conclusion_sir": conclusion_sir,
            "violations": list(critic.violations),
            "notes": list(critic.notes),
            "provenance_sha256": _canonical_sha256(critic_provenance),
        },
        clock.now(), parent_message_id=fusion_message.message_id,
    )
    bus.send(critic_message)

    # --- 报告 ---
    downgrade = ([route.reason] if route.disposition == "downgrade" else [])
    report = build_report(
        task_id=msg.task_id, drug=drug,
        ensemble_result={"output_kind": ens.output_kind, "ensemble": ens.ensemble},
        abstain=abstain, abstain_reasons=abstain_reasons, downgrade_reasons=downgrade,
        caution_flags=route.caution_flags, breakpoint_source=bp_source,
        critic_violations=critic.violations,
        provenance=critic_provenance,
        mechanism=mechanism)
    report_sha256 = _canonical_sha256(report)
    # Keep the preliminary abstention gate distinct from the post-fusion,
    # post-critic report outcome.  The critic is deliberately record-only: it
    # audits the rule-first conclusion but does not silently rewrite it.  This
    # event binds both stages to the exact report hash before report_built
    # remains the final core event expected by the API adapter.
    final_decision_message = AgentMessage(
        idg.next(), "DecisionResolver", "ReportBuilder", "final_decision_resolved",
        {
            "schema_version": "mdr-final-decision-v1",
            "preliminary_abstained": abstain,
            "preliminary_abstain_reasons": list(abstain_reasons),
            "final_abstained": bool(report["abstained"]),
            "final_abstain_reasons": list(report["abstain_reasons"]),
            "final_output_kind": report["output_kind"],
            "final_sir": report["sir"],
            "critic_policy_version": _CRITIC_POLICY_VERSION,
            "critic_action": "record_only",
            "critic_violations": list(critic.violations),
            "report_sha256": report_sha256,
        },
        clock.now(), parent_message_id=critic_message.message_id,
    )
    bus.send(final_decision_message)
    bus.send(AgentMessage(
        idg.next(), "ReportBuilder", "API", "report_built",
        {
            "schema_version": "mdr-report-v1",
            "task_id": report["task_id"],
            "report_sha256": report_sha256,
            "abstained": report["abstained"],
            "output_kind": report["output_kind"],
        },
        clock.now(), parent_message_id=final_decision_message.message_id,
    ))

    return {
        "trace": bus.trace,
        "trace_metadata": {
            "schema_version": _TRACE_SCHEMA_VERSION,
            "input_sha256": parsed_message.payload["input_sha256"],
            "report_sha256": report_sha256,
            "critic_policy_version": _CRITIC_POLICY_VERSION,
            "governance_snapshot_digest": governance_snapshot["governance_digest"],
            "governance_snapshot": governance_snapshot,
            **(
                {"requested_model_integrity": runtime_model_preflight}
                if runtime_model_preflight
                else {}
            ),
        },
        "route": route.__dict__,
        "report": report,
        "disagreement": ens.disagreement,
    }
