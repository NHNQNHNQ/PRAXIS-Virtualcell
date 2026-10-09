"""Frozen train templates preserve real tool values and only private answer pointers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets.species_supervision import _build_view, prepare_species_supervision
from praxis_virtualcell.llm_prediction.evidence import _reference
from praxis_virtualcell.llm_prediction.schemas import EvidenceReference
from praxis_virtualcell.omics import load_profile
from tests.omics.conftest import baseline_sources as baseline_sources, tiny_profile_root as tiny_profile_root


def _snapshot(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _fixture(tmp_path, taxa=(470, 562, 573, 287)):
    root = tmp_path / "profiles"
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    collections, references, inputs, answers = [], [], [], []
    for taxon in taxa:
        species = {"scientific_name": f"Synthetic software fixture {taxon}", "taxonomy_id": f"NCBITaxon:{taxon}"}
        source_ids = {}
        for name in ("genome", "transcriptome", "proteome"):
            profile_id = f"F{taxon}-{name}"
            source_ids[name] = profile_id
            directory = root / profile_id
            directory.mkdir(parents=True)
            condition = {"condition_id": f"{name}-source-condition", "role": "sequenced_reference"
                         if name == "genome" else "untreated_reference", "medium": None,
                         "time_h": None, "temperature_c": None, "growth_phase": None}
            values = {"genome": {"presence": True, "variant": None, "copy_number": None},
                      "transcriptome": {"expression_value": 0.0}, "proteome": {"abundance_value": None}}[name]
            records = [{"feature_id": f"native-{name}-feature", "gene_id": f"native-{name}-gene",
                        "protein_id": f"{name}-unresolved-native-group;p2", "gene_symbol": None,
                        "product": f"{name}-private-marker protein", "source_locator": {
                            "path": "/fixture/native/original", "row": 2, "accession": "fixture-accession",
                            "record_id": "original-record"}, **values}]
            path = directory / f"{name}.json"
            path.write_text(json.dumps(records))
            manifest = {"schema_version": "praxis.organism-profile.v2", "profile_id": profile_id,
                        "species": species, "strain": f"{name}-source-strain", "genotype": None,
                        "condition": condition, "pairing": None, "modalities": {name: {
                            "species": species, "strain": f"{name}-source-strain", "genotype": None,
                            "condition": condition, "sample_id": f"{name}-source-sample", "pairing_id": None,
                            "assay": {"genome": "assembly_annotation", "transcriptome": "RNA_seq",
                                      "proteome": "LC_MS_MS"}[name], "feature_namespace": "fixture native IDs",
                            "unit": f"{name}-declared-unit", "scale": f"{name}-declared-scale",
                            "value_semantics": (f"{name}-private-source-semantics; synthetic fixture; "
                                                "reference_condition_identity_status=inferred_from_author_group_design; "
                                                "strict untreated identity not verified per sample"),
                            "observation_unit": "measured_reference_assembly" if name == "genome"
                            else "measured_baseline_sample", "features": {
                                "path": path.name, "format": "json", "size_bytes": path.stat().st_size,
                                "sha256": _snapshot(path)["sha256"]}, "provenance": {
                                    "study_id": f"{name}-source-study", "source_samples": [f"{name}-source-sample"],
                                    "citation": "Synthetic fixture, no biological claims", "terms": {
                                        "usage": "software_test", "redistribution_approved": False,
                                        "license_status": "fixture"}, "input_role": "sequenced_reference"
                                    if name == "genome" else "measured_pre_treatment"}}}}
            manifest_path = directory / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            references.append({"taxon_id": taxon, "modality": name, "profile_id": profile_id,
                               "manifest": _snapshot(manifest_path),
                               "assets": [_snapshot(path) | {"size_bytes": path.stat().st_size}]})
        profile_id = f"F{taxon}-SPECIES-REFERENCE"
        directory = root / profile_id
        directory.mkdir()
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps({
            "schema_version": "praxis.species-reference.v1", "profile_id": profile_id, "species": species,
            "reference_profiles": source_ids, "input_role": "species_reference",
            "relation": "species_level_reference", "prediction_scope": "species_reference",
            "selection_reasons": {name: "Traceable software fixture" for name in source_ids},
        }))
        collections.append({"taxon_id": taxon, "profile_id": profile_id, "manifest": _snapshot(manifest_path),
                            "available_modalities": list(source_ids)})
        for n, (smiles, split) in enumerate((("CC", "train"), ("CC", "train"), ("CCC", "train"),
                                           ("O", "validation"), ("N", "test"))):
            case_id = f"case-{taxon}-{n}"
            group = f"group-{smiles}"
            inputs.append({"case_id": case_id, "split": split, "group_id": group, "input": {
                "candidate": {"id": case_id, "smiles": smiles},
                "organism": {"species": species["scientific_name"], "taxon_id": taxon},
                "profile_id": profile_id, "prediction_scope": "species_reference"}})
            answers.append({"case_id": case_id, "split": split, "group_id": group,
                            "record_id": f"source-record-{taxon}-{n}", "label_file_id": 1,
                            "byte_offset": n * 100, "line_number": n + 1})
    database = tmp_path / "fixture.sqlite"
    database.write_bytes(b"Software fixture snapshot, never queried for answers")
    label = tmp_path / "private-labels.jsonl"
    label.write_text('{"mic":456781.23,"secret":"PRIVATE_MIC_DO_NOT_COPY"}\n')
    _write_rows(frozen / "inputs.jsonl", inputs)
    _write_rows(frozen / "answers.index.jsonl", answers)
    manifest = {"schema_version": "praxis.species-frozen-evaluation.v1", "status": "ready", "grouping": "compound",
                "database": _snapshot(database),
                "label_sources": [_snapshot(label) | {"id": 1}], "references": references,
                "collections": collections, "files": {filename: {"sha256": _snapshot(frozen / filename)["sha256"]}
                                                       for filename in ("inputs.jsonl", "answers.index.jsonl")}}
    path = frozen / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def _read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_four_species_have_seven_true_tool_views_and_valid_source_citations(tmp_path):
    frozen = _fixture(tmp_path)
    report = prepare_species_supervision(frozen, tmp_path / "queue")
    records = _read(tmp_path / "queue/observations.jsonl")
    assert report["observation_view_count"] == len(records) == 28
    assert len({row["view_id"] for row in records}) == 28
    for row in records:
        calls = {call["tool_call_id"]: call for call in row["execution_trace"]["tool_calls"]}
        assert {call["name"] for call in calls.values()} == {"overview", "search_features", "query_features"}
        selected = row["source"]["selected_modalities"]
        queries = [call for call in calls.values() if call["name"] == "query_features"]
        assert {call["arguments"]["modality"] for call in queries} == set(selected)
        assert all(len(call["data"]["features"]) == 1 for call in queries)
        for observation in row["public_observations"]["observations"]:
            actual, _ = _reference(EvidenceReference.model_validate(observation["evidence_ref"]), calls)
            assert actual == observation["value"]
        assert json.loads(row["messages"][-1]["content"]) == row["public_observations"]
        assert row["origin"] == "source_grounded_template"
        assert row["review_status"] == "needs_review"
        assert row["trainable"] is row["prediction_is_gold"] is False
        encoded = json.dumps(row)
        for absent in {"genome", "transcriptome", "proteome"} - set(selected):
            assert f"{absent}-private-marker" not in encoded
            assert f"{absent}-source-strain" not in encoded
            assert f"{absent}-declared-unit" not in encoded


def test_train_structure_ceiling_keeps_repeated_private_locators_without_mic_copy(tmp_path):
    frozen = _fixture(tmp_path)
    report = prepare_species_supervision(frozen, tmp_path / "queue", limit_per_species=1)
    records = _read(tmp_path / "queue/queue.jsonl")
    assert len(records) == 4
    assert report["private_answer_locator_count"] == 8
    assert all(count == 1 for count in report["queue_counts_by_taxon"].values())
    for row in records:
        assert row["split"] == "train"
        assert row["input"]["candidate"]["smiles"] == "CC"
        assert len(row["observation_view_ids"]) == 7
        assert len(row["private_answer_locators"]) == 2
        assert {answer["split"] for answer in row["private_answer_locators"]} == {"train"}
        assert all(answer["case_id"].endswith(("-0", "-1")) for answer in row["private_answer_locators"])
        assert row["trainable"] is row["prediction_is_gold"] is False
    encoded = "\n".join(path.read_text() for path in (tmp_path / "queue").iterdir())
    assert "PRIVATE_MIC_DO_NOT_COPY" not in encoded
    assert "456781.23" not in encoded
    assert report["model_calls"] == report["training_runs"] == report["experimental_answer_materializations"] == 0


def test_native_strains_conditions_units_scales_inferred_identity_and_nulls_survive(tmp_path):
    frozen = _fixture(tmp_path, taxa=(470,))
    prepare_species_supervision(frozen, tmp_path / "queue")
    records = _read(tmp_path / "queue/observations.jsonl")
    full = next(row for row in records if len(row["source"]["selected_modalities"]) == 3)
    calls = full["execution_trace"]["tool_calls"]
    queries = {call["arguments"]["modality"]: call["data"]["features"][0]
               for call in calls if call["name"] == "query_features"}
    assert queries["genome"]["presence"] is True
    assert queries["transcriptome"]["expression_value"] == 0.0
    assert queries["proteome"]["abundance_value"] is None
    for name, row in queries.items():
        assert row["source_strain"] == f"{name}-source-strain"
        assert row["source_condition"]["condition_id"] == f"{name}-source-condition"
        assert row["source_condition"]["medium"] is None
        assert row["unit"] == f"{name}-declared-unit"
        assert row["scale"] == f"{name}-declared-scale"
        assert "inferred_from_author_group_design" in row["value_semantics"]
    assert full["public_observations"]["mic"]["value"] is None


def test_historical_v1_nested_reference_preserves_all_mean_members(tiny_profile_root):
    native = load_profile(data_root=tiny_profile_root)
    profile_id = "fixture-historical-species-reference"
    directory = tiny_profile_root / profile_id
    directory.mkdir()
    (directory / "manifest.json").write_text(json.dumps({
        "schema_version": "praxis.species-reference.v1", "profile_id": profile_id,
        "species": native.overview()["species"], "reference_profiles": {"transcriptome": native.profile_id},
        "input_role": "species_reference", "relation": "species_level_reference",
        "prediction_scope": "species_reference",
    }))
    view = _build_view(load_profile(profile_id, tiny_profile_root), ("transcriptome",))
    calls = {call["tool_call_id"]: call for call in view["execution_trace"]["tool_calls"]}
    for observation in view["public_observations"]["observations"]:
        _reference(EvidenceReference.model_validate(observation["evidence_ref"]), calls)
    observations = view["public_observations"]["observations"]
    assert any(item["field"] == "observation_unit" and item["value"] == "historical_condition_mean"
               for item in observations)
    assert any(item["field"] == "source_samples" and item["value"] == ["Abaum_0017", "Abaum_0023"]
               for item in observations)
    assert any(item["field"] == "provenance" and "annotation_source" in item["value"]
               for item in observations)
    assert all(item["field"] != "abundance_value" for item in observations)


def test_changed_frozen_input_is_rejected_before_output(tmp_path):
    frozen = _fixture(tmp_path, taxa=(470,))
    (frozen.parent / "inputs.jsonl").write_text("CHANGED")
    with pytest.raises(ValueError, match="frozen_source_changed"):
        prepare_species_supervision(frozen, tmp_path / "queue")
    assert not (tmp_path / "queue").exists()


def test_no_train_cases_does_not_fill_with_validation_or_test(tmp_path):
    frozen = _fixture(tmp_path, taxa=(470,))
    manifest = json.loads(frozen.read_text())
    for filename in ("inputs.jsonl", "answers.index.jsonl"):
        rows = _read(frozen.parent / filename)
        for row in rows:
            if row["split"] == "train":
                row["split"] = "unassigned"
        _write_rows(frozen.parent / filename, rows)
        manifest["files"][filename]["sha256"] = _snapshot(frozen.parent / filename)["sha256"]
    frozen.write_text(json.dumps(manifest))
    report = prepare_species_supervision(frozen, tmp_path / "queue")
    assert report["observation_view_count"] == 7
    assert report["queue_record_count"] == 0
    assert _read(tmp_path / "queue/queue.jsonl") == []


def test_insufficient_frozen_groups_cannot_supply_a_supervision_queue(tmp_path):
    frozen = _fixture(tmp_path, taxa=(470,))
    manifest = json.loads(frozen.read_text())
    manifest["status"] = "insufficient_groups"
    frozen.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="frozen_training_split_not_ready"):
        prepare_species_supervision(frozen, tmp_path / "queue")
    assert not (tmp_path / "queue").exists()


@pytest.mark.parametrize("limit", [True, 0, -1, 1.5, "8", None])
def test_invalid_limit_is_rejected(tmp_path, limit):
    with pytest.raises(ValueError, match="limit_per_species"):
        prepare_species_supervision(tmp_path / "missing.json", tmp_path / "queue", limit)


def test_nonempty_output_is_refused_before_validation(tmp_path, monkeypatch):
    output = tmp_path / "queue"
    output.mkdir()
    sentinel = output / "existing.jsonl"
    sentinel.write_text("KEEP")
    def forbidden(*args, **kwargs):
        raise AssertionError("Source must not be read before overwrite refusal")
    monkeypatch.setattr("praxis_virtualcell.datasets.species_evaluation.validate_species_evaluation", forbidden)
    with pytest.raises(FileExistsError, match="nonempty"):
        prepare_species_supervision(tmp_path / "missing.json", output)
    assert sentinel.read_text() == "KEEP"
