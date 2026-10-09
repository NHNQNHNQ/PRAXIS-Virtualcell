"""Inventories separate missing originals, means, and numeric feature indices."""
from __future__ import annotations

import csv
import json
import shutil

import pytest

from praxis_virtualcell.datasets.inventory import _matrix, build_omics_inventory, render_inventory_markdown


@pytest.fixture
def synthetic_collection(tmp_path):
    """Three synthetic native PA sources and a collection that reuses all three."""
    from tests.omics.test_species_reference import _references

    repo = tmp_path / "repo"
    organisms = repo / "data/organisms"
    organisms.mkdir(parents=True)
    _references(organisms)
    species = {"scientific_name": "Pseudomonas aeruginosa", "taxonomy_id": "NCBITaxon:287"}
    for path in organisms.glob("*/manifest.json"):
        manifest = json.loads(path.read_text())
        manifest["species"] = species
        for item in manifest.get("modalities", {}).values():
            item["species"] = species
        path.write_text(json.dumps(manifest))
    return repo


def test_inventory_is_read_only_and_does_not_invent_individual_samples(tmp_path, tiny_profile_root):
    repo = tmp_path / "repo"
    organisms = repo / "data/organisms"
    shutil.copytree(tiny_profile_root, organisms)
    before = {path: path.read_bytes() for path in organisms.rglob("*") if path.is_file()}
    result = build_omics_inventory(repo, tmp_path / "absent-archive")
    assert len(result["verified_profiles"]) == 1
    assert result["profile_modality_counts"] == {"transcriptome": 1}
    assert result["native_profile_modality_counts"] == {"transcriptome": 1}
    assert result["reference_collection_count"] == 0
    assert result["verified_profiles"][0]["is_reference_collection"] is False
    assert result["verified_profiles"][0]["input_role"]
    assert result["verified_profiles"][0]["prediction_scope"] is None
    assert result["ab_canonical_metadata_only"]["recoverable_verified_column_count"] == 0
    assert result["ab_frozen_control_means"]["individual_vectors_recoverable_from_means"] is False
    assert result["genome_references"]["verified_assembly_count"] == 0
    assert result["proteome"]["verified_measured_profile_count"] == 0
    assert result["scope"]["network_requests"] == 0 and result["scope"]["source_assets_copied"] is False
    assert {path: path.read_bytes() for path in organisms.rglob("*") if path.is_file()} == before
    markdown = render_inventory_markdown(result)
    assert "不能据此恢复这些单样本向量" in markdown
    assert "不表示功能" in markdown


def test_reference_collection_is_listed_without_double_counting_native_measurements(synthetic_collection):
    result = build_omics_inventory(synthetic_collection, synthetic_collection / "absent-archive")
    assert result["profile_errors"] == []
    assert len(result["verified_profiles"]) == 4
    assert result["profile_modality_counts"] == {"genome": 2, "transcriptome": 2, "proteome": 2}
    assert result["native_profile_modality_counts"] == {"genome": 1, "transcriptome": 1, "proteome": 1}
    assert result["reference_collection_count"] == 1
    assert result["proteome"]["verified_measured_profile_count"] == 1
    reference = next(row for row in result["verified_profiles"] if row["is_reference_collection"])
    assert reference["input_role"] == reference["prediction_scope"] == "species_reference"
    assert reference["observation_unit"] == "independent_species_references"
    assert reference["reference_profiles"] == {name: f"source-{name}" for name in ("genome", "transcriptome", "proteome")}
    for row in result["verified_profiles"]:
        if not row["is_reference_collection"]:
            assert set(row["input_role"].values()) == {"measured_pre_treatment"}


def test_measured_proteome_and_admitted_pa_rna_remove_obsolete_missing_data_blockers(synthetic_collection):
    result = build_omics_inventory(synthetic_collection, synthetic_collection / "absent-archive")
    assert "1 native measured proteome profiles" in result["proteome"]["note"]
    assert "No measured" not in result["proteome"]["note"]
    assert result["pa_author_expression_candidate"]["verified_native_transcriptome_profile_ids"] == ["source-transcriptome"]
    assert "1 verified native PA transcriptome" in result["pa_author_expression_candidate"]["profile_availability_note"]
    assert not any("PA expression requires" in line or "No verified pre-treatment measured proteome" in line
                   for line in result["readiness_blockers"])
    assert any("Strict MIC pairing has not been verified" in line for line in result["readiness_blockers"])
    markdown = render_inventory_markdown(result)
    assert "| 原生 proteome profile | 1 |" in markdown
    assert "| 物种参考集合 | 1；复用原生档案，不新增独立观测 |" in markdown
    assert "Strict MIC pairing has not been verified" in markdown


def test_old_inventory_markdown_without_new_count_fields_still_renders(tmp_path, tiny_profile_root):
    repo = tmp_path / "repo"
    shutil.copytree(tiny_profile_root, repo / "data/organisms")
    result = build_omics_inventory(repo, tmp_path / "absent-archive")
    assert "No measured protein abundance profile" in result["proteome"]["note"]
    assert any("No verified pre-treatment measured proteome" in line for line in result["readiness_blockers"])
    result.pop("native_profile_modality_counts")
    result.pop("reference_collection_count")
    result["pa_author_expression_candidate"].pop("profile_availability_note")
    markdown = render_inventory_markdown(result)
    assert "| 原生 transcriptome profile | 1；" in markdown
    assert "| 原生 proteome profile | 0 |" in markdown


def test_numeric_author_matrix_rows_are_not_reported_as_native_genes(tmp_path):
    path = tmp_path / "author-matrix.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["", "sample-A", "sample-B"])
        writer.writerow(["0", "1.2", "2.2"])
        writer.writerow(["1", "0", "3.3"])
    result = _matrix(path)
    assert result["feature_identity_kind"] == "numeric_row_index"
    assert result["feature_count"] == 2 and result["sample_column_count"] == 2
    assert len(result["sha256"]) == 64
