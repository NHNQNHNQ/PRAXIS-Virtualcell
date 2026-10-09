"""Individual column preparation preserves values and unresolved replicate identity."""
from __future__ import annotations

import csv
import json

import numpy as np
import pytest

from praxis_virtualcell.omics import ProfileError, load_profile
from praxis_virtualcell.omics.prepare_baseline_samples import prepare_baseline_samples


def _csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def author_sources(tmp_path):
    root = tmp_path / "author-data"
    common = {"reference_sequence": "AB5075", "strain_description": "AB5075", "base_media": "CA-MHB",
              "reference_condition": "AZI_000"}
    _csv(root / "raw_data/metadata.csv", [common | {
        "Experiment": sample, "project_name": "AB5075_AZI", "condition_name": "AZI_000",
        "BioProject": "PRJNA658638", "Run": f"SRRTEST{index}", "BioSample": "SAME_BIOSAMPLE",
        "temperature": "0", "growth_phase": "0",
    } for index, sample in enumerate(("Abaum_0017", "Abaum_0023"))])
    _csv(root / "interim/metadata_qc.csv", [common | {"": sample, "project": "AB5075_AZI", "condition": "AZI_000",
        **{flag: "TRUE" for flag in ("passed_fastqc", "passed_reads_mapped_to_CDS", "passed_global_correlation",
                                     "passed_similar_replicates", "passed_number_replicates")}}
        for sample in ("Abaum_0017", "Abaum_0023")])
    _csv(root / "external/gene_info.csv", [
        {"locus_tag": "ABUW_0001", "gene_name": "dnaA", "gene_product": "Synthetic annotation A"},
        {"locus_tag": "ABUW_0002", "gene_name": "", "gene_product": "Synthetic annotation B"},
    ])
    _csv(root / "interim/log_tpm_qc.csv", [
        {"Geneid": "ABUW_0001", "Abaum_0017": "0.0", "Abaum_0023": "2.0", "treated-unselected": "999"},
        {"Geneid": "ABUW_0002", "Abaum_0017": "4.5", "Abaum_0023": "6.5", "treated-unselected": "999"},
    ])
    return root


def test_individual_columns_are_not_means_or_claimed_independent_biosamples(tmp_path, author_sources):
    original = {path: path.read_bytes() for path in author_sources.rglob("*.csv")}
    frozen = tmp_path / "baseline.npz"
    np.savez_compressed(frozen, genes=np.array(["ABUW_0001", "ABUW_0002"]), expression=np.array([1.0, 5.5]))
    targets = prepare_baseline_samples(author_sources, tmp_path / "profiles", reference_baseline=frozen)
    assert len(targets) == 2
    for sample, expected in [("Abaum_0017", 0.0), ("Abaum_0023", 2.0)]:
        profile = load_profile(f"AB5075-{sample}", tmp_path / "profiles")
        row = profile.query_features("transcriptome", ["ABUW_0001"])["features"][0]
        assert row["expression_value"] == expected
        assert row["source_locator"]["native_source"] == {
            "path": str(author_sources / "interim/log_tpm_qc.csv"), "row": 2, "accession": None, "record_id": sample}
        overview = profile.overview()
        assert overview["condition"]["temperature_c"] is None
        assert overview["genotype"] is None
        assert overview["source_samples"] == [sample]
        assert overview["available_modalities"] == ["transcriptome"]
        assert "not verified independent biological replicates" in overview["modalities"]["transcriptome"]["provenance"]["citation"]
        receipt = json.loads((tmp_path / "profiles" / f"AB5075-{sample}" / "source_receipt.json").read_text())
        assert receipt["biosample_accession"] == "SAME_BIOSAMPLE"
        assert receipt["biological_replicate_independence"] == "not_established"
        assert receipt["frozen_mean_crosscheck"]["matches"] is True
    assert all(path.read_bytes() == value for path, value in original.items())
    with pytest.raises(ProfileError, match="already exists"):
        prepare_baseline_samples(author_sources, tmp_path / "profiles")


@pytest.mark.parametrize("file,column,value", [
    ("raw_data/metadata.csv", "condition_name", "AZI_003"),
    ("raw_data/metadata.csv", "strain_description", "different-strain"),
    ("raw_data/metadata.csv", "Run", "0"),
    ("interim/metadata_qc.csv", "passed_similar_replicates", "FALSE"),
    ("interim/log_tpm_qc.csv", "Abaum_0017", "nan"),
    ("interim/log_tpm_qc.csv", "Geneid", "0"),
])
def test_unverified_identity_or_non_native_missing_values_rejected(tmp_path, author_sources, file, column, value):
    path = author_sources / file
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    rows[0][column] = value
    _csv(path, rows)
    with pytest.raises(ProfileError):
        prepare_baseline_samples(author_sources, tmp_path / "profiles")
    assert not (tmp_path / "profiles/AB5075-Abaum_0017").exists()


def test_source_matrix_required_and_treated_samples_not_auto_promoted(tmp_path, author_sources):
    with pytest.raises(ProfileError, match="explicitly verified"):
        prepare_baseline_samples(author_sources, tmp_path / "profiles", ["treated-unselected"])
    (author_sources / "interim/log_tpm_qc.csv").unlink()
    with pytest.raises(ProfileError, match="Missing author source"):
        prepare_baseline_samples(author_sources, tmp_path / "profiles")


def test_disagreement_with_frozen_mean_blocks_preparation(tmp_path, author_sources):
    path = tmp_path / "baseline.npz"
    np.savez_compressed(path, genes=np.array(["ABUW_0001", "ABUW_0002"]), expression=np.array([77.0, 88.0]))
    with pytest.raises(ProfileError, match="reproduce the frozen"):
        prepare_baseline_samples(author_sources, tmp_path / "profiles", reference_baseline=path)
