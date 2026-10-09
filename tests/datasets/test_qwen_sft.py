from copy import deepcopy
import json

import pytest

from praxis_virtualcell.datasets import qwen_sft, strain_dataset
from praxis_virtualcell.datasets.labels import ExperimentRecord
from praxis_virtualcell.datasets.qwen_sft import prepare_qwen_sft, qwen_messages, validate_qwen_sft
from praxis_virtualcell.datasets.species_registry import _digest
from praxis_virtualcell.datasets.strain_supervision import prepare_strain_supervision
from tests.datasets.test_labels import payload


def fixture_components(tmp_path, monkeypatch):
    database = tmp_path / "database"
    database.mkdir()
    summary_path = database / "summary.json"
    summary_path.write_text("{}")
    frozen = tmp_path / "frozen.json"
    frozen.write_text(json.dumps({"status": "ready", "grouping": "scaffold"}))
    cases = []
    labels = tmp_path / "labels.jsonl"
    with labels.open("wb") as stream:
        for number, smiles, split, strain, study, medium, relation, value in (
            (1, "C1CCCCC1", "train", "A", "paper-a", "MHB", "=", 2.0),
            (2, "C1CCCCC1", "train", "A", "paper-a", "MHB", ">", 64.0),
            (3, "C1CCCCC1", "train", "A", "paper-a", "LB", "=", 8.0),
            (4, "c1ccccc1", "validation", "B", "paper-b", "MHB", "=", 777.0),
            (5, "c1ccncc1", "test", "B", "paper-b", "MHB", "=", 999.0),
            (6, "c1ccoc1", "test", None, "paper-c", "MHB", "=", 111.0),
        ):
            data = deepcopy(payload())
            data["record_id"] = f"experiment:{number}"
            data["molecule"]["canonical_smiles"] = smiles
            data["organism"].update(taxon_id=470, strain=strain, strain_namespace="source")
            data["source"].update(document_id=study, doi="10.1234/" + study)
            data["conditions"]["medium"] = medium
            data["endpoint"].update(relation=relation, value=value)
            record = ExperimentRecord.model_validate(data)
            offset = stream.tell()
            stream.write((record.model_dump_json() + "\n").encode())
            cases.append({"case_id": f"case-{number}", "split": split, "group_id": "group-" + smiles,
                          "candidate": {"id": f"case-{number}", "smiles": smiles},
                          "strain": {"strain_id": "strain-" + str(strain), "species": record.organism.species,
                                     "taxon_id": 470, "label": strain, "namespace": "source", "identity_basis": "source assay strain"},
                          "conditions": record.conditions.model_dump(exclude={"provenance"}),
                          "reference_profiles": {}, "profile_id": None,
                          "literature": {"doi": record.source.doi, "document_id": study},
                          "private_answer": {"path": str(labels), "byte_offset": offset, "line_number": number,
                                             "record_id": record.record_id, "label_file_id": 1}})
    for case in cases:
        case["private_answer"]["sha256"] = _digest(labels)
    (database / "cases.jsonl").write_text("".join(json.dumps(case) + "\n" for case in cases))
    dataset = {"frozen_manifest": {"path": str(frozen), "sha256": _digest(frozen)}}
    monkeypatch.setattr(strain_dataset, "validate_strain_dataset", lambda _: dataset)
    monkeypatch.setattr(qwen_sft, "validate_strain_dataset", lambda _: dataset)
    source = tmp_path / "components"
    prepare_strain_supervision(summary_path, source)
    return source, cases


