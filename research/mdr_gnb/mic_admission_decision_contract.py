"""Negative-only, offline governance receipts for MIC admission candidates.

This module neither admits data nor writes a ledger.  It validates a future
write-new governance receipt against a structurally screened record and keeps
every authorization flag false.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from research.mdr_gnb.mic_admission_contract import (
    SCHEMA_VERSION as RECORD_SCHEMA_VERSION,
)
from research.mdr_gnb.mic_admission_contract import (
    MICAdmissionRecordError,
    _parse_rfc3339_timestamp,
    validate_mic_admission_record,
)

SCHEMA_VERSION = "gnb.mic-admission-decision.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "decision_id",
        "decided_at",
        "record_binding",
        "decision",
        "governance",
        "supersedes_decision_fingerprint",
    }
)
_RECORD_BINDING_FIELDS = frozenset(
    {
        "record_schema_version",
        "record_id",
        "record_fingerprint",
        "structural_status",
        "admission_status_at_screen",
    }
)
_DECISION_FIELDS = frozenset(
    {
        "outcome",
        "reason_codes",
        "pack_authorized",
        "training_authorized",
        "artifact_authorized",
        "runtime_authorized",
    }
)
_GOVERNANCE_FIELDS = frozenset(
    {
        "authority_status",
        "license_review_status",
        "provenance_review_status",
        "authorization_evidence_fingerprint",
    }
)
_ALLOWED_OUTCOMES = frozenset({"deferred", "rejected"})
_ALLOWED_REASON_CODES = frozenset(
    {
        "authority_not_granted",
        "license_review_unresolved",
        "provenance_review_unresolved",
        "source_scope_not_authorized",
    }
)


class MICAdmissionDecisionError(ValueError):
    """A fail-closed error for a negative-only MIC governance receipt."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid MIC admission decision: {code}")


class _InternalMICAdmissionDecisionError(MICAdmissionDecisionError):
    """Marks errors created by this module's validator."""


def _fail(code: str) -> None:
    raise _InternalMICAdmissionDecisionError(code)


def _mapping(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(code)
    return value


def _exact_fields(value: Any, fields: frozenset[str], code: str) -> dict[str, Any]:
    mapping = _mapping(value, code)
    if set(mapping) != fields:
        _fail(code)
    return mapping


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
    except Exception:  # noqa: BLE001 - canonical identity must fail closed
        _fail("schema_invalid")


def _plain_mapping(value: Any) -> dict[str, Any]:
    """Freeze an untrusted JSON-shaped input before validating its bindings."""

    if not isinstance(value, dict):
        _fail("schema_invalid")
    try:
        source = {key: value[key] for key, _ in value.items()}
        frozen = json.loads(
            json.dumps(
                source, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
        )
    except Exception:  # noqa: BLE001 - public research boundary must fail closed
        _fail("schema_invalid")
    if not isinstance(frozen, dict):
        _fail("schema_invalid")
    return frozen


def _record_summary(record: Any) -> dict[str, str]:
    try:
        return validate_mic_admission_record(record)
    except MICAdmissionRecordError:
        _fail("record_not_structurally_complete")
    except Exception:  # noqa: BLE001 - a malformed offline record remains fail-closed
        _fail("record_not_structurally_complete")


def _record_binding(value: Any, *, record_summary: dict[str, str]) -> None:
    binding = _exact_fields(value, _RECORD_BINDING_FIELDS, "record_binding_mismatch")
    if (
        binding["record_schema_version"] != RECORD_SCHEMA_VERSION
        or _text(binding["record_id"], "record_binding_mismatch") != record_summary["record_id"]
        or _sha256(binding["record_fingerprint"], "record_binding_mismatch")
        != record_summary["record_fingerprint"]
        or binding["structural_status"] != "structurally_complete_unreviewed"
        or binding["admission_status_at_screen"] != "not_admitted"
    ):
        _fail("record_binding_mismatch")


def _decision(value: Any) -> tuple[str, tuple[str, ...]]:
    decision = _exact_fields(value, _DECISION_FIELDS, "schema_invalid")
    outcome = _text(decision["outcome"], "positive_admission_not_supported")
    if outcome not in _ALLOWED_OUTCOMES:
        _fail("positive_admission_not_supported")
    if any(
        decision[field] is not False
        for field in (
            "pack_authorized",
            "training_authorized",
            "artifact_authorized",
            "runtime_authorized",
        )
    ):
        _fail("positive_admission_not_supported")
    reasons = decision["reason_codes"]
    if not isinstance(reasons, list) or not reasons:
        _fail("decision_reason_invalid")
    normalized = tuple(_text(reason, "decision_reason_invalid") for reason in reasons)
    if any(reason not in _ALLOWED_REASON_CODES for reason in normalized) or normalized != tuple(
        sorted(set(normalized))
    ):
        _fail("decision_reason_invalid")
    return outcome, normalized


def _governance(value: Any) -> None:
    governance = _exact_fields(value, _GOVERNANCE_FIELDS, "schema_invalid")
    if (
        governance["authority_status"] != "not_granted"
        or governance["license_review_status"] != "unreviewed"
        or governance["provenance_review_status"] != "unreviewed"
        or governance["authorization_evidence_fingerprint"] is not None
    ):
        _fail("positive_admission_not_supported")


def _timestamp(value: Any):
    try:
        parsed = _parse_rfc3339_timestamp(_text(value, "schema_invalid"))
    except ValueError:
        _fail("schema_invalid")
    if parsed.tzinfo is None:
        _fail("schema_invalid")
    return parsed


def _supersession(value: Any) -> None:
    if value is not None:
        _sha256(value, "supersession_invalid")


def validate_mic_admission_decision(value: Any, record: Any) -> dict[str, Any]:
    """Validate a synthetic/offline decision without granting any authorization."""

    try:
        return _validate_mic_admission_decision(value, record)
    except _InternalMICAdmissionDecisionError:
        raise
    except Exception:  # noqa: BLE001 - public research boundary must fail closed
        _fail("schema_invalid")


def _validate_mic_admission_decision(value: Any, record: Any) -> dict[str, Any]:
    decision_record = _plain_mapping(value)
    record = _plain_mapping(record)
    record_summary = _record_summary(record)
    decision_record = _exact_fields(decision_record, _TOP_LEVEL_FIELDS, "schema_invalid")
    if decision_record["schema_version"] != SCHEMA_VERSION:
        _fail("schema_invalid")
    decision_id = _text(decision_record["decision_id"], "schema_invalid")
    decided_at = _timestamp(decision_record["decided_at"])
    _record_binding(decision_record["record_binding"], record_summary=record_summary)
    if decided_at < _timestamp(record["split"]["pre_registered_at"]):
        _fail("decision_precedes_split_preregistration")
    outcome, reasons = _decision(decision_record["decision"])
    _governance(decision_record["governance"])
    _supersession(decision_record["supersedes_decision_fingerprint"])
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_id": decision_id,
        "decision_fingerprint": _canonical_fingerprint(decision_record),
        "record_fingerprint": record_summary["record_fingerprint"],
        "outcome": outcome,
        "status": f"{outcome}_not_admitted",
        "admission_status": "not_admitted",
        "reason_codes": reasons,
    }


__all__ = [
    "MICAdmissionDecisionError",
    "SCHEMA_VERSION",
    "validate_mic_admission_decision",
]
