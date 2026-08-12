"""v0.6:本地 job store —— 把一次 query 的 request/candidate/report/trace/provenance/narrative/llm 落盘。

runs/<job_id>/{request,candidate_request,report,trace,provenance,narrative_report,llm_meta}。
无数据库依赖(纯文件);API/CLI/web 共用。LLM 只存 hash 元数据,不存 key/原始 prompt 敏感内容。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from pathlib import Path

try:  # POSIX-only: direct reservation transitions need an inter-process lock.
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - exercised by the explicit runtime guard
    _fcntl = None

_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIRECT_V2_EXECUTION_CONTRACT = "vc.direct-v2-execution.v1"
_DIRECT_V2_TRACE_KEYS = {
    "schema_version",
    "message_id",
    "sender",
    "receiver",
    "message_type",
    "timestamp",
    "parent_message_id",
    "trace_id",
    "task_id",
    "payload_fingerprint",
}
_DIRECT_V2_TRACE_ROUTE = (
    ("client", "ModelBrokerAgent", "execution_plan_v2_request"),
    ("ModelBrokerAgent", "AgentRuntime", "execution_plan_ready"),
    ("AgentRuntime", "client", "execution_result_ready"),
)
_JSON_COMPANION_TYPES = {
    "report": dict,
    "trace": list,
    "provenance": dict,
    "execution_identity": dict,
    "candidate_request": dict,
    "request": dict,
    "llm_meta": dict,
}


def _canonical_fingerprint(value: dict) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_direct_v2_public_trace(trace: object) -> bool:
    """Accept only the payload-free, three-message direct-v2 hash spine."""

    if not isinstance(trace, list) or len(trace) != len(_DIRECT_V2_TRACE_ROUTE):
        return False
    message_ids: list[str] = []
    trace_id = None
    task_id = None
    for index, (item, expected_route) in enumerate(zip(trace, _DIRECT_V2_TRACE_ROUTE, strict=True)):
        if not isinstance(item, dict) or set(item) != _DIRECT_V2_TRACE_KEYS:
            return False
        if item.get("schema_version") != "vc.msg.v1":
            return False
        if (item.get("sender"), item.get("receiver"), item.get("message_type")) != (expected_route):
            return False
        text_fields = (
            "message_id",
            "sender",
            "receiver",
            "message_type",
            "timestamp",
            "trace_id",
            "task_id",
        )
        if not all(
            isinstance(item.get(field), str) and bool(item[field]) and item[field].strip() == item[field]
            for field in text_fields
        ):
            return False
        if not isinstance(item.get("payload_fingerprint"), str) or (
            _SHA256.fullmatch(item["payload_fingerprint"]) is None
        ):
            return False
        if index == 0:
            if item.get("parent_message_id") is not None:
                return False
            trace_id = item["trace_id"]
            task_id = item["task_id"]
        elif item.get("parent_message_id") != message_ids[-1]:
            return False
        if item["trace_id"] != trace_id or item["task_id"] != task_id:
            return False
        message_ids.append(item["message_id"])
    return len(message_ids) == len(set(message_ids))


def _validate_direct_domain_identity(provenance: dict, *, taxonomy_id: str) -> None:
    """Bind an optional public domain identity to the submitted V2 request."""

    raw_identity = provenance.get("domain_extension_identity")
    if raw_identity is None:
        return
    from praxis_virtualcell.core.domain_extension import DomainExtensionIdentityV1

    try:
        identity = DomainExtensionIdentityV1.from_dict(raw_identity)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("direct execution domain extension identity is invalid") from exc
    if identity.taxonomy_id != taxonomy_id:
        raise ValueError("direct execution domain extension identity taxon does not match submitted request")


def _direct_v2_execution_identity(
    result: dict,
    *,
    request: dict,
    plan,
    pack: dict | None,
) -> dict:
    """Build the write-new v4 identity without widening v1–v3 semantics."""

    from praxis_virtualcell.core.request_v2 import require_v2_request
    from praxis_virtualcell.data_packs.registry import (
        pack_view_receipt_from_dict,
        validate_selected_content_receipt_binding,
    )
    from praxis_virtualcell.model_zoo.adapter_sdk import (
        AdapterInputReceiptV2,
        adapter_input_receipt_from_dict,
    )
    from praxis_virtualcell.model_zoo.registry_v2 import public_model_version
    from praxis_virtualcell.pack_product import _public_provenance

    if not isinstance(request, dict) or request.get("schema_version") != "vc.request.v2":
        raise ValueError("direct-v2 execution identity requires an exact v2 request")
    normalized_request = require_v2_request(request)
    submitted_request_fingerprint = _canonical_fingerprint(request)
    if _canonical_fingerprint(normalized_request.to_dict()) != plan.request_fingerprint:
        raise ValueError("submitted request does not match direct-v2 execution plan")

    provenance = result.get("provenance")
    structured_report = result.get("structured_report")
    if not isinstance(provenance, dict) or not isinstance(structured_report, dict):
        raise ValueError("direct-v2 execution identity requires report and provenance")
    if provenance.get("execution_contract") != _DIRECT_V2_EXECUTION_CONTRACT:
        raise ValueError("direct-v2 execution contract marker is missing")
    if "virtual_experiment" in provenance:
        raise ValueError("direct-v2 execution cannot carry a virtual experiment")
    _validate_direct_domain_identity(
        provenance,
        taxonomy_id=normalized_request.species.taxonomy_id,
    )
    if _public_provenance(provenance).get("available") is False:
        raise ValueError("direct-v2 provenance contains unsupported fields")
    if structured_report.get("provenance") != provenance:
        raise ValueError("direct-v2 report and provenance differ")
    if structured_report.get("request_id") != plan.request_id or (
        structured_report.get("request_fingerprint") != plan.request_fingerprint
    ):
        raise ValueError("direct-v2 structured report does not match execution plan")

    report_keys = {
        "request_id",
        "request_fingerprint",
        "execution_status",
        "execution_scope",
        "scientifically_validated",
        "prediction",
        "models_used",
        "models_rejected",
        "models_failed",
        "abstain",
        "abstain_reasons",
        "reliability",
        "runtime_confidence",
        "provenance",
    }
    if set(structured_report) != report_keys:
        raise ValueError("direct-v2 structured report is inconsistent")
    if structured_report["execution_status"] not in {"completed", "abstained"}:
        raise ValueError("direct-v2 execution status is invalid")
    if structured_report["execution_scope"] not in {
        None,
        "production",
        "research_only",
    }:
        raise ValueError("direct-v2 execution scope is invalid")
    if not isinstance(structured_report["scientifically_validated"], bool) or not isinstance(
        structured_report["abstain"], bool
    ):
        raise ValueError("direct-v2 result state must be boolean")
    if not isinstance(structured_report["reliability"], str) or not isinstance(
        structured_report["runtime_confidence"], str
    ):
        raise ValueError("direct-v2 result reliability must be text")

    list_fields = (
        "models_used",
        "models_rejected",
        "models_failed",
        "abstain_reasons",
    )
    for field in list_fields:
        value = structured_report[field]
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) or not item or item.strip() != item for item in value)
            or len(value) != len(set(value))
        ):
            raise ValueError(f"direct-v2 {field} must be a unique text array")

    report_by_name = {report.model_name: report for report in plan.reports}
    step_by_name = {step.model_name: step for step in plan.steps}
    if len(report_by_name) != len(plan.reports) or len(step_by_name) != len(plan.steps):
        raise ValueError("direct-v2 execution plan has duplicate model names")
    models_used = structured_report["models_used"]
    models_rejected = structured_report["models_rejected"]
    models_failed = structured_report["models_failed"]
    if not set(models_used).issubset(step_by_name) or not (set(models_rejected) | set(models_failed)).issubset(
        report_by_name
    ):
        raise ValueError("direct-v2 result names are outside the execution plan")
    if len(set(models_used) | set(models_rejected) | set(models_failed)) != (
        len(models_used) + len(models_rejected) + len(models_failed)
    ):
        raise ValueError("direct-v2 result model states overlap")

    abstain = structured_report["abstain"]
    prediction = structured_report["prediction"]
    if abstain:
        if not (
            structured_report["execution_status"] == "abstained"
            and structured_report["execution_scope"] is None
            and prediction is None
            and models_used == []
            and structured_report["scientifically_validated"] is False
        ):
            raise ValueError("direct-v2 abstention semantics are inconsistent")
    elif not (
        structured_report["execution_status"] == "completed"
        and isinstance(prediction, dict)
        and len(models_used) == 1
        and not models_rejected
        and not models_failed
    ):
        raise ValueError("direct-v2 completed result semantics are inconsistent")

    used_reports = [report_by_name[name] for name in models_used]
    if used_reports:
        expected_scope = (
            "research_only"
            if all(report.research_execution_authorized is True for report in used_reports)
            else "production"
        )
        expected_scientific = all(report.scientifically_validated is True for report in used_reports)
        if structured_report["execution_scope"] != expected_scope or (
            structured_report["scientifically_validated"] != expected_scientific
        ):
            raise ValueError("direct-v2 result scope does not match policy state")
        if expected_scope == "production" and not all(report.production_promoted for report in used_reports):
            raise ValueError("direct-v2 production result lacks promotion")
    elif structured_report["execution_scope"] is not None:
        raise ValueError("direct-v2 abstention cannot claim an execution scope")

    receipts = provenance.get("adapter_input_receipts")
    per_call_hashes = provenance.get("per_call_hashes")
    if not isinstance(receipts, dict) or not isinstance(per_call_hashes, dict):
        raise ValueError("direct-v2 adapter provenance is missing")
    if set(receipts) != set(step_by_name) or not set(per_call_hashes).issubset(step_by_name):
        raise ValueError("direct-v2 adapter provenance does not match plan steps")
    raw_pack_view_receipt = provenance.get("pack_view_receipt")
    if plan.steps:
        try:
            pack_view_receipt = pack_view_receipt_from_dict(raw_pack_view_receipt)
        except Exception as exc:  # noqa: BLE001 - persisted Pack view is a hard replay gate
            raise ValueError("direct-v2 Pack view receipt is invalid") from exc
        if not (
            pack_view_receipt.pack_id == plan.pack_id
            and pack_view_receipt.pack_version == plan.pack_version
            and pack_view_receipt.pack_fingerprint == plan.pack_fingerprint
        ):
            raise ValueError("direct-v2 Pack view receipt does not match execution plan")
    elif raw_pack_view_receipt is not None:
        try:
            pack_view_receipt_from_dict(raw_pack_view_receipt)
        except Exception as exc:  # noqa: BLE001 - public receipt must always be canonical
            raise ValueError("direct-v2 Pack view receipt is invalid") from exc
    for model_name, raw_receipt in receipts.items():
        receipt = adapter_input_receipt_from_dict(raw_receipt)
        step = step_by_name[model_name]
        if not (
            receipt.request_fingerprint == plan.request_fingerprint
            and receipt.pack_fingerprint == plan.pack_fingerprint
            and receipt.compatibility_fingerprint == step.compatibility_fingerprint
            and receipt.adapter_fingerprint in step.adapter_fingerprints
            and len(step.adapter_fingerprints) == 1
        ):
            raise ValueError("direct-v2 adapter receipt does not match execution step")
        if isinstance(receipt, AdapterInputReceiptV2):
            selected = receipt.selected_content_receipt
            if not (
                pack_view_receipt is not None
                and selected.request_fingerprint == plan.request_fingerprint
                and selected.pack_id == plan.pack_id
                and selected.pack_version == plan.pack_version
                and selected.pack_fingerprint == plan.pack_fingerprint
                and selected.pack_view_receipt_fingerprint == pack_view_receipt.fingerprint()
                and selected.model_id == step.model_name
                and selected.model_version == step.model_version
                and validate_selected_content_receipt_binding(
                    selected,
                    pack_view_receipt,
                )
                and selected.feature_contract_fingerprint == receipt.feature_contract_fingerprint
                and selected.alignment_fingerprint == receipt.alignment_fingerprint
                and selected.unit == receipt.unit
            ):
                raise ValueError("direct-v2 selected-content receipt does not match execution")
    for model_name, raw_call in per_call_hashes.items():
        step = step_by_name[model_name]
        if not isinstance(raw_call, dict) or set(raw_call) != {
            "model_name",
            "model_version",
            "input_hash",
            "output_hash",
        }:
            raise ValueError("direct-v2 per-call hash has an invalid shape")
        if not (
            raw_call["model_name"] == model_name
            and raw_call["model_version"] == step.model_version
            and raw_call["input_hash"]
            == adapter_input_receipt_from_dict(receipts[model_name]).prepared_input_fingerprint
            and isinstance(raw_call["output_hash"], str)
            and _SHA256.fullmatch(raw_call["output_hash"]) is not None
        ):
            raise ValueError("direct-v2 per-call hash does not match execution step")
    if models_used:
        model_name = models_used[0]
        if model_name not in per_call_hashes or (
            per_call_hashes[model_name]["output_hash"] != _canonical_fingerprint(prediction)
        ):
            raise ValueError("direct-v2 prediction does not match per-call output hash")

    trace = result.get("trace")
    if not _valid_direct_v2_public_trace(trace):
        raise ValueError("direct-v2 public trace is invalid")
    public_provenance = _public_provenance(provenance)
    public_report = json.loads(json.dumps(structured_report))
    public_report["provenance"] = public_provenance
    return {
        "schema_version": "vc.job-execution-identity.v4",
        "execution_contract": _DIRECT_V2_EXECUTION_CONTRACT,
        "legacy_adapter": False,
        "plan_id": plan.plan_id,
        "submitted_request_fingerprint": submitted_request_fingerprint,
        "request_fingerprint": plan.request_fingerprint,
        "pack": pack,
        "environment_snapshot_fingerprint": plan.environment_snapshot_fingerprint,
        "execution_step_fingerprints": [step.fingerprint() for step in plan.steps],
        "structured_report_fingerprint": _canonical_fingerprint(public_report),
        "public_trace_fingerprint": _canonical_fingerprint(trace),
        "execution_status": structured_report["execution_status"],
        "execution_scope": structured_report["execution_scope"],
        "scientifically_validated": structured_report["scientifically_validated"],
        "outcome": {
            "abstain": abstain,
            "models_used": models_used,
            "prediction_present": prediction is not None,
        },
        "models": [
            {
                "name": report.model_name,
                "version": public_model_version(report.model_version),
                "fingerprint": report.model_fingerprint,
                "release_fingerprint": report.release_fingerprint,
                "capability_fingerprint": report.capability_fingerprint,
                "artifact_fingerprints": list(report.artifact_fingerprints),
                "environment_fingerprint": report.environment_fingerprint,
                "adapter_fingerprints": list(report.adapter_fingerprints),
                "evidence_fingerprints": list(report.evidence_fingerprints),
                "policy_fingerprint": report.policy_fingerprint,
                "compatibility_fingerprint": report.fingerprint(),
                "cataloged": report.cataloged,
                "artifact_ready": report.artifact_ready,
                "revoked": report.revoked,
                "superseded_by": report.superseded_by,
                "benchmark_passed": report.benchmark_passed,
                "scientifically_validated": report.scientifically_validated,
                "promotion_eligible": report.promotion_eligible,
                "policy_present": report.policy_present,
                "production_promoted": report.production_promoted,
                "research_execution_authorized": (report.research_execution_authorized),
                "research_execution_scope": report.research_execution_scope,
                "executable": report.executable,
            }
            for report in plan.reports
        ],
    }


def _direct_v3_execution_identity(
    result: dict,
    *,
    request: dict,
    plan,
    pack: dict | None,
) -> dict:
    """Build the write-new v5 identity for a reducer-bound V3 direct execution.

    V4 remains the U1 single-model contract.  V5 deliberately binds every
    ordered V3 step and the public reducer receipt instead of widening V4's
    one-model completion rules.
    """

    from praxis_virtualcell.core.request_v2 import require_v2_request
    from praxis_virtualcell.data_packs.registry import (
        pack_view_receipt_from_dict,
        validate_selected_content_receipt_binding,
    )
    from praxis_virtualcell.model_zoo.adapter_sdk import (
        AdapterInputReceiptV2,
        adapter_input_receipt_from_dict,
    )
    from praxis_virtualcell.model_zoo.post_result_policy import OutputReducerReceiptV1
    from praxis_virtualcell.model_zoo.registry_v2 import public_model_version
    from praxis_virtualcell.pack_product import _public_provenance

    if not isinstance(request, dict) or request.get("schema_version") != "vc.request.v2":
        raise ValueError("direct-v3 execution identity requires an exact v2 request")
    normalized_request = require_v2_request(request)
    submitted_request_fingerprint = _canonical_fingerprint(request)
    if _canonical_fingerprint(normalized_request.to_dict()) != plan.request_fingerprint:
        raise ValueError("submitted request does not match direct-v3 execution plan")

    provenance = result.get("provenance")
    structured_report = result.get("structured_report")
    if not isinstance(provenance, dict) or not isinstance(structured_report, dict):
        raise ValueError("direct-v3 execution identity requires report and provenance")
    if provenance.get("execution_contract") != _DIRECT_V2_EXECUTION_CONTRACT:
        raise ValueError("direct-v3 execution contract marker is missing")
    if "virtual_experiment" in provenance:
        raise ValueError("direct-v3 execution cannot carry a virtual experiment")
    _validate_direct_domain_identity(
        provenance,
        taxonomy_id=normalized_request.species.taxonomy_id,
    )
    if _public_provenance(provenance).get("available") is False:
        raise ValueError("direct-v3 provenance contains unsupported fields")
    if structured_report.get("provenance") != provenance:
        raise ValueError("direct-v3 report and provenance differ")
    if structured_report.get("request_id") != plan.request_id or (
        structured_report.get("request_fingerprint") != plan.request_fingerprint
    ):
        raise ValueError("direct-v3 structured report does not match execution plan")

    report_keys = {
        "request_id",
        "request_fingerprint",
        "execution_status",
        "execution_scope",
        "scientifically_validated",
        "prediction",
        "models_used",
        "models_rejected",
        "models_failed",
        "abstain",
        "abstain_reasons",
        "reliability",
        "runtime_confidence",
        "provenance",
    }
    if set(structured_report) != report_keys:
        raise ValueError("direct-v3 structured report is inconsistent")
    if structured_report["execution_status"] not in {"completed", "abstained"}:
        raise ValueError("direct-v3 execution status is invalid")
    if structured_report["execution_scope"] not in {None, "production", "research_only"}:
        raise ValueError("direct-v3 execution scope is invalid")
    if not isinstance(structured_report["scientifically_validated"], bool) or not isinstance(
        structured_report["abstain"], bool
    ):
        raise ValueError("direct-v3 result state must be boolean")
    if not isinstance(structured_report["reliability"], str) or not isinstance(
        structured_report["runtime_confidence"], str
    ):
        raise ValueError("direct-v3 result reliability must be text")

    list_fields = (
        "models_used",
        "models_rejected",
        "models_failed",
        "abstain_reasons",
    )
    for field in list_fields:
        value = structured_report[field]
        if (
            not isinstance(value, list)
            or any(not isinstance(item, str) or not item or item.strip() != item for item in value)
            or len(value) != len(set(value))
        ):
            raise ValueError(f"direct-v3 {field} must be a unique text array")

    report_by_name = {report.model_name: report for report in plan.reports}
    step_by_name = {step.model_name: step for step in plan.steps}
    if len(report_by_name) != len(plan.reports) or len(step_by_name) != len(plan.steps):
        raise ValueError("direct-v3 execution plan has duplicate model names")
    step_names = tuple(step.model_name for step in plan.steps)
    models_used = structured_report["models_used"]
    models_rejected = structured_report["models_rejected"]
    models_failed = structured_report["models_failed"]
    if not set(models_used).issubset(step_by_name) or not (set(models_rejected) | set(models_failed)).issubset(
        report_by_name
    ):
        raise ValueError("direct-v3 result names are outside the execution plan")
    if len(set(models_used) | set(models_rejected) | set(models_failed)) != (
        len(models_used) + len(models_rejected) + len(models_failed)
    ):
        raise ValueError("direct-v3 result model states overlap")

    abstain = structured_report["abstain"]
    prediction = structured_report["prediction"]
    if abstain:
        if not (
            structured_report["execution_status"] == "abstained"
            and structured_report["execution_scope"] is None
            and prediction is None
            and models_used == []
            and structured_report["scientifically_validated"] is False
        ):
            raise ValueError("direct-v3 abstention semantics are inconsistent")
        if "output_reducer_receipt" in provenance:
            raise ValueError("direct-v3 abstention must not carry an output reducer receipt")
    elif not (
        structured_report["execution_status"] == "completed"
        and isinstance(prediction, dict)
        and models_used == list(step_names)
        and not models_rejected
        and not models_failed
    ):
        raise ValueError("direct-v3 completed result semantics are inconsistent")

    used_reports = [report_by_name[name] for name in models_used]
    if used_reports:
        expected_scope = (
            "research_only"
            if any(report.research_execution_authorized is True for report in used_reports)
            else "production"
        )
        expected_scientific = all(report.scientifically_validated is True for report in used_reports)
        if structured_report["execution_scope"] != expected_scope or (
            structured_report["scientifically_validated"] != expected_scientific
        ):
            raise ValueError("direct-v3 result scope does not match policy state")
        if expected_scope == "production" and not all(report.production_promoted for report in used_reports):
            raise ValueError("direct-v3 production result lacks promotion")
    elif structured_report["execution_scope"] is not None:
        raise ValueError("direct-v3 abstention cannot claim an execution scope")

    receipts = provenance.get("adapter_input_receipts")
    per_call_hashes = provenance.get("per_call_hashes")
    if not isinstance(receipts, dict) or not isinstance(per_call_hashes, dict):
        raise ValueError("direct-v3 adapter provenance is missing")
    if set(receipts) != set(step_by_name) or not set(per_call_hashes).issubset(step_by_name):
        raise ValueError("direct-v3 adapter provenance does not match plan steps")
    raw_pack_view_receipt = provenance.get("pack_view_receipt")
    pack_view_receipt = None
    if plan.steps:
        try:
            pack_view_receipt = pack_view_receipt_from_dict(raw_pack_view_receipt)
        except Exception as exc:  # noqa: BLE001 - persisted Pack view is a hard replay gate
            raise ValueError("direct-v3 Pack view receipt is invalid") from exc
        if not (
            pack_view_receipt.pack_id == plan.pack_id
            and pack_view_receipt.pack_version == plan.pack_version
            and pack_view_receipt.pack_fingerprint == plan.pack_fingerprint
        ):
            raise ValueError("direct-v3 Pack view receipt does not match execution plan")
    elif raw_pack_view_receipt is not None:
        try:
            pack_view_receipt_from_dict(raw_pack_view_receipt)
        except Exception as exc:  # noqa: BLE001 - public receipt must always be canonical
            raise ValueError("direct-v3 Pack view receipt is invalid") from exc
    for model_name, raw_receipt in receipts.items():
        receipt = adapter_input_receipt_from_dict(raw_receipt)
        step = step_by_name[model_name]
        if not (
            receipt.request_fingerprint == plan.request_fingerprint
            and receipt.pack_fingerprint == plan.pack_fingerprint
            and receipt.compatibility_fingerprint == step.compatibility_fingerprint
            and receipt.adapter_fingerprint in step.adapter_fingerprints
            and len(step.adapter_fingerprints) == 1
        ):
            raise ValueError("direct-v3 adapter receipt does not match execution step")
        if isinstance(receipt, AdapterInputReceiptV2):
            selected = receipt.selected_content_receipt
            if not (
                pack_view_receipt is not None
                and selected.request_fingerprint == plan.request_fingerprint
                and selected.pack_id == plan.pack_id
                and selected.pack_version == plan.pack_version
                and selected.pack_fingerprint == plan.pack_fingerprint
                and selected.pack_view_receipt_fingerprint == pack_view_receipt.fingerprint()
                and selected.model_id == step.model_name
                and selected.model_version == step.model_version
                and validate_selected_content_receipt_binding(selected, pack_view_receipt)
                and selected.feature_contract_fingerprint == receipt.feature_contract_fingerprint
                and selected.alignment_fingerprint == receipt.alignment_fingerprint
                and selected.unit == receipt.unit
            ):
                raise ValueError("direct-v3 selected-content receipt does not match execution")
    for model_name, raw_call in per_call_hashes.items():
        step = step_by_name[model_name]
        if not isinstance(raw_call, dict) or set(raw_call) != {
            "model_name",
            "model_version",
            "input_hash",
            "output_hash",
        }:
            raise ValueError("direct-v3 per-call hash has an invalid shape")
        if not (
            raw_call["model_name"] == model_name
            and raw_call["model_version"] == step.model_version
            and raw_call["input_hash"]
            == adapter_input_receipt_from_dict(receipts[model_name]).prepared_input_fingerprint
            and isinstance(raw_call["output_hash"], str)
            and _SHA256.fullmatch(raw_call["output_hash"]) is not None
        ):
            raise ValueError("direct-v3 per-call hash does not match execution step")

    reducer_receipt = None
    if not abstain:
        if set(per_call_hashes) != set(step_by_name):
            raise ValueError("direct-v3 completed result requires every per-call hash")
        try:
            reducer_receipt = OutputReducerReceiptV1.from_dict(provenance.get("output_reducer_receipt"))
        except Exception as exc:  # noqa: BLE001 - persisted receipt is a hard replay gate
            raise ValueError("direct-v3 output reducer receipt is invalid") from exc
        if reducer_receipt.output_reducer.to_dict() != plan.output_reducer.to_dict():
            raise ValueError("direct-v3 output reducer receipt does not match execution plan")
        if tuple(item.model_name for item in reducer_receipt.step_receipts) != step_names:
            raise ValueError("direct-v3 output reducer receipt order does not match execution plan")
        for reducer_step, step in zip(reducer_receipt.step_receipts, plan.steps, strict=True):
            expected_receipt = adapter_input_receipt_from_dict(receipts[step.model_name])
            expected_call = per_call_hashes[step.model_name]
            if not (
                reducer_step.execution_step_fingerprint == step.fingerprint()
                and reducer_step.input_hash == expected_receipt.prepared_input_fingerprint
                and reducer_step.output_hash == expected_call["output_hash"]
            ):
                raise ValueError("direct-v3 output reducer receipt does not match a step")
        if reducer_receipt.reduced_output_hash != _canonical_fingerprint(prediction):
            raise ValueError("direct-v3 prediction does not match reduced output hash")

    trace = result.get("trace")
    if not _valid_direct_v2_public_trace(trace):
        raise ValueError("direct-v3 public trace is invalid")
    public_provenance = _public_provenance(provenance)
    public_report = json.loads(json.dumps(structured_report))
    public_report["provenance"] = public_provenance
    return {
        "schema_version": "vc.job-execution-identity.v5",
        "execution_contract": _DIRECT_V2_EXECUTION_CONTRACT,
        "legacy_adapter": False,
        "plan_id": plan.plan_id,
        "plan_schema_version": "vc.execution-plan.v3",
        "submitted_request_fingerprint": submitted_request_fingerprint,
        "request_fingerprint": plan.request_fingerprint,
        "pack": pack,
        "environment_snapshot_fingerprint": plan.environment_snapshot_fingerprint,
        "execution_step_fingerprints": [step.fingerprint() for step in plan.steps],
        "execution_step_model_names": list(step_names),
        "output_reducer": plan.output_reducer.to_dict(),
        "output_reducer_receipt_fingerprint": (None if reducer_receipt is None else reducer_receipt.fingerprint()),
        "structured_report_fingerprint": _canonical_fingerprint(public_report),
        "public_trace_fingerprint": _canonical_fingerprint(trace),
        "execution_status": structured_report["execution_status"],
        "execution_scope": structured_report["execution_scope"],
        "scientifically_validated": structured_report["scientifically_validated"],
        "outcome": {
            "abstain": abstain,
            "models_used": models_used,
            "prediction_present": prediction is not None,
        },
        "models": [
            {
                "name": report.model_name,
                "version": public_model_version(report.model_version),
                "fingerprint": report.model_fingerprint,
                "release_fingerprint": report.release_fingerprint,
                "capability_fingerprint": report.capability_fingerprint,
                "artifact_fingerprints": list(report.artifact_fingerprints),
                "environment_fingerprint": report.environment_fingerprint,
                "adapter_fingerprints": list(report.adapter_fingerprints),
                "evidence_fingerprints": list(report.evidence_fingerprints),
                "policy_fingerprint": report.policy_fingerprint,
                "compatibility_fingerprint": report.fingerprint(),
                "cataloged": report.cataloged,
                "artifact_ready": report.artifact_ready,
                "revoked": report.revoked,
                "superseded_by": report.superseded_by,
                "benchmark_passed": report.benchmark_passed,
                "scientifically_validated": report.scientifically_validated,
                "promotion_eligible": report.promotion_eligible,
                "policy_present": report.policy_present,
                "production_promoted": report.production_promoted,
                "research_execution_authorized": (report.research_execution_authorized),
                "research_execution_scope": report.research_execution_scope,
                "executable": report.executable,
            }
            for report in plan.reports
        ],
    }


def _valid_execution_identity(value: dict) -> bool:
    """Validate stored identity bytes before projecting them to public fields."""

    def text(item) -> bool:
        return isinstance(item, str) and bool(item) and item.strip() == item

    def fingerprint(item) -> bool:
        return isinstance(item, str) and _SHA256.fullmatch(item) is not None

    def optional_fingerprint(item) -> bool:
        return item is None or fingerprint(item)

    def fingerprints(items) -> bool:
        return isinstance(items, list) and all(fingerprint(item) for item in items) and len(items) == len(set(items))

    def pack(item) -> bool:
        return item is None or (
            isinstance(item, dict)
            and set(item) == {"pack_id", "pack_version", "fingerprint"}
            and text(item["pack_id"])
            and text(item["pack_version"])
            and fingerprint(item["fingerprint"])
        )

    schema = value.get("schema_version")
    if schema not in {
        "vc.job-execution-identity.v1",
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
        "vc.job-execution-identity.v4",
        "vc.job-execution-identity.v5",
    }:
        return False
    common_keys = {
        "schema_version",
        "legacy_adapter",
        "pack",
        "models",
        "fingerprint",
    }
    expected_keys = common_keys
    if schema in {
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
    }:
        expected_keys = common_keys | {
            "plan_id",
            "submitted_request_fingerprint",
            "request_fingerprint",
            "environment_snapshot_fingerprint",
            "execution_step_fingerprints",
            "structured_report_fingerprint",
            "outcome",
        }
        if schema == "vc.job-execution-identity.v3":
            expected_keys |= {"brain_fingerprint", "dag_fingerprint"}
    elif schema == "vc.job-execution-identity.v4":
        expected_keys = common_keys | {
            "execution_contract",
            "plan_id",
            "submitted_request_fingerprint",
            "request_fingerprint",
            "environment_snapshot_fingerprint",
            "execution_step_fingerprints",
            "structured_report_fingerprint",
            "public_trace_fingerprint",
            "execution_status",
            "execution_scope",
            "scientifically_validated",
            "outcome",
        }
    elif schema == "vc.job-execution-identity.v5":
        expected_keys = common_keys | {
            "execution_contract",
            "plan_id",
            "plan_schema_version",
            "submitted_request_fingerprint",
            "request_fingerprint",
            "environment_snapshot_fingerprint",
            "execution_step_fingerprints",
            "execution_step_model_names",
            "output_reducer",
            "output_reducer_receipt_fingerprint",
            "structured_report_fingerprint",
            "public_trace_fingerprint",
            "execution_status",
            "execution_scope",
            "scientifically_validated",
            "outcome",
        }
    if set(value) != expected_keys:
        return False

    stored_fingerprint = value["fingerprint"]
    unsigned = dict(value)
    unsigned.pop("fingerprint")
    try:
        signature_valid = fingerprint(stored_fingerprint) and (_canonical_fingerprint(unsigned) == stored_fingerprint)
    except (TypeError, ValueError, OverflowError):
        return False
    if not signature_valid or not isinstance(value["legacy_adapter"], bool):
        return False
    if not pack(value["pack"]) or not isinstance(value["models"], list):
        return False

    v1_model_keys = {
        "name",
        "version",
        "fingerprint",
        "compatibility_fingerprint",
        "executable",
    }
    v2_model_keys = v1_model_keys | {
        "release_fingerprint",
        "capability_fingerprint",
        "artifact_fingerprints",
        "environment_fingerprint",
        "adapter_fingerprints",
        "evidence_fingerprints",
        "policy_fingerprint",
        "cataloged",
        "artifact_ready",
        "revoked",
        "superseded_by",
        "benchmark_passed",
        "scientifically_validated",
        "promotion_eligible",
        "policy_present",
        "production_promoted",
    }
    v4_model_keys = v2_model_keys | {
        "research_execution_authorized",
        "research_execution_scope",
    }
    for model in value["models"]:
        expected_model_keys = (
            v1_model_keys
            if schema == "vc.job-execution-identity.v1"
            else v4_model_keys
            if schema
            in {
                "vc.job-execution-identity.v4",
                "vc.job-execution-identity.v5",
            }
            else v2_model_keys
        )
        if not isinstance(model, dict) or set(model) != expected_model_keys:
            return False
        if not (
            text(model["name"])
            and (
                text(model["version"])
                if schema.endswith(".v1")
                else (model["version"] is None or text(model["version"]))
            )
            and fingerprint(model["fingerprint"])
            and fingerprint(model["compatibility_fingerprint"])
            and isinstance(model["executable"], bool)
        ):
            return False
        if schema.endswith(".v1"):
            continue
        if not (
            optional_fingerprint(model["release_fingerprint"])
            and optional_fingerprint(model["capability_fingerprint"])
            and fingerprints(model["artifact_fingerprints"])
            and optional_fingerprint(model["environment_fingerprint"])
            and fingerprints(model["adapter_fingerprints"])
            and fingerprints(model["evidence_fingerprints"])
            and optional_fingerprint(model["policy_fingerprint"])
            and optional_fingerprint(model["superseded_by"])
            and all(
                isinstance(model[name], bool)
                for name in (
                    "cataloged",
                    "artifact_ready",
                    "revoked",
                    "policy_present",
                    "production_promoted",
                )
            )
            and all(
                model[name] is None or isinstance(model[name], bool)
                for name in (
                    "benchmark_passed",
                    "scientifically_validated",
                    "promotion_eligible",
                )
            )
        ):
            return False
        release_fields = (
            model["release_fingerprint"],
            model["capability_fingerprint"],
        )
        release_present = all(item is not None for item in release_fields)
        if any(item is not None for item in release_fields) != release_present:
            return False
        if not release_present and (
            model["environment_fingerprint"] is not None
            or model["artifact_fingerprints"]
            or model["adapter_fingerprints"]
            or model["evidence_fingerprints"]
            or model["policy_fingerprint"] is not None
            or model["cataloged"]
            or model["artifact_ready"]
            or model["revoked"]
            or model["superseded_by"] is not None
        ):
            return False
        evidence = (
            model["benchmark_passed"],
            model["scientifically_validated"],
            model["promotion_eligible"],
        )
        if any(item is None for item in evidence) != all(item is None for item in evidence):
            return False
        if model["scientifically_validated"] and not model["benchmark_passed"]:
            return False
        if model["promotion_eligible"] and not (model["benchmark_passed"] and model["scientifically_validated"]):
            return False
        if model["policy_present"] != (model["policy_fingerprint"] is not None):
            return False
        if model["production_promoted"] and not model["policy_present"]:
            return False
        if model["production_promoted"] and not (
            model["evidence_fingerprints"]
            and model["benchmark_passed"] is True
            and model["scientifically_validated"] is True
            and model["promotion_eligible"] is True
        ):
            return False
        if schema in {
            "vc.job-execution-identity.v4",
            "vc.job-execution-identity.v5",
        }:
            research_authorized = model["research_execution_authorized"]
            research_scope = model["research_execution_scope"]
            if not (research_authorized is None or isinstance(research_authorized, bool)):
                return False
            if research_scope not in {None, "research_only"}:
                return False
            if research_authorized is None and research_scope is not None:
                return False
            if research_authorized is not None and (research_authorized != (research_scope == "research_only")):
                return False
            if research_authorized and (not model["policy_present"] or model["production_promoted"]):
                return False
        if model["executable"] and not (
            release_present
            and model["version"] is not None
            and model["artifact_fingerprints"]
            and model["environment_fingerprint"] is not None
            and model["adapter_fingerprints"]
            and model["evidence_fingerprints"]
            and model["cataloged"]
            and model["artifact_ready"]
            and not model["revoked"]
            and model["superseded_by"] is None
            and model["policy_present"]
            and (
                (all(evidence) and model["production_promoted"])
                if schema
                not in {
                    "vc.job-execution-identity.v4",
                    "vc.job-execution-identity.v5",
                }
                else (
                    (all(evidence) and model["production_promoted"])
                    or (
                        model["research_execution_authorized"] is True
                        and model["research_execution_scope"] == "research_only"
                    )
                )
            )
        ):
            return False

    if schema == "vc.job-execution-identity.v1":
        return not value["legacy_adapter"] or (value["pack"] is None and value["models"] == [])

    if value["legacy_adapter"] or not re.fullmatch(r"plan_[0-9a-f]{24}", value["plan_id"]):
        return False
    if not (
        fingerprint(value["submitted_request_fingerprint"])
        and fingerprint(value["request_fingerprint"])
        and fingerprint(value["environment_snapshot_fingerprint"])
        and fingerprints(value["execution_step_fingerprints"])
        and fingerprint(value["structured_report_fingerprint"])
    ):
        return False
    if schema == "vc.job-execution-identity.v3" and not (
        fingerprint(value["brain_fingerprint"]) and fingerprint(value["dag_fingerprint"])
    ):
        return False
    if schema == "vc.job-execution-identity.v4" and not (
        value["execution_contract"] == _DIRECT_V2_EXECUTION_CONTRACT
        and fingerprint(value["public_trace_fingerprint"])
        and value["execution_status"] in {"completed", "abstained"}
        and value["execution_scope"] in {None, "production", "research_only"}
        and isinstance(value["scientifically_validated"], bool)
    ):
        return False
    if schema == "vc.job-execution-identity.v5" and not (
        value["execution_contract"] == _DIRECT_V2_EXECUTION_CONTRACT
        and value["plan_schema_version"] == "vc.execution-plan.v3"
        and fingerprint(value["public_trace_fingerprint"])
        and value["execution_status"] in {"completed", "abstained"}
        and value["execution_scope"] in {None, "production", "research_only"}
        and isinstance(value["scientifically_validated"], bool)
        and optional_fingerprint(value["output_reducer_receipt_fingerprint"])
    ):
        return False
    if schema == "vc.job-execution-identity.v5":
        try:
            from praxis_virtualcell.model_zoo.post_result_policy import OutputReducerBindingV1

            output_reducer = OutputReducerBindingV1.from_dict(value["output_reducer"])
        except (TypeError, ValueError):
            return False
        if output_reducer.to_dict() != value["output_reducer"]:
            return False
        step_model_names = value["execution_step_model_names"]
        if not (
            isinstance(step_model_names, list)
            and all(text(name) for name in step_model_names)
            and len(step_model_names) == len(set(step_model_names))
            and len(step_model_names) == len(value["execution_step_fingerprints"])
        ):
            return False
    outcome = value["outcome"]
    if not (
        isinstance(outcome, dict)
        and set(outcome) == {"abstain", "models_used", "prediction_present"}
        and isinstance(outcome["abstain"], bool)
        and isinstance(outcome["prediction_present"], bool)
        and isinstance(outcome["models_used"], list)
        and all(text(name) for name in outcome["models_used"])
        and len(outcome["models_used"]) == len(set(outcome["models_used"]))
    ):
        return False
    executable_models = {model["name"] for model in value["models"] if model["executable"]}
    model_names = [model["name"] for model in value["models"]]
    valid_outcome = (
        len(model_names) == len(set(model_names))
        and len(value["execution_step_fingerprints"]) == len(executable_models)
        and set(outcome["models_used"]).issubset(executable_models)
        and outcome["prediction_present"] == (not outcome["abstain"])
        and (not outcome["prediction_present"] or bool(outcome["models_used"]))
        and (not executable_models or value["pack"] is not None)
    )
    if not valid_outcome:
        return False
    if schema == "vc.job-execution-identity.v5":
        step_model_names = value["execution_step_model_names"]
        if set(step_model_names) != executable_models:
            return False
        if outcome["abstain"]:
            return (
                value["execution_status"] == "abstained"
                and value["execution_scope"] is None
                and value["scientifically_validated"] is False
                and outcome["models_used"] == []
                and value["output_reducer_receipt_fingerprint"] is None
            )
        used_models = [model for model in value["models"] if model["name"] in outcome["models_used"]]
        if not (
            value["execution_status"] == "completed"
            and outcome["models_used"] == step_model_names
            and len(used_models) == len(step_model_names)
            and value["output_reducer_receipt_fingerprint"] is not None
        ):
            return False
        if value["scientifically_validated"] != all(model["scientifically_validated"] is True for model in used_models):
            return False
        if any(model["research_execution_authorized"] is True for model in used_models):
            return value["execution_scope"] == "research_only" and all(model["policy_present"] for model in used_models)
        return (
            value["execution_scope"] == "production"
            and all(model["production_promoted"] for model in used_models)
            and all(model["benchmark_passed"] is True for model in used_models)
            and all(model["scientifically_validated"] is True for model in used_models)
            and all(model["promotion_eligible"] is True for model in used_models)
        )
    if schema != "vc.job-execution-identity.v4":
        return True
    used_models = [model for model in value["models"] if model["name"] in outcome["models_used"]]
    if outcome["abstain"]:
        return (
            value["execution_status"] == "abstained"
            and value["execution_scope"] is None
            and value["scientifically_validated"] is False
            and not used_models
        )
    if value["execution_status"] != "completed" or len(used_models) != 1:
        return False
    used = used_models[0]
    if value["scientifically_validated"] != (used["scientifically_validated"] is True):
        return False
    if value["execution_scope"] == "research_only":
        return (
            used["research_execution_authorized"] is True
            and used["research_execution_scope"] == "research_only"
            and not used["production_promoted"]
        )
    return (
        value["execution_scope"] == "production"
        and used["production_promoted"]
        and used["benchmark_passed"] is True
        and used["scientifically_validated"] is True
        and used["promotion_eligible"] is True
    )


def _public_execution_identity(value: object) -> dict:
    from praxis_virtualcell.model_zoo.registry_v2 import public_model_version

    if (
        not isinstance(value, dict)
        or value.get("schema_version")
        not in {
            "vc.job-execution-identity.v1",
            "vc.job-execution-identity.v2",
            "vc.job-execution-identity.v3",
            "vc.job-execution-identity.v4",
            "vc.job-execution-identity.v5",
        }
        or not _valid_execution_identity(value)
    ):
        return {
            "schema_version": None,
            "available": False,
            "reason": "unsupported_or_invalid_execution_identity",
        }

    def fingerprint(item):
        return item if isinstance(item, str) and _SHA256.fullmatch(item) else None

    def fingerprints(items):
        if not isinstance(items, list):
            return []
        return [item for item in items if fingerprint(item) is not None]

    raw_pack = value.get("pack")
    pack = None
    if isinstance(raw_pack, dict):
        pack = {
            "pack_id": public_model_version(raw_pack.get("pack_id")),
            "pack_version": public_model_version(raw_pack.get("pack_version")),
            "fingerprint": fingerprint(raw_pack.get("fingerprint")),
        }

    models = []
    for raw in value.get("models", []):
        if not isinstance(raw, dict):
            continue
        model = {
            "name": public_model_version(raw.get("name")),
            "version": public_model_version(raw.get("version")),
            "fingerprint": fingerprint(raw.get("fingerprint")),
            "compatibility_fingerprint": fingerprint(raw.get("compatibility_fingerprint")),
            "executable": raw.get("executable") if isinstance(raw.get("executable"), bool) else False,
        }
        if value["schema_version"] in {
            "vc.job-execution-identity.v2",
            "vc.job-execution-identity.v3",
            "vc.job-execution-identity.v4",
            "vc.job-execution-identity.v5",
        }:
            model.update(
                {
                    "release_fingerprint": fingerprint(raw.get("release_fingerprint")),
                    "capability_fingerprint": fingerprint(raw.get("capability_fingerprint")),
                    "artifact_fingerprints": fingerprints(raw.get("artifact_fingerprints")),
                    "environment_fingerprint": fingerprint(raw.get("environment_fingerprint")),
                    "adapter_fingerprints": fingerprints(raw.get("adapter_fingerprints")),
                    "evidence_fingerprints": fingerprints(raw.get("evidence_fingerprints")),
                    "policy_fingerprint": fingerprint(raw.get("policy_fingerprint")),
                    "cataloged": raw.get("cataloged") if isinstance(raw.get("cataloged"), bool) else False,
                    "artifact_ready": raw.get("artifact_ready")
                    if isinstance(raw.get("artifact_ready"), bool)
                    else False,
                    "revoked": raw.get("revoked") if isinstance(raw.get("revoked"), bool) else False,
                    "superseded_by": fingerprint(raw.get("superseded_by")),
                    "benchmark_passed": raw.get("benchmark_passed")
                    if isinstance(raw.get("benchmark_passed"), bool)
                    else None,
                    "scientifically_validated": raw.get("scientifically_validated")
                    if isinstance(raw.get("scientifically_validated"), bool)
                    else None,
                    "promotion_eligible": raw.get("promotion_eligible")
                    if isinstance(raw.get("promotion_eligible"), bool)
                    else None,
                    "policy_present": raw.get("policy_present")
                    if isinstance(raw.get("policy_present"), bool)
                    else False,
                    "production_promoted": raw.get("production_promoted")
                    if isinstance(raw.get("production_promoted"), bool)
                    else False,
                }
            )
            if value["schema_version"] in {
                "vc.job-execution-identity.v4",
                "vc.job-execution-identity.v5",
            }:
                model.update(
                    {
                        "research_execution_authorized": raw.get("research_execution_authorized")
                        if isinstance(raw.get("research_execution_authorized"), bool)
                        else None,
                        "research_execution_scope": raw.get("research_execution_scope")
                        if raw.get("research_execution_scope") == "research_only"
                        else None,
                    }
                )
        models.append(model)

    public = {
        "schema_version": value["schema_version"],
        "legacy_adapter": value.get("legacy_adapter") if isinstance(value.get("legacy_adapter"), bool) else True,
        "pack": pack,
        "models": models,
        "fingerprint": fingerprint(value.get("fingerprint")),
    }
    if value["schema_version"] in {
        "vc.job-execution-identity.v2",
        "vc.job-execution-identity.v3",
        "vc.job-execution-identity.v4",
        "vc.job-execution-identity.v5",
    }:
        raw_outcome = value.get("outcome")
        outcome = None
        if isinstance(raw_outcome, dict):
            outcome = {
                "abstain": raw_outcome.get("abstain") if isinstance(raw_outcome.get("abstain"), bool) else None,
                "models_used": [
                    name for name in raw_outcome.get("models_used", []) if public_model_version(name) is not None
                ]
                if isinstance(raw_outcome.get("models_used"), list)
                else [],
                "prediction_present": raw_outcome.get("prediction_present")
                if isinstance(raw_outcome.get("prediction_present"), bool)
                else None,
            }
        public.update(
            {
                "plan_id": public_model_version(value.get("plan_id")),
                "submitted_request_fingerprint": fingerprint(value.get("submitted_request_fingerprint")),
                "request_fingerprint": fingerprint(value.get("request_fingerprint")),
                "environment_snapshot_fingerprint": fingerprint(value.get("environment_snapshot_fingerprint")),
                "execution_step_fingerprints": fingerprints(value.get("execution_step_fingerprints")),
                "structured_report_fingerprint": fingerprint(value.get("structured_report_fingerprint")),
                "outcome": outcome,
            }
        )
        if value["schema_version"] == "vc.job-execution-identity.v3":
            public.update(
                {
                    "brain_fingerprint": fingerprint(value.get("brain_fingerprint")),
                    "dag_fingerprint": fingerprint(value.get("dag_fingerprint")),
                }
            )
        elif value["schema_version"] == "vc.job-execution-identity.v4":
            public.update(
                {
                    "execution_contract": value.get("execution_contract"),
                    "public_trace_fingerprint": fingerprint(value.get("public_trace_fingerprint")),
                    "execution_status": value.get("execution_status"),
                    "execution_scope": value.get("execution_scope"),
                    "scientifically_validated": value.get("scientifically_validated"),
                }
            )
        elif value["schema_version"] == "vc.job-execution-identity.v5":
            public.update(
                {
                    "execution_contract": value.get("execution_contract"),
                    "plan_schema_version": value.get("plan_schema_version"),
                    "execution_step_model_names": [
                        public_model_version(name)
                        for name in value.get("execution_step_model_names", [])
                        if public_model_version(name) is not None
                    ],
                    "output_reducer": value.get("output_reducer"),
                    "output_reducer_receipt_fingerprint": fingerprint(value.get("output_reducer_receipt_fingerprint")),
                    "public_trace_fingerprint": fingerprint(value.get("public_trace_fingerprint")),
                    "execution_status": value.get("execution_status"),
                    "execution_scope": value.get("execution_scope"),
                    "scientifically_validated": value.get("scientifically_validated"),
                }
            )
    return public


class JobStore:
    def __init__(self, runs_dir: str = "runs") -> None:
        self.root = Path(os.path.abspath(os.fspath(runs_dir)))
        if self.root == Path(self.root.anchor):
            raise ValueError("runs_dir must not be a filesystem root")

    def _path(self, job_id: str) -> Path:
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            raise ValueError("job_id must be a safe local identifier")
        return self.root / job_id

    @staticmethod
    def _open_child_directory(parent_fd: int, name: str) -> int:
        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nofollow is None:
            raise OSError("secure JobStore writes require O_NOFOLLOW")
        fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow,
            dir_fd=parent_fd,
        )
        try:
            if not stat.S_ISDIR(os.fstat(fd).st_mode):
                raise NotADirectoryError(name)
        except Exception:
            os.close(fd)
            raise
        return fd

    def _open_root_directory(self, *, create: bool) -> int:
        """Open every runs-root component without ever following a symlink."""

        current_fd = os.open(
            self.root.anchor,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            for name in self.root.parts[1:]:
                try:
                    child_fd = self._open_child_directory(current_fd, name)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(name, mode=0o700, dir_fd=current_fd)
                    child_fd = self._open_child_directory(current_fd, name)
                os.close(current_fd)
                current_fd = child_fd
        except Exception:
            os.close(current_fd)
            raise
        return current_fd

    def _open_job_directory(self, job_id: str) -> int:
        self._path(job_id)
        root_fd = self._open_root_directory(create=False)
        try:
            return self._open_child_directory(root_fd, job_id)
        finally:
            os.close(root_fd)

    def _new_job_directory(self, job_id: str) -> tuple[Path, int]:
        directory = self._path(job_id)
        root_fd = self._open_root_directory(create=True)
        try:
            try:
                os.mkdir(job_id, mode=0o700, dir_fd=root_fd)
            except FileExistsError as exc:
                raise FileExistsError(f"job already exists: {job_id}") from exc
            return directory, self._open_child_directory(root_fd, job_id)
        finally:
            os.close(root_fd)

    @staticmethod
    def _require_posix_reservation_lock() -> None:
        if _fcntl is None:
            raise OSError("direct JobStore reservations require POSIX flock")

    @classmethod
    def _lock_reservation_directory(cls, directory_fd: int) -> None:
        """Serialize reservation transitions on the already-pinned directory inode."""

        cls._require_posix_reservation_lock()
        _fcntl.flock(directory_fd, _fcntl.LOCK_EX)

    @staticmethod
    def _open_regular_at(
        directory_fd: int,
        name: str,
        flags: int,
        *,
        require_single_link: bool = False,
    ) -> int:
        """Open one direct child from a pinned directory, never through a link."""

        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nofollow is None:
            raise OSError("secure JobStore writes require O_NOFOLLOW")
        fd = os.open(
            name,
            flags | nofollow | getattr(os, "O_NONBLOCK", 0),
            0o600,
            dir_fd=directory_fd,
        )
        try:
            file_stat = os.fstat(fd)
            if not stat.S_ISREG(file_stat.st_mode):
                raise OSError(f"job companion is not a regular file: {name}")
            if require_single_link and file_stat.st_nlink != 1:
                raise OSError(f"job companion is not private to this job: {name}")
        except Exception:
            os.close(fd)
            raise
        return fd

    @staticmethod
    def _write_fd(fd: int, text: str) -> None:
        data = text.encode("utf-8")
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        while data:
            written = os.write(fd, data)
            if written <= 0:
                raise OSError("unable to write job file")
            data = data[written:]

    @classmethod
    def _write_new_at(cls, directory_fd: int, name: str, text: str) -> None:
        fd = cls._open_regular_at(directory_fd, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            cls._write_fd(fd, text)
        finally:
            os.close(fd)

    @classmethod
    def _read_text_at(cls, directory_fd: int, name: str) -> str | None:
        try:
            fd = cls._open_regular_at(
                directory_fd,
                name,
                os.O_RDONLY,
                require_single_link=True,
            )
        except FileNotFoundError:
            return None
        try:
            chunks = []
            while chunk := os.read(fd, 65_536):
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8")
        finally:
            os.close(fd)

    def _open_reserved_directory(self, job_id: str) -> int:
        directory_fd = self._open_job_directory(job_id)
        try:
            self._lock_reservation_directory(directory_fd)
            status_fd = self._open_regular_at(
                directory_fd,
                "status",
                os.O_RDONLY,
                require_single_link=True,
            )
            try:
                if self._status_value(status_fd) != "reserved":
                    raise ValueError("reservation status is not reserved")
            finally:
                os.close(status_fd)
        except Exception:
            os.close(directory_fd)
            raise
        return directory_fd

    @classmethod
    def _replace_status_at(cls, directory_fd: int, value: str) -> None:
        """Replace status by name, so an old linked inode is never modified."""

        temporary_name = f".status-{secrets.token_hex(16)}.tmp"
        cls._write_new_at(directory_fd, temporary_name, value)
        try:
            os.replace(
                temporary_name,
                "status",
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
        except Exception:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _status_value(status_fd: int) -> str:
        if os.fstat(status_fd).st_size > 128:
            return ""
        os.lseek(status_fd, 0, os.SEEK_SET)
        return os.read(status_fd, 129).decode("utf-8").strip()

    def reserve(self, job_id: str) -> str:
        """Atomically claim a write-new job ID before an execution can start."""

        self._require_posix_reservation_lock()
        directory, directory_fd = self._new_job_directory(job_id)
        try:
            self._lock_reservation_directory(directory_fd)
            try:
                self._write_new_at(directory_fd, "status", "reserved")
            except Exception:
                # The directory name is the durable, write-new claim.  Keep an
                # inspectable terminal marker when possible, but never mask the
                # original reservation error or make this ID reusable.
                try:
                    self._replace_status_at(directory_fd, "unknown")
                except Exception:
                    pass
                raise
        finally:
            os.close(directory_fd)
        return str(directory)

    def mark_failed_reservation(self, job_id: str) -> None:
        """Retain an execution reservation when direct-v2 fails before persistence."""

        try:
            directory_fd = self._open_reserved_directory(job_id)
        except (OSError, UnicodeDecodeError) as exc:
            raise FileNotFoundError(job_id) from exc
        try:
            self._replace_status_at(directory_fd, "failed")
        finally:
            os.close(directory_fd)

    def _w(self, directory_fd: int, name: str, obj) -> None:
        if isinstance(obj, str):
            filename = name
            text = obj
        else:
            filename = f"{name}.json"
            text = json.dumps(obj, ensure_ascii=False, indent=2)
        self._write_new_at(directory_fd, filename, text)

    @staticmethod
    def _execution_identity(result: dict, *, request: dict | None = None) -> dict:
        from praxis_virtualcell.model_zoo.capability_registry import (
            ExecutionPlan,
            ExecutionPlanV2,
            ExecutionPlanV3,
        )

        provenance = result.get("provenance") or {}
        raw_plan = provenance.get("execution_plan")
        if raw_plan is None:
            value = {
                "schema_version": "vc.job-execution-identity.v1",
                "legacy_adapter": True,
                "pack": None,
                "models": [],
            }
        else:
            schema = raw_plan.get("schema_version") if isinstance(raw_plan, dict) else None
            if schema == "vc.execution-plan.v1":
                plan = ExecutionPlan.from_dict(raw_plan)
            elif schema == "vc.execution-plan.v2":
                plan = ExecutionPlanV2.from_dict(raw_plan)
            elif schema == "vc.execution-plan.v3":
                plan = ExecutionPlanV3.from_dict(raw_plan)
            else:
                raise ValueError("unsupported execution plan schema in job provenance")
            pack = (
                {
                    "pack_id": plan.pack_id,
                    "pack_version": plan.pack_version,
                    "fingerprint": plan.pack_fingerprint,
                }
                if plan.pack_id is not None
                else None
            )
            if (
                isinstance(plan, ExecutionPlanV2)
                and provenance.get("execution_contract") == _DIRECT_V2_EXECUTION_CONTRACT
            ):
                value = _direct_v2_execution_identity(
                    result,
                    request=request,
                    plan=plan,
                    pack=pack,
                )
                value["fingerprint"] = _canonical_fingerprint(value)
                return value
            if (
                isinstance(plan, ExecutionPlanV3)
                and provenance.get("execution_contract") == _DIRECT_V2_EXECUTION_CONTRACT
            ):
                if request is None:
                    raise ValueError("direct-v3 execution identity requires the submitted request")
                value = _direct_v3_execution_identity(
                    result,
                    request=request,
                    plan=plan,
                    pack=pack,
                )
                value["fingerprint"] = _canonical_fingerprint(value)
                return value
            if isinstance(plan, ExecutionPlanV3):
                raise ValueError("direct-v3 execution contract marker is missing")
            if isinstance(plan, ExecutionPlan):
                value = {
                    "schema_version": "vc.job-execution-identity.v1",
                    "legacy_adapter": False,
                    "pack": pack,
                    "models": [
                        {
                            "name": report.model_name,
                            "version": report.model_version,
                            "fingerprint": report.model_fingerprint,
                            "compatibility_fingerprint": report.fingerprint(),
                            "executable": report.executable,
                        }
                        for report in plan.reports
                    ],
                }
            else:
                if request is None:
                    raise ValueError("v2 execution identity requires the submitted request")
                from praxis_virtualcell.model_zoo.registry_v2 import (
                    public_model_version,
                )
                from praxis_virtualcell.pack_product import (
                    _public_provenance,
                    _runtime_request_v2,
                )

                submitted_request_fingerprint = _canonical_fingerprint(request)
                normalized_request = _runtime_request_v2(request)
                normalized_request_fingerprint = _canonical_fingerprint(normalized_request.to_dict())
                if normalized_request_fingerprint != plan.request_fingerprint:
                    raise ValueError("submitted request does not match execution plan")
                raw_compilation = provenance.get("virtual_experiment")
                experiment_contract = provenance.get("execution_contract")
                compilation = None
                if raw_compilation is not None:
                    from praxis_virtualcell.virtual_experiment import (
                        VirtualExperimentCompilationV1,
                    )

                    compilation = VirtualExperimentCompilationV1.from_dict(raw_compilation)
                structured_report = result.get("structured_report")
                if not isinstance(structured_report, dict):
                    raise ValueError("v2 execution identity requires a structured report")
                experiment_report_keys = {
                    "request_id",
                    "prediction",
                    "models_used",
                    "models_rejected",
                    "models_failed",
                    "abstain",
                    "abstain_reasons",
                    "reliability",
                    "provenance",
                }
                direct_contract_shape = (
                    request.get("schema_version") == "vc.request.v2"
                    and structured_report.get("abstain") is True
                    and structured_report.get("prediction") is None
                    and structured_report.get("models_used") == []
                )
                if compilation is None and (
                    experiment_contract == "vc.virtual-experiment-compilation.v1" or direct_contract_shape
                ):
                    raise ValueError("direct contract-only jobs require a virtual experiment")
                if compilation is not None and (experiment_contract != "vc.virtual-experiment-compilation.v1"):
                    raise ValueError("virtual experiment provenance contract marker is missing")
                report_provenance = structured_report.get("provenance") or {}
                if compilation is not None and report_provenance != provenance:
                    raise ValueError("structured report and top-level provenances differ")
                report_plan = report_provenance.get("execution_plan") if isinstance(report_provenance, dict) else None
                if report_plan != raw_plan:
                    raise ValueError("structured report and provenance execution plans differ")
                report_compilation = (
                    report_provenance.get("virtual_experiment") if isinstance(report_provenance, dict) else None
                )
                if report_compilation != raw_compilation:
                    raise ValueError("structured report and provenance virtual experiments differ")
                if compilation is not None:
                    from praxis_virtualcell.virtual_experiment import (
                        execution_plan_fingerprint,
                    )

                    dag = compilation.dag
                    brain = compilation.brain_context
                    reports = plan.reports
                    steps_by_fingerprint = {step.fingerprint(): step for step in plan.steps}
                    expected_step_fingerprints = tuple(sorted(steps_by_fingerprint))
                    expected_capability_fingerprints = tuple(
                        sorted({step.capability_fingerprint for step in plan.steps})
                    )
                    if not (
                        dag.request_id == plan.request_id
                        and dag.request_fingerprint == plan.request_fingerprint
                        and dag.cell_context_fingerprint
                        == _canonical_fingerprint(normalized_request.cell_context.to_dict())
                        and dag.pack_id == plan.pack_id
                        and dag.pack_version == plan.pack_version
                        and dag.pack_fingerprint == plan.pack_fingerprint
                        and dag.environment_snapshot_fingerprint == plan.environment_snapshot_fingerprint
                        and dag.plan_id == plan.plan_id
                        and dag.plan_fingerprint == execution_plan_fingerprint(plan)
                        and brain.request_id == plan.request_id
                        and brain.request_fingerprint == plan.request_fingerprint
                        and brain.pack_id == plan.pack_id
                        and brain.pack_version == plan.pack_version
                        and brain.pack_fingerprint == plan.pack_fingerprint
                        and brain.environment_snapshot_fingerprint == plan.environment_snapshot_fingerprint
                        and brain.plan_id == plan.plan_id
                        and brain.plan_fingerprint == dag.plan_fingerprint
                        and brain.dag_fingerprint == dag.fingerprint()
                        and dag.validated_step_fingerprints == expected_step_fingerprints
                        and dag.participating_capability_fingerprints == expected_capability_fingerprints
                        and brain.execution_step_fingerprints == expected_step_fingerprints
                        and brain.participating_capability_fingerprints == expected_capability_fingerprints
                        and compilation.decision.participating_capability_fingerprints
                        == expected_capability_fingerprints
                    ):
                        raise ValueError("virtual experiment does not match execution plan")
                    for node in dag.nodes:
                        step = steps_by_fingerprint.get(node.execution_step_fingerprint)
                        if step is None or not (
                            node.model_fingerprint == step.model_fingerprint
                            and node.release_fingerprint == step.release_fingerprint
                            and node.capability_fingerprint == step.capability_fingerprint
                            and node.environment_fingerprint == step.environment_fingerprint
                            and node.adapter_fingerprints == step.adapter_fingerprints
                        ):
                            raise ValueError("DAG node does not match an execution plan step")
                    expected_brain_bindings = {
                        "compatibility_fingerprints": tuple(sorted({report.fingerprint() for report in reports})),
                        "model_fingerprints": tuple(sorted({report.model_fingerprint for report in reports})),
                        "release_fingerprints": tuple(
                            sorted(
                                {
                                    report.release_fingerprint
                                    for report in reports
                                    if report.release_fingerprint is not None
                                }
                            )
                        ),
                        "capability_fingerprints": tuple(
                            sorted(
                                {
                                    report.capability_fingerprint
                                    for report in reports
                                    if report.capability_fingerprint is not None
                                }
                            )
                        ),
                        "environment_fingerprints": tuple(
                            sorted(
                                {
                                    report.environment_fingerprint
                                    for report in reports
                                    if report.environment_fingerprint is not None
                                }
                            )
                        ),
                        "adapter_fingerprints": tuple(
                            sorted({item for report in reports for item in report.adapter_fingerprints})
                        ),
                        "evidence_fingerprints": tuple(
                            sorted({item for report in reports for item in report.evidence_fingerprints})
                        ),
                        "policy_fingerprints": tuple(
                            sorted(
                                {
                                    report.policy_fingerprint
                                    for report in reports
                                    if report.policy_fingerprint is not None
                                }
                            )
                        ),
                    }
                    if any(getattr(brain, field) != expected for field, expected in expected_brain_bindings.items()):
                        raise ValueError("Brain context does not match compatibility reports")
                model_names = {step.model_name for step in plan.steps}
                models_used = structured_report.get("models_used")
                if not isinstance(models_used, list) or any(not isinstance(name, str) for name in models_used):
                    raise ValueError("structured report models_used must be an array of names")
                if len(set(models_used)) != len(models_used):
                    raise ValueError("structured report models_used must be unique")
                if not set(models_used).issubset(model_names):
                    raise ValueError("structured report used a model outside the execution plan")
                abstain = structured_report.get("abstain")
                prediction = structured_report.get("prediction")
                if not isinstance(abstain, bool):
                    raise ValueError("structured report abstain must be boolean")
                if prediction is not None and (abstain or not models_used):
                    raise ValueError("structured report prediction requires a non-abstained used model")
                if not abstain and prediction is None:
                    raise ValueError("non-abstained structured report requires a prediction")
                if compilation is not None and (
                    not abstain
                    or prediction is not None
                    or models_used
                    or not compilation.decision.abstain
                    or compilation.decision.execution_performed
                ):
                    raise ValueError("virtual experiment jobs must remain contract-only abstentions")
                if compilation is not None:
                    rejected_models = [report.model_name for report in plan.reports if not report.executable]
                    if not (
                        set(structured_report) == experiment_report_keys
                        and structured_report["request_id"] == plan.request_id
                        and structured_report["models_rejected"] == rejected_models
                        and structured_report["models_failed"] == []
                        and structured_report["abstain_reasons"] == [compilation.decision.reason]
                        and structured_report["reliability"] == "low"
                    ):
                        raise ValueError("virtual experiment structured report is inconsistent")
                    if result.get("trace") != [] or result.get("narrative") is not None:
                        raise ValueError("virtual experiment trace and narrative must be empty")
                public_report = json.loads(json.dumps(structured_report))
                public_report["provenance"] = _public_provenance(structured_report.get("provenance") or {})
                if compilation is not None:
                    public_report["provenance"]["virtual_experiment"] = compilation.authoritative_dict()
                value = {
                    "schema_version": (
                        "vc.job-execution-identity.v3" if compilation is not None else "vc.job-execution-identity.v2"
                    ),
                    "legacy_adapter": False,
                    "plan_id": plan.plan_id,
                    "submitted_request_fingerprint": (submitted_request_fingerprint),
                    "request_fingerprint": plan.request_fingerprint,
                    "pack": pack,
                    "environment_snapshot_fingerprint": (plan.environment_snapshot_fingerprint),
                    "execution_step_fingerprints": [step.fingerprint() for step in plan.steps],
                    "structured_report_fingerprint": _canonical_fingerprint(public_report),
                    "outcome": {
                        "abstain": abstain,
                        "models_used": models_used,
                        "prediction_present": prediction is not None,
                    },
                    "models": [
                        {
                            "name": report.model_name,
                            "version": public_model_version(report.model_version),
                            "fingerprint": report.model_fingerprint,
                            "release_fingerprint": report.release_fingerprint,
                            "capability_fingerprint": report.capability_fingerprint,
                            "artifact_fingerprints": list(report.artifact_fingerprints),
                            "environment_fingerprint": (report.environment_fingerprint),
                            "adapter_fingerprints": list(report.adapter_fingerprints),
                            "evidence_fingerprints": list(report.evidence_fingerprints),
                            "policy_fingerprint": report.policy_fingerprint,
                            "compatibility_fingerprint": report.fingerprint(),
                            "cataloged": report.cataloged,
                            "artifact_ready": report.artifact_ready,
                            "revoked": report.revoked,
                            "superseded_by": report.superseded_by,
                            "benchmark_passed": report.benchmark_passed,
                            "scientifically_validated": (report.scientifically_validated),
                            "promotion_eligible": report.promotion_eligible,
                            "policy_present": report.policy_present,
                            "production_promoted": report.production_promoted,
                            "executable": report.executable,
                        }
                        for report in plan.reports
                    ],
                }
                if compilation is not None:
                    value.update(
                        {
                            "brain_fingerprint": (compilation.brain_context.fingerprint()),
                            "dag_fingerprint": compilation.dag.fingerprint(),
                        }
                    )
        value["fingerprint"] = _canonical_fingerprint(value)
        return value

    def save(
        self,
        job_id: str,
        *,
        candidate=None,
        request=None,
        result=None,
        reserved: bool = False,
    ) -> str:
        """落盘一次 job;result 为 run_query 的返回。返回 job 目录。"""
        directory_fd = None
        d = None
        if reserved:
            d = self._path(job_id)
            try:
                directory_fd = self._open_reserved_directory(job_id)
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                if directory_fd is not None:
                    os.close(directory_fd)
                raise FileExistsError(f"job is not reserved: {job_id}") from exc
        elif self._path(job_id).exists():
            raise FileExistsError(f"job already exists: {job_id}")
        try:
            execution_identity = self._execution_identity(result, request=request) if result is not None else None
            public_provenance = None
            public_report = None
            if result is not None:
                from praxis_virtualcell.pack_product import _public_provenance

                public_provenance = _public_provenance(result.get("provenance") or {})
                public_report = json.loads(json.dumps(result.get("structured_report", {})))
                if isinstance(public_report, dict):
                    public_report["provenance"] = public_provenance
            if not reserved:
                d, directory_fd = self._new_job_directory(job_id)
            if candidate is not None:
                self._w(directory_fd, "candidate_request", candidate)
            if request is not None:
                self._w(directory_fd, "request", request)
            if result is not None:
                self._w(directory_fd, "report", public_report)
                self._w(directory_fd, "trace", result.get("trace", []))
                self._w(directory_fd, "provenance", public_provenance)
                self._w(
                    directory_fd,
                    "execution_identity",
                    execution_identity,
                )
                if result.get("narrative"):
                    self._w(directory_fd, "narrative_report.md", result["narrative"])
                # 确定性 Markdown 报告:每次都写(含 offline),与 LLM narrative 正交
                from praxis_virtualcell.io.report_markdown import render_report_md

                job_like = {
                    "report": public_report,
                    "request": request,
                    "candidate_request": candidate,
                    "trace": result.get("trace", []),
                    "provenance": public_provenance,
                    "mode": result.get("mode"),
                    "llm_enabled": result.get("llm_enabled"),
                }
                self._w(directory_fd, "report.md", render_report_md(job_like))
                # LLM 元数据只存 hash(不存 key/原文)
                llm = (result.get("parsed") or {}).get("llm_metadata") or {}
                self._w(
                    directory_fd,
                    "llm_meta",
                    {k: v for k, v in llm.items() if k != "api_key"},
                )
            self._replace_status_at(directory_fd, "done")
        except Exception:
            # A direct-v2 caller owns a prior atomic reservation and will mark
            # it failed.  For ordinary write-new jobs, retain a local failed
            # audit anchor too: a pathname cleanup could delete a directory
            # swapped in after its descriptor was pinned.  Never mask the
            # original write error if that best-effort marker also fails.
            if not reserved and directory_fd is not None:
                try:
                    self._replace_status_at(directory_fd, "failed")
                except OSError:
                    pass
            raise
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
        return str(d)

    def load(self, job_id: str) -> dict:
        """Read one archive without letting untrusted JSON escape this boundary."""

        self._path(job_id)  # Preserve the public invalid-job-id validation.
        try:
            return self._load(job_id)
        except RecursionError:
            return {"job_id": job_id, "status": "corrupt"}

    def _load(self, job_id: str) -> dict:
        try:
            directory_fd = self._open_job_directory(job_id)
        except FileNotFoundError:
            raise FileNotFoundError(job_id) from None
        except OSError:
            return {"job_id": job_id, "status": "corrupt"}
        try:
            status_text = self._read_text_at(directory_fd, "status")
            if status_text is None:
                return {"job_id": job_id, "status": "unknown"}
            status = status_text.strip()
            if status not in {"reserved", "failed", "done", "unknown"}:
                return {"job_id": job_id, "status": "unknown"}
            out: dict = {"job_id": job_id, "status": status}
            # A reservation may fail while a JSON companion is only partly written.
            # It is an audit anchor, not a replayable result; never surface partial
            # contents as authoritative job output.
            if out["status"] != "done":
                return out
            for name, expected_type in _JSON_COMPANION_TYPES.items():
                try:
                    text = self._read_text_at(directory_fd, f"{name}.json")
                except OSError:
                    return {"job_id": job_id, "status": "corrupt"}
                if text is not None:
                    try:
                        value = json.loads(text)
                    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                        return {"job_id": job_id, "status": "corrupt"}
                    if not isinstance(value, expected_type):
                        return {"job_id": job_id, "status": "corrupt"}
                    out[name] = value
            raw_identity = out.get("execution_identity")
            raw_provenance = out.get("provenance")
            direct_v2_archive = (
                isinstance(raw_identity, dict)
                and raw_identity.get("schema_version")
                in {"vc.job-execution-identity.v4", "vc.job-execution-identity.v5"}
            ) or (
                isinstance(raw_provenance, dict)
                and raw_provenance.get("execution_contract") == _DIRECT_V2_EXECUTION_CONTRACT
            )
            if direct_v2_archive and not _valid_direct_v2_public_trace(out.get("trace")):
                out["trace"] = []
            try:
                narrative = self._read_text_at(directory_fd, "narrative_report.md")
                report_markdown = self._read_text_at(directory_fd, "report.md")
            except OSError:
                return {"job_id": job_id, "status": "corrupt"}
            if narrative is not None:
                out["narrative"] = narrative
            if report_markdown is not None:
                out["report_md"] = report_markdown
            from praxis_virtualcell.pack_product import _public_provenance

            if isinstance(out.get("provenance"), dict):
                out["provenance"] = _public_provenance(out["provenance"])
            if isinstance(out.get("report"), dict):
                report = json.loads(json.dumps(out["report"]))
                if isinstance(report.get("provenance"), dict):
                    report["provenance"] = _public_provenance(report["provenance"])
                out["report"] = report
            if "execution_identity" in out:
                execution_identity = out["execution_identity"]
                schema = execution_identity.get("schema_version") if isinstance(execution_identity, dict) else None
                if schema in {
                    "vc.job-execution-identity.v1",
                    "vc.job-execution-identity.v2",
                    "vc.job-execution-identity.v3",
                    "vc.job-execution-identity.v4",
                    "vc.job-execution-identity.v5",
                }:
                    companion_keys = ("request", "report", "provenance", "trace")
                    companions_present = tuple(key in out for key in companion_keys)
                    if schema in {
                        "vc.job-execution-identity.v4",
                        "vc.job-execution-identity.v5",
                    } and not all(companions_present):
                        # v4/v5 are write-new and claim a payload-free trace spine;
                        # unlike historical v1–v3 archives it is not meaningful
                        # without every replay companion available for recomputation.
                        execution_identity = {}
                    elif any(companions_present) and not all(companions_present):
                        execution_identity = {}
                    elif all(companions_present):
                        try:
                            expected = self._execution_identity(
                                {
                                    "structured_report": out["report"],
                                    "provenance": out["provenance"],
                                    "trace": out["trace"],
                                    "narrative": out.get("narrative"),
                                },
                                request=out["request"],
                            )
                        except (KeyError, TypeError, ValueError):
                            execution_identity = {}
                        else:
                            if execution_identity != expected:
                                execution_identity = {}
                out["execution_identity"] = _public_execution_identity(execution_identity)
            return out
        except (OSError, UnicodeDecodeError):
            return {"job_id": job_id, "status": "corrupt"}
        finally:
            os.close(directory_fd)

    def list_jobs(self) -> list[str]:
        try:
            root_fd = self._open_root_directory(create=False)
        except (FileNotFoundError, OSError):
            return []
        try:
            return sorted(
                name
                for name in os.listdir(root_fd)
                if stat.S_ISDIR(os.stat(name, dir_fd=root_fd, follow_symlinks=False).st_mode)
            )
        except OSError:
            return []
        finally:
            os.close(root_fd)
