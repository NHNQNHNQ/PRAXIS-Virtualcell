"""Exact, non-promoting linkage of MIC candidates to local AMR profiles.

This module is intentionally research-only.  A linkage is a provenance fact,
not data admission, a Pack binding, a training set, or a MIC prediction.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

CANDIDATE_SCHEMA_VERSION = "gnb.mic-record-level-candidate.v1"
PROFILE_SOURCE_STATUS = "local_dirty_legacy_source_observation"
_ASSEMBLY = re.compile(r"GC[AF]_\d+\.\d+")
_PROFILE_FIELDS = (
    "genome_id",
    "genome_name",
    "antibiotic",
    "laboratory_typing_method",
    "measurement",
    "measurement_unit",
    "measurement_sign",
    "resistant_phenotype",
    "ncbi_target_acc",
    "ncbi_biosample_acc",
    "ncbi_amr_genotypes",
)


class CandidateProfileQualificationError(ValueError):
    """Raised when exact linkage inputs are malformed or internally inconsistent."""


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate_key(candidate: dict[str, object]) -> tuple[str, str]:
    return _text(candidate.get("BioSample_ID")), _text(candidate.get("assembly_ID"))


def _profile_key(profile: dict[str, str]) -> tuple[str, str]:
    return _text(profile.get("ncbi_biosample_acc")), _text(profile.get("genome_id"))


def _validate_candidate(candidate: dict[str, object]) -> None:
    if candidate.get("candidate_schema_version") not in (None, CANDIDATE_SCHEMA_VERSION):
        raise CandidateProfileQualificationError("candidate schema drift")
    if not _text(candidate.get("candidate_id")):
        raise CandidateProfileQualificationError("candidate id is missing")
    if candidate.get("candidate_status") != "record_level_quantitative_mic_candidate_unverified":
        raise CandidateProfileQualificationError("candidate status is not research-only")
    if candidate.get("data_admission_status") != "not_admitted":
        raise CandidateProfileQualificationError("candidate admission state drift")
    if candidate.get("scientific_status") != "unverified":
        raise CandidateProfileQualificationError("candidate scientific state drift")
    if candidate.get("lossless_relation") not in {"=", "<", ">"}:
        raise CandidateProfileQualificationError("candidate relation is not lossless")
    gaps = candidate.get("m1_gap_codes")
    if not isinstance(gaps, list) or not all(isinstance(item, str) for item in gaps):
        raise CandidateProfileQualificationError("candidate gaps are invalid")


def _build_profile_index(
    profiles: Iterable[dict[str, str]],
) -> tuple[dict[tuple[str, str], list[dict[str, str]]], set[str]]:
    by_pair: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    biosamples_with_null_assembly: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            raise CandidateProfileQualificationError("profile row is invalid")
        pair = _profile_key(profile)
        if not pair[0]:
            continue
        if pair[1].upper() == "NULL":
            biosamples_with_null_assembly.add(pair[0])
            continue
        by_pair[pair].append(profile)
    return dict(by_pair), biosamples_with_null_assembly


def _exact_profile_evidence(
    profile_rows: list[dict[str, str]],
) -> tuple[str, list[str], str]:
    meropenem = [
        row
        for row in profile_rows
        if _text(row.get("antibiotic")).casefold() == "meropenem"
    ]
    if not meropenem:
        raise CandidateProfileQualificationError("exact pair has no local meropenem reference")
    genotypes = {_text(row.get("ncbi_amr_genotypes")) for row in meropenem}
    genotypes.discard("")
    if not genotypes:
        raise CandidateProfileQualificationError("exact pair has no local profile payload")
    if len(genotypes) != 1:
        raise CandidateProfileQualificationError("profile payload conflict")
    labels = sorted({_text(row.get("resistant_phenotype")).upper() for row in meropenem})
    if not labels or any(label not in {"S", "I", "R"} for label in labels):
        raise CandidateProfileQualificationError("local SIR reference is invalid")
    genotype = next(iter(genotypes))
    return genotype, labels, _sha256_text(genotype)


def _year(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = _text(value)
    if text.isdigit() and len(text) == 4:
        return int(text)
    return None


def qualify_candidate_profile_rows(
    candidates: Iterable[dict[str, object]],
    profiles: Iterable[dict[str, str]],
    st_map: dict[str, str],
    biosample_year_map: dict[str, int],
) -> list[dict[str, object]]:
    """Qualify exact candidate/profile linkage without changing candidate semantics.

    Exact means both the BioSample and the versioned assembly accession agree.
    A matching local S/I/R label is retained only as a QA reference; it never
    replaces, discretizes, or validates the quantitative MIC label.
    """

    profile_index, biosamples_with_null_assembly = _build_profile_index(profiles)
    out: list[dict[str, object]] = []
    seen_candidate_ids: set[str] = set()
    for source_candidate in candidates:
        if not isinstance(source_candidate, dict):
            raise CandidateProfileQualificationError("candidate row is invalid")
        _validate_candidate(source_candidate)
        candidate = dict(source_candidate)
        candidate_id = _text(candidate["candidate_id"])
        if candidate_id in seen_candidate_ids:
            raise CandidateProfileQualificationError("candidate id is duplicated")
        seen_candidate_ids.add(candidate_id)

        biosample, assembly = _candidate_key(candidate)
        gaps = set(candidate["m1_gap_codes"])
        row: dict[str, object] = dict(candidate)
        row.update(
            {
                "profile_linkage_key": None,
                "profile_linkage_status": None,
                "profile_toolchain_status": None,
                "profile_raw_genotypes": None,
                "profile_payload_sha256": None,
                "profile_token_count": None,
                "local_sir_reference_labels": [],
                "lineage_st": None,
                "profile_collection_year": _year(biosample_year_map.get(biosample)),
                "research_baseline_status": "profile_unlinked_candidate",
            }
        )

        if biosample and _ASSEMBLY.fullmatch(assembly):
            exact_rows = profile_index.get((biosample, assembly))
            if exact_rows is None:
                row["profile_linkage_status"] = "unmatched_assembly"
                gaps.add("exact_profile_linkage_missing")
            else:
                genotype, labels, genotype_sha256 = _exact_profile_evidence(exact_rows)
                st = _text(st_map.get(assembly))
                row.update(
                    {
                        "profile_linkage_key": f"{biosample}|{assembly}",
                        "profile_linkage_status": "exact_profile_join",
                        "profile_toolchain_status": PROFILE_SOURCE_STATUS,
                        "profile_raw_genotypes": genotype,
                        "profile_payload_sha256": genotype_sha256,
                        "profile_token_count": len(
                            [token for token in genotype.split(",") if token.strip()]
                        ),
                        "local_sir_reference_labels": labels,
                        "lineage_st": st or None,
                        "research_baseline_status": "profile_linked_candidate_pending_governance",
                    }
                )
                gaps.update(
                    {
                        "local_profile_not_pack_bound",
                        "sparse_positive_profile_negative_semantics_missing",
                    }
                )
                if not st or st.casefold() == "unknown":
                    gaps.add("lineage_assignment_missing")
                if len(labels) > 1:
                    gaps.add("local_sir_reference_conflict")
        elif biosample and biosample in biosamples_with_null_assembly:
            row["profile_linkage_status"] = "missing_assembly_biosample_NULL"
            gaps.add("versioned_assembly_identity_missing")
            gaps.add("exact_profile_linkage_missing")
        else:
            row["profile_linkage_status"] = "missing_assembly_no_local"
            gaps.add("versioned_assembly_identity_missing")
            gaps.add("exact_profile_linkage_missing")

        row["qualification_gap_codes"] = sorted(gaps)
        out.append(row)
    return out


def read_profile_tsv(path: Path) -> list[dict[str, str]]:
    """Read the exact local NCBI legacy profile schema fail-closed."""

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != _PROFILE_FIELDS:
            raise CandidateProfileQualificationError("local profile schema drift")
        return [dict(row) for row in reader]


def read_st_tsv(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != ("asm_acc", "st"):
            raise CandidateProfileQualificationError("local lineage schema drift")
        out: dict[str, str] = {}
        for row in reader:
            assembly = _text(row["asm_acc"])
            st = _text(row["st"])
            if not assembly or not st or assembly in out:
                raise CandidateProfileQualificationError("local lineage mapping is invalid")
            out[assembly] = st
    return out


def read_biosample_year_tsv(path: Path) -> dict[str, int]:
    """Read the headerless two-column legacy year cache without inferring values."""

    out: dict[str, int] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if len(row) != 2:
                raise CandidateProfileQualificationError("local year schema drift")
            biosample, year = (_text(row[0]), _year(row[1]))
            if not biosample or biosample in out:
                raise CandidateProfileQualificationError("local year mapping is invalid")
            if year is None:
                if _text(row[1]).upper() == "NA":
                    continue
                raise CandidateProfileQualificationError("local year mapping is invalid")
            out[biosample] = year
    return out


def qualification_summary(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    materialized = list(rows)
    linkage_counts = Counter(str(row["profile_linkage_status"]) for row in materialized)
    relation_counts = Counter(str(row["lossless_relation"]) for row in materialized)
    linked = [row for row in materialized if row["profile_linkage_status"] == "exact_profile_join"]
    linked_keys = {str(row["profile_linkage_key"]) for row in linked}
    return {
        "rows": len(materialized),
        "linkage_counts": dict(sorted(linkage_counts.items())),
        "exact_profile_join_unique_keys": len(linked_keys),
        "linked_relation_counts": dict(
            sorted(Counter(str(row["lossless_relation"]) for row in linked).items())
        ),
        "linked_with_lineage": sum(bool(row["lineage_st"]) for row in linked),
        "linked_with_collection_year": sum(
            row["profile_collection_year"] is not None for row in linked
        ),
        "linked_sir_reference_conflicts": sum(
            "local_sir_reference_conflict" in row["qualification_gap_codes"]
            for row in linked
        ),
        "candidate_relation_counts": dict(sorted(relation_counts.items())),
        "data_admission_statuses": sorted(
            {str(row["data_admission_status"]) for row in materialized}
        ),
        "scientific_statuses": sorted({str(row["scientific_status"]) for row in materialized}),
    }


def canonical_json_sha256(value: dict[str, Any]) -> str:
    """Stable JSON fingerprint helper for a caller-owned report."""

    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
