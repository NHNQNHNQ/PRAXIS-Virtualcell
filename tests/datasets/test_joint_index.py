from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from praxis_virtualcell.datasets.joint_index import (
    _select_samples, load_indexed_record, prepare_joint_inspection,
)
from praxis_virtualcell.datasets.joint_qwen_sft import prepare_joint_qwen_sft
from praxis_virtualcell.datasets.species_registry import _digest
from tests.datasets.test_joint_qwen_sft import joint_source  # noqa: F401


@pytest.fixture
def indexed_dataset(joint_source, tmp_path):
    source, joint, _, _, _, _, _ = joint_source
    dataset = tmp_path / "joint_qwen"
    prepare_joint_qwen_sft(source, joint, dataset)
    return dataset, source


def test_index_keeps_offsets_exact_and_exposes_source_review_quality(indexed_dataset, tmp_path):
    dataset, source = indexed_dataset
    output = tmp_path / "inspection"
    report = prepare_joint_inspection(dataset, output, component_dir=source)
    assert report["record_count"] == 1 and report["MIC_measurement_count"] == 2
    assert report["single_modality_record_count"] == 1 and report["multiple_modality_record_count"] == 0
    assert report["human_gold"] is False and report["heldout_MIC_sources_opened"] == 0
    assert report["table_counts"] == {"record": 1, "drug": 1, "strain": 1, "profile": 1, "paper": 1, "record_case": 2}
    preview = json.loads((output / "inspection_samples.json").read_text())["samples"][0]
    assert preview["strain"]["species"] == "Acinetobacter baumannii" and preview["strain"]["label"] == "A"
    assert preview["omics"]["selected_modalities"] == ["genome"]
    assert preview["omics"]["paired_with_MIC_experiment"] is False
    assert preview["mechanism_supervision"] == "agent_source_reviewed_weak_supervision"
    assert preview["mechanism_claims"][0]["evidence_grade"] == "author_proposed"
    with Path(preview["record_locator"]["file"]).open("rb") as stream:
        stream.seek(preview["record_locator"]["byte_offset"])
        expected = json.loads(stream.readline())
    resolved = load_indexed_record(output / "joint_index.sqlite", preview["record_id"])
    assert resolved["record"] == expected
    assert resolved["source_ref"]["record_id"] == preview["record_id"]
    with sqlite3.connect(output / "joint_index.sqlite") as connection:
        row = connection.execute("SELECT split, MIC_label_origin, human_gold, evidence_grade_summary FROM record").fetchone()
        assert row[:3] == ("train", "source_verified_experimental_MIC", 0)
        assert json.loads(row[3]) == {"author_proposed": 1}
        assert connection.execute("SELECT COUNT(*) FROM record_case").fetchone()[0] == 2
        columns = {row[1] for row in connection.execute("PRAGMA table_info(record)")}
        assert "messages" not in columns and "fulltext" not in columns
    assert set(path.name for path in output.iterdir()) == {"joint_index.sqlite", "inspection_samples.json", "manifest.json"}


def test_index_never_opens_native_MIC_labels_or_heldout_files(indexed_dataset, tmp_path, monkeypatch):
    dataset, source = indexed_dataset
    component_summary = json.loads((source / "summary.json").read_text())
    cases = [json.loads(line) for line in (Path(component_summary["dataset_summary"]).parent / "cases.jsonl").read_text().splitlines()]
    native_paths = {Path(case["private_answer"]["path"]).resolve() for case in cases}
    original_open = Path.open
    def isolated_open(path, *args, **kwargs):
        if path.resolve() in native_paths or path.name.startswith(("validation.", "test.")):
            raise AssertionError("Inspection attempted to open native/heldout MIC supervision.")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", isolated_open)
    result = prepare_joint_inspection(dataset, tmp_path / "isolated", component_dir=source)
    assert result["heldout_MIC_sources_opened"] == 0


@pytest.mark.parametrize("mutation", ["private_split", "case_split", "review_quality", "subset", "hash"])
def test_index_rejects_heldout_or_forged_training_bindings(indexed_dataset, tmp_path, mutation):
    dataset, source = indexed_dataset
    manifest = json.loads((dataset / "manifest.json").read_text())
    if mutation == "case_split":
        summary = json.loads((source / "summary.json").read_text())
        path = Path(summary["dataset_summary"]).parent / "cases.jsonl"
        cases = [json.loads(line) for line in path.read_text().splitlines()]
        for case in cases:
            if case["split"] == "train":
                case["split"] = "test"
        path.write_text("".join(json.dumps(row) + "\n" for row in cases))
    elif mutation == "subset":
        path = dataset / "joint.train.jsonl"
        row = json.loads(path.read_text())
        row["record_id"] = "joint:forged"
        path.write_text(json.dumps(row) + "\n")
        manifest["files"][path.name]["sha256"] = _digest(path)
    else:
        path = dataset / "source_refs.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        row = next(row for row in rows if "literature_review" in row)
        if mutation == "review_quality":
            row["human_gold"] = True
        else:
            row["split"] = "test"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        if mutation != "hash":
            manifest["files"][path.name]["sha256"] = _digest(path)
    (dataset / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        prepare_joint_inspection(dataset, tmp_path / "rejected", component_dir=source)
    assert not (tmp_path / "rejected").exists()


def test_sample_selection_uses_real_evidence_strains_and_available_modalities():
    samples = []
    for number, grade, strain, modalities in (
        (1, "experimental", "A", ["genome", "proteome"]),
        (2, "author_proposed", "A", ["genome", "proteome"]),
        (3, "unresolved", "A", ["genome", "proteome"]),
        (4, "experimental", "B", ["genome"]),
        (5, "experimental", "B", ["genome"]),
    ):
        samples.append({"record_id": f"joint:{number}", "mechanism_claims": [{"evidence_grade": grade}],
                        "strain": {"species": "same species", "label": strain},
                        "omics": {"selected_modalities": modalities}})
    before = deepcopy(samples)
    result = _select_samples(samples, 4)
    assert [row["record_id"] for row in result] == ["joint:1", "joint:2", "joint:3", "joint:4"]
    assert samples == before


def test_indexed_locator_rejects_changed_source_and_output_is_preserved(indexed_dataset, tmp_path):
    dataset, _ = indexed_dataset
    output = tmp_path / "inspection"
    prepare_joint_inspection(dataset, output)
    record_id = json.loads((dataset / "joint.train.jsonl").read_text())["record_id"]
    with pytest.raises(FileExistsError):
        prepare_joint_inspection(dataset, output)
    with (dataset / "joint.train.jsonl").open("a") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="source_changed"):
        load_indexed_record(output / "joint_index.sqlite", record_id)
    with pytest.raises(KeyError):
        load_indexed_record(output / "joint_index.sqlite", "joint:missing")
