"""Synthetic files exercise import and selection, never claim biological measurements."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json

import pytest

from praxis_virtualcell.omics import ProfileError, list_profiles, load_profile

NAMES = ("genome", "transcriptome", "proteome")
COMBINATIONS = [list(combo) for size in range(1, 4) for combo in itertools.combinations(NAMES, size)]
PROFILE_ID = "synthetic-multiomics-test"


def _asset(path, format):
    return {"path": path.name, "format": format, "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _build(root, modalities=NAMES, table_format="json"):
    directory = root / PROFILE_ID
    directory.mkdir()
    species = {"scientific_name": "Synthetic test organism", "taxonomy_id": "NCBITaxon:000"}
    condition = {"condition_id": "synthetic-baseline", "role": "pre_treatment_baseline", "medium": None,
                 "time_h": None, "temperature_c": None, "growth_phase": None}
    pairing_id = "synthetic-paired-assays" if len(modalities) > 1 else None
    manifest = {
        "schema_version": "praxis.organism-profile.v2", "profile_id": PROFILE_ID,
        "species": species, "strain": "synthetic-strain", "genotype": None, "condition": condition,
        "pairing": {"pairing_id": pairing_id, "relation": "same_sample", "evidence": "synthetic test only"}
        if pairing_id else None,
        "modalities": {},
    }
    for name in modalities:
        values = {"genome": {"presence": True, "variant": None, "copy_number": 1.0},
                  "transcriptome": {"expression_value": 0.0}, "proteome": {"abundance_value": 3.5}}[name]
        records = [{
            "feature_id": f"{name}-feature-{index}", "gene_id": f"native-gene-{index}",
            "protein_id": f"native-protein-{index}", "gene_symbol": f"symbol-{index}",
            "product": f"{name}-private-product-{index}",
            "source_locator": {"path": f"{name}-private-native.csv", "row": index + 2,
                               "accession": None, "record_id": None},
            **{key: value if index == 0 else None for key, value in values.items()},
        } for index in range(2)]
        path = directory / f"{name}.{table_format}"
        if table_format == "json":
            path.write_text(json.dumps(records))
        else:
            rows = [{key: value for key, value in row.items() if key != "source_locator"} |
                    {"source_path": row["source_locator"]["path"], "source_row": row["source_locator"]["row"]}
                    for row in records]
            for row in rows:
                if isinstance(row.get("presence"), bool):
                    row["presence"] = str(row["presence"]).lower()
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        manifest["modalities"][name] = {
            "species": species, "strain": "synthetic-strain", "genotype": None, "condition": condition,
            "sample_id": "synthetic-sample", "pairing_id": pairing_id,
            "assay": {"genome": "whole_genome_sequencing", "transcriptome": "RNA_seq", "proteome": "SWATH_MS"}[name],
            "feature_namespace": "synthetic-native-ids", "unit": f"{name}-declared-unit", "scale": "native",
            "value_semantics": f"synthetic {name} test values", "observation_unit": "measured_baseline_sample",
            "features": _asset(path, table_format),
            "provenance": {"study_id": f"{name}-private-study", "source_samples": ["synthetic-sample"],
                           "citation": "Synthetic fixture only", "terms": {
                               "usage": "software test", "redistribution_approved": True, "license_status": "synthetic"},
                           "input_role": "measured_pre_treatment"},
        }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def _update(root, change):
    path = root / PROFILE_ID / "manifest.json"
    manifest = json.loads(path.read_text())
    change(manifest)
    path.write_text(json.dumps(manifest))


def test_sequenced_reference_preserves_unknown_conditions(tmp_path):
    _build(tmp_path, ["genome"])
    def reference(manifest):
        manifest["condition"]["role"] = "sequenced_reference"
        manifest["modalities"]["genome"]["condition"]["role"] = "sequenced_reference"
        manifest["modalities"]["genome"]["provenance"]["input_role"] = "sequenced_reference"
    _update(tmp_path, reference)
    overview = load_profile(PROFILE_ID, tmp_path).overview()
    assert overview["condition"]["role"] == "sequenced_reference"
    assert overview["condition"]["medium"] is None


@pytest.mark.parametrize("modalities", [["transcriptome"], ["genome", "proteome"]])
def test_sequenced_reference_cannot_imply_measured_baseline(tmp_path, modalities):
    _build(tmp_path, modalities)
    def reference(manifest):
        manifest["condition"]["role"] = "sequenced_reference"
        for item in manifest["modalities"].values():
            item["condition"]["role"] = "sequenced_reference"
    _update(tmp_path, reference)
    with pytest.raises(ProfileError, match="genome-only"):
        load_profile(PROFILE_ID, tmp_path)


@pytest.mark.parametrize("selected", COMBINATIONS)
def test_all_seven_selected_views_expose_only_selected_evidence(tmp_path, selected):
    _build(tmp_path)
    profile = load_profile(PROFILE_ID, tmp_path).select_modalities(list(reversed(selected)))
    overview = profile.overview()
    assert overview["available_modalities"] == list(NAMES)
    assert overview["selected_modalities"] == selected
    assert list(overview["modalities"]) == selected
    assert overview["feature_count"] == len(selected) * 2
    genes = profile.query_genes(["native-gene-0"])["genes"]
    assert [gene["modality"] for gene in genes] == selected
    assert profile.search_annotations("private-product")["match_count"] == len(selected) * 2
    payload = json.dumps({"overview": overview, "genes": genes, "search": profile.search_annotations("private")})
    for name in set(NAMES) - set(selected):
        for marker in (f"{name}-private-product", f"{name}-private-native", f"{name}-private-study", f"{name}-declared-unit"):
            assert marker not in payload
        with pytest.raises(ProfileError, match="unselected"):
            profile.query_features(name, [f"{name}-feature-0"])
    assert profile.select_modalities(None).overview()["selected_modalities"] == list(NAMES)


@pytest.mark.parametrize("available", COMBINATIONS)
@pytest.mark.parametrize("table_format", ["json", "csv"])
def test_all_seven_import_combinations_keep_native_values_and_nulls(tmp_path, available, table_format):
    _build(tmp_path, available, table_format)
    profile = load_profile(PROFILE_ID, tmp_path)
    assert profile.overview()["available_modalities"] == available
    assert list_profiles(tmp_path)[0]["available_modalities"] == available
    for name in available:
        result = profile.query_features(name, [f"{name}-feature-0", "missing", f"{name}-feature-0", f"{name}-feature-1"])
        assert result["missing_feature_ids"] == ["missing"]
        assert len(result["features"]) == 2
        row, missing = result["features"]
        assert row["source_id"] == f"omics:{PROFILE_ID}:{name}:feature:{name}-feature-0"
        assert row["source_locator"]["native_source"] == {
            "path": f"{name}-private-native.csv", "row": 2, "accession": None, "record_id": None}
        assert row["source_locator"]["asset_record_index"] == 0
        value_key = {"genome": "presence", "transcriptome": "expression_value", "proteome": "abundance_value"}[name]
        assert missing[value_key] is None
        if name == "transcriptome":
            assert row[value_key] == 0.0
        assert profile.search_features(name, "SYMBOL-0")["match_count"] == 1
        row["source_locator"]["native_source"]["row"] = 999
        assert profile.query_features(name, [row["feature_id"]])["features"][0]["source_locator"]["native_source"]["row"] == 2
    for name in set(NAMES) - set(available):
        with pytest.raises(ProfileError, match="unavailable"):
            profile.select_modalities([name])


@pytest.mark.parametrize("change,match", [
    (lambda m: m["modalities"]["proteome"].update(strain="other-strain"), "identity differs"),
    (lambda m: m["modalities"]["genome"].update(genotype="other-genotype"), "identity differs"),
    (lambda m: m["modalities"]["transcriptome"]["condition"].update(time_h=2.0), "identity differs"),
    (lambda m: m["modalities"]["genome"]["species"].update(taxonomy_id="NCBITaxon:1"), "identity differs"),
    (lambda m: m.update(pairing=None), "explicit sample pairing"),
    (lambda m: m["modalities"]["proteome"].update(pairing_id="other-pair"), "pairing identity"),
    (lambda m: m["modalities"]["proteome"].update(sample_id="unknown-sample"), "sample identity"),
    (lambda m: m["modalities"]["proteome"].update(assay="assembly_annotation"), "measured proteome"),
    (lambda m: m["modalities"]["proteome"]["provenance"].update(input_role="sequenced_reference"), "pre-treatment"),
    (lambda m: m["modalities"]["proteome"]["provenance"].update(mic=1.0), "Invalid organism"),
])
def test_cross_strain_condition_sample_and_nonmeasurement_fusion_rejected(tmp_path, change, match):
    _build(tmp_path)
    _update(tmp_path, change)
    with pytest.raises(ProfileError, match=match):
        load_profile(PROFILE_ID, tmp_path)


def test_distinct_sample_ids_require_explicit_matched_pairing(tmp_path):
    _build(tmp_path)
    def change(m):
        m["modalities"]["proteome"]["sample_id"] = "protein-aliquot"
        m["modalities"]["proteome"]["provenance"]["source_samples"] = ["protein-aliquot"]
    _update(tmp_path, change)
    with pytest.raises(ProfileError, match="same explicit sample ID"):
        load_profile(PROFILE_ID, tmp_path)
    _update(tmp_path, lambda m: m["pairing"].update(relation="matched_samples", evidence="Explicit synthetic aliquot mapping"))
    assert load_profile(PROFILE_ID, tmp_path).overview()["modalities"]["proteome"]["sample_id"] == "protein-aliquot"


@pytest.mark.parametrize("selection", [[], ["RNA"], "genome", [None]])
def test_invalid_selection_rejected(tmp_path, selection):
    _build(tmp_path)
    with pytest.raises(ProfileError, match="modalities"):
        load_profile(PROFILE_ID, tmp_path).select_modalities(selection)


def test_v1_is_only_transcriptome_despite_protein_annotation(tiny_profile_root):
    profile = load_profile(data_root=tiny_profile_root)
    assert profile.select_modalities(["transcriptome"]).overview()["selected_modalities"] == ["transcriptome"]
    assert profile.query_features("transcriptome", ["ABUW_0001"])["features"][0]["feature_id"] == "ABUW_0001"
    assert profile.search_features("transcriptome", "dnaA")["features"][0]["gene_id"] == "ABUW_0001"
    with pytest.raises(ProfileError, match="unavailable"):
        profile.select_modalities(["proteome"])


@pytest.mark.parametrize("corruption,match", [("hash", "hash mismatch"), ("path", "unsafe asset path")])
def test_v2_uses_declared_asset_hash_and_safe_paths(tmp_path, corruption, match):
    _build(tmp_path)
    def change(m):
        asset = m["modalities"]["genome"]["features"]
        asset.update({"sha256": "0" * 64} if corruption == "hash" else {"path": "../genome.json"})
    _update(tmp_path, change)
    with pytest.raises(ProfileError, match=match):
        load_profile(PROFILE_ID, tmp_path)


@pytest.mark.parametrize("change", [
    lambda rows: rows[0].update(expression_value=float("nan")),
    lambda rows: rows[0].update(expression_value="1.0"),
    lambda rows: rows[1].update(feature_id=rows[0]["feature_id"]),
    lambda rows: rows[0].update(mic=2.0),
    lambda rows: rows[0].update(gene_id=""),
    lambda rows: rows[0].update(source_locator={"path": None, "row": None, "accession": None, "record_id": None}),
])
def test_invalid_feature_records_fail_even_with_correct_hash(tmp_path, change):
    _build(tmp_path, ["transcriptome"])
    path = tmp_path / PROFILE_ID / "transcriptome.json"
    records = json.loads(path.read_text())
    change(records)
    path.write_text(json.dumps(records))
    _update(tmp_path, lambda m: m["modalities"]["transcriptome"].update(features=_asset(path, "json")))
    with pytest.raises(ProfileError, match="Invalid transcriptome feature asset"):
        load_profile(PROFILE_ID, tmp_path)
