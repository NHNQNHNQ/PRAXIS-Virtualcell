"""Contract checks for the identity-only pre-governance MIC allocation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "research/mdr_gnb/mic_discovery/2026-08-14-pre-governance-identity-split-ecoli-meropenem"
    / "derived/freeze_pre_governance_identity_split_v1.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("pre_governance_identity_split", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def test_identity_only_allocation_keeps_an_st_group_together_and_excludes_outcome_fields() -> None:
    module = _module()
    rows = [
        {
            "candidate_id": "candidate-a",
            "biosample_accession": "SAMN00000001",
            "assembly_accession": "GCA_000000001.1",
            "profile_payload_sha256": "a" * 64,
            "lineage_st": "ST131",
            "profile_toolchain_status": "local_dirty_legacy_source_observation",
        },
        {
            "candidate_id": "candidate-b",
            "biosample_accession": "SAMN00000002",
            "assembly_accession": "GCA_000000002.1",
            "profile_payload_sha256": "b" * 64,
            "lineage_st": "ST131",
            "profile_toolchain_status": "local_dirty_legacy_source_observation",
        },
        {
            "candidate_id": "candidate-c",
            "biosample_accession": "SAMN00000003",
            "assembly_accession": "GCA_000000003.1",
            "profile_payload_sha256": "c" * 64,
            "lineage_st": "ST167",
            "profile_toolchain_status": "local_dirty_legacy_source_observation",
        },
    ]

    allocation = module.allocate_identity_only(rows)

    assert len(allocation) == 3
    assert allocation[0]["assignment"] == allocation[1]["assignment"]
    assert allocation[0]["leakage_group_fingerprint"] == allocation[1]["leakage_group_fingerprint"]
    assert {row["assignment"] for row in allocation} <= {"train", "dev", "held_out"}
    forbidden = {"mic", "measurement", "sir", "assay", "phenotype", "publication"}
    assert all(
        not any(token in key.lower() for token in forbidden) for row in allocation for key in row
    )


def test_identity_only_reader_uses_a_column_allowlist_and_rejects_an_outcome_field() -> None:
    module = _module()
    forbidden_source_columns = {
        "raw_measurement_decimal",
        "lossless_relation",
        "lossless_censoring",
        "local_sir_reference_labels",
        "ast_standard",
        "laboratory_typing_method",
        "platform",
        "AMR_associated_publications",
        "profile_raw_genotypes",
    }

    assert forbidden_source_columns.isdisjoint(module.PROFILE_COLUMNS)
    assert "measurement" not in " ".join(module.PROFILE_COLUMNS).lower()

    row = {
        "candidate_id": "candidate-a",
        "biosample_accession": "SAMN00000001",
        "assembly_accession": "GCA_000000001.1",
        "profile_payload_sha256": "a" * 64,
        "lineage_st": "ST131",
        "profile_toolchain_status": "local_dirty_legacy_source_observation",
        "mic_value": "1",
    }
    with pytest.raises(SystemExit, match="identity row schema drift"):
        module.allocate_identity_only([row])


def test_identity_readers_never_decode_007_attributes_and_push_scope_to_parquet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()

    class _Table:
        def __init__(self, rows: list[dict[str, object]]) -> None:
            self._rows = rows

        def to_pylist(self) -> list[dict[str, object]]:
            return self._rows

    accessions = set(module.FROZEN_BIOSAMPLES)
    profile_rows = [
        {
            "candidate_id": f"candidate-{index}",
            "candidate_status": "record_level_quantitative_mic_candidate_unverified",
            "data_admission_status": "not_admitted",
            "scientific_status": "unverified",
            "BioSample_ID": accession,
            "assembly_ID": f"GCA_{index:09d}.1",
            "profile_linkage_status": "exact_profile_join",
            "profile_toolchain_status": "local_dirty_legacy_source_observation",
            "profile_payload_sha256": f"{index:064x}",
            "lineage_st": f"ST{index}",
        }
        for index, accession in enumerate(sorted(accessions), start=1)
    ]
    assembly_rows = [
        {
            "assembly_accession": row["assembly_ID"],
            "biosample_accession": row["BioSample_ID"],
            "metadata_qualification_status": "metadata_exact_match_candidate_not_admitted",
            "species_evidence_status": "checkm_species_tax_id_562",
            "returned_organism_name": "Escherichia coli",
            "returned_organism_tax_id": 562,
            "returned_checkm_species_tax_id": 562,
            "candidate_status": "record_level_quantitative_mic_candidate_unverified",
            "data_admission_status": "not_admitted",
            "scientific_status": "unverified",
        }
        for row in profile_rows
    ]
    calls: list[tuple[Path, tuple[str, ...], list[tuple[str, str, list[str]]]]] = []

    def fake_read_table(
        path: Path,
        *,
        columns: list[str],
        filters: list[tuple[str, str, list[str]]],
    ) -> _Table:
        calls.append((path, tuple(columns), filters))
        if path == module.PROFILE_PATH:
            return _Table(profile_rows)
        assert path == module.ASSEMBLY_PATH
        return _Table(assembly_rows)

    def fake_sha256(path: object) -> str:
        if path is module.COHORT_PATH:
            return module.COHORT_SHA256
        if path == module.PROFILE_PATH:
            return module.PROFILE_SHA256
        if path == module.ASSEMBLY_PATH:
            return module.ASSEMBLY_SHA256
        raise AssertionError(f"unexpected hash path: {path!r}")

    monkeypatch.setattr(module, "_sha256_file", fake_sha256)
    monkeypatch.setattr(module.pq, "read_table", fake_read_table)
    cohort_path = module.COHORT_PATH
    monkeypatch.setattr(module, "COHORT_PATH", object())
    assert module._read_cohort() == accessions
    monkeypatch.setattr(module, "COHORT_PATH", cohort_path)

    selected = module._read_identity_rows(accessions)
    module._check_assembly_rows(selected)

    assert calls == [
        (
            module.PROFILE_PATH,
            module.PROFILE_COLUMNS,
            [("BioSample_ID", "in", sorted(accessions))],
        ),
        (
            module.ASSEMBLY_PATH,
            module.ASSEMBLY_COLUMNS,
            [("biosample_accession", "in", sorted(accessions))],
        ),
    ]
