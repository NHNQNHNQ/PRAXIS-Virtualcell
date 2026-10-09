from copy import deepcopy
import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets.labels import ExperimentRecord
from praxis_virtualcell.datasets.species_registry import _digest
from praxis_virtualcell.datasets.strain_supervision import prepare_strain_supervision
from tests.datasets.test_labels import payload


def source_cases(tmp_path, monkeypatch):
    from praxis_virtualcell.datasets import strain_dataset

    base = tmp_path / "dataset"
    base.mkdir()
    summary = base / "summary.json"
    summary.write_text("{}")
    raw = []
    for number, relation, value in ((1, "=", 2.0), (2, ">", 64.0), (3, "=", 8.0), (4, "=", 999.0)):
        record = deepcopy(payload())
        record["record_id"] = f"experiment:{number}"
        record["organism"].update(taxon_id=470, strain="AB5075", strain_namespace="strain_reference")
        record["endpoint"].update(relation=relation, value=value)
        record["conditions"]["medium"] = "LB" if number == 3 else "MHB"
        raw.append(ExperimentRecord.model_validate(record))
    labels = tmp_path / "labels.jsonl"
    offsets = []
    with labels.open("wb") as stream:
        for record in raw:
            offsets.append(stream.tell())
            stream.write((record.model_dump_json() + "\n").encode())
    cases = []
    for number, record in enumerate(raw, 1):
        cases.append({"case_id": f"opaque-{number}", "split": "test" if number == 4 else "train",
                      "candidate": {"id": f"opaque-{number}", "smiles": record.molecule.canonical_smiles},
                      "strain": {"strain_id": "strain-a", "species": record.organism.species,
                                 "taxon_id": 470, "label": "AB5075", "namespace": "strain_reference",
                                 "identity_basis": "source assay strain"},
                      "conditions": record.conditions.model_dump(exclude={"provenance"}),
                      "reference_profiles": {}, "profile_id": None,
                      "literature": {"doi": "10.1234/answer-paper", "document_id": "private-study"},
                      "private_answer": {"path": str(labels), "sha256": _digest(labels), "label_file_id": 1,
                                         "byte_offset": offsets[number - 1], "line_number": number,
                                         "record_id": record.record_id}})
    (base / "cases.jsonl").write_text("".join(json.dumps(row) + "\n" for row in cases))
    monkeypatch.setattr(strain_dataset, "validate_strain_dataset", lambda _: {})
    return summary, cases, labels


def test_train_only_same_condition_distribution_and_distinct_conditions(tmp_path, monkeypatch):
    summary, _, _ = source_cases(tmp_path, monkeypatch)
    output = tmp_path / "training"
    result = prepare_strain_supervision(summary, output)
    assert result["training_record_count"] == 2
    assert result["training_MIC_measurement_count"] == 3
    assert result["MIC_without_omics_auxiliary_records"] == 2
    rows = [json.loads(line) for line in (output / "mic_sft.jsonl").read_text().splitlines()]
    combined = next(row for row in rows if row["source_case_count"] == 2)
    target = json.loads(combined["messages"][-1]["content"])
    assert [(r["relation"], r["value"]) for r in target["observations"]] == [("=", 2.0), (">", 64.0)]
    assert target["observations"][1]["lower"] == 64.0
    assert target["observations"][1]["lower_closed"] is False
    assert all(row["trainable"] and row["experimental_target_is_source_verified"] for row in rows)
    assert "999" not in (output / "mic_sft.jsonl").read_text()
    assert set(sum((row["case_ids"] for row in rows), [])) == {"opaque-1", "opaque-2", "opaque-3"}


def test_inference_messages_exclude_private_answers_and_answer_papers(tmp_path, monkeypatch):
    summary, _, _ = source_cases(tmp_path, monkeypatch)
    output = tmp_path / "training"
    prepare_strain_supervision(summary, output)
    for line in (output / "mic_sft.jsonl").read_text().splitlines():
        row = json.loads(line)
        request = json.loads(row["messages"][1]["content"])
        assert set(request) == {"candidate", "organism", "conditions", "profile_id", "prediction_scope", "available_modalities"}
        input_text = json.dumps(row["messages"][1:-1])
        for forbidden in ("endpoint", "private_answer", "answer-paper", "private-study", "labels.jsonl", "experiment:"):
            assert forbidden not in input_text


def test_source_context_quarantine_keeps_valid_measurement_in_same_group(tmp_path, monkeypatch):
    summary, _, _ = source_cases(tmp_path, monkeypatch)
    output = tmp_path / "training"
    result = prepare_strain_supervision(
        summary, output, exclude_training_records={"experiment:2": "co-agent assay"})
    assert result["training_record_count"] == 2
    assert result["training_MIC_measurement_count"] == 2
    assert result["quarantined_training_measurement_count"] == 1
    rows = [json.loads(line) for line in (output / "mic_sft.jsonl").read_text().splitlines()]
    assert {case for row in rows for case in row["case_ids"]} == {"opaque-1", "opaque-3"}
    assert "999" not in (output / "mic_sft.jsonl").read_text()
    quarantine = json.loads((output / "quarantined_training_measurements.jsonl").read_text())
    assert quarantine["case_id"] == "opaque-2"


@pytest.mark.parametrize("record_id", ["experiment:4", "experiment:missing"])
def test_quarantine_must_identify_a_training_measurement(tmp_path, monkeypatch, record_id):
    summary, _, _ = source_cases(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="quarantine_requires"):
        prepare_strain_supervision(summary, tmp_path / "training",
                                  exclude_training_records={record_id: "review required"})


def test_source_changes_and_wrong_record_locator_stop_training(tmp_path, monkeypatch):
    summary, cases, labels = source_cases(tmp_path, monkeypatch)
    labels.write_text(labels.read_text() + "\n")
    with pytest.raises(ValueError, match="source_changed"):
        prepare_strain_supervision(summary, tmp_path / "training")
    assert not (tmp_path / "training").exists()
    for case in cases:
        case["private_answer"]["sha256"] = _digest(labels)
    cases[0]["private_answer"]["record_id"] = "different-experiment"
    (summary.parent / "cases.jsonl").write_text("".join(json.dumps(row) + "\n" for row in cases))
    with pytest.raises(ValueError, match="identity_mismatch"):
        prepare_strain_supervision(summary, tmp_path / "training")


def test_unknown_strain_does_not_borrow_a_species_reference(tmp_path, monkeypatch):
    summary, cases, _ = source_cases(tmp_path, monkeypatch)
    cases[0]["strain"].update(label=None, identity_basis="unresolved")
    (summary.parent / "cases.jsonl").write_text("".join(json.dumps(row) + "\n" for row in cases))
    result = prepare_strain_supervision(summary, tmp_path / "training")
    assert result["training_MIC_measurement_count"] == 2
    assert result["excluded"]["unknown_strain_not_admitted_to_strain_sft"] == 1


def test_output_is_nonoverwriting_and_frozen_validation_runs_first(tmp_path, monkeypatch):
    summary, _, _ = source_cases(tmp_path, monkeypatch)
    output = tmp_path / "training"
    prepare_strain_supervision(summary, output)
    with pytest.raises(FileExistsError):
        prepare_strain_supervision(summary, output)
    from praxis_virtualcell.datasets import strain_dataset
    def changed(_):
        raise ValueError("frozen_source_changed")
    monkeypatch.setattr(strain_dataset, "validate_strain_dataset", changed)
    with pytest.raises(ValueError, match="frozen_source_changed"):
        prepare_strain_supervision(summary, tmp_path / "another")
    assert not (tmp_path / "another").exists()
