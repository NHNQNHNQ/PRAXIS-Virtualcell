"""Fail-closed NCBI Assembly metadata observations for MIC research candidates.

This module validates only identity/provenance observations from the one
authorized NCBI Datasets endpoint.  It never admits data, creates a Pack,
assigns a split, trains, evaluates, or predicts.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable

_GCA_ACCESSION = re.compile(r"GCA_\d+\.\d+")
_PAIR_FIELDS = frozenset({"assembly_accession", "biosample_accession"})
_RAW_REQUEST_FIELDS = _PAIR_FIELDS | {"endpoint"}
_CANDIDATE_STATUS = "record_level_quantitative_mic_candidate_unverified"
_NOT_ADMITTED = "not_admitted"
_UNVERIFIED = "unverified"


class AssemblyMetadataQualificationError(ValueError):
    """Raised when the pinned profile-linkage input has drifted or is ambiguous."""


def _text(value: object) -> str | None:
    if not isinstance(value, str) or not value or value.strip() != value:
        return None
    return value


def _mapping(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _observed_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _observed_int(value: object) -> int | None:
    return value if type(value) is int else None


def _canonical_observation(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_json_sha256(value: object) -> str:
    """Fingerprint an observation without treating it as an immutable NCBI release."""

    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def endpoint_for_assembly(assembly_accession: str) -> str:
    """Return the sole endpoint authorized for a validated versioned GenBank accession."""

    if _GCA_ACCESSION.fullmatch(assembly_accession) is None:
        raise AssemblyMetadataQualificationError("assembly is not a versioned GCA accession")
    return (
        "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/"
        f"{assembly_accession}/dataset_report"
    )


def _pair(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != _PAIR_FIELDS:
        raise AssemblyMetadataQualificationError("pair schema drift")
    assembly = _text(value.get("assembly_accession"))
    biosample = _text(value.get("biosample_accession"))
    if assembly is None or _GCA_ACCESSION.fullmatch(assembly) is None:
        raise AssemblyMetadataQualificationError("assembly is not a versioned GCA accession")
    if biosample is None:
        raise AssemblyMetadataQualificationError("biosample is missing")
    return {"assembly_accession": assembly, "biosample_accession": biosample}


def pair_from_raw_request(value: object) -> dict[str, str]:
    """Recover the exact request pair without treating audit metadata as identity."""

    if not isinstance(value, dict) or set(value) != _RAW_REQUEST_FIELDS:
        raise AssemblyMetadataQualificationError("raw request schema drift")
    pair = _pair(
        {
            "assembly_accession": value.get("assembly_accession"),
            "biosample_accession": value.get("biosample_accession"),
        }
    )
    if value.get("endpoint") != endpoint_for_assembly(pair["assembly_accession"]):
        raise AssemblyMetadataQualificationError("raw request endpoint drift")
    return pair


def derive_exact_profile_pairs(
    rows: Iterable[dict[str, object]], *, expected_count: int | None = None
) -> list[dict[str, str]]:
    """Derive the exact query set while retaining candidate data outside this operation.

    Only ``exact_profile_join`` rows participate; de-duplication here is strictly
    for the authorized request list and does not modify source candidate rows.
    """

    by_assembly: dict[str, str] = {}
    by_biosample: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise AssemblyMetadataQualificationError("profile-linkage row is invalid")
        if row.get("profile_linkage_status") != "exact_profile_join":
            continue
        if (
            row.get("candidate_status") != _CANDIDATE_STATUS
            or row.get("data_admission_status") != _NOT_ADMITTED
            or row.get("scientific_status") != _UNVERIFIED
        ):
            raise AssemblyMetadataQualificationError("profile-linked candidate state drift")
        assembly = _text(row.get("assembly_ID"))
        biosample = _text(row.get("BioSample_ID"))
        if assembly is None or _GCA_ACCESSION.fullmatch(assembly) is None:
            raise AssemblyMetadataQualificationError("assembly is not a versioned GCA accession")
        if biosample is None:
            raise AssemblyMetadataQualificationError("biosample is missing")
        if row.get("profile_linkage_key") != f"{biosample}|{assembly}":
            raise AssemblyMetadataQualificationError("profile linkage key drift")
        existing_biosample = by_assembly.setdefault(assembly, biosample)
        if existing_biosample != biosample:
            raise AssemblyMetadataQualificationError("assembly maps to multiple biosamples")
        existing_assembly = by_biosample.setdefault(biosample, assembly)
        if existing_assembly != assembly:
            raise AssemblyMetadataQualificationError("biosample maps to multiple assemblies")

    pairs = [
        {"assembly_accession": assembly, "biosample_accession": biosample}
        for assembly, biosample in sorted(by_assembly.items())
    ]
    if not pairs:
        raise AssemblyMetadataQualificationError("no exact profile-linked GCA/BioSample pairs")
    if expected_count is not None and len(pairs) != expected_count:
        raise AssemblyMetadataQualificationError(
            "exact profile-linked pair count drift: "
            f"expected {expected_count}, observed {len(pairs)}"
        )
    return pairs


def _unresolved_base(
    pair: dict[str, str],
    *,
    http_status: int | None,
    content_type: str | None,
    response_body: str | None,
) -> dict[str, object]:
    return {
        **pair,
        "endpoint": endpoint_for_assembly(pair["assembly_accession"]),
        "http_status": http_status,
        "response_content_type": content_type,
        "response_sha256": (
            hashlib.sha256(response_body.encode("utf-8")).hexdigest()
            if response_body is not None
            else None
        ),
        "metadata_qualification_status": "metadata_unresolved_not_admitted",
        "species_evidence_status": "species_evidence_unresolved",
        "unresolved_reason_codes": [],
        "returned_accession": None,
        "returned_current_accession": None,
        "returned_paired_accession": None,
        "returned_source_database": None,
        "returned_organism_tax_id": None,
        "returned_organism_name": None,
        "returned_checkm_species_tax_id": None,
        "returned_assembly_status": None,
        "returned_biosample_accession": None,
        "returned_biosample_status": None,
        "returned_bioproject_accession": None,
        "returned_assembly_level": None,
        "returned_release_date": None,
        "returned_ani_taxonomy_check_status": None,
        "returned_ani_match_status": None,
        "returned_assembly_stats_observation": None,
        "returned_atypical_observation": None,
        "returned_ani_observation": None,
        "candidate_status": _CANDIDATE_STATUS,
        "data_admission_status": _NOT_ADMITTED,
        "scientific_status": _UNVERIFIED,
        "data_admission_authorized": False,
        "pack_authorized": False,
        "training_authorized": False,
        "evaluation_authorized": False,
        "prediction_authorized": False,
    }


def _report_observations(row: dict[str, object], report: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    assembly_info = _mapping(report.get("assembly_info"))
    organism = _mapping(report.get("organism"))
    checkm_info = _mapping(report.get("checkm_info"))
    biosample = _mapping(assembly_info.get("biosample")) if assembly_info else None
    biosample_state = _mapping(biosample.get("status")) if biosample else None
    ani = _mapping(report.get("average_nucleotide_identity"))
    assembly_stats = _mapping(report.get("assembly_stats"))

    row.update(
        {
            "returned_accession": _observed_text(report.get("accession")),
            "returned_current_accession": _observed_text(report.get("current_accession")),
            "returned_paired_accession": _observed_text(report.get("paired_accession")),
            "returned_source_database": _observed_text(report.get("source_database")),
            "returned_organism_tax_id": (
                _observed_int(organism.get("tax_id")) if organism else None
            ),
            "returned_organism_name": (
                _observed_text(organism.get("organism_name")) if organism else None
            ),
            "returned_checkm_species_tax_id": (
                _observed_int(checkm_info.get("checkm_species_tax_id")) if checkm_info else None
            ),
            "returned_assembly_status": (
                _observed_text(assembly_info.get("assembly_status")) if assembly_info else None
            ),
            "returned_biosample_accession": (
                _observed_text(biosample.get("accession")) if biosample else None
            ),
            "returned_biosample_status": (
                _observed_text(biosample_state.get("status")) if biosample_state else None
            ),
            "returned_bioproject_accession": (
                _observed_text(assembly_info.get("bioproject_accession")) if assembly_info else None
            ),
            "returned_assembly_level": (
                _observed_text(assembly_info.get("assembly_level")) if assembly_info else None
            ),
            "returned_release_date": (
                _observed_text(assembly_info.get("release_date")) if assembly_info else None
            ),
            "returned_ani_taxonomy_check_status": (
                _observed_text(ani.get("taxonomy_check_status")) if ani else None
            ),
            "returned_ani_match_status": _observed_text(ani.get("match_status")) if ani else None,
            "returned_assembly_stats_observation": _canonical_observation(assembly_stats),
            "returned_atypical_observation": _canonical_observation(
                assembly_info.get("atypical") if assembly_info else None
            ),
            "returned_ani_observation": _canonical_observation(ani),
        }
    )

    if row["returned_accession"] != row["assembly_accession"]:
        reasons.append("accession_mismatch")
    if row["returned_source_database"] != "SOURCE_DATABASE_GENBANK":
        reasons.append("source_database_not_genbank")
    if row["returned_biosample_accession"] != row["biosample_accession"]:
        reasons.append("biosample_mismatch")
    if row["returned_checkm_species_tax_id"] == 562:
        row["species_evidence_status"] = "checkm_species_tax_id_562"
    else:
        reasons.append("checkm_species_tax_id_not_562")
    if row["returned_assembly_status"] != "current":
        reasons.append("assembly_status_not_current")
    if row["returned_biosample_status"] != "live":
        reasons.append("biosample_status_not_live")
    return reasons


def qualify_ncbi_assembly_metadata_response(
    pair: dict[str, str],
    *,
    http_status: int | None,
    content_type: str | None,
    response_body: str | None,
    transport_error: str | None = None,
) -> dict[str, object]:
    """Classify one raw response without promoting any candidate data.

    Species evidence is intentionally *only* ``checkm_info.checkm_species_tax_id == 562``.
    A strain-level ``organism.tax_id`` is retained as an observation, never a substitute.
    """

    normalized_pair = _pair(pair)
    row = _unresolved_base(
        normalized_pair,
        http_status=http_status,
        content_type=content_type,
        response_body=response_body,
    )
    reasons: list[str] = []
    if http_status != 200:
        reasons.append("http_status_not_200")
    if transport_error is not None:
        reasons.append("transport_error")
    if response_body is None:
        reasons.append("response_body_missing")
    if reasons:
        row["unresolved_reason_codes"] = sorted(set(reasons))
        return row
    is_json_content_type = (
        content_type is not None
        and content_type.split(";", 1)[0].strip().casefold() == "application/json"
    )
    if not is_json_content_type:
        row["unresolved_reason_codes"] = ["content_type_not_json"]
        return row
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError:
        row["unresolved_reason_codes"] = ["response_not_json"]
        return row
    if not isinstance(payload, dict):
        row["unresolved_reason_codes"] = ["response_schema_invalid"]
        return row
    reports = payload.get("reports")
    if not isinstance(reports, list) or len(reports) != 1 or not isinstance(reports[0], dict):
        row["unresolved_reason_codes"] = ["response_report_count_not_one"]
        return row
    if payload.get("total_count") != 1:
        row["unresolved_reason_codes"] = ["response_total_count_not_one"]
        return row

    reasons.extend(_report_observations(row, reports[0]))
    if not reasons:
        row["metadata_qualification_status"] = "metadata_exact_match_candidate_not_admitted"
    row["unresolved_reason_codes"] = sorted(set(reasons))
    return row


def qualification_summary(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    """Summarize metadata observations while asserting their non-admission state."""

    materialized = list(rows)
    if any(row.get("data_admission_status") != _NOT_ADMITTED for row in materialized):
        raise AssemblyMetadataQualificationError("data admission state drift")
    if any(row.get("scientific_status") != _UNVERIFIED for row in materialized):
        raise AssemblyMetadataQualificationError("scientific state drift")
    status_counts = Counter(str(row.get("metadata_qualification_status")) for row in materialized)
    species_counts = Counter(str(row.get("species_evidence_status")) for row in materialized)
    unresolved_reasons = Counter(
        str(reason) for row in materialized for reason in row.get("unresolved_reason_codes", [])
    )
    return {
        "pairs": len(materialized),
        "metadata_qualification_status_counts": dict(sorted(status_counts.items())),
        "species_evidence_status_counts": dict(sorted(species_counts.items())),
        "unresolved_reason_counts": dict(sorted(unresolved_reasons.items())),
        "http_status_counts": dict(
            sorted(Counter(str(row.get("http_status")) for row in materialized).items())
        ),
        "data_admission_statuses": sorted(
            {str(row.get("data_admission_status")) for row in materialized}
        ),
        "scientific_statuses": sorted({str(row.get("scientific_status")) for row in materialized}),
        "training_authorized": False,
        "evaluation_authorized": False,
        "prediction_authorized": False,
    }


__all__ = [
    "AssemblyMetadataQualificationError",
    "canonical_json_sha256",
    "derive_exact_profile_pairs",
    "endpoint_for_assembly",
    "pair_from_raw_request",
    "qualification_summary",
    "qualify_ncbi_assembly_metadata_response",
]
