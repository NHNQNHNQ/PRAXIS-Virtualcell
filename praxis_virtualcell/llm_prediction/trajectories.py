"""Export public agent conversations without turning predictions into labels.

An export is a review queue by default. Curator approval and label provenance
are separate from model-visible messages; only an explicitly supplied, checked
assessment can replace the final accepted assessment as a supervised target.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .evidence import validate_modality_coverage
from .schemas import Assessment
from .workflow import validate_assessment_evidence

STAGES = {"planning", "analysis", "review", "revision"}
_CREDENTIAL_FIELDS = {
    "apikey", "authorization", "accesstoken", "refreshtoken", "password",
    "clientsecret", "secret", "secretkey", "privatekey",
}
_PRIVATE_FIELDS = _CREDENTIAL_FIELDS | {
    "reasoningcontent", "reasoning", "thinking", "rawresponse", "rawapiresponse",
    "requestheaders", "responseheaders", "apimetadata",
}


def _field(name: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _secrets(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _field(key) in _CREDENTIAL_FIELDS and isinstance(child, str) and len(child) >= 4:
                found.add(child)
            found.update(_secrets(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_secrets(child))
    elif isinstance(value, str):
        try:
            child = json.loads(value)
        except (ValueError, TypeError):
            pass
        else:
            if isinstance(child, (dict, list)):
                found.update(_secrets(child))
    return found


def _clean(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clean(child, secrets) for key, child in value.items()
                if _field(key) not in _PRIVATE_FIELDS}
    if isinstance(value, list):
        return [_clean(child, secrets) for child in value]
    if isinstance(value, str):
        value = re.sub(r"<think>.*?</think>", "", value, flags=re.DOTALL | re.IGNORECASE)
        value = re.sub(r"<think>.*$", "", value, flags=re.DOTALL | re.IGNORECASE)
        for secret in sorted(secrets, key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value,
                       flags=re.IGNORECASE)
        value = re.sub(
            r"\b(?:[A-Z0-9_]*API_KEY|api[-_]?key|access[-_]?token|password|client[-_]?secret)"
            r"\s*[:=]\s*[^\s,;]+", "[REDACTED_CREDENTIAL]", value, flags=re.IGNORECASE,
        )
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value
        if isinstance(parsed, (dict, list)):
            return _dump(_clean(parsed, secrets))
    return value


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _assessment(value: Any) -> Assessment:
    """Remove only the display annotations added after contract validation."""
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("```json\n") and value.endswith("```"):
            value = value[8:-3].strip()
        value = json.loads(value)
    if isinstance(value, Mapping):
        value = dict(value)
        for key in ("targets", "mechanism_hypotheses"):
            if isinstance(value.get(key), list):
                value[key] = [
                    {k: v for k, v in item.items() if k not in {"causality_verified", "identity_observed"}}
                    if isinstance(item, Mapping) else item for item in value[key]
                ]
    return Assessment.model_validate(value)


def _public_messages(messages: Any, tools: Any, secrets: set[str]) -> list[dict]:
    if not isinstance(messages, list) or not messages:
        raise ValueError("missing_messages")
    names = None
    if tools is not None:
        if not isinstance(tools, list):
            raise ValueError("invalid_tools")
        names = set()
        for tool in tools:
            if not isinstance(tool, Mapping) or tool.get("type") != "function":
                raise ValueError("invalid_tool_schema")
            function = tool.get("function")
            if not isinstance(function, Mapping) or not isinstance(function.get("name"), str):
                raise ValueError("invalid_tool_schema")
            names.add(function["name"])
    public = []
    seen: set[str] = set()
    pending: dict[str, str] = {}
    for original in messages:
        if not isinstance(original, Mapping) or original.get("role") not in {"system", "user", "assistant", "tool"}:
            raise ValueError("invalid_message")
        role = original["role"]
        if pending and role != "tool":
            raise ValueError("tool_results_out_of_order")
        content = original.get("content")
        if content is not None and not isinstance(content, str):
            raise ValueError("non_text_message_content")
        message = {"role": role, "content": _clean(content, secrets)}
        calls = original.get("tool_calls")
        if calls:
            if role != "assistant" or not isinstance(calls, list):
                raise ValueError("invalid_tool_calls")
            public_calls = []
            for call in calls:
                if not isinstance(call, Mapping) or call.get("type") != "function":
                    raise ValueError("invalid_tool_call")
                call_id, function = call.get("id"), call.get("function")
                if not isinstance(call_id, str) or not call_id or call_id in seen:
                    raise ValueError("duplicate_or_missing_tool_call_id")
                if not isinstance(function, Mapping) or not isinstance(function.get("name"), str) or not function["name"]:
                    raise ValueError("invalid_tool_function")
                if names is not None and function["name"] not in names:
                    raise ValueError("tool_not_in_schema")
                arguments = function.get("arguments")
                try:
                    parsed = json.loads(arguments) if isinstance(arguments, str) else None
                except ValueError as exc:
                    raise ValueError("invalid_tool_arguments") from exc
                if not isinstance(parsed, dict):
                    raise ValueError("invalid_tool_arguments")
                seen.add(call_id)
                pending[call_id] = function["name"]
                public_calls.append({"id": call_id, "type": "function", "function": {
                    "name": function["name"], "arguments": _dump(_clean(parsed, secrets)),
                }})
            message["tool_calls"] = public_calls
        if role == "tool":
            call_id = original.get("tool_call_id")
            if not isinstance(call_id, str) or call_id not in pending or content is None:
                raise ValueError("unmatched_or_duplicate_tool_result")
            if original.get("name") is not None and original["name"] != pending[call_id]:
                raise ValueError("tool_result_name_mismatch")
            del pending[call_id]
            message["tool_call_id"] = call_id
        public.append(message)
    if pending:
        raise ValueError("missing_tool_result")
    if public[-1]["role"] != "assistant" or public[-1].get("tool_calls") or not public[-1].get("content"):
        raise ValueError("missing_final_assistant_output")
    return public


def _supervision(value: Mapping[str, Any] | None, result: Mapping[str, Any]) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or value.get("approved") is not True:
        raise ValueError("supervision_requires_explicit_approval")
    curator, sources = value.get("curator"), value.get("label_source_ids")
    if not isinstance(curator, str) or not curator.strip():
        raise ValueError("supervision_requires_curator")
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(source, str) or not source.strip() for source in sources)):
        raise ValueError("supervision_requires_label_sources")
    indices = value.get("curated_stage_indices", [])
    if (not isinstance(indices, list)
            or any(isinstance(index, bool) or not isinstance(index, int) or index < 0 for index in indices)):
        raise ValueError("invalid_curated_stage_indices")
    approved = {"curator": curator.strip(), "label_source_ids": list(dict.fromkeys(sources)),
                "curated_stage_indices": indices}
    if value.get("gold_assessment") is not None:
        try:
            assessment = Assessment.model_validate(value["gold_assessment"])
        except ValidationError as exc:
            raise ValueError("invalid_gold_assessment_schema") from exc
        calls = result.get("execution_trace", {}).get("tool_calls", [])
        try:
            require_structure = result.get("cell_structure") is not None or any(
                call.get("name") in {"cell_structure_overview", "query_cell_structure"} for call in calls)
            issues = validate_assessment_evidence(assessment, calls, require_structure=require_structure)
            selected = result.get("profile", {}).get("selected_modalities")
            if selected is not None:
                issues.extend(validate_modality_coverage(assessment, calls, selected))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid_gold_evidence_trace") from exc
        if issues:
            raise ValueError("invalid_gold_assessment_evidence")
        approved["gold_assessment"] = assessment.model_dump()
    return approved


def export_trajectories(
    result: Mapping[str, Any], supervision: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Create stage records and explicit skip reasons without modifying a run.

    ``supervision`` is out-of-band curator metadata: ``approved=True``, a
    nonempty ``curator`` and ``label_source_ids`` are mandatory. An optional
    ``gold_assessment`` must satisfy the public Assessment/evidence contracts.
    ``curated_stage_indices`` can explicitly retain rejected completed stages;
    these remain workflow examples, not gold predictions.
    """
    exported: dict[str, list[dict[str, Any]]] = {"records": [], "skipped": []}
    if result.get("status") != "completed" or result.get("evidence_validation", {}).get("status") != "passed":
        exported["skipped"].append({"stage": "run", "reason": "run_not_accepted"})
        return exported
    approval = _supervision(supervision, result)
    trace = result.get("agent_trace")
    if not isinstance(trace, Mapping) or trace.get("schema_version") != "praxis.agent-trace.v1":
        exported["skipped"].append({"stage": "run", "reason": "missing_agent_trace"})
        return exported
    stages = trace.get("stages")
    if not isinstance(stages, list):
        exported["skipped"].append({"stage": "run", "reason": "invalid_agent_stages"})
        return exported
    secrets = _secrets(result) | _secrets(supervision)
    accepted_assessment = None
    try:
        accepted_assessment = _assessment(result.get("assessment")).model_dump()
    except (ValueError, TypeError, ValidationError):
        pass
    replacements = []
    for index, stage in enumerate(stages):
        name = stage.get("stage") if isinstance(stage, Mapping) else None
        skip = {"stage": name if name in STAGES else "unknown", "stage_index": index}
        if name not in STAGES:
            exported["skipped"].append({**skip, "reason": "invalid_stage"})
            continue
        if stage.get("status") != "completed":
            exported["skipped"].append({**skip, "reason": "stage_not_completed"})
            continue
        rejected = stage.get("accepted") is False or stage.get("rejected") is True
        if rejected and (approval is None or index not in approval["curated_stage_indices"]):
            exported["skipped"].append({**skip, "reason": "rejected_stage_not_curated"})
            continue
        try:
            messages = _public_messages(stage.get("messages"), stage.get("tools"), secrets)
            tools = _clean(stage.get("tools", []), secrets)
            _dump(messages)
            _dump(tools)
        except (TypeError, ValueError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) else "non_json_stage"
            exported["skipped"].append({**skip, "reason": reason})
            continue
        record = {
            "schema_version": "praxis.supervised-trajectory.v1",
            "task": {"type": "analyze_candidate", "candidate_id": result.get("candidate", {}).get("id"),
                     "profile_id": result.get("profile", {}).get("profile_id")},
            "stage": name, "stage_index": index, "tools": tools, "messages": messages,
            "provenance": {"origin": "model_generated", "run_schema_version": result.get("schema_version"),
                           "agent_trace_schema_version": trace["schema_version"],
                           "model": stage.get("model") or result.get("execution_trace", {}).get("model")},
            "supervision": {"kind": "workflow_supervision" if approval else "evidence_tool_use",
                            "review_status": "approved" if approval else "needs_review",
                            "prediction_is_gold": False, "curator": approval["curator"] if approval else None,
                            "label_source_ids": approval["label_source_ids"] if approval else [],
                            "rejected_output_curated": rejected},
        }
        exported["records"].append(_clean(record, secrets))
        if name in {"analysis", "revision"} and not rejected:
            try:
                final = _assessment(messages[-1]["content"]).model_dump()
            except (ValueError, TypeError, ValidationError):
                continue
            if final == accepted_assessment:
                replacements.append(len(exported["records"]) - 1)
    if approval and "gold_assessment" in approval:
        if not replacements:
            raise ValueError("gold_requires_final_accepted_assessment_message")
        record = exported["records"][replacements[-1]]
        record["messages"][-1]["content"] = _dump(approval["gold_assessment"])
        record["supervision"].update(kind="gold_assessment", prediction_is_gold=True,
                                      target_origin="curator_supplied")
    return exported


def write_trajectories_jsonl(path: str | Path, exported: Mapping[str, Any]) -> int:
    """Write only exported records, retaining skip audit information in memory.

    This helper does not infer approval or transform reports into supervision.
    The caller should save ``skipped`` separately when a persistent audit is needed.
    """
    records = exported.get("records")
    if not isinstance(records, list) or any(not isinstance(record, Mapping) for record in records):
        raise ValueError("invalid_export_records")
    lines = [_dump(record) for record in records]
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return len(lines)
