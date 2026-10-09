"""Freeze a public, strain-balanced validation pilot without opening MIC answers."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from praxis_virtualcell.llm_prediction.schemas import Assessment

from .assessment_supervision import validate_candidate
from .joint_qwen_sft import _public_messages
from .qwen_sft import qwen_messages
from .species_registry import _digest, _json
from .structure_supervision import _add_tools, _real_executor, _tool_definitions

SEED = "praxis-v4-validation-pilot-20261008"
STRUCTURE_TOOLS = {"cell_structure_overview", "query_cell_structure"}
OMICS_TOOLS = {"overview", "search_features", "query_features"}
PUBLIC_FIELDS = {"record_id", "split", "case_ids", "cohorts", "target_contract", "messages", "tools"}


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _request(row: dict) -> dict:
    if set(row) - PUBLIC_FIELDS or row.get("split") != "validation":
        raise ValueError("public_validation_record_required")
    messages = qwen_messages(row["messages"])
    if any(m["role"] == "assistant" and not m.get("tool_calls") for m in messages):
        raise ValueError("validation_input_contains_assistant_answer")
    users = [m for m in messages if m["role"] == "user"]
    if len(users) != 1:
        raise ValueError("one_public_request_required")
    request = json.loads(users[0]["content"])
    if set(request) - {"candidate", "organism", "conditions", "available_modalities", "profile_id", "prediction_scope",
                       "assessment_schema"}:
        raise ValueError("private_or_unrecognized_request_fields")
    if "assessment_schema" in request and request["assessment_schema"] != Assessment.model_json_schema():
        raise ValueError("assessment_schema_must_equal_public_platform_contract")
    validate_candidate(request["candidate"])
    return request


def add_assessment_schema(row: dict) -> dict:
    """Supply the same public response contract as the platform workflow."""
    request = _request(row)
    request["assessment_schema"] = Assessment.model_json_schema()
    result = deepcopy(row)
    for message in result["messages"]:
        if message["role"] == "user":
            message["content"] = _json(request)
    return result


def select_public_rows(rows: list[dict], eligible_ids: set[str], *, count=64, seed=SEED) -> list[dict]:
    """Round-robin species × reference availability, then exact strain identity.

    Hash ordering is independent of JSONL order. No assay descriptions, labels,
    predictions or private answer locators participate in sampling.
    """
    if count < 1 or len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("invalid_pilot_count_or_duplicate_public_ID")
    rank = lambda value: hashlib.sha256((seed + "\0" + value).encode()).hexdigest()
    bins = defaultdict(lambda: defaultdict(list))
    for row in rows:
        request = _request(row)
        if row["record_id"] not in eligible_ids:
            continue
        organism = request["organism"]
        group = (request.get("profile_id") or
                 organism["namespace"] + ":" + organism["strain_id"])
        bins[(organism["taxon_id"], bool(request.get("profile_id")))][group].append(row)
    if sum(len(values) for groups in bins.values() for values in groups.values()) < count:
        raise ValueError("not_enough_eligible_public_records")
    queues = {}
    for key, groups in bins.items():
        ordered = [deque(sorted(groups[group], key=lambda row: rank(row["record_id"])))
                   for group in sorted(groups, key=rank)]
        queue = deque()
        while any(ordered):
            for group in ordered:
                if group:
                    queue.append(group.popleft())
        queues[key] = queue
    selected = []
    while len(selected) < count:
        for key in sorted(queues):
            if queues[key] and len(selected) < count:
                selected.append(queues[key].popleft())
    return selected


def _remove_tools(row: dict, names: set[str]) -> dict:
    result = deepcopy(row)
    removed = {call["id"] for message in result["messages"] for call in message.get("tool_calls", [])
               if call["function"]["name"] in names}
    messages = []
    for message in result["messages"]:
        if message["role"] == "tool" and message["tool_call_id"] in removed:
            continue
        if message.get("tool_calls"):
            message["tool_calls"] = [call for call in message["tool_calls"] if call["id"] not in removed]
            if not message["tool_calls"]:
                if message.get("content"):
                    raise ValueError("cannot_drop_assistant_text_with_removed_tool")
                continue
        messages.append(message)
    result["messages"] = messages
    result["tools"] = [tool for tool in result["tools"] if tool["function"]["name"] not in names]
    qwen_messages(messages)
    return result


def add_live_structure_context(row: dict, execute) -> dict:
    """Use the same full structure overview bootstrap as the runtime agent."""
    request = _request(row)
    if not request.get("profile_id"):
        result = _remove_tools(row, STRUCTURE_TOOLS)
        result["messages"][0]["content"] += (
            "\nNo verified reference profile or structure context is available for this auxiliary case. "
            "Do not call unavailable tools; keep structure evidence and localization unknown.")
        return result
    data = execute({"profile_id": request["profile_id"], "organism": deepcopy(request["organism"])})
    scope, organism = data.get("request_scope", {}), request["organism"]
    if (data.get("profile_id") != request["profile_id"] or
            scope.get("taxonomy_id") != "NCBITaxon:" + str(organism["taxon_id"]) or
            scope.get("strain") != organism["label"] or scope.get("strain_namespace") != organism["namespace"]):
        raise ValueError("structure_context_strain_identity_mismatch")
    identifier = "context-cell-structure"
    if any(m.get("tool_call_id") == identifier for m in row["messages"]):
        raise ValueError("structure_bootstrap_already_present")
    call = {"tool_call_id": identifier, "name": "cell_structure_overview", "arguments": {},
            "ok": True, "origin": "bootstrap", "data": data}
    context = _public_messages([
        {"role": "assistant", "content": "", "tool_calls": [{"id": identifier, "type": "function",
            "function": {"name": "cell_structure_overview", "arguments": {}}}]},
        {"role": "tool", "tool_call_id": identifier, "content": _json(call)}], {})
    result = deepcopy(row)
    result["messages"].extend(context)
    qwen_messages(result["messages"])
    return result


def paired_ablation(row: dict, *, remove: str, structure_system: str) -> dict:
    if not _request(row).get("profile_id") or remove not in {"omics", "structure"}:
        raise ValueError("paired_ablation_requires_reference_and_known_layer")
    result = _remove_tools(row, OMICS_TOOLS if remove == "omics" else STRUCTURE_TOOLS)
    if remove == "structure":
        result["messages"][0]["content"] = result["messages"][0]["content"].replace("\n" + structure_system, "")
        result["messages"][0]["content"] += "\nCell structure is withheld in this paired ablation; do not infer structural observations."
    else:
        for message in result["messages"]:
            if message["role"] == "user":
                request = json.loads(message["content"])
                request["available_modalities"] = []
                message["content"] = _json(request)
        result["messages"][0]["content"] += (
            "\nOmics observations and retrieval tools are withheld in this paired ablation. "
            "The reference profile identifies the sourced structure context only. Do not invent genes, RNA, "
            "protein measurements or omics citations; selected modalities are empty.")
    return result


def prepare_validation_pilot(dataset_dir, audit_path, output_dir, *, count=64, seed=SEED,
                             omics_data_root=None, catalog_path=None, execute=None) -> dict:
    """Read public validation and audit eligibility only; score with sealed v3."""
    root, output, audit_file = Path(dataset_dir).resolve(), Path(output_dir).resolve(), Path(audit_path).resolve()
    if output == root or output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("pilot_output_must_be_separate")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("pilot_output_nonempty")
    manifest = json.loads((root / "manifest.json").read_text())
    derivation = manifest.get("structure_derivation", {})
    base = (root / derivation["base_dataset"]["path"]).resolve()
    base_manifest_path = base / "manifest.json"
    if _digest(base_manifest_path) != derivation["base_dataset"]["manifest"]["sha256"]:
        raise ValueError("sealed_base_manifest_changed")
    base_manifest = json.loads(base_manifest_path.read_text())
    audit = json.loads(audit_file.read_text())
    if (audit.get("status") != "reviewed" or audit.get("split") != "validation" or
            audit.get("dataset_manifest_sha256") != _digest(base_manifest_path)):
        raise ValueError("reviewed_base_validation_audit_required")
    name = "validation.inputs.jsonl"
    for directory, metadata in ((root, manifest), (base, base_manifest)):
        if _digest(directory / name) != metadata["files"][name]["sha256"]:
            raise ValueError("sealed_public_input_changed")
    rows, originals = _rows(root / name), _rows(base / name)
    original_map = {row["record_id"]: row for row in originals}
    if len(original_map) != len(originals) or len(rows) != len(originals):
        raise ValueError("base_validation_IDs_changed")
    tools, system = _tool_definitions()
    for row in rows:
        if row != _add_tools(original_map.get(row["record_id"], {}), tools, system):
            raise ValueError("v4_public_input_differs_from_frozen_base")
    excluded = set(audit.get("excluded_record_ids", []))
    if excluded - original_map.keys() or audit.get("record_count") != len(rows):
        raise ValueError("audit_public_IDs_or_counts_mismatch")
    eligible = set(original_map) - excluded
    if audit.get("eligible_record_count") != len(eligible):
        raise ValueError("audit_eligible_count_mismatch")
    selected = select_public_rows(rows, eligible, count=count, seed=seed)
    executor = execute or _real_executor(omics_data_root=omics_data_root, catalog_path=catalog_path,
                                        structure_view="full")
    prepared = [add_assessment_schema(add_live_structure_context(row, executor)) for row in selected]
    reference_rows = [row for row in prepared if _request(row).get("profile_id")]
    variants = {"validation.inputs.jsonl": prepared,
                "without_structure.inputs.jsonl": [paired_ablation(row, remove="structure", structure_system=system)
                                                              for row in reference_rows],
                "without_omics.inputs.jsonl": [paired_ablation(row, remove="omics", structure_system=system)
                                                          for row in reference_rows]}
    output.mkdir(parents=True, exist_ok=True)
    for filename, variant in variants.items():
        (output / filename).write_text("".join(_json(row) + "\n" for row in variant), encoding="utf-8")
    def receipt(path):
        return {"path": os.path.relpath(path, output), "sha256": _digest(path)}
    requests = [_request(row) for row in prepared]
    report = {"schema_version": "praxis.public-validation-pilot.v1", "status": "prepared_public_only",
              "seed": seed, "selection": "species_reference_availability_then_exact_strain_round_robin_hash_order",
              "record_count": len(prepared), "paired_ablation_record_count": len(reference_rows),
              "record_ids": [row["record_id"] for row in prepared],
              "paired_ablation_record_ids": [row["record_id"] for row in reference_rows],
              "species_reference_counts": dict(Counter(str(r["organism"]["taxon_id"]) + ":" +
                                                  ("omics" if r.get("profile_id") else "auxiliary") for r in requests)),
              "reference_profile_counts": dict(Counter(r["profile_id"] for r in requests if r.get("profile_id"))),
              "source_public_inputs": receipt(root / name), "source_manifest": receipt(root / "manifest.json"),
              "scoring_dataset_manifest": receipt(base_manifest_path), "scoring_audit": receipt(audit_file),
              "files": {filename: {"sha256": _digest(output / filename), "records": len(variant)}
                        for filename, variant in variants.items()},
              "structure_bootstrap": "runtime cell_structure_overview; full sourced topology; species priors retain scope",
              "assessment_schema": {"source": "Assessment.model_json_schema(); same public contract as platform workflow",
                                    "sha256": hashlib.sha256(_json(Assessment.model_json_schema()).encode()).hexdigest(),
                                    "all_views_same_contract": True},
              "private_answers_opened": 0, "MIC_labels_opened": 0, "raw_assets_copied": False,
              "scoring": "Use the original v3 dataset and reviewed v3 audit with --pilot-subset; same record IDs.",
              "limitations": ["This balanced pilot is diagnostic, not a prevalence-weighted validation estimate.",
                              "Ablations retain compound, exact strain and requested conditions; no_omics clears selected modalities."]}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--seed", default=SEED)
    parser.add_argument("--omics-data-root")
    parser.add_argument("--catalog")
    args = parser.parse_args()
    if not 50 <= args.count <= 100:
        parser.error("public pilot count must be between 50 and 100")
    report = prepare_validation_pilot(args.dataset_dir, args.audit, args.output_dir, count=args.count,
                                     seed=args.seed, omics_data_root=args.omics_data_root, catalog_path=args.catalog)
    print(json.dumps({key: report[key] for key in ("status", "record_count", "paired_ablation_record_count",
                                                 "species_reference_counts", "reference_profile_counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
