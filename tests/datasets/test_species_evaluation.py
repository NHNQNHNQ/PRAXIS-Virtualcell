"""Global reference evaluation isolates sources and preserves heterogeneous MICs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from praxis_virtualcell.datasets.labels import ExperimentRecord
from praxis_virtualcell.datasets.species_evaluation import (
    freeze_species_evaluation, score_species_evaluation, validate_species_evaluation,
)
from praxis_virtualcell.datasets.species_registry import SPECIES, build_species_database
from tests.datasets.test_evaluation import experiment, prediction, rows, write_predictions, write_records
from tests.omics.test_multiomics_profiles import PROFILE_ID, _build


def sample(identifier, smiles="CCO", *, taxon=470, study="DOC0", relation="=", value=4.0, unit="ug/mL"):
    data = experiment(identifier, smiles, study=study, relation=relation, value=value, unit=unit).model_dump()
    data["organism"].update(species=SPECIES[taxon][0], taxon_id=taxon)
    data["molecule"]["identity_key"] = "test-structure:" + smiles
    return ExperimentRecord.model_validate(data)


def build_database(root, records, *, two_label_files=False):
    profiles = root / "profiles"
    profiles.mkdir()
    selected = []
    for taxon, (species, _) in SPECIES.items():
        for modality in ("genome", "transcriptome", "proteome"):
            manifest = _build(profiles, [modality])
            identity = {"scientific_name": species, "taxonomy_id": f"NCBITaxon:{taxon}"}
            profile_id = f"source-{taxon}-{modality}"
            manifest.update(profile_id=profile_id, species=identity)
            manifest["modalities"][modality]["species"] = identity
            directory = profiles / PROFILE_ID
            (directory / "manifest.json").write_text(json.dumps(manifest))
            directory.rename(profiles / profile_id)
            selected.append({"taxon_id": taxon, "modality": modality, "profile_id": profile_id,
                             "status": "ready", "selection_reason": "Synthetic software fixture"})
    selection = root / "selection.json"
    selection.write_text(json.dumps({"references": selected, "gaps": []}))
    sources = [write_records(root / "labels.jsonl", records)]
    if two_label_files:
        sources = [write_records(root / "labels.jsonl", records[::2]), write_records(root / "labels2.jsonl", records[1::2])]
    summary = build_species_database(selection, sources, root / "database", profile_root=profiles)
    return Path(summary["database"]), sources


def freeze(root, records, *, grouping="compound", **kwargs):
    database, sources = build_database(root, records)
    destination = root / "frozen"
    manifest = freeze_species_evaluation(database, destination, grouping=grouping, **kwargs)
    return destination / "manifest.json", manifest, sources


def index_by_record(path):
    return {row["record_id"]: row for row in rows(path.parent / "answers.index.jsonl")}


def test_compound_groups_cross_species_and_repeat_labels_without_mic_inputs(tmp_path):
    records = [sample("ab1"), sample("ab2", value=16.0), sample("ec1", taxon=562),
               sample("salt", "CC[OH2+].[Cl-]", taxon=573), sample("benzene", "c1ccccc1"),
               sample("pyridine", "c1ccncc1", taxon=287)]
    path, manifest, sources = freeze(tmp_path, records)
    indexed = index_by_record(path)
    family = [indexed[name] for name in ("ab1", "ab2", "ec1", "salt")]
    assert len({row["split"] for row in family}) == len({row["group_id"] for row in family}) == 1
    assert len({row["case_id"] for row in family}) == 4
    assert manifest["records"] == 6 and manifest["unique_input_count"] == 5 and manifest["independent_groups"] == 3
    assert len(manifest["references"]) == 12 and len(manifest["collections"]) == 4
    assert sum(item["records"] for item in manifest["splits"].values()) == 6
    assert validate_species_evaluation(path) == manifest
    text = (path.parent / "inputs.jsonl").read_text()
    for sentinel in ("MIC", "DO_NOT_EXPOSE_LABEL_SENTINEL", "CA-MHB", "AB5075", "DOC0", "TEST_ACTIVITY", '"value"', '"endpoint"'):
        assert sentinel not in text
    assert all(set(row["input"]) == {"candidate", "organism", "profile_id", "prediction_scope"} for row in rows(path.parent / "inputs.jsonl"))
    assert all(set(row) == {"case_id", "split", "group_id", "record_id", "label_file_id", "byte_offset", "line_number"} for row in indexed.values())
    with sqlite3.connect(manifest["database"]["path"]) as connection:
        assert {row[0] for row in connection.execute("SELECT case_id FROM experiments")} == {row["case_id"] for row in indexed.values()}
    assert [row["endpoint"]["value"] for row in rows(sources[0])][:2] == [4.0, 16.0]


def test_scaffold_global_split_groups_substitutions_and_acyclic_compounds(tmp_path):
    path, manifest, _ = freeze(tmp_path, [sample("ring-ab", "c1ccccc1"), sample("ring-ec", "Oc1ccccc1", taxon=562),
        sample("acyclic-ab", "CCO"), sample("acyclic-kp", "CCN", taxon=573),
        sample("pyridine", "c1ccncc1"), sample("cyclohexane", "C1CCCCC1")], grouping="scaffold")
    indexed = index_by_record(path)
    assert indexed["ring-ab"]["group_id"] == indexed["ring-ec"]["group_id"]
    assert indexed["acyclic-ab"]["group_id"] == indexed["acyclic-kp"]["group_id"]
    assert manifest["independent_groups"] == 4


def test_scaffold_study_is_transitive_across_species_and_reports_degenerate_groups(tmp_path):
    path, manifest, _ = freeze(tmp_path, [sample("a", "c1ccccc1", study="D1"),
        sample("b", "Oc1ccccc1", taxon=562, study="D2"),
        sample("c", "c1ccncc1", taxon=573, study="D2"),
        sample("d", "Oc1ccncc1", taxon=287, study="D3"), sample("e", "C1CCCCC1", study="D4")], grouping="scaffold_study")
    indexed = index_by_record(path)
    assert len({indexed[name]["group_id"] for name in "abcd"}) == 1
    assert manifest["status"] == "insufficient_groups" and manifest["independent_groups"] == 2
    assert manifest["largest_group_records"] == 4 and manifest["largest_group_fraction"] == 0.8
    assert manifest["splits"]["unassigned"]["records"] == 5
    assert manifest["splits"]["test"]["absent_species"] == [287, 470, 562, 573]
    assert all(row["split"] == "unassigned" for row in indexed.values())
    with pytest.raises(ValueError, match="evaluation_not_ready"):
        score_species_evaluation(path, write_predictions(tmp_path / "predictions.jsonl", []))


def test_study_split_is_global_and_missing_study_is_excluded(tmp_path):
    path, manifest, _ = freeze(tmp_path, [sample("same-ab", study="D1"), sample("same-ec", "CCN", taxon=562, study="D1"),
        sample("other", "c1ccccc1", study="D2"), sample("third", "c1ccncc1", study="D3"),
        sample("unknown", "C1CCCCC1", study=None)], grouping="study")
    indexed = index_by_record(path)
    assert indexed["same-ab"]["group_id"] == indexed["same-ec"]["group_id"]
    assert "unknown" not in indexed and manifest["excluded_records"] == 1
    assert rows(path.parent / "excluded.jsonl")[0]["reason"] == "study_identity_required"


@pytest.mark.parametrize("changed", ["database", "label", "native_manifest", "feature", "collection", "inputs", "answers"])
def test_version_drift_is_rejected_before_supervision_or_scoring(tmp_path, changed):
    path, manifest, sources = freeze(tmp_path, [sample("one"), sample("two", "c1ccccc1"), sample("three", "c1ccncc1")])
    target = {"database": Path(manifest["database"]["path"]), "label": sources[0],
              "native_manifest": Path(manifest["references"][0]["manifest"]["path"]),
              "feature": Path(manifest["references"][0]["assets"][0]["path"]),
              "collection": Path(manifest["collections"][0]["manifest"]["path"]),
              "inputs": path.parent / "inputs.jsonl", "answers": path.parent / "answers.index.jsonl"}[changed]
    with target.open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="frozen_source_changed"):
        validate_species_evaluation(path)
    with pytest.raises(ValueError, match="frozen_source_changed"):
        score_species_evaluation(path, tmp_path / "nonexistent-predictions.jsonl")


def test_multi_file_answer_locations_and_no_freeze_overwrite(tmp_path):
    database, sources = build_database(tmp_path, [sample("one"), sample("two", "c1ccccc1"),
        sample("three", "c1ccncc1"), sample("four", "C1CCCCC1")], two_label_files=True)
    destination = tmp_path / "frozen"
    manifest = freeze_species_evaluation(database, destination, grouping="compound")
    assert len(manifest["label_sources"]) == 2
    assert set(row["label_file_id"] for row in rows(destination / "answers.index.jsonl")) == {1, 2}
    before = {path.name: path.read_bytes() for path in destination.iterdir()}
    with pytest.raises(ValueError, match="destination_exists"):
        freeze_species_evaluation(database, destination, seed=1)
    assert before == {path.name: path.read_bytes() for path in destination.iterdir()}
    assert all(source.is_file() for source in sources)


def test_score_coverage_exact_steps_censoring_and_macro_species(tmp_path):
    path, manifest, _ = freeze(tmp_path, [sample("ab-exact", value=4.0), sample("ab-repeat", value=16.0),
        sample("ec-right", taxon=562, relation=">", value=8.0),
        sample("ec-left", taxon=562, relation="<=", value=8.0),
        sample("ec-interval", taxon=562, relation="interval"), sample("kp-null", taxon=573),
        sample("kp-wrong-unit", taxon=573, unit="uM"),
        sample("filler-a", "c1ccccc1"), sample("filler-b", "c1ccncc1")])
    indexed = index_by_record(path)
    split = indexed["ab-exact"]["split"]
    values = {"ab-exact": 8.0, "ab-repeat": 8.0, "ec-right": 8.0, "ec-left": 8.0, "ec-interval": 8.0}
    predictions = [prediction(indexed[record]["case_id"], value) for record, value in values.items()]
    score = score_species_evaluation(path, write_predictions(tmp_path / "predictions.jsonl", predictions), split=split)
    assert score["cases"] == 7 and score["unique_input_count"] == 3
    assert score["eligible_mic_cases"] == 6 and score["answered_mic_cases"] == 5
    assert score["numeric_answer_coverage"] == pytest.approx(5 / 6)
    assert score["mean_absolute_log2_error"] == score["within_one_twofold_step"] == 1.0
    assert score["censored_interval_consistency"] == pytest.approx(2 / 3)
    per_species = {row["taxon_id"]: row for row in score["per_species"]}
    assert per_species[470]["cases"] == 2 and per_species[470]["unique_input_count"] == 1
    assert per_species[573]["numeric_answer_coverage"] == 0.0
    assert per_species[287]["numeric_answer_coverage"] is None
    assert score["macro"]["numeric_answer_coverage"] == pytest.approx(2 / 3)
    assert score["macro_species_counts"]["numeric_answer_coverage"] == 3
    assert score["macro_species_counts"]["mean_absolute_log2_error"] == 1


@pytest.mark.parametrize("value", [None, True, 0.0, -1.0, float("inf")])
def test_invalid_numeric_answers_remain_in_coverage_denominator(tmp_path, value):
    path, _, _ = freeze(tmp_path, [sample("focus"), sample("a", "c1ccccc1"), sample("b", "c1ccncc1")])
    indexed = index_by_record(path)["focus"]
    result = score_species_evaluation(path, write_predictions(tmp_path / "predictions.jsonl", [prediction(indexed["case_id"], value)]), split=indexed["split"])
    assert result["eligible_mic_cases"] == 1 and result["answered_mic_cases"] == 0
    assert result["numeric_answer_coverage"] == 0.0 and result["mean_absolute_log2_error"] is None


def test_duplicate_and_other_split_predictions_are_rejected(tmp_path):
    path, _, _ = freeze(tmp_path, [sample("focus"), sample("a", "c1ccccc1"), sample("b", "c1ccncc1")])
    indexed = index_by_record(path)
    item = indexed["focus"]
    duplicate = prediction(item["case_id"], 4.0)
    with pytest.raises(ValueError, match="duplicate_prediction_case"):
        score_species_evaluation(path, write_predictions(tmp_path / "predictions.jsonl", [duplicate, duplicate]), split=item["split"])
    other = next(row for row in indexed.values() if row["split"] != item["split"])
    with pytest.raises(ValueError, match="outside_requested_split"):
        score_species_evaluation(path, write_predictions(tmp_path / "predictions.jsonl", [prediction(other["case_id"], 4.0)]), split=item["split"])


@pytest.mark.parametrize("parameters", [{"seed": True}, {"grouping": "row"}, {"test_fraction": 0.0},
    {"validation_fraction": float("nan")}, {"test_fraction": 0.8, "validation_fraction": 0.3}])
def test_invalid_parameters_do_not_create_frozen_files(tmp_path, parameters):
    database, _ = build_database(tmp_path, [sample("one")])
    destination = tmp_path / "frozen"
    with pytest.raises(ValueError, match="invalid_split_parameters"):
        freeze_species_evaluation(database, destination, **parameters)
    assert not destination.exists()
