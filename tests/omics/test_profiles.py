"""Actual baseline loading, identity, provenance, and malformed input boundaries."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from praxis_virtualcell.omics import ProfileError, list_profiles, load_profile
from praxis_virtualcell.omics.prepare_ab5075 import prepare_ab5075_profile

PROFILE_ID = "AB5075-AZI000"
REAL_ROOT = Path(__file__).resolve().parents[2] / "data/organisms"


def _manifest(root):
    return root / PROFILE_ID / "manifest.json"


def _update_manifest(root, update):
    path = _manifest(root)
    manifest = json.loads(path.read_text())
    update(manifest)
    path.write_text(json.dumps(manifest))


def _replace_npz(root, **arrays):
    path = root / PROFILE_ID / "baseline.npz"
    np.savez_compressed(path, **arrays)
    _update_manifest(root, lambda manifest: manifest["expression"].update(
        size_bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    ))


@pytest.fixture
def real_profile():
    if not (REAL_ROOT / PROFILE_ID / "manifest.json").is_file():
        pytest.skip("Local AB5075 dataset is not redistributed; rebuild it from declared sources")
    return load_profile(PROFILE_ID, REAL_ROOT)


def test_real_ab5075_overview_and_dnaa_value_have_native_source(real_profile):
    overview = real_profile.overview()
    assert overview["feature_count"] == overview["annotated_feature_count"] == 3895
    assert overview["strain"] == "AB5075"
    assert overview["species"] == {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"}
    assert overview["condition"]["medium"] == "CA-MHB"
    assert overview["observation_unit"] == "historical_condition_mean"
    assert overview["source_samples"] == ["Abaum_0017", "Abaum_0023"]
    assert overview["genotype"] is None
    for key in ("time_h", "temperature_c", "growth_phase"):
        assert overview["condition"][key] is None
    assert set(overview["unknown_fields"]) == {"time_h", "temperature_c", "growth_phase", "genotype"}

    row = real_profile.query_genes(["ABUW_0001"])["genes"][0]
    assert row["gene_symbol"] == "dnaA"
    assert row["expression_value"] == pytest.approx(5.837963104248047, abs=1e-7)
    assert row["unit"] == "author_log2_TPM_QC"
    assert row["scale"] == "author_log2_tpm_qc_unscaled_ABUW_namespace"
    assert row["source_id"] == "omics:AB5075-AZI000:gene:ABUW_0001"
    assert row["protein_id"] == "AKA29801.1"
    locator = row["source_locator"]
    assert locator["feature_index"] == 16
    assert locator["reference_row"] == 2 and locator["mapping_row"] == 18
    source = locator["native_source"]
    assert source["array_key"] == "control" and source["row_index"] == 0
    with np.load(REAL_ROOT / source["path"], allow_pickle=False) as archive:
        assert archive["genes"][locator["feature_index"]] == "ABUW_0001"
        assert float(archive["control"][source["row_index"], locator["feature_index"]]) == row["expression_value"]
    matches = real_profile.search_annotations("dnaA")
    assert {gene["gene_id"] for gene in matches["genes"]} == {"ABUW_0001", "ABUW_0983"}
    assert real_profile.query_genes(["dnaA"])["missing_gene_ids"] == ["dnaA"]


def test_preparation_reads_only_control_and_preserves_unknowns_and_source_bytes(tmp_path, baseline_sources):
    original = {path: path.read_bytes() for path in baseline_sources.rglob("*") if path.is_file()}
    root = tmp_path / "new-profiles"
    result = prepare_ab5075_profile(root, baseline_sources)
    assert result == root / PROFILE_ID
    profile = load_profile(PROFILE_ID, root)
    overview = profile.overview()
    assert overview["genotype"] is None
    assert all(overview["condition"][key] is None for key in ("time_h", "temperature_c", "growth_phase"))
    assert overview["provenance"]["expression_source"]["array_key"] == "control"
    with np.load(result / "baseline.npz", allow_pickle=False) as archive:
        assert set(archive.files) == {"genes", "expression"}
        np.testing.assert_array_equal(archive["expression"], [0.0, 4.5])
    assert all(path.read_bytes() == content for path, content in original.items())
    with pytest.raises(ProfileError, match="already exists"):
        prepare_ab5075_profile(root, baseline_sources)


def test_profile_loading_requires_no_historical_prediction_modules(tiny_profile_root):
    code = """