def test_real_targets_preserve_censoring_and_conditions_without_heldout_answers(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / "qwen"
    result = prepare_qwen_sft(source, output)
    assert result["training_record_count"] == 2
    assert result["training_MIC_measurement_count"] == 3
    rows = [json.loads(line) for line in (output / "train.jsonl").read_text().splitlines()]
    distribution = next(json.loads(row["messages"][-1]["content"]) for row in rows
                        if len(json.loads(row["messages"][-1]["content"])["observations"]) == 2)
    assert [(row["relation"], row["value"]) for row in distribution["observations"]] == [("=", 2.0), (">", 64.0)]
    assert distribution["observations"][1]["lower_closed"] is False
    for path in output.glob("*.jsonl"):
        assert "777.0" not in path.read_text()
        assert "999.0" not in path.read_text()
        assert "111.0" not in path.read_text()
    for row in rows:
        assert "endpoint" not in json.dumps(row["messages"][1:-1])
        assert "source_refs" not in row
        assert row["source_record_id"] == row["record_id"]
    assert validate_qwen_sft(output)["schema_version"] == qwen_sft.SCHEMA


def test_cohorts_preserve_scaffold_and_test_checks_validation_groups(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    output = tmp_path / "qwen"
    result = prepare_qwen_sft(source, output)
    validation = json.loads((output / "validation.inputs.jsonl").read_text())
    test = json.loads((output / "test.inputs.jsonl").read_text())
    assert set(validation["cohorts"]) == set(qwen_sft._COHORTS)
    assert set(test["cohorts"]) == {"frozen_scaffold", "compound_unseen"}
    assert result["evaluation"]["test"]["cohorts"]["compound_strain_source_unseen"] == 0
    assert result["excluded"]["test_unknown_strain"] == 1
    assert validation["messages"][-1]["role"] == "user"
    assert "private_answer" not in json.dumps(test)


def test_modified_component_or_fabricated_target_is_rejected(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    path = source / "mic_sft.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    target = json.loads(rows[0]["messages"][-1]["content"])
    target["observations"][0]["value"] = 123.0
    rows[0]["messages"][-1]["content"] = json.dumps(target)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="component_changed"):
        prepare_qwen_sft(source, tmp_path / "qwen")
    summary_path = source / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["files"]["mic_sft.jsonl"]["sha256"] = _digest(path)
    summary_path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="differs_from_experiment"):
        prepare_qwen_sft(source, tmp_path / "qwen")
    assert not (tmp_path / "qwen").exists()


def test_leaked_scaffold_stops_export_and_nonempty_output_is_preserved(tmp_path, monkeypatch):
    source, cases = fixture_components(tmp_path, monkeypatch)
    dataset_path = json.loads((source / "summary.json").read_text())["dataset_summary"]
    cases[3]["group_id"] = cases[0]["group_id"]
    from pathlib import Path
    (Path(dataset_path).parent / "cases.jsonl").write_text("".join(json.dumps(case) + "\n" for case in cases))
    with pytest.raises(ValueError, match="scaffold_leakage"):
        prepare_qwen_sft(source, tmp_path / "qwen")
    output = tmp_path / "existing"
    output.mkdir()
    (output / "keep").write_text("original")
    with pytest.raises(FileExistsError):
        prepare_qwen_sft(source, output)
    assert (output / "keep").read_text() == "original"


def test_qwen_tool_arguments_are_objects_without_mutating_source():
    messages = [{"role": "assistant", "content": None, "tool_calls": [{"id": "call-1", "type": "function",
                 "function": {"name": "overview", "arguments": "{}"}}]},
                {"role": "tool", "tool_call_id": "call-1", "content": json.dumps({"name": "overview", "arguments": {}, "ok": True, "data": {}})}]
    result = qwen_messages(messages)
    assert result[0]["tool_calls"][0]["function"]["arguments"] == {}
    assert result[0]["content"] == ""
    assert messages[0]["tool_calls"][0]["function"]["arguments"] == "{}"


@pytest.mark.parametrize("messages", [
    [{"role": "assistant", "content": "", "reasoning_content": "hidden"}],
    [{"role": "tool", "tool_call_id": "unknown", "content": '{"name":"overview","ok":true}'}],
    [{"role": "assistant", "content": "", "tool_calls": [{"id": "call", "type": "function", "function": {"name": "query_MIC", "arguments": "{}"}}]}],
    [{"role": "assistant", "content": "", "tool_calls": [{"id": "call", "type": "function", "function": {"name": "overview", "arguments": "[]"}}]}],
])
def test_private_reasoning_or_MIC_lookup_and_unbound_tools_are_rejected(messages):
    with pytest.raises(ValueError):
        qwen_messages(messages)


def test_mechanism_annotations_are_review_only_and_integrity_checked(tmp_path, monkeypatch):
    source, _ = fixture_components(tmp_path, monkeypatch)
    joint = tmp_path / "joint"
    joint.mkdir()
    (joint / "joint_sft.jsonl").write_text(json.dumps({"record_id": "joint:one", "human_reviewed": False}) + "\n")
    output = tmp_path / "qwen"
    result = prepare_qwen_sft(source, output, joint_dir=joint)
    assert result["mechanism_training_records"] == 0
    assert result["mechanism_review_records"] == 1
    assert "joint:one" not in (output / "train.jsonl").read_text()
    (output / "train.jsonl").write_text("changed")
    with pytest.raises(ValueError, match="file_changed"):
        validate_qwen_sft(output)
