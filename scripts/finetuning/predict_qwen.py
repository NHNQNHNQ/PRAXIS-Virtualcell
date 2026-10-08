#!/usr/bin/env python3
"""Generate frozen predictions from public inputs only, before private scoring.

Use the same command against the base model and the adapter service. It reads no
answer index or experimental label files. Omics tools read the selected profile.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
from uuid import uuid4

from praxis_virtualcell.datasets.joint_qwen_sft import _public_messages
from praxis_virtualcell.llm_prediction.evidence import validate_modality_coverage
from praxis_virtualcell.llm_prediction.qwen_serving import QwenAnalysisClient
from praxis_virtualcell.llm_prediction.schemas import Assessment
from praxis_virtualcell.llm_prediction.workflow import (
    _assessment_json, _execute, _load_organism, normalize_molecule, validate_assessment_evidence,
)


async def predict_record(record: dict, client, *, model: str, data_root: str,
                         max_turns: int = 4, max_tokens: int = 12288) -> dict:
    messages = deepcopy(record["messages"])
    if messages[-1]["role"] == "assistant":
        raise ValueError("evaluation_input_contains_final_answer")
    request = json.loads(next(message["content"] for message in messages if message["role"] == "user"))
    if set(request["candidate"]) != {"smiles"}:
        raise ValueError("candidate_input_must_be_SMILES_only")
    molecule = normalize_molecule(request["candidate"]["smiles"])
    profile = _load_organism(request["profile_id"], data_root) if request.get("profile_id") else None
    tools = record.get("tools") or []
    if request.get("available_modalities") == []:
        tools = [tool for tool in tools if tool["function"]["name"] in
                 {"cell_structure_overview", "query_cell_structure"}]
    allowed = {tool["function"]["name"] for tool in tools}
    observed = []
    for message in messages:
        if message["role"] == "tool":
            call = json.loads(message["content"])
            call.setdefault("tool_call_id", message["tool_call_id"])
            observed.append(call)
    if request.get("available_modalities") == [] and any(call.get("name") in {
            "overview", "query_genes", "search_annotations", "query_features", "search_features"} for call in observed):
        raise ValueError("omics_withheld_input_contains_omics_observations")
    seen = {call["tool_call_id"] for call in observed}
    result = {"record_id": record["record_id"], "model": model, "status": "incomplete",
              "tool_calls": [], "token_usage": {}, "generation_steps": []}
    for turn in range(max_turns):
        final = turn == max_turns - 1
        reply = await client.messages(model=model, messages=messages,
                                      tools=None if final else tools or None, max_tokens=max_tokens)
        choice = reply["choices"][0]
        message = choice["message"]
        result["generation_steps"].append({"turn": turn + 1, "finish_reason": choice.get("finish_reason"),
                                           "generation_budget": reply.get("generation_budget")})
        for key, value in (reply.get("usage") or {}).items():
            if isinstance(value, int) and not isinstance(value, bool):
                result["token_usage"][key] = result["token_usage"].get(key, 0) + value
        if choice.get("finish_reason") == "length":
            result["reason"] = "output_truncated"
            result["raw_response"] = message.get("content")
            return result
        calls = message.get("tool_calls") or []
        if calls:
            if final or len(calls) > 4:
                result["reason"] = "tool_turn_budget_exhausted"
                return result
            messages.append({key: message[key] for key in ("role", "content", "tool_calls") if key in message})
            for call in calls:
                function, call_id = call["function"], call["id"]
                if call_id in seen or function["name"] not in allowed or profile is None:
                    result["reason"] = "unapproved_or_duplicate_tool_call"
                    return result
                seen.add(call_id)
                arguments = function["arguments"]
                arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
                data = _execute(function["name"], arguments, profile, molecule, "candidate")
                if not isinstance(data, dict) or data.get("profile_id") != request["profile_id"]:
                    raise ValueError("tool_result_profile_identity_mismatch")
                tool = {"tool_call_id": call_id, "name": function["name"], "arguments": arguments,
                        "ok": True, "data": data}
                public = _public_messages([{"role": "assistant", "content": "", "tool_calls": [call]},
                                          {"role": "tool", "tool_call_id": call_id,
                                           "content": json.dumps(tool, ensure_ascii=False)}], {})[-1]
                tool = json.loads(public["content"])
                observed.append(tool)
                messages.append(public)
                result["tool_calls"].append(tool)
            continue
        result["raw_response"] = message.get("content")
        try:
            target = Assessment.model_validate(_assessment_json(message.get("content")))
        except (ValueError, TypeError) as exc:
            result.update(status="error", reason="invalid_final_assessment", exception_type=type(exc).__name__,
                          turns=turn + 1)
            return result
        issues = []
        selected_modalities = []
        if profile is not None:
            issues = validate_assessment_evidence(target, observed,
                require_structure=bool(allowed & {"cell_structure_overview", "query_cell_structure"}))
            overview = next((call["data"] for call in observed if call["name"] == "overview"), {})
            selected_modalities = overview.get("selected_modalities", [])
            if request.get("available_modalities") == []:
                selected_modalities = []
            issues.extend(validate_modality_coverage(target, observed, selected_modalities))
        # Experimental missing-input controls remain scoreable, while all
        # platform rejection reasons stay visible and platform admission stays false.
        withheld = request.get("available_modalities") == [] and bool(issues) and set(issues).issubset({
            "no_gene_observations_loaded", "mic_observations_require_verified_gene_evidence",
            "numeric_mic_requires_verified_gene_evidence"})
        evidence_status = ("passed" if not issues else "failed") if profile is not None else "not_applicable_auxiliary"
        if withheld:
            evidence_status = "not_applicable_omics_withheld"
        result.update(status="completed" if not issues or withheld else "unsupported", assessment=target.model_dump(),
                      evidence_validation={"status": evidence_status, "issues": sorted(set(issues)),
                                           "selected_modalities": selected_modalities},
                      platform_eligible=profile is not None and bool(selected_modalities) and not issues,
                      turns=turn + 1)
        return result
    result["reason"] = "turn_budget_exhausted"
    return result


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def _save_manifest(path, manifest):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    temporary.replace(path)


async def _service_identity(client, model):
    reply = await client._http.get("/health", timeout=30)
    reply.raise_for_status()
    health = reply.json()
    if (health.get("status") != "ok" or health.get("model") != model
            or health.get("enable_thinking") is not False or not isinstance(health.get("model_identity"), str)
            or not health["model_identity"]):
        raise ValueError("generation_service_identity_unverified")
    return {key: health.get(key) for key in
            ("model", "model_identity", "adapter_loaded", "max_context", "generation")}


def _existing_results(output, manifest, record_digests):
    if not output.exists():
        return {}
    content = output.read_text()
    if content and not content.endswith("\n"):
        raise ValueError("prediction_output_has_incomplete_last_line")
    seen = {}
    for line in content.splitlines():
        result = json.loads(line)
        record_id = result.get("record_id")
        if record_id not in record_digests or record_id in seen:
            raise ValueError("prediction_output_has_unknown_or_duplicate_record")
        if (result.get("run_identity") != manifest["run_identity"]
                or result.get("record_sha256") != record_digests[record_id]
                or result.get("model") != manifest["identity"]["model"]
                or result.get("status") not in {"completed", "unsupported", "incomplete", "error"}):
            raise ValueError("prediction_output_does_not_match_run")
        seen[record_id] = result["status"]
    return seen


def _update_progress(manifest, seen):
    manifest["processed_record_ids"] = list(seen)
    manifest["completed_record_ids"] = [key for key, status in seen.items() if status == "completed"]
    manifest["status_counts"] = dict(Counter(seen.values()))
    manifest["coverage"] = {"processed": len(seen), "expected": len(manifest["identity"]["record_ids"])}


async def run(args) -> None:
    # The explicit .inputs.jsonl boundary prevents accidentally passing train or
    # private answer files to the generator.
    inputs = Path(args.inputs)
    if not inputs.name.endswith(".inputs.jsonl"):
        raise ValueError("public_evaluation_inputs_required")
    output = Path(args.output)
    manifest_path = output.with_name(output.name + ".run.json")
    resume = getattr(args, "resume", False)
    if (output.exists() or manifest_path.exists()) and not resume:
        raise FileExistsError("prediction_output_exists")
    if resume and not manifest_path.is_file():
        raise ValueError("resume_requires_prediction_run_manifest")
    segment_start = time.monotonic()
    input_bytes = inputs.read_bytes()
    rows = [json.loads(line) for line in input_bytes.decode().splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    record_ids = [row.get("record_id") for row in rows]
    if not rows or any(not isinstance(value, str) or not value for value in record_ids) or len(set(record_ids)) != len(rows):
        raise ValueError("evaluation_record_ids_must_be_nonempty_and_unique")
    record_digests = {row["record_id"]: _digest(row) for row in rows}
    timeout = getattr(args, "record_timeout_seconds", 900)
    soft_limit = getattr(args, "max_seconds", 0)
    output.parent.mkdir(parents=True, exist_ok=True)
    client = QwenAnalysisClient("local", args.base_url, timeout_s=timeout)
    try:
        identity = {"input_path": str(inputs.resolve()), "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
                    "record_ids": record_ids, "model": args.model, "base_url": args.base_url.rstrip("/"),
                    "data_root": str(Path(args.data_root).resolve()),
                    "generation": {"max_turns": args.max_turns, "max_tokens": args.max_tokens,
                                   "record_timeout_seconds": timeout, "do_sample": False, "enable_thinking": False},
                    "service": await _service_identity(client, args.model)}
        if resume:
            manifest = json.loads(manifest_path.read_text())
            if (manifest.get("schema") != "praxis.qwen-prediction-run.v1" or manifest.get("identity") != identity
                    or getattr(args, "run_id", None) not in {None, manifest.get("run_id")}
                    or manifest.get("run_identity") != _digest({"run_id": manifest.get("run_id"), "identity": identity})):
                raise ValueError("prediction_resume_identity_mismatch")
        else:
            run_id = getattr(args, "run_id", None) or uuid4().hex
            manifest = {"schema": "praxis.qwen-prediction-run.v1", "run_id": run_id, "identity": identity,
                        "run_identity": _digest({"run_id": run_id, "identity": identity}), "segments": []}
        seen = _existing_results(output, manifest, record_digests)
        _update_progress(manifest, seen)
        _save_manifest(manifest_path, manifest)
        segment = {"started_at": datetime.now(timezone.utc).isoformat(), "resume": resume,
                   "max_seconds": soft_limit, "processed_at_start": len(seen), "processed_this_segment": 0,
                   "status": "completed"}
        with output.open("a" if resume else "x") as stream:
            for row in rows:
                if row["record_id"] in seen:
                    continue  # Errors and truncated/unsupported outputs also count as attempted coverage.
                if soft_limit and time.monotonic() - segment_start >= soft_limit:
                    segment["status"] = "soft_limit_reached"
                    break
                record_start = time.monotonic()
                try:
                    result = await asyncio.wait_for(
                        predict_record(row, client, model=args.model, data_root=args.data_root,
                                       max_turns=args.max_turns, max_tokens=args.max_tokens), timeout=timeout)
                except Exception as exc:
                    result = {"record_id": row["record_id"], "model": args.model, "status": "error",
                              "exception_type": type(exc).__name__,
                              "reason": "record_timeout" if isinstance(exc, TimeoutError) else "record_generation_failed"}
                    response = getattr(exc, "response", None)
                    if response is not None:
                        try:
                            result["service_error"] = response.json()
                        except ValueError:
                            pass
                result.update(run_id=manifest["run_id"], run_identity=manifest["run_identity"],
                              record_sha256=record_digests[row["record_id"]],
                              elapsed_seconds=round(time.monotonic() - record_start, 3),
                              finished_at=datetime.now(timezone.utc).isoformat())
                stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                seen[row["record_id"]] = result["status"]
                segment["processed_this_segment"] += 1
                _update_progress(manifest, seen)
                _save_manifest(manifest_path, manifest)
                progress = {key: result.get(key) for key in ("record_id", "status", "turns", "reason", "elapsed_seconds")}
                progress.update(processed=len(seen), expected=len(rows), status_counts=manifest["status_counts"])
                print(json.dumps(progress), flush=True)
        segment["elapsed_seconds"] = round(time.monotonic() - segment_start, 3)
        manifest["segments"].append(segment)
        _save_manifest(manifest_path, manifest)
        print(json.dumps({"segment": segment, "coverage": manifest["coverage"],
                          "run_id": manifest["run_id"]}), flush=True)
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--model", default="qwen-praxis-mic")
    parser.add_argument("--data-root", default="runtime/data/organisms")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=12288)
    parser.add_argument("--resume", action="store_true", help="Continue this exact run; never retry existing error rows")
    parser.add_argument("--run-id", help="Optional stable experiment name, checked when resuming")
    parser.add_argument("--max-seconds", type=float, default=0,
                        help="Segment soft wall limit, checked only between records; 0 disables it")
    parser.add_argument("--record-timeout-seconds", type=float, default=900,
                        help="Total wall limit for one record, including all tool turns")
    args = parser.parse_args()
    if args.limit < 0 or not 1 <= args.max_turns <= 20 or not 1 <= args.max_tokens <= 32768:
        parser.error("invalid_generation_budget")
    if (not math.isfinite(args.max_seconds) or args.max_seconds < 0
            or not math.isfinite(args.record_timeout_seconds) or args.record_timeout_seconds <= 0):
        parser.error("invalid_wall_time_budget")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