import builtins, json, sys
original_import = builtins.__import__
blocked = ('praxis_virtualcell.mdr_gnb', 'praxis_virtualcell.predictors', 'praxis_virtualcell.model_zoo', 'abwm')
def guarded(name, *args, **kwargs):
    if any(name == prefix or name.startswith(prefix + '.') for prefix in blocked):
        raise AssertionError('Historical prediction module must not be loaded: ' + name)
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded
from praxis_virtualcell.omics import load_profile
profile = load_profile(data_root=sys.argv[1])
print(json.dumps({'overview': profile.overview(), 'genes': profile.query_genes(['ABUW_0001'])}))
"""
    result = subprocess.run([sys.executable, "-c", code, str(tiny_profile_root)],
                            capture_output=True, text=True, check=True, timeout=30)
    payload = json.loads(result.stdout)
    assert payload["overview"]["feature_count"] == 2
    forbidden = {"treated", "delta", "mic", "mic_value", "state_vector", "prediction"}

    def keys(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert keys(payload).isdisjoint(forbidden)


def test_native_gene_lookup_zero_missing_duplicates_and_limits(tiny_profile_root):
    profile = load_profile(data_root=tiny_profile_root)
    result = profile.query_genes(["ABUW_0001", "not-a-gene", "ABUW_0001", "ABUW_0002"], limit=1)
    assert result["genes"][0]["expression_value"] == 0.0
    assert result["missing_gene_ids"] == ["not-a-gene"] and result["truncated"] is True
    assert profile.query_genes([]) == {"profile_id": PROFILE_ID, "genes": [], "missing_gene_ids": [], "truncated": False}
    second = profile.query_genes(["ABUW_0002"])["genes"][0]
    assert second["gene_symbol"] is None and second["protein_id"] is None
    assert profile.search_annotations("DNAa")["genes"][0]["gene_id"] == "ABUW_0001"
    assert profile.search_annotations("no such annotation")["genes"] == []


@pytest.mark.parametrize("gene_ids", [None, "dnaA", [""], [1]])
def test_invalid_gene_query_is_rejected(tiny_profile_root, gene_ids):
    with pytest.raises(ValueError, match="gene_ids"):
        load_profile(data_root=tiny_profile_root).query_genes(gene_ids)


@pytest.mark.parametrize("query", [None, "", "  "])
def test_empty_annotation_query_is_rejected(tiny_profile_root, query):
    with pytest.raises(ValueError, match="query"):
        load_profile(data_root=tiny_profile_root).search_annotations(query)


@pytest.mark.parametrize("limit", [0, 101, True, 2.5, "2"])
def test_invalid_result_limits_are_rejected(tiny_profile_root, limit):
    with pytest.raises(ValueError, match="limit"):
        load_profile(data_root=tiny_profile_root).query_genes(["ABUW_0001"], limit=limit)


@pytest.mark.parametrize("profile_id", ["", "..", "../AB5075", "/tmp/AB5075", None])
def test_unsafe_or_empty_profile_id_is_rejected(tmp_path, profile_id):
    with pytest.raises(ProfileError, match="Invalid profile ID"):
        load_profile(profile_id, tmp_path)


def test_missing_profile_and_empty_registry_are_explicit(tmp_path):
    assert list_profiles(tmp_path) == list_profiles(tmp_path / "missing") == []
    with pytest.raises(ProfileError, match="Profile not found"):
        load_profile("unknown-profile", tmp_path)


def test_profile_hash_is_checked_before_npz_is_opened(tiny_profile_root, monkeypatch):
    _update_manifest(tiny_profile_root, lambda manifest: manifest["expression"].update(sha256="0" * 64))
    monkeypatch.setattr(np, "load", lambda *args, **kwargs: pytest.fail("Corrupt asset was opened"))
    with pytest.raises(ProfileError, match="hash mismatch"):
        load_profile(data_root=tiny_profile_root)


@pytest.mark.parametrize("arrays", [
    {"genes": np.array(["ABUW_0001", "ABUW_0002"]), "expression": np.array([[1.0, 2.0]])},
    {"genes": np.array(["ABUW_0001", "ABUW_0002"]), "expression": np.array([1.0])},
    {"genes": np.array(["ABUW_0001", "ABUW_0002"]), "expression": np.array([1.0, np.nan])},
    {"genes": np.array(["ABUW_0001", "ABUW_0001"]), "expression": np.array([1.0, 2.0])},
    {"genes": np.array(["ABUW_0001", ""]), "expression": np.array([1.0, 2.0])},
])
def test_malformed_measured_vectors_are_rejected_even_with_valid_asset_hash(tiny_profile_root, arrays):
    _replace_npz(tiny_profile_root, **arrays)
    with pytest.raises(ProfileError):
        load_profile(data_root=tiny_profile_root)


@pytest.mark.parametrize("extra", ["treated", "delta", "mic", "state_vector"])
def test_non_baseline_arrays_cannot_enter_the_loaded_profile(tiny_profile_root, extra):
    _replace_npz(tiny_profile_root, genes=np.array(["ABUW_0001", "ABUW_0002"]),
                 expression=np.array([0.0, 4.5]), **{extra: np.array([8.0])})
    with pytest.raises(ProfileError, match="Invalid baseline NPZ"):
        load_profile(data_root=tiny_profile_root)


@pytest.mark.parametrize("field,value", [("time_h", 0.0), ("temperature_c", 0.0), ("growth_phase", "0")])
def test_unknown_ab5075_metadata_cannot_be_relabelled_as_observed_zero(tiny_profile_root, field, value):
    _update_manifest(tiny_profile_root, lambda manifest: manifest["condition"].update({field: value}))
    with pytest.raises(ProfileError, match="identity, native scale"):
        load_profile(data_root=tiny_profile_root)


def test_response_or_mic_provenance_fields_are_not_accepted(tiny_profile_root):
    _update_manifest(tiny_profile_root, lambda manifest: manifest["provenance"]["expression_source"].update(
        mic=1.0, treated_array_key="treated",
    ))
    with pytest.raises(ProfileError, match="Invalid organism manifest"):
        load_profile(data_root=tiny_profile_root)
