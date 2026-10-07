"""Species associations preserve heterogeneous labels without exposing answers."""
from __future__ import annotations

from copy import deepcopy
import json
import sqlite3

import pytest

from praxis_virtualcell.datasets.species_registry import (
    build_species_database, database_coverage, export_species_inputs,
    read_experimental_answer, register_references,
)
from tests.datasets.test_labels import payload
from tests.omics.test_species_reference import _references


def setup_data(root, records=None):
    profile_root = root / "profiles"
    profile_root.mkdir()
    _references(profile_root)
    references = {"references": [{
        "taxon_id": 470, "modality": name, "profile_id": f"source-{name}",
        "status": "ready", "selection_reason": f"Synthetic {name} software fixture",
    } for name in ("genome", "transcriptome", "proteome")], "gaps": []}
    selection = root / "selection.json"
    selection.write_text(json.dumps(references))
    labels = root / "labels.jsonl"
    first = payload()
    first["organism"]["taxon_id"] = 470
    first["source"].update(source_id="chembl:activity:1", activity_id="1", document_id="DOC1")
    first["source"]["measured_qualifier"] = "实验测量 MIC >64；评估答案，禁止作为输入。"
    second = deepcopy(first)
    second.update(record_id="activity:2")
    second["organism"].update(strain="different-experimental-strain", identity_evidence="unresolved")
    second["source"].update(source_id="chembl:activity:2", activity_id="2")
    second["endpoint"].update(value=8.0, relation="=")
    labels.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in (records or [first, second])))
    return profile_root, selection, labels


def test_species_links_preserve_individual_measurements_and_single_reference(tmp_path):
    root, selection, labels = setup_data(tmp_path)
    summary = build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    assert summary["MIC_records"] == 2 and summary["unique_compounds"] == 1
    assert not summary["raw_assets_copied"] and not summary["MIC_values_copied"]
    ab = next(item for item in summary["species"] if item["taxon_id"] == 470)
    assert ab["species_reference_input_records"] == 2
    assert set(ab["available_modalities"]) == {"genome", "transcriptome", "proteome"}
    db = summary["database"]
    assert read_experimental_answer(db, "activity:1").endpoint.relation == ">"
    assert read_experimental_answer(db, "activity:2").endpoint.value == 8.0
    with sqlite3.connect(db) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(experiments)")}
        assert not columns & {"value", "MIC", "lower", "upper", "endpoint"}
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM reference_modalities").fetchone()[0] == 3
        assert set(connection.execute("SELECT experimental_strain FROM experiments")) == {
            ("AB5075",), ("different-experimental-strain",)}
        case_id = connection.execute("SELECT case_id FROM experiments WHERE record_id='activity:2'").fetchone()[0]
    assert read_experimental_answer(db, case_id).endpoint.value == 8.0
    assert database_coverage(db)["MIC_records"] == 2


def test_inference_export_does_not_open_labels_or_reveal_experimental_identity(tmp_path):
    root, selection, labels = setup_data(tmp_path)
    summary = build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    labels.unlink()
    destination = tmp_path / "inputs.jsonl"
    assert export_species_inputs(summary["database"], destination) == 2
    inputs = [json.loads(line) for line in destination.read_text().splitlines()]
    assert inputs[0]["input"]["profile_id"] == inputs[1]["input"]["profile_id"] == "AB-SPECIES-REFERENCE"
    assert inputs[0]["input"]["organism"] == {"species": "Acinetobacter baumannii", "taxon_id": 470}
    text = destination.read_text()
    for forbidden in ("MIC", "endpoint", "64", "qualifier", "activity:", "AB5075", "different-experimental-strain", "DOC1"):
        assert forbidden not in text


def test_duplicate_native_activity_is_counted_once_across_curation_versions(tmp_path):
    root, selection, labels = setup_data(tmp_path)
    records = [json.loads(line) for line in labels.read_text().splitlines()]
    records[0]["record_id"] = "another-version:1"
    other = tmp_path / "other.jsonl"
    other.write_text(json.dumps(records[0]) + "\n")
    summary = build_species_database(selection, [labels, labels, other], tmp_path / "db", profile_root=root)
    assert summary["MIC_records"] == 2
    assert summary["duplicate_native_experiments_skipped"] == 1


@pytest.mark.parametrize("field", ["endpoint", "organism", "conditions", "assay"])
def test_conflicting_native_activity_answer_is_not_silently_deduplicated(tmp_path, field):
    root, selection, labels = setup_data(tmp_path)
    duplicate = json.loads(labels.read_text().splitlines()[0])
    if field == "endpoint":
        duplicate["endpoint"]["value"] = 128.0
    elif field == "organism":
        duplicate["organism"]["strain"] = "another-experimental-strain"
    elif field == "conditions":
        duplicate["conditions"]["medium"] = "different-medium"
    else:
        duplicate["source"]["assay_id"] = "different-assay"
    other = tmp_path / "changed.jsonl"
    other.write_text(json.dumps(duplicate) + "\n")
    with pytest.raises(ValueError, match="conflicting native experiment"):
        build_species_database(selection, [labels, other], tmp_path / "db", profile_root=root)
    assert not (tmp_path / "db/praxis_species_reference.sqlite3").exists()


def test_missing_modality_and_species_remain_explicit(tmp_path):
    root, selection, labels = setup_data(tmp_path)
    content = json.loads(selection.read_text())
    content["references"] = content["references"][:1]
    selection.write_text(json.dumps(content))
    summary = build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    ab = next(item for item in summary["species"] if item["taxon_id"] == 470)
    assert ab["available_modalities"] == ["genome"]
    assert ab["missing_modalities"] == ["transcriptome", "proteome"]
    ec = next(item for item in summary["species"] if item["taxon_id"] == 562)
    assert ec["profile_id"] is None and ec["species_reference_input_records"] == 0


def test_reference_selection_rejects_multiple_defaults_per_modality(tmp_path):
    root, selection, _ = setup_data(tmp_path)
    content = json.loads(selection.read_text())
    content["references"].append(content["references"][0])
    selection.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="only one"):
        register_references(selection, root)


@pytest.mark.parametrize("wrong_taxon", [562, 999])
def test_reference_species_mismatch_and_conflicting_label_taxonomy(tmp_path, wrong_taxon):
    root, selection, labels = setup_data(tmp_path)
    content = json.loads(selection.read_text())
    content["references"][0]["taxon_id"] = 562
    selection.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="species identity mismatch"):
        register_references(selection, root)
    content["references"][0]["taxon_id"] = 470
    selection.write_text(json.dumps(content))
    records = [json.loads(line) for line in labels.read_text().splitlines()]
    records[0]["organism"]["taxon_id"] = wrong_taxon
    labels.write_text("".join(json.dumps(r) + "\n" for r in records))
    summary = build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    assert summary["MIC_records"] == 1
    assert summary["excluded"] == {"conflicting_species_taxonomy": 1}


def test_changed_canonical_labels_and_output_overwrite_rejected(tmp_path):
    root, selection, labels = setup_data(tmp_path)
    summary = build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    with pytest.raises(ValueError, match="already exists"):
        build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    labels.write_text(labels.read_text().replace('"value": 64.0', '"value": 128.0'))
    with pytest.raises(ValueError, match="canonical label file changed"):
        read_experimental_answer(summary["database"], "activity:1")
