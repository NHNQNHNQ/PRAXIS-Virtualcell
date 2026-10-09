"""Add traceable species structure priors to sealed Assessment training rows.

This derivative never opens heldout answer indexes or their label sources.
Existing MIC/omics/literature provenance is shared by immutable file receipts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Callable

from praxis_virtualcell.llm_prediction.schemas import Assessment, StructureAnalysis

from .assessment_supervision import CONTRACT, validate_candidate
from .joint_qwen_sft import _LOCAL_PATH
from .species_registry import _digest, _json

DERIVATION_SCHEMA = "praxis.structure-supervision-derivative.v1"
_LIMITATIONS = [
    "Species-level reference architecture is weak supervision, not a measured strain-specific cell state.",
    "Strain genotype, membrane permeability, protein localization and current morphology remain unknown.",
    "Unknown genotype does not establish wild type; reference omics are not a current MIC-paired sample.",
    "Candidate-specific access, transport, target engagement and killing are unmeasured and remain unknown.",
]


def _receipt(path: Path, expected: dict | None = None) -> dict:
    digest = _digest(path)
    if expected is not None and digest != expected["sha256"]:
        raise ValueError(f"sealed_base_file_changed:{path.name}")
    return {"path": str(path), "sha256": digest,
            **({"records": expected["records"]} if expected and "records" in expected else {})}


def resolve_shared_file(dataset_dir: str | Path, name: str) -> Path:
    """Resolve a v4 shared small index without copying its source labels/raw data."""
    root = Path(dataset_dir).resolve()
    local = root / name
    if local.is_file():
        return local
    manifest = json.loads((root / "manifest.json").read_text())
    receipt = manifest.get("shared_files", {}).get(name)
    if not receipt:
        raise FileNotFoundError(name)
    path = (root / receipt["path"]).resolve()
    _receipt(path, manifest["files"][name])
    return path


def _request(row: dict) -> dict:
    users = [message for message in row["messages"] if message["role"] == "user"]
    if len(users) != 1:
        raise ValueError("structure_derivative_requires_one_original_request")
    request = json.loads(users[0]["content"])
    validate_candidate(request["candidate"])
    return request


def structure_analysis(call: dict) -> dict:
    """Copy source facts as scoped hypotheses, never candidate accessibility gold."""
    if call.get("name") not in {"cell_structure_overview", "query_cell_structure"} or call.get("ok") is not True:
        raise ValueError("structure_teacher_requires_successful_real_overview")
    coverage = call["data"].get("coverage", {})
    if (coverage.get("current_state_supported") is True or coverage.get("strain_evidence_count", 0) != 0
            or coverage.get("protein_localization_count", 0) != 0):
        raise ValueError("initial_structure_derivative_requires_unknown_strain_state")
    rows = call["data"].get("structures", [])
    if not rows or len(rows) > 20:
        raise ValueError("structure_teacher_requires_1_to_20_species_prior_rows")
    hypotheses, barriers = [], []
    for index, row in enumerate(rows):
        if (row.get("evidence_scope") != "species_prior" or row.get("evidence_type") != "reference_knowledge"
                or row.get("protein_id") is not None or row.get("protein_namespace") is not None):
            raise ValueError("initial_structure_derivative_requires_species_prior_without_protein_localization")
        refs = [{"tool_call_id": call["tool_call_id"], "source_id": row["source_id"],
                 "pointer": f"/structures/{index}/{field}", "value": row[field]}
                for field in ("statement", "compartment")]
        item = {"structure_id": row["structure_id"], "compartment": row["compartment"],
                "evidence_scope": row["evidence_scope"], "evidence_type": row["evidence_type"],
                "hypothesis": row["statement"],
                "status": "hypothesis", "evidence_refs": refs}
        hypotheses.append(item)
        if row.get("kind") == "compartment" and any(
                term in row["compartment"].casefold() for term in ("membrane", "wall", "envelope")):
            barriers.append({**deepcopy(item), "accessibility": "unknown",
                             "hypothesis": "Candidate-specific accessibility across this reference compartment is unknown; no permeability or transport measurement is supplied."})
    return StructureAnalysis(compartment_hypotheses=hypotheses, accessibility_barriers=barriers,
                             limitations=_LIMITATIONS).model_dump(exclude_none=True)


def _real_executor(*, omics_data_root=None, catalog_path=None, structure_view="compartment_nodes") -> Callable:
    from praxis_virtualcell.cell_structure import cell_structure_overview, query_cell_structure
    from praxis_virtualcell.omics import load_profile
    profiles = {}

    def execute(request: dict) -> dict:
        profile_id = request["profile_id"]
        if profile_id not in profiles:
            profiles[profile_id] = load_profile(profile_id, data_root=omics_data_root)
        # Each teacher call executes the actual structure API. Only parsed
        # reference profiles are cached; no MIC or mechanism answer is supplied.
        overview = profiles[profile_id].overview()
        if overview["species"]["taxonomy_id"] != "NCBITaxon:" + str(request["organism"]["taxon_id"]):
            raise ValueError("structure_reference_profile_taxon_differs_from_request")
        structures = cell_structure_overview(overview, catalog_path=catalog_path)
        if structure_view == "full":
            return structures
        ids = [row["structure_id"] for row in structures["structures"] if row["kind"] == "compartment"]
        if not ids:
            raise ValueError("structure_reference_has_no_compartment_nodes")
        return query_cell_structure(overview, structure_ids=ids, limit=len(ids), catalog_path=catalog_path)
    return execute


def _tool_definitions() -> tuple[list[dict], str]:
    from praxis_virtualcell.llm_prediction.workflow import CELL_STRUCTURE_SYSTEM, CELL_STRUCTURE_TOOLS
    return deepcopy(CELL_STRUCTURE_TOOLS), CELL_STRUCTURE_SYSTEM


def _add_tools(row: dict, tools: list[dict], system: str) -> dict:
    result = deepcopy(row)
    result["messages"][0]["content"] += "\n" + system
    known = {item["function"]["name"] for item in result["tools"]}
    result["tools"].extend(deepcopy(item) for item in tools if item["function"]["name"] not in known)
    return result


def augment_training_record(row: dict, execute: Callable, *, tools: list[dict], system: str,
                            structure_view="compartment_nodes") -> tuple[dict, dict]:
    request = _request(row)
    if not request.get("profile_id"):
        raise ValueError("structure_training_requires_verified_reference_profile")
    # The executor sees only organism/profile metadata, never a supervised
    # target, candidate identity, MIC value or literature mechanism answer.
    context = {"profile_id": request["profile_id"], "organism": deepcopy(request["organism"])}
    data = execute(context)
    if _LOCAL_PATH.search(_json(data)):
        raise ValueError("structure_tool_contains_private_local_path")
    if structure_view not in {"full", "compartment_nodes"}:
        raise ValueError("invalid_structure_view")
    name = "cell_structure_overview" if structure_view == "full" else "query_cell_structure"
    if structure_view == "compartment_nodes" and any(row["kind"] != "compartment" for row in data["structures"]):
        raise ValueError("compartment_nodes_teacher_returned_other_structure_kind")
    arguments = {} if structure_view == "full" else {
        "structure_ids": [row["structure_id"] for row in data["structures"]], "limit": len(data["structures"])}
    identifier = "structure-" + ("overview-" if structure_view == "full" else "query-") + hashlib.sha256(row["record_id"].encode()).hexdigest()[:20]
    call = {"tool_call_id": identifier, "name": name, "arguments": arguments, "ok": True, "data": data}
    result = _add_tools(row, tools, system)
    result["messages"][-1:-1] = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": identifier, "type": "function",
         "function": {"name": name, "arguments": arguments}}]},
        {"role": "tool", "tool_call_id": identifier, "content": _json(call)},
    ]
    original_target = json.loads(row["messages"][-1]["content"])
    if original_target.get("structure_analysis") is not None:
        raise ValueError("base_record_already_has_structure_supervision")
    target = {**original_target, "structure_analysis": structure_analysis(call)}
    Assessment.model_validate(target)
    from praxis_virtualcell.llm_prediction.evidence import validate_structure_evidence
    issues = validate_structure_evidence(Assessment.model_validate(target), [call])
    if issues:
        raise ValueError("structure_teacher_evidence_invalid:" + ",".join(issues))
    result["messages"][-1]["content"] = _json(target)
    return result, {"record_id": row["record_id"], "source_record_id": row["source_record_id"],
                    "profile_id": request["profile_id"], "tool_call_id": identifier,
                    "evidence_scope": "species_prior", "human_gold": False,
                    "current_strain_state_supported": False, "structure_rows": len(data["structures"])}


def prepare_structure_sft(base_dir: str | Path, output_dir: str | Path, *,
                          omics_data_root=None, catalog_path=None,
                          structure_view="compartment_nodes",
                          expected_base_manifest_sha256: str | None = None,
                          execute: Callable | None = None) -> dict:
    """Derive trainable public chat; leave the sealed base and shared indexes intact."""
    base, output = Path(base_dir).resolve(), Path(output_dir).resolve()
    if structure_view not in {"full", "compartment_nodes"}:
        raise ValueError("invalid_structure_view")
    if output == base or output.is_relative_to(base) or base.is_relative_to(output):
        raise ValueError("structure_output_must_be_separate_from_sealed_base")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("structure_output_nonempty")
    base_receipt = _receipt(base / "manifest.json")
    if expected_base_manifest_sha256 and base_receipt["sha256"] != expected_base_manifest_sha256:
        raise ValueError("sealed_base_manifest_changed")
    manifest = json.loads((base / "manifest.json").read_text())
    if manifest.get("assessment_supervision") is not True:
        raise ValueError("structure_derivative_requires_assessment_base")
    for name in ("train.jsonl", "validation.inputs.jsonl", "test.inputs.jsonl"):
        _receipt(base / name, manifest["files"][name])
    if catalog_path is None:
        catalog_path = Path(__file__).resolve().parents[2] / "data/cell_structure/catalog.json"
    catalog_receipt = _receipt(Path(catalog_path).resolve())
    executor = execute or _real_executor(omics_data_root=omics_data_root, catalog_path=catalog_path,
                                        structure_view=structure_view)
    tools, system = _tool_definitions()
    output.mkdir(parents=True, exist_ok=True)
    augmented, auxiliary, index, seen = 0, 0, [], set()
    joint_ids = set(manifest.get("joint_training_record_ids", []))
    with (base / "train.jsonl").open("rb") as source, (output / "train.jsonl").open("wb") as destination, \
            (output / "joint.train.jsonl").open("wb") as joint:
        for line_number, original in enumerate(source, 1):
            row = json.loads(original)
            if row["record_id"] in seen or row["target_contract"] != CONTRACT:
                raise ValueError("base_training_identity_or_contract_invalid")
            seen.add(row["record_id"])
            if _request(row).get("profile_id"):
                prepared, receipt = augment_training_record(row, executor, tools=tools, system=system,
                                                             structure_view=structure_view)
                encoded = (_json(prepared) + "\n").encode()
                receipt.update(line_number=line_number, byte_offset=destination.tell(), file="train.jsonl",
                               task_scope=row["task_scope"], omics_evidence_status="passed",
                               base_row_sha256=hashlib.sha256(original).hexdigest(),
                               derived_row_sha256=hashlib.sha256(encoded).hexdigest())
                index.append(receipt)
                augmented += 1
            else:
                encoded = original
                auxiliary += 1
            destination.write(encoded)
            if row["record_id"] in joint_ids:
                joint.write(encoded)
    if augmented != manifest["training_with_omics_records"] or len(seen) != manifest["training_record_count"]:
        raise ValueError("base_record_or_reference_profile_count_changed")
    if not joint_ids.issubset(seen):
        raise ValueError("joint_subset_identity_changed")
    derived_files = {"train.jsonl": len(seen), "joint.train.jsonl": len(joint_ids)}
    for split in ("validation", "test"):
        name = f"{split}.inputs.jsonl"
        count = 0
        with (base / name).open("rb") as source, (output / name).open("wb") as destination:
            for original in source:
                row = json.loads(original)
                # Tools operate on reference organism data at inference time;
                # export does not execute heldout tools or materialize answers.
                prepared = _add_tools(row, tools, system)
                destination.write((_json(prepared) + "\n").encode())
                count += 1
        derived_files[name] = count
    index_name = "structure.train.index.jsonl"
    (output / index_name).write_text("".join(_json(item) + "\n" for item in index), encoding="utf-8")
    derived_files[index_name] = augmented
    omics_name = "omics.train.index.jsonl"
    (output / omics_name).write_text("".join(_json({key: item[key] for key in
        ("record_id", "task_scope", "omics_evidence_status", "file", "line_number", "byte_offset")}) + "\n"
        for item in index), encoding="utf-8")
    derived_files[omics_name] = augmented
    shared_names = {name for name in manifest["files"] if name not in derived_files}
    relative_base = os.path.relpath(base, output)
    base_receipt["path"] = str(Path(relative_base) / "manifest.json")
    catalog_receipt["path"] = os.path.relpath(Path(catalog_path).resolve(), output)
    report = {**deepcopy(manifest),
              "status": "prepared_not_trained", "training_runs": 0,
              "structure_derivation": {"schema": DERIVATION_SCHEMA,
                  "base_dataset": {"path": relative_base, "manifest": base_receipt,
                                   "files": deepcopy(manifest["files"])},
                  "catalog": catalog_receipt, "structure_view": structure_view,
                  "retrieval_policy": "all_compartment_nodes" if structure_view == "compartment_nodes" else "full_topology",
                  "teacher_tool": "query_cell_structure" if structure_view == "compartment_nodes" else "cell_structure_overview",
                  "derived_files": sorted(derived_files)},
              "shared_files": {name: {"path": str(Path(relative_base) / name)}
                               for name in sorted(shared_names)},
              "files": {**{name: deepcopy(manifest["files"][name]) for name in shared_names},
                        **{name: {"sha256": _digest(output / name), "records": count}
                           for name, count in derived_files.items()}},
              "structure_supervision": {"records": augmented, "unchanged_auxiliary_records": auxiliary,
                   "scope": "species_prior", "current_strain_state_supported": False,
                   "human_gold_records": 0, "new_MIC_values": 0, "heldout_answers_opened": 0,
                   "heldout_structure_tools_executed": 0, "shared_indexes_copied": False},
              "limitations": [*manifest.get("limitations", []), *_LIMITATIONS]}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_structure_sft(output)
    return report


def validate_structure_sft(output_dir: str | Path) -> dict:
    """Verify derivative rows against v3 without reading any heldout answer file."""
    from praxis_virtualcell.llm_prediction.evidence import validate_structure_evidence
    root = Path(output_dir).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    derivation = manifest.get("structure_derivation", {})
    if derivation.get("schema") != DERIVATION_SCHEMA:
        raise ValueError("not_a_structure_derivative")
    base = (root / derivation["base_dataset"]["path"]).resolve()
    _receipt(base / "manifest.json", derivation["base_dataset"]["manifest"])
    _receipt((root / derivation["catalog"]["path"]).resolve(), derivation["catalog"])
    from praxis_virtualcell.cell_structure import load_catalog
    catalog = load_catalog(catalog_path=(root / derivation["catalog"]["path"]).resolve())
    native_facts = {fact.structure_id: fact.model_dump() for fact in catalog.structures}
    for name in ("train.jsonl", "validation.inputs.jsonl", "test.inputs.jsonl"):
        _receipt(base / name, derivation["base_dataset"]["files"][name])
    for name in derivation["derived_files"]:
        _receipt(root / name, manifest["files"][name])
    counts = {"augmented": 0, "auxiliary": 0}
    derivations = [json.loads(line) for line in (root / "structure.train.index.jsonl").read_text().splitlines()]
    indexed = {item["record_id"]: item for item in derivations}
    if len(indexed) != len(derivations):
        raise ValueError("duplicate_structure_derivation_index")
    tools, system = _tool_definitions()
    structure_view = derivation.get("structure_view", "full")
    tool_name = "query_cell_structure" if structure_view == "compartment_nodes" else "cell_structure_overview"
    joint_ids = set(manifest.get("joint_training_record_ids", []))
    joint_lines = []
    with (base / "train.jsonl").open("rb") as original, (root / "train.jsonl").open("rb") as derived:
        for line_number, (old_line, new_line) in enumerate(zip(original, derived, strict=True), 1):
            old, new = json.loads(old_line), json.loads(new_line)
            if old["record_id"] in joint_ids:
                joint_lines.append(new_line)
            if not _request(old).get("profile_id"):
                if old_line != new_line:
                    raise ValueError("auxiliary_training_row_changed")
                counts["auxiliary"] += 1
                continue
            if ({key: value for key, value in old.items() if key not in {"messages", "tools"}}
                    != {key: value for key, value in new.items() if key not in {"messages", "tools"}}):
                raise ValueError("training_record_identity_changed")
            if old["messages"][1:-1] != new["messages"][1:-3]:
                raise ValueError("original_request_or_tool_observations_changed")
            expected = _add_tools(old, tools, system)
            if new["tools"] != expected["tools"] or new["messages"][0] != expected["messages"][0]:
                raise ValueError("structure_tool_or_system_contract_changed")
            old_target, new_target = json.loads(old["messages"][-1]["content"]), json.loads(new["messages"][-1]["content"])
            if {key: value for key, value in new_target.items() if key != "structure_analysis"} != {
                    key: value for key, value in old_target.items() if key != "structure_analysis"}:
                raise ValueError("existing_MIC_or_mechanism_supervision_changed")
            call = json.loads(new["messages"][-2]["content"])
            request = _request(old)
            taxon = "NCBITaxon:" + str(request["organism"]["taxon_id"])
            if (call["data"].get("profile_id") != request["profile_id"]
                    or call["data"].get("request_scope", {}).get("taxonomy_id") != taxon
                    or any(row != native_facts.get(row.get("structure_id")) or row["scope"]["taxonomy_id"] != taxon
                           for row in call["data"].get("structures", []))):
                raise ValueError("structure_teacher_result_differs_from_native_catalog_or_request")
            if structure_view == "compartment_nodes":
                expected_ids = [fact.structure_id for fact in catalog.structures if fact.kind == "compartment"
                                and fact.scope.taxonomy_id == taxon and fact.evidence_scope == "species_prior"]
                arguments = {"structure_ids": expected_ids, "limit": len(expected_ids)}
                if [row["structure_id"] for row in call["data"]["structures"]] != expected_ids:
                    raise ValueError("structure_compartment_node_selection_changed")
            else:
                arguments = {}
            identifier = call["tool_call_id"]
            if (new["messages"][-2]["role"] != "tool" or new["messages"][-2]["tool_call_id"] != identifier
                    or call["name"] != tool_name or call["arguments"] != arguments or new["messages"][-3] != {
                        "role": "assistant", "content": "", "tool_calls": [{"id": identifier, "type": "function",
                        "function": {"name": tool_name, "arguments": arguments}}]}):
                raise ValueError("structure_teacher_tool_binding_changed")
            receipt = indexed.get(old["record_id"], {})
            if (receipt.get("line_number") != line_number or receipt.get("source_record_id") != old["source_record_id"]
                    or receipt.get("base_row_sha256") != hashlib.sha256(old_line).hexdigest()
                    or receipt.get("derived_row_sha256") != hashlib.sha256(new_line).hexdigest()):
                raise ValueError("structure_derivation_receipt_changed")
            if new_target["structure_analysis"] != structure_analysis(call):
                raise ValueError("structure_weak_target_differs_from_tool")
            issues = validate_structure_evidence(Assessment.model_validate(new_target), [call])
            if issues:
                raise ValueError("invalid_structure_evidence:" + ",".join(issues))
            counts["augmented"] += 1
    if (root / "joint.train.jsonl").read_bytes() != b"".join(joint_lines):
        raise ValueError("joint_subset_changed")
    for split in ("validation", "test"):
        name = f"{split}.inputs.jsonl"
        with (base / name).open() as original, (root / name).open() as derived:
            for old_line, new_line in zip(original, derived, strict=True):
                old, new = json.loads(old_line), json.loads(new_line)
                expected = _add_tools(old, tools, system)
                if new["messages"][0] != expected["messages"][0] or new["tools"] != expected["tools"]:
                    raise ValueError("heldout_structure_contract_changed")
                if ({key: value for key, value in old.items() if key not in {"messages", "tools"}}
                        != {key: value for key, value in new.items() if key not in {"messages", "tools"}}
                        or old["messages"][1:] != new["messages"][1:]):
                    raise ValueError("frozen_heldout_assignment_or_request_changed")
                # Sealed inputs can already contain observed omics trajectories.
                # Exact equality above preserves them without adding new
                # teacher calls, results, or supervised assistant targets.
    if (counts["augmented"] != manifest["structure_supervision"]["records"]
            or counts["auxiliary"] != manifest["structure_supervision"]["unchanged_auxiliary_records"]):
        raise ValueError("structure_derivative_count_mismatch")
    return {"status": "passed", "records": sum(counts.values()), **counts,
            "heldout_answers_opened": 0, "existing_MIC_and_mechanism_unchanged": True}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--omics-data-root")
    parser.add_argument("--catalog-path")
    parser.add_argument("--structure-view", choices=("compartment_nodes", "full"), default="compartment_nodes",
                        help="Compartment nodes only by default; full preserves the earlier topology diagnostic")
    parser.add_argument("--expected-base-manifest-sha256")
    args = parser.parse_args(argv)
    print(_json(prepare_structure_sft(args.base_dir, args.output_dir, omics_data_root=args.omics_data_root,
          catalog_path=args.catalog_path, structure_view=args.structure_view,
          expected_base_manifest_sha256=args.expected_base_manifest_sha256)))
