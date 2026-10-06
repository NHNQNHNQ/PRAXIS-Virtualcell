"""Tests for exact, non-promoting MIC candidate/profile linkage."""

from __future__ import annotations

import pytest

from research.mdr_gnb.mic_profile_linkage_qualification import (
    CandidateProfileQualificationError,
    qualify_candidate_profile_rows,
    read_biosample_year_tsv,
)


def _candidate(
    candidate_id: str,
    *,
    biosample: str | None = "SAMN0001",
    assembly: str | None = "GCA_000000001.1",
    relation: str = "=",
    gaps: list[str] | None = None,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "candidate_status": "record_level_quantitative_mic_candidate_unverified",
        "data_admission_status": "not_admitted",
        "scientific_status": "unverified",
        "BioSample_ID": biosample,
        "assembly_ID": assembly,
        "lossless_relation": relation,
        "m1_gap_codes": list(
            gaps or ["assay_conditions_missing", "profile_toolchain_missing"]
        ),
    }


def _profile(
    *,
    biosample: str = "SAMN0001",
    assembly: str = "GCA_000000001.1",
    drug: str = "meropenem",
    phenotype: str = "R",
    genotype: str = "blaKPC-2,ompF_D29GfsTer1=POINT",
) -> dict[str, str]:
    return {
        "ncbi_biosample_acc": biosample,
        "genome_id": assembly,
        "antibiotic": drug,
        "resistant_phenotype": phenotype,
        "ncbi_amr_genotypes": genotype,
    }


def test_exact_pair_linkage_keeps_candidate_unadmitted_and_marks_research_only() -> None:
    rows = qualify_candidate_profile_rows(
        [_candidate("candidate-1")],
        [_profile()],
        {"GCA_000000001.1": "ST42"},
        {"SAMN0001": 2020},
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["profile_linkage_status"] == "exact_profile_join"
    assert row["profile_linkage_key"] == "SAMN0001|GCA_000000001.1"
    assert row["profile_toolchain_status"] == "local_dirty_legacy_source_observation"
    assert row["profile_raw_genotypes"] == "blaKPC-2,ompF_D29GfsTer1=POINT"
    assert row["lineage_st"] == "ST42"
    assert row["profile_collection_year"] == 2020
    assert row["local_sir_reference_labels"] == ["R"]
    assert row["data_admission_status"] == "not_admitted"
    assert row["scientific_status"] == "unverified"
    assert row["research_baseline_status"] == "profile_linked_candidate_pending_governance"
    assert "profile_toolchain_missing" in row["qualification_gap_codes"]
    assert "sparse_positive_profile_negative_semantics_missing" in row["qualification_gap_codes"]


@pytest.mark.parametrize(
    ("candidate", "profiles", "expected_status"),
    [
        (
            _candidate("assembly-only", biosample="SAMNwrong"),
            [_profile()],
            "unmatched_assembly",
        ),
        (
            _candidate("biosample-null", assembly=None),
            [_profile(assembly="NULL")],
            "missing_assembly_biosample_NULL",
        ),
        (
            _candidate("missing", assembly=None, biosample="SAMNmissing"),
            [],
            "missing_assembly_no_local",
        ),
    ],
)
def test_non_exact_or_missing_keys_never_promote_to_profile_linkage(
    candidate: dict[str, object], profiles: list[dict[str, str]], expected_status: str
) -> None:
    row = qualify_candidate_profile_rows(
        [candidate], profiles, {"GCA_000000001.1": "ST42"}, {}
    )[0]

    assert row["profile_linkage_status"] == expected_status
    assert row["profile_raw_genotypes"] is None
    assert row["research_baseline_status"] == "profile_unlinked_candidate"
    assert row["data_admission_status"] == "not_admitted"


def test_conflicting_local_sir_is_a_qa_flag_not_a_rewritten_mic_label() -> None:
    row = qualify_candidate_profile_rows(
        [_candidate("conflict")],
        [_profile(phenotype="I"), _profile(phenotype="R")],
        {"GCA_000000001.1": "ST42"},
        {},
    )[0]

    assert row["profile_linkage_status"] == "exact_profile_join"
    assert row["local_sir_reference_labels"] == ["I", "R"]
    assert "local_sir_reference_conflict" in row["qualification_gap_codes"]
    assert "resistant_phenotype" not in row


def test_conflicting_profile_payload_fails_closed() -> None:
    with pytest.raises(CandidateProfileQualificationError, match="profile payload conflict"):
        qualify_candidate_profile_rows(
            [_candidate("profile-conflict")],
            [_profile(genotype="blaKPC-2"), _profile(genotype="blaNDM-1")],
            {"GCA_000000001.1": "ST42"},
            {},
        )


def test_candidate_state_and_lossless_relation_are_preserved() -> None:
    candidate = _candidate("censored", relation="<", gaps=["existing-gap"])
    row = qualify_candidate_profile_rows(
        [candidate], [_profile()], {"GCA_000000001.1": "ST42"}, {}
    )[0]

    assert candidate["m1_gap_codes"] == ["existing-gap"]
    assert row["lossless_relation"] == "<"
    assert row["candidate_status"] == "record_level_quantitative_mic_candidate_unverified"
    assert row["qualification_gap_codes"] == sorted(row["qualification_gap_codes"])


def test_headerless_year_cache_preserves_na_as_missing(tmp_path) -> None:
    source = tmp_path / "biosample_year.tsv"
    source.write_text("SAMNknown\t2020\nSAMNunknown\tNA\n", encoding="utf-8")

    assert read_biosample_year_tsv(source) == {"SAMNknown": 2020}
