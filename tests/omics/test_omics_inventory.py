"""Inventories separate missing originals, means, and numeric feature indices."""
from __future__ import annotations

import csv
import shutil

from praxis_virtualcell.datasets.inventory import _matrix, build_omics_inventory, render_inventory_markdown


def test_inventory_is_read_only_and_does_not_invent_individual_samples(tmp_path, tiny_profile_root):
    repo = tmp_path / "repo"
    organisms = repo / "data/organisms"
    shutil.copytree(tiny_profile_root, organisms)
    before = {path: path.read_bytes() for path in organisms.rglob("*") if path.is_file()}
    result = build_omics_inventory(repo, tmp_path / "absent-archive")
    assert len(result["verified_profiles"]) == 1
    assert result["profile_modality_counts"] == {"transcriptome": 1}
    assert result["ab_canonical_metadata_only"]["recoverable_verified_column_count"] == 0
    assert result["ab_frozen_control_means"]["individual_vectors_recoverable_from_means"] is False
    assert result["genome_references"]["verified_assembly_count"] == 0
    assert result["proteome"]["verified_measured_profile_count"] == 0
    assert result["scope"]["network_requests"] == 0 and result["scope"]["source_assets_copied"] is False
    assert {path: path.read_bytes() for path in organisms.rglob("*") if path.is_file()} == before
    markdown = render_inventory_markdown(result)
    assert "不能据此恢复这些单样本向量" in markdown
    assert "不表示功能" in markdown


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
