"""Export frozen experimental MIC components into Qwen tool-chat records.

Experimental answers are assistant targets only. Evaluation keeps private label
locators instead of materializing held-out answers. Original scaffold assignments
are retained; stricter strain/source cohorts are subsets, never new random splits.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from .evaluation import _compound_key
from .labels import ExperimentRecord
from .species_registry import _digest, _json
from .strain_dataset import validate_strain_dataset
from .strain_supervision import _identity, _request, _rows, _view

SCHEMA = "praxis.qwen-MIC-chat.v1"
_COMPONENT_FILES = {"mic_sft.jsonl", "private_training_sources.jsonl", "observation_views.jsonl", "joint_review_queue.jsonl"}
_TOOLS = {"overview", "search_features", "query_features"}
_OBSERVATION_FIELDS = ("relation", "value", "lower", "upper", "lower_closed", "upper_closed")
_COHORTS = ("frozen_scaffold", "compound_unseen", "strain_unseen", "source_unseen", "compound_strain_source_unseen")


def qwen_messages(messages: list[dict]) -> list[dict]:
    """Use HF Qwen tool-chat arguments as objects; never export hidden reasoning."""
    result = deepcopy(messages)
    pending = {}
    for message in result:
        if message.get("role") not in {"system", "user", "assistant", "tool"}:
            raise ValueError("unsupported_chat_role")
        if set(message) - {"role", "content", "tool_calls", "tool_call_id"}:
            raise ValueError("private_or_unrecognized_chat_fields")
        if message.get("content") is None:
            message["content"] = ""
        if not isinstance(message.get("content"), str):
            raise ValueError("chat_content_must_be_text")
        for call in message.get("tool_calls", []):
            if message["role"] != "assistant" or call.get("type") != "function":
                raise ValueError("invalid_assistant_tool_call")
            function = call["function"]
            if function["name"] not in _TOOLS or call["id"] in pending:
                raise ValueError("unapproved_or_duplicate_tool_call")
            arguments = function["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, dict):
                raise ValueError("tool_arguments_must_be_object")
            function["arguments"] = arguments
            pending[call["id"]] = function
        if message["role"] == "tool":
            call = pending.pop(message.get("tool_call_id"), None)
            reply = json.loads(message["content"])
            if (call is None or reply.get("name") != call["name"]
                    or reply.get("arguments") != call["arguments"] or reply.get("ok") is not True):
                raise ValueError("unbound_or_failed_tool_reply")
    if pending:
        raise ValueError("unfinished_tool_trajectory")
    return result


def _group_keys(cases: list[dict]) -> dict[str, set[str]]:
    compounds, sources = set(), set()
    for case in cases:
        molecule = SimpleNamespace(molecule=SimpleNamespace(canonical_smiles=case["candidate"]["smiles"]))
        compounds.add(_compound_key(molecule))
        for name in ("doi", "document_id"):
            value = case["literature"].get(name)
            if value:
                sources.add(f"{name}:" + str(value).strip().casefold())
    return {"compound": compounds, "strain": {case["strain"]["strain_id"] for case in cases},
            "source": sources, "scaffold": {case["group_id"] for case in cases}}


def _cohorts(keys: dict, seen: dict) -> list[str]:
    unseen = {name: bool(keys[name]) and keys[name].isdisjoint(seen[name]) for name in keys}
    if not unseen["scaffold"]:
        raise ValueError("frozen_scaffold_leakage")
    result = ["frozen_scaffold"]
    result.extend(name + "_unseen" for name in ("compound", "strain", "source") if unseen[name])
    if all(unseen[name] for name in ("compound", "strain", "source")):
        result.append("compound_strain_source_unseen")
    return result


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(_json(row) + "\n" for row in rows), encoding="utf-8")


def prepare_qwen_sft(supervision_dir: str | Path, output_dir: str | Path, *, joint_dir: str | Path | None = None) -> dict:
    """Prepare train conversations, answer-free evaluation and provenance.

    No LLM, training, data download or original-asset copy is performed. Current
    mechanism paraphrases lack human review and remain an excluded review index.
    """
    source, output = Path(supervision_dir).resolve(), Path(output_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("qwen_sft_output_nonempty")
    if output == source or output.is_relative_to(source):
        raise ValueError("qwen_output_must_be_separate_from_components")
    summary_path = source / "summary.json"
    summary = json.loads(summary_path.read_text())
    if (summary.get("schema_version") != "praxis.strain-supervision.v1"
            or set(summary.get("files", {})) != _COMPONENT_FILES):
        raise ValueError("invalid_frozen_MIC_components")
    if _digest(Path(summary["dataset_summary"])) != summary["dataset_summary_sha256"]:
        raise ValueError("strain_dataset_snapshot_changed")
    for name, receipt in summary["files"].items():
        if _digest(source / name) != receipt["sha256"]:
            raise ValueError("MIC_component_changed")
    dataset = validate_strain_dataset(summary["dataset_summary"])
    if dataset["frozen_manifest"] is None:
        raise ValueError("frozen_scaffold_manifest_required")
    frozen = json.loads(Path(dataset["frozen_manifest"]["path"]).read_text())
    if frozen["grouping"] != "scaffold" or frozen["status"] != "ready":
        raise ValueError("ready_frozen_scaffold_split_required")
    cases = {row["case_id"]: row for row in _rows(Path(summary["dataset_summary"]).parent / "cases.jsonl")}
    components = _rows(source / "mic_sft.jsonl")
    private = {row["record_id"]: row["private_sources"] for row in _rows(source / "private_training_sources.jsonl")}
    views = {row["profile_id"]: row for row in _rows(source / "observation_views.jsonl")}
    train, provenance = [], []
    relations, scopes = Counter(), Counter()
    seen = {name: set() for name in ("compound", "strain", "source", "scaffold")}
    used_cases, used_records, measurement_count = set(), set(), 0
    label_paths = {case["private_answer"]["path"] for case in cases.values() if case["split"] == "train"}
    with ExitStack() as stack:
        streams = {path: stack.enter_context(Path(path).open("rb")) for path in label_paths}
        for component in components:
            if (component.get("schema_version") != "praxis.strain-component-sft.v1" or component.get("split") != "train"
                    or component.get("trainable") is not True or component.get("model_generated_target") is not False
                    or component.get("label_origin") != "source_verified_experimental_MIC"
                    or component.get("experimental_target_is_source_verified") is not True
                    or component.get("mechanism_supervision") != "not_supplied"):
                raise ValueError("unapproved_MIC_component")
            key = component["record_id"]
            if key in used_records:
                raise ValueError("duplicate_MIC_component")
            used_records.add(key)
            members = [cases[case_id] for case_id in component["case_ids"]]
            if (not members or any(case["split"] != "train" or case["strain"]["label"] is None for case in members)
                    or used_cases.intersection(component["case_ids"])):
                raise ValueError("train_case_split_or_identity_mismatch")
            used_cases.update(component["case_ids"])
            request = _request(members[0])
            if any(_request(case) != request for case in members):
                raise ValueError("heterogeneous_condition_distribution")
            messages = component["messages"]
            if json.loads(messages[1]["content"]) != request or messages[-1]["role"] != "assistant":
                raise ValueError("component_public_input_mismatch")
            expected_tools = views[request["profile_id"]]["messages"] if request["profile_id"] else []
            if messages[2:-1] != expected_tools:
                raise ValueError("component_tool_view_mismatch")
            observations = []
            source_rows = private[key]
            if [row["case_id"] for row in source_rows] != component["case_ids"]:
                raise ValueError("component_private_locator_mismatch")
            for case, source_row in zip(members, source_rows, strict=True):
                locator = case["private_answer"]
                if source_row["locator"] != locator:
                    raise ValueError("component_private_locator_mismatch")
                stream = streams[locator["path"]]
                stream.seek(locator["byte_offset"])
                answer = ExperimentRecord.model_validate_json(stream.readline())
                if (answer.record_id != locator["record_id"] or answer.molecule.canonical_smiles != request["candidate"]["smiles"]
                        or answer.organism.taxon_id != request["organism"]["taxon_id"]
                        or not answer.admission.label_eligible or answer.endpoint.kind != "MIC" or answer.endpoint.unit != "ug/mL"):
                    raise ValueError("experimental_MIC_answer_mismatch")
                observations.append({field: getattr(answer.endpoint, field) for field in _OBSERVATION_FIELDS})
                relations[answer.endpoint.relation] += 1
            target = {"endpoint": "MIC", "unit": "ug/mL", "observations": observations}
            if json.loads(messages[-1]["content"]) != target:
                raise ValueError("component_target_differs_from_experiment")
            if component["source_case_count"] != len(members):
                raise ValueError("MIC_measurement_count_mismatch")
            keys = _group_keys(members)
            for name, values in keys.items():
                seen[name].update(values)
            scopes[component["task_scope"]] += 1
            measurement_count += len(members)
            train.append({"record_id": key, "source_record_id": key, "task_scope": component["task_scope"],
                          "target_contract": component["target_contract"], "messages": qwen_messages(messages),
                          "tools": deepcopy(component["tools"])})
            provenance.append({"record_id": key, "split": "train", "source_refs": source_rows,
                               "groups": {name: sorted(values) for name, values in keys.items()},
                               "source_component": str(source / "mic_sft.jsonl")})
    if len(train) != summary["training_record_count"] or measurement_count != summary["training_MIC_measurement_count"]:
        raise ValueError("component_summary_count_mismatch")
    outputs = {"train.jsonl": train, "source_refs.jsonl": provenance}
    evaluation, excluded = {}, Counter()
    system = components[0]["messages"][0] if components else None
    tool_definitions = next((row["tools"] for row in components if row["tools"]), [])
    for split in ("validation", "test"):
        groups = defaultdict(list)
        for case in cases.values():
            if case["split"] != split:
                continue
            if case["strain"]["label"] is None:
                excluded[split + "_unknown_strain"] += 1
                continue
            groups[_identity(_request(case))].append(case)
        inputs, answers, counts = [], [], Counter()
        previous = {name: set(values) for name, values in seen.items()}
        for key, members in sorted(groups.items()):
            request = _request(members[0])
            keys = _group_keys(members)
            cohorts = _cohorts(keys, previous)
            counts.update(cohorts)
            messages = [deepcopy(system), {"role": "user", "content": _json(request)}]
            profile_id = request["profile_id"]
            if profile_id:
                if profile_id not in views:
                    native = next(iter(members[0]["reference_profiles"].values()))
                    views[profile_id] = _view(profile_id, Path(native["manifest_path"]).parent.parent)
                messages.extend(deepcopy(views[profile_id]["messages"]))
            record_id = split + ":" + key
            inputs.append({"record_id": record_id, "case_ids": [case["case_id"] for case in members],
                           "split": split, "cohorts": cohorts, "messages": qwen_messages(messages),
                           "tools": deepcopy(tool_definitions) if profile_id else [],
                           "target_contract": "praxis.conditional-MIC-distribution.v1"})
            answers.append({"record_id": record_id, "split": split, "cohorts": cohorts,
                            "groups": {name: sorted(values) for name, values in keys.items()},
                            "private_answer_refs": [{"case_id": case["case_id"], "locator": case["private_answer"]} for case in members]})
        # Test independence is checked against train AND validation, including
        # validation examples omitted from stricter cohorts.
        for members in groups.values():
            for name, values in _group_keys(members).items():
                seen[name].update(values)
        outputs[split + ".inputs.jsonl"] = inputs
        outputs[split + ".answers.index.jsonl"] = answers
        evaluation[split] = {"record_count": len(inputs), "measurement_count": sum(len(row["case_ids"]) for row in inputs),
                             "cohorts": {name: counts[name] for name in _COHORTS},
                             "comparison": "train" if split == "validation" else "train_and_validation"}
    review = []
    if joint_dir is not None:
        joint = Path(joint_dir).resolve()
        for row in _rows(joint / "joint_sft.jsonl"):
            review.append({"record_id": row["record_id"], "source_ref": str(joint / "joint_sft.jsonl"),
                           "trainable_in_this_export": False, "human_reviewed": row.get("human_reviewed", False),
                           "reason": "Mechanism paraphrases require separate human admission; MIC component already included."})
    outputs["mechanism_review.index.jsonl"] = review
    profile_count = len({row["observation_view_id"] for row in components if row["observation_view_id"]})
    report = {"schema_version": SCHEMA, "status": "prepared_not_trained", "training_record_count": len(train),
              "training_MIC_measurement_count": measurement_count, "training_scopes": dict(scopes),
              "training_omics_view_count": profile_count,
              "relations": dict(relations), "evaluation": evaluation, "excluded": dict(excluded),
              "mechanism_training_records": 0, "mechanism_review_records": len(review),
              "loss_mask": "assistant_only", "reasoning_content_exported": False,
              "raw_assets_copied": False, "heldout_MIC_values_materialized": False, "training_runs": 0,
              "source_refs": {"component_summary": {"path": str(summary_path), "sha256": _digest(summary_path)},
                              "strain_dataset_summary": {"path": summary["dataset_summary"], "sha256": summary["dataset_summary_sha256"]},
                              "frozen_scaffold_manifest": dataset["frozen_manifest"]},
              "limitations": [f"{scopes['strain_reference_MIC']} same-strain reference components use {profile_count} omics views; they are not paired MIC experiment samples.",
                              "Most auxiliary components have no omics and partially unknown culture conditions.",
                              "A frozen scaffold split does not hold out shared strains or papers. Stricter cohorts are explicit subsets and may be empty.",
                              "MIC distribution targets preserve empirical repeated/censored measurements; they are not calibrated predictive distributions.",
                              "This numeric component is not a complete activity/target/mechanism agent report."]}
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        _write_rows(output / name, rows)
    report["files"] = {name: {"sha256": _digest(output / name), "records": len(rows)} for name, rows in outputs.items()}
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def validate_qwen_sft(output_dir: str | Path) -> dict:
    """Check prepared file integrity and role/answer isolation before training."""
    root = Path(output_dir)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("invalid_qwen_sft_manifest")
    for name, receipt in manifest["files"].items():
        if _digest(root / name) != receipt["sha256"]:
            raise ValueError("prepared_Qwen_file_changed")
        rows = _rows(root / name)
        if len(rows) != receipt["records"]:
            raise ValueError("prepared_Qwen_count_changed")
        if name == "train.jsonl":
            for row in rows:
                qwen_messages(row["messages"])
                target = json.loads(row["messages"][-1]["content"])
                if row["messages"][-1]["role"] != "assistant" or set(target) != {"endpoint", "unit", "observations"}:
                    raise ValueError("invalid_numeric_training_target")
        elif name.endswith(".inputs.jsonl"):
            for row in rows:
                qwen_messages(row["messages"])
                if row["messages"][-1]["role"] == "assistant":
                    raise ValueError("heldout_answer_in_inference_messages")
    return manifest
