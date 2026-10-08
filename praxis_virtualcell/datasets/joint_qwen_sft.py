"""Export source-checked joint MIC/mechanism supervision without paper inputs.

Joint records replace their numeric components; they never add a second copy of
the same MIC supervision. Native articles, verbatim spans and filesystem paths
remain private provenance. Source review is recorded separately from human gold.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .joint_supervision import prepare_joint_supervision
from .qwen_sft import prepare_qwen_sft, qwen_messages, validate_qwen_sft
from .species_registry import _digest, _json
from .strain_supervision import _rows

SCHEMA = "praxis.qwen-MIC-mechanism-chat.v1"
TARGET_CONTRACT = "praxis.conditional-MIC-mechanism.v1"
_EVALUATION_FILES = tuple(f"{split}.{kind}.jsonl" for split in ("validation", "test")
                          for kind in ("inputs", "answers.index"))
_LOCAL_PATH = re.compile(r"(?<![A-Za-z0-9])/(?:Volumes|Users|home|private|tmp|mnt|scratch|data[12])/[^\s\"'<>;,]*")
_JOINT_SYSTEM = """根据候选分子结构、明确的菌株身份、已知实验条件和可用的参考组学估计 MIC，
并给出受证据范围限制的机制解析。参考组学可以来自同一菌株的不同实验条件，
不等于当前 MIC 实验的配对样本。未知条件和缺失组学保持未知。
输出 endpoint、unit、observations、mechanism_claims 和 mechanism_limitations。
observations 保留重复测量及 relation/value/lower/upper/lower_closed/upper_closed，
不把不等号替换成精确数值。机制 claim 保留 statement、evidence_grade、experiment_type、
target_names、mechanism_role、scope、sources（doi 与 locator_id）和 limitations。
mechanism_role 区分药物靶点、耐药机制、活性修饰因素和未确定角色；降解药物的耐药酶不是药物杀伤靶点。
作者假说、表型实验和直接靶点结合证据必须区分；未确认靶点时 target_names 为空。
通用机制不能升级为该菌株的靶点结合实验。参考组学的表达或存在不能证明靶点因果关系。
工具只提供实际组学观察。实验 MIC 和文献机制属于独立训练监督，推理时不得查询 MIC。
没有文献原文输入时不得编造逐字引文。只训练 assistant 输出与工具调用。"""


def _joint_sources(source: Path, joint: Path) -> tuple[Path, Path]:
    """Recover and verify the original compilation inputs, never trust a flag."""
    summary = json.loads((joint / "summary.json").read_text())
    if (summary.get("schema_version") != "praxis.joint-supervision.v1"
            or summary.get("source_reviewed") is not True
            or summary.get("model_generated_MIC_targets") is not False):
        raise ValueError("joint_export_requires_source_reviewed_experimental_MIC")
    receipts = summary.get("input_files", {})
    if len(receipts) != 5:
        raise ValueError("joint_export_requires_original_review_receipts")
    paths = {Path(path).resolve(): digest for path, digest in receipts.items()}
    for path, expected in paths.items():
        if _digest(path) != expected:
            raise ValueError("joint_review_input_changed")
    for name in ("mic_sft.jsonl", "joint_review_queue.jsonl"):
        if source / name not in paths:
            raise ValueError("joint_review_bound_to_different_components")
    papers = [path for path in paths if path.name == "papers.jsonl"]
    passages = [path for path in paths if path.name == "passages.jsonl"]
    if len(papers) != 1 or len(passages) != 1 or papers[0].parent != passages[0].parent:
        raise ValueError("joint_export_requires_bound_literature_snapshot")
    reviews = set(paths) - {source / "mic_sft.jsonl", source / "joint_review_queue.jsonl",
                           papers[0], passages[0]}
    if len(reviews) != 1:
        raise ValueError("joint_export_requires_one_annotation_source")
    return papers[0].parent, reviews.pop()


def _verified_joint_rows(source: Path, joint: Path) -> tuple[list[dict], list[dict]]:
    literature, reviews = _joint_sources(source, joint)
    # Recompilation verifies byte spans against native JATS, compound IDs and
    # canonical structures against MIC source rows, and exact strain views.
    with TemporaryDirectory(prefix="praxis-joint-verification-") as temporary:
        prepared = Path(temporary) / "joint"
        report = prepare_joint_supervision(source, literature, reviews, prepared)
        rows = _rows(joint / "joint_sft.jsonl")
        private = _rows(joint / "private_literature_reviews.jsonl")
        if (rows != _rows(prepared / "joint_sft.jsonl")
                or private != _rows(prepared / "private_literature_reviews.jsonl")):
            raise ValueError("joint_records_differ_from_verified_sources")
        if report["record_count"] != len(rows):
            raise ValueError("joint_review_record_count_mismatch")
    return rows, private


def _public_messages(messages: list[dict], path_map: dict[str, str]) -> list[dict]:
    """Keep biological values and tool binding; replace local path strings."""
    def identifier_for(path: str) -> str:
        identifier = "asset:" + hashlib.sha256(path.encode()).hexdigest()[:24]
        path_map[identifier] = path
        return identifier

    def replace(match: re.Match) -> str:
        return identifier_for(match.group())

    def public(value, key=None):
        if isinstance(value, str):
            if value.startswith("/") and key not in {"xpath", "pointer"}:
                return identifier_for(value)
            return _LOCAL_PATH.sub(replace, value)
        if isinstance(value, list):
            return [public(item) for item in value]
        if isinstance(value, dict):
            return {key: public(item, key) for key, item in value.items()}
        return value

    result = qwen_messages(messages)
    for message in result:
        content = message["content"]
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            message["content"] = public(content)
        else:
            message["content"] = _json(public(parsed))
        if "tool_calls" in message:
            message["tool_calls"] = public(message["tool_calls"])
    qwen_messages(result)
    return result


def _joint_target(row: dict) -> dict:
    source = json.loads(row["messages"][-1]["content"])
    scope = source["mechanism_scope"]
    limitations = source["mechanism_limitations"]
    claims = []
    for claim in source["literature_mechanisms"]:
        sources = sorted({(evidence["doi"], evidence["passage_id"]) for evidence in claim["evidence"]})
        claim_limitations = ["Agent source-reviewed paraphrase; not a human-reviewed mechanism gold label."]
        if claim["experiment_type"] != "target_binding":
            claim_limitations.append("This experiment does not establish direct target binding.")
        if not claim["strain_specific_experiment"]:
            claim_limitations.append("This is not a demonstrated strain-specific target experiment.")
        if claim["experiment_type"] == "enzyme_hydrolysis":
            claim_limitations.append("The named protein is a drug-hydrolyzing resistance enzyme, not a demonstrated drug-killing target.")
        claims.append({key: deepcopy(claim[key]) for key in
                       ("statement", "evidence_grade", "experiment_type", "target_names")}
                      | {"mechanism_role": claim.get("mechanism_role", "unresolved"),
                         "scope": scope, "sources": [{"doi": doi, "locator_id": locator}
                                                      for doi, locator in sources],
                         "limitations": claim_limitations})
    if not claims:
        raise ValueError("joint_export_requires_at_least_one_reviewed_claim")
    return {key: deepcopy(source[key]) for key in ("endpoint", "unit", "observations")} | {
        "mechanism_claims": claims, "mechanism_limitations": deepcopy(limitations)}


def prepare_joint_qwen_sft(component_dir: str | Path, joint_dirs: str | Path | list[str | Path],
                           output_dir: str | Path, *, base_qwen_dir: str | Path | None = None,
                           exclude_component_ids: dict[str, str] | set[str] | list[str] | None = None) -> dict:
    """Prepare native Qwen chat, replacing reviewed MIC components exactly once.

    Existing frozen numeric evaluation is retained. Mechanism claims are train
    annotations only: no held-out mechanism gold set is created or claimed.
    """
    source, output = Path(component_dir).resolve(), Path(output_dir).resolve()
    component_summary = json.loads((source / "summary.json").read_text())
    source_quarantine = []
    if component_summary.get("quarantined_training_measurement_count", 0):
        receipt = component_summary["quarantined_training_measurements"]
        quarantine_source = Path(receipt["path"])
        if _digest(quarantine_source) != receipt["sha256"]:
            raise ValueError("training_measurement_quarantine_changed")
        source_quarantine = _rows(quarantine_source)
        if len(source_quarantine) != component_summary["quarantined_training_measurement_count"]:
            raise ValueError("training_measurement_quarantine_count_mismatch")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("joint_qwen_output_nonempty")
    joints = ([joint_dirs] if isinstance(joint_dirs, (str, Path)) else joint_dirs)
    joints = [Path(path).resolve() for path in joints]
    if not joints or output == source or output.is_relative_to(source) or any(output == path for path in joints):
        raise ValueError("joint_qwen_output_must_be_separate_from_sources")
    base = Path(base_qwen_dir).resolve() if base_qwen_dir is not None else None
    if base is not None and (output == base or output.is_relative_to(base)):
        raise ValueError("joint_qwen_output_must_be_separate_from_base_export")
    excluded = (dict(exclude_component_ids) if isinstance(exclude_component_ids, dict) else
                {key: "Explicitly quarantined from supervision." for key in (exclude_component_ids or [])})
    if any(not isinstance(key, str) or not isinstance(reason, str) or not reason.strip()
           for key, reason in excluded.items()):
        raise ValueError("quarantine_requires_component_ID_and_reason")
    rows, private_reviews = [], {}
    for joint in joints:
        verified, provenance = _verified_joint_rows(source, joint)
        for row, review in zip(verified, provenance, strict=True):
            key = review["annotation"]["component_record_id"]
            if key in private_reviews:
                raise ValueError("duplicate_joint_component_review")
            private_reviews[key] = review
            rows.append(row)
    if not rows:
        raise ValueError("joint_qwen_export_has_no_reviewed_components")

    # Revalidate the real numeric source and its frozen train/val/test groups.
    # This also prevents a forged base export from becoming the trust boundary.
    with TemporaryDirectory(prefix="praxis-joint-qwen-") as temporary:
        numeric = Path(temporary) / "numeric"
        numeric_manifest = prepare_qwen_sft(source, numeric)
        if base is not None:
            validate_qwen_sft(base)
            for name in ("train.jsonl", "source_refs.jsonl", *_EVALUATION_FILES):
                if _digest(base / name) != _digest(numeric / name):
                    raise ValueError("base_qwen_export_differs_from_frozen_components")
        original = {row["record_id"]: row for row in _rows(numeric / "train.jsonl")}
        provenance = {row["record_id"]: row for row in _rows(numeric / "source_refs.jsonl")}
        if set(excluded) - set(original):
            raise ValueError("quarantined_component_not_in_frozen_training_set")
        if set(excluded).intersection(private_reviews):
            raise ValueError("reviewed_joint_component_is_quarantined")
        replacements, grades, views = {}, Counter(), set()
        for row in rows:
            component_id = "mic:" + row["record_id"].removeprefix("joint:")
            if (row.get("split") != "train" or row.get("trainable") is not True
                    or row.get("mechanism_supervision") != "source_reviewed_literature"
                    or component_id not in original or component_id not in private_reviews):
                raise ValueError("joint_export_requires_bound_train_component")
            component = original[component_id]
            if qwen_messages(row["messages"])[1:-1] != component["messages"][1:-1] or row["tools"] != component["tools"]:
                raise ValueError("joint_input_or_tools_differ_from_numeric_component")
            request = json.loads(row["messages"][1]["content"])
            if (not request.get("profile_id") or not request.get("available_modalities")
                    or request.get("prediction_scope") != "strain_reference"
                    or request["organism"].get("identity_basis") not in {
                        "exact_source_reference_label", "exact_native_reference_label_with_assembly_accession"}
                    or not request["organism"].get("label")):
                raise ValueError("joint_export_requires_explicit_same_strain_omics")
            target = _joint_target(row)
            numeric_target = json.loads(component["messages"][-1]["content"])
            if {key: target[key] for key in numeric_target} != numeric_target:
                raise ValueError("joint_MIC_target_differs_from_verified_numeric_component")
            messages = deepcopy(component["messages"])
            messages[0]["content"] = _JOINT_SYSTEM
            messages[-1]["content"] = _json(target)
            replacements[component_id] = {"record_id": row["record_id"], "source_record_id": component_id,
                                          "task_scope": "strain_reference_MIC_mechanism",
                                          "target_contract": TARGET_CONTRACT,
                                          "messages": messages, "tools": deepcopy(component["tools"])}
            views.add(request["profile_id"])
            grades.update(claim["evidence_grade"] for claim in target["mechanism_claims"])

        train, private = [], []
        for component_id, component in original.items():
            if component_id in excluded:
                continue
            record = replacements.get(component_id, deepcopy(component))
            paths = {}
            record["messages"] = _public_messages(record["messages"], paths)
            train.append(record)
            reference = deepcopy(provenance[component_id])
            reference.update(record_id=record["record_id"], component_id=component_id,
                             public_asset_paths=paths)
            if component_id in replacements:
                reference.update(literature_review=private_reviews[component_id],
                                 mechanism_admission="agent_source_reviewed", human_gold=False,
                                 inference_eligible=False)
            private.append(reference)
        joint_train = [row for row in train if row["source_record_id"] in replacements]
        quarantine = [{**deepcopy(provenance[key]), "component_id": key, "reason": reason,
                       "training_eligible": False} for key, reason in sorted(excluded.items())]
        excluded_measurements = sum(len(row["source_refs"]) for row in quarantine)
        report = {"schema_version": SCHEMA, "status": "prepared_not_trained",
                  "training_record_count": len(train),
                  "training_MIC_measurement_count": numeric_manifest["training_MIC_measurement_count"] - excluded_measurements,
                  "mechanism_training_records": len(replacements), "joint_training_record_ids": sorted(
                      row["record_id"] for row in replacements.values()),
                  "joint_omics_view_count": len(views), "mechanism_claim_grades": dict(grades),
                  "numeric_only_training_records": len(train) - len(replacements),
                  "training_with_omics_records": sum(bool(json.loads(row["messages"][1]["content"]).get("profile_id")) for row in train),
                  "training_omics_view_count": component_summary["observation_view_count"],
                  "quarantined_component_count": len(excluded),
                  "quarantined_MIC_measurement_count": excluded_measurements,
                  "upstream_quarantined_MIC_measurement_count": len(source_quarantine),
                  "upstream_quarantine_reason_counts": dict(Counter(
                      row["reason"].partition(":")[0] for row in source_quarantine)),
                  "duplicate_MIC_components": 0, "source_reviewed_mechanisms": True,
                  "human_gold_mechanism_records": 0, "heldout_mechanism_gold_records": 0,
                  "complete_agent_report_count": 0, "raw_assets_copied": False,
                  "literature_fulltext_in_inputs": False, "verbatim_quotes_in_targets": False,
                  "absolute_local_paths_in_public_messages": False,
                  "heldout_MIC_values_materialized": False, "loss_mask": "assistant_only",
                  "heldout_native_assay_context_review": "pending_before_formal_scoring",
                  "reasoning_content_exported": False, "training_runs": 0,
                  "evaluation": numeric_manifest["evaluation"],
                  "source_refs": {"component_summary": {"path": str(source / "summary.json"),
                                                         "sha256": _digest(source / "summary.json")},
                                  "joint_summaries": [{"path": str(path / "summary.json"),
                                                       "sha256": _digest(path / "summary.json")} for path in joints],
                                  "frozen_scaffold_manifest": numeric_manifest["source_refs"]["frozen_scaffold_manifest"]},
                  "limitations": ["Mechanism paraphrases were source-reviewed by an agent, not a human gold annotation team.",
                                   "Same-strain reference omics are not samples paired to the MIC measurement.",
                                   "The fixed tool trajectories do not supervise adaptive feature selection.",
                                   "Frozen MIC evaluation does not establish held-out mechanism accuracy.",
                                   "joint.train.jsonl is an alternative subset of train.jsonl, not an additional training source.",
                                   "Joint components replace numeric components; component and measurement counts are not inflated."]}
        output.mkdir(parents=True, exist_ok=True)
        prepared_rows = (("train.jsonl", train), ("joint.train.jsonl", joint_train), ("source_refs.jsonl", private),
                         ("quarantined_components.index.jsonl", quarantine),
                         ("quarantined_measurements.index.jsonl", source_quarantine))
        for name, records in prepared_rows:
            (output / name).write_text("".join(_json(row) + "\n" for row in records), encoding="utf-8")
        files = {name: len(records) for name, records in prepared_rows}
        # Derived evaluation rows are small; originals/raw omics are never copied.
        # Rewrite only public local paths, preserving record IDs and frozen cohorts.
        for name in _EVALUATION_FILES:
            records = _rows(numeric / name)
            if name.endswith(".inputs.jsonl"):
                for row in records:
                    row["messages"] = _public_messages(row["messages"], {})
            (output / name).write_text("".join(_json(row) + "\n" for row in records), encoding="utf-8")
            files[name] = len(records)
        report["files"] = {name: {"sha256": _digest(output / name), "records": count} for name, count in files.items()}
        (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_joint_qwen_sft(output)
    return report


def validate_joint_qwen_sft(output_dir: str | Path) -> dict:
    root = Path(output_dir)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("invalid_joint_qwen_manifest")
    components, mechanism_count = set(), 0
    for name, receipt in manifest["files"].items():
        if _digest(root / name) != receipt["sha256"]:
            raise ValueError("prepared_joint_Qwen_file_changed")
        records = _rows(root / name)
        if len(records) != receipt["records"]:
            raise ValueError("prepared_joint_Qwen_count_changed")
        if name == "train.jsonl":
            for row in records:
                if row["source_record_id"] in components:
                    raise ValueError("duplicate_joint_numeric_MIC_component")
                components.add(row["source_record_id"])
                qwen_messages(row["messages"])
                target = json.loads(row["messages"][-1]["content"])
                if row["messages"][-1]["role"] != "assistant":
                    raise ValueError("joint_training_requires_final_assistant")
                if row["target_contract"] == TARGET_CONTRACT:
                    mechanism_count += 1
                    if set(target) != {"endpoint", "unit", "observations", "mechanism_claims", "mechanism_limitations"}:
                        raise ValueError("invalid_joint_training_target")
                    for claim in target["mechanism_claims"]:
                        if set(claim) != {"statement", "evidence_grade", "experiment_type", "target_names", "mechanism_role", "scope", "sources", "limitations"}:
                            raise ValueError("private_or_unrecognized_mechanism_target_field")
                        if any(set(item) != {"doi", "locator_id"} for item in claim["sources"]):
                            raise ValueError("private_or_verbatim_mechanism_source")
                elif set(target) != {"endpoint", "unit", "observations"}:
                    raise ValueError("invalid_numeric_training_target")
                if _LOCAL_PATH.search(_json(row["messages"])):
                    raise ValueError("absolute_local_path_in_public_training_messages")
        elif name.endswith(".inputs.jsonl"):
            for row in records:
                qwen_messages(row["messages"])
                if row["messages"][-1]["role"] == "assistant":
                    raise ValueError("heldout_answer_in_joint_inference_messages")
                if _LOCAL_PATH.search(_json(row["messages"])):
                    raise ValueError("absolute_local_path_in_public_evaluation_messages")
    if mechanism_count != manifest["mechanism_training_records"] or len(components) != manifest["training_record_count"]:
        raise ValueError("joint_Qwen_manifest_count_mismatch")
    mixed = {row["record_id"]: row for row in _rows(root / "train.jsonl")}
    subset = _rows(root / "joint.train.jsonl")
    if (len(subset) != mechanism_count or len({row["record_id"] for row in subset}) != len(subset)
            or any(row != mixed.get(row["record_id"]) or row["target_contract"] != TARGET_CONTRACT for row in subset)):
        raise ValueError("joint_training_subset_does_not_match_mixed_export")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component-dir")
    parser.add_argument("--joint-dir", action="append")
    parser.add_argument("--base-qwen-dir")
    parser.add_argument("--exclude-components", help="JSON object mapping quarantined component IDs to reasons")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        result = validate_joint_qwen_sft(args.output_dir)
    else:
        if not args.component_dir or not args.joint_dir:
            parser.error("--component-dir and --joint-dir are required for export")
        result = prepare_joint_qwen_sft(args.component_dir, args.joint_dir, args.output_dir,
                                       base_qwen_dir=args.base_qwen_dir,
                                       exclude_component_ids=json.loads(Path(args.exclude_components).read_text())
                                       if args.exclude_components else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
