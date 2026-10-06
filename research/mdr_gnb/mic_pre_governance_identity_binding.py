"""Bind a future MIC record to one frozen identity-only allocation row.

This offline research contract does not create an admission decision, Pack,
model, artifact, or prediction.  A caller must separately bind the allocation
file and authorization identities before using this row-level check.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from research.mdr_gnb.mic_admission_contract import MICAdmissionRecordError, validate_mic_admission_record

SCHEMA_VERSION = "gnb.mic-pre-governance-identity-allocation-binding.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOCATION_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "biosample_accession",
        "assembly_accession",
        "profile_payload_sha256",
        "profile_toolchain_status",
        "lineage_st",
        "allocation_protocol_id",
        "allocation_protocol_version",
        "allocation_protocol_fingerprint",
        "leakage_unit",
        "leakage_group_fingerprint",
        "assignment",
        "allocation_status",
        "candidate_status",
        "data_admission_status",
        "scientific_status",
        "pack_authorized",
        "training_authorized",
        "evaluation_authorized",
        "prediction_authorized",
    }
)
_CANDIDATE_RECORD_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_id",
        "source_record_id",
        "biosample_id",
        "assembly_accession",
        "profile_payload_fingerprint",
    }
)


class MICPreGovernanceIdentityBindingError(ValueError):
    """A fail-closed error for an identity-only allocation mismatch."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid MIC identity allocation binding: {code}")


class _InternalMICPreGovernanceIdentityBindingError(MICPreGovernanceIdentityBindingError):
    """Marks errors created by this module's validator."""


def _fail(code: str) -> None:
    raise _InternalMICPreGovernanceIdentityBindingError(code)


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        _fail(code)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _fail(code)
    return value


def _sha256(value: Any, code: str) -> str:
    value = _text(value, code)
    if _SHA256.fullmatch(value) is None:
        _fail(code)
    return value


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    try:
        return hashlib.sha256(
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
    except Exception:  # noqa: BLE001 - identity binding is a fail-closed boundary
        _fail("schema_invalid")


def _plain_mapping(value: Any) -> dict[str, Any]:
    """Freeze an untrusted JSON-shaped input before validating its bindings."""

    try:
        frozen = json.loads(
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
        )
    except Exception:  # noqa: BLE001 - untrusted mapping access must fail closed
        _fail("schema_invalid")
    if not isinstance(frozen, dict):
        _fail("schema_invalid")
    return frozen


def _allocation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _ALLOCATION_FIELDS:
        _fail("schema_invalid")
    if value["schema_version"] != "gnb.mic-pre-governance-identity-allocation.v1":
        _fail("schema_invalid")
    for field in (
        "candidate_id",
        "biosample_accession",
        "assembly_accession",
        "profile_toolchain_status",
        "lineage_st",
        "allocation_protocol_id",
        "allocation_protocol_version",
        "leakage_unit",
    ):
        _text(value[field], "schema_invalid")
    for field in (
        "profile_payload_sha256",
        "allocation_protocol_fingerprint",
        "leakage_group_fingerprint",
    ):
        _sha256(value[field], "schema_invalid")
    if value["assignment"] not in {"train", "dev", "held_out"}:
        _fail("schema_invalid")
    if (
        value["allocation_status"] != "identity_only_pre_governance_not_admitted"
        or value["candidate_status"] != "record_level_quantitative_mic_candidate_unverified"
        or value["data_admission_status"] != "not_admitted"
        or value["scientific_status"] != "unverified"
        or any(
            value[field] is not False
            for field in (
                "pack_authorized",
                "training_authorized",
                "evaluation_authorized",
                "prediction_authorized",
            )
        )
    ):
        _fail("allocation_not_pre_governance_not_admitted")
    return value


def _candidate_record_binding(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _CANDIDATE_RECORD_BINDING_FIELDS:
        _fail("schema_invalid")
    if value["schema_version"] != "gnb.mic-pre-governance-candidate-record-binding.v1":
        _fail("schema_invalid")
    for field in ("candidate_id", "source_record_id", "biosample_id", "assembly_accession"):
        _text(value[field], "schema_invalid")
    _sha256(value["profile_payload_fingerprint"], "schema_invalid")
    return value


def _validate(record: Any, allocation_row: Any, candidate_binding: Any) -> dict[str, str]:
    record = _plain_mapping(record)
    allocation_row = _plain_mapping(allocation_row)
    candidate_binding = _plain_mapping(candidate_binding)
    try:
        record_summary = validate_mic_admission_record(record)
    except MICAdmissionRecordError:
        _fail("record_not_structurally_complete")
    if (
        record_summary.get("status") != "structurally_complete_unreviewed"
        or record_summary.get("admission_status") != "not_admitted"
    ):
        _fail("record_not_structurally_complete")
    allocation = _allocation(allocation_row)
    candidate_binding = _candidate_record_binding(candidate_binding)
    isolate = record["isolate_profile"]
    split = record["split"]
    expected = {
        "biosample_accession": isolate["biosample_id"],
        "assembly_accession": isolate["assembly_accession"],
        "profile_payload_sha256": isolate["profile_payload_fingerprint"],
        "allocation_protocol_id": split["protocol_id"],
        "allocation_protocol_version": split["protocol_version"],
        "allocation_protocol_fingerprint": split["protocol_fingerprint"],
        "leakage_unit": split["leakage_unit"],
        "leakage_group_fingerprint": split["leakage_group_fingerprint"],
        "assignment": split["assignment"],
    }
    if any(allocation[field] != expected[field] for field in expected):
        _fail("identity_allocation_binding_mismatch")
    expected_candidate_binding = {
        "candidate_id": allocation["candidate_id"],
        "source_record_id": record["source"]["source_record_id"],
        "biosample_id": isolate["biosample_id"],
        "assembly_accession": isolate["assembly_accession"],
        "profile_payload_fingerprint": isolate["profile_payload_fingerprint"],
    }
    if any(
        candidate_binding[field] != expected_candidate_binding[field]
        for field in expected_candidate_binding
    ):
        _fail("candidate_record_binding_mismatch")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_summary["record_id"],
        "record_fingerprint": record_summary["record_fingerprint"],
        "candidate_record_binding_fingerprint": _canonical_fingerprint(candidate_binding),
        "allocation_row_fingerprint": _canonical_fingerprint(allocation),
        "status": "not_admitted",
        "admission_status": "not_admitted",
    }


def validate_mic_record_identity_allocation_binding(
    record: Any, allocation_row: Any, candidate_binding: Any
) -> dict[str, str]:
    """Validate row-level identity/split equality without granting admission.

    The candidate-binding and allocation rows must themselves be bound to
    authenticated, immutable source artifacts by the caller's future receipt.
    This function deliberately verifies only their row-level correspondence.
    """

    try:
        return _validate(record, allocation_row, candidate_binding)
    except _InternalMICPreGovernanceIdentityBindingError:
        raise
    except Exception:  # noqa: BLE001 - public research boundary must fail closed
        _fail("schema_invalid")


__all__ = [
    "MICPreGovernanceIdentityBindingError",
    "SCHEMA_VERSION",
    "validate_mic_record_identity_allocation_binding",
]
