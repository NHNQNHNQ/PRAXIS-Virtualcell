#!/usr/bin/env python3
"""Generate frozen predictions from public inputs only, before private scoring.

Use the same command against the base model and the adapter service. It reads no
answer index or experimental label files. Omics tools read the selected profile.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import json
from pathlib import Path

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
    allowed = {tool["function"]["name"] for tool in tools}
    observed = []
    for message in messages:
        if message["role"] == "tool":
            call = json.loads(message["content"])
            call.setdefault("tool_call_id", message["tool_call_id"])
            observed.append(call)
    seen = {call["tool_call_id"] for call in observed}
    result = {"record_id": record["record_id"], "model": model, "status": "incomplete",
              "tool_calls": [], "token_usage": {}}
    for turn in range(max_turns):
        final = turn == max_turns - 1
        reply = await client.messages(model=model, messages=messages,
                                      tools=None if final else tools or None, max_tokens=max_tokens)
        choice = reply["choices"][0]
        message = choice["message"]
        for key, value in (reply.get("usage") or {}).items():
            if isinstance(value, int) and not isinstance(value, bool):
                result["token_usage"][key] = result["token_usage"].get(key, 0) + value
        if choice.get("finish_reason") == "length":
            result["reason"] = "output_truncated"
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
        target = Assessment.model_validate(_assessment_json(message.get("content")))
        issues = []
        if profile is not None:
            issues = validate_assessment_evidence(target, observed,
                                                  require_structure="cell_structure_overview" in allowed)
            overview = next((call["data"] for call in observed if call["name"] == "overview"), {})
            issues.extend(validate_modality_coverage(target, observed, overview.get("selected_modalities", [])))
        result.update(status="completed" if not issues else "unsupported", assessment=target.model_dump(),
                      evidence_validation={"status": ("passed" if not issues else "failed") if profile is not None
                                           else "not_applicable_auxiliary", "issues": sorted(set(issues))},
                      platform_eligible=profile is not None and not issues,
                      turns=turn + 1)
        return result
    result["reason"] = "turn_budget_exhausted"
    return result


async def run(args) -> None:
    # The explicit .inputs.jsonl boundary prevents accidentally passing train or
    # private answer files to the generator.
    inputs = Path(args.inputs)
    if not inputs.name.endswith(".inputs.jsonl"):
        raise ValueError("public_evaluation_inputs_required")
    output = Path(args.output)
    if output.exists():
        raise FileExistsError("prediction_output_exists")
    rows = [json.loads(line) for line in inputs.read_text().splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    output.parent.mkdir(parents=True, exist_ok=True)
    client = QwenAnalysisClient("local", args.base_url, timeout_s=600)
    try:
        with output.open("w") as stream:
            for row in rows:
                try:
                    result = await predict_record(row, client, model=args.model, data_root=args.data_root,
                                                  max_turns=args.max_turns, max_tokens=args.max_tokens)
                except Exception as exc:
                    result = {"record_id": row["record_id"], "model": args.model, "status": "error",
                              "exception_type": type(exc).__name__}
                stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                print(json.dumps({key: result.get(key) for key in ("record_id", "status", "turns", "reason")}))
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
    args = parser.parse_args()
    if args.limit < 0 or not 1 <= args.max_turns <= 20 or not 1 <= args.max_tokens <= 32768:
        parser.error("invalid_generation_budget")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
