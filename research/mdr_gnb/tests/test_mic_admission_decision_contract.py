"""Negative-only governance receipts for synthetic MIC admission candidates."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from research.mdr_gnb.mic_admission_decision_contract import (
    MICAdmissionDecisionError,
    validate_mic_admission_decision,
)
from research.mdr_gnb.tests.test_mic_admission_contract import _record

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decision(record: dict | None = None) -> tuple[dict, dict]:
    record = _record() if record is None else record
    record_fingerprint = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return record, {
        "schema_version": "gnb.mic-admission-decision.v1",
        "decision_id": "synthetic-mic-decision-001",
        "decided_at": "2026-08-11T00:00:00Z",
        "record_binding": {
            "record_schema_version": "gnb.mic-admission-record.v1",
            "record_id": record["record_id"],
            "record_fingerprint": record_fingerprint,
            "structural_status": "structurally_complete_unreviewed",
            "admission_status_at_screen": "not_admitted",
        },
        "decision": {
            "outcome": "deferred",
            "reason_codes": [
                "authority_not_granted",
                "license_review_unresolved",
                "provenance_review_unresolved",
            ],
            "pack_authorized": False,
            "training_authorized": False,
            "artifact_authorized": False,
            "runtime_authorized": False,
        },
        "governance": {
            "authority_status": "not_granted",
            "license_review_status": "unreviewed",
            "provenance_review_status": "unreviewed",
            "authorization_evidence_fingerprint": None,
        },
        "supersedes_decision_fingerprint": None,
    }


def test_complete_structural_record_only_receives_deferred_not_admitted_decision():
    record, decision = _decision()

    summary = validate_mic_admission_decision(decision, record)

    assert summary["status"] == "deferred_not_admitted"
    assert summary["admission_status"] == "not_admitted"
    assert summary["record_fingerprint"] == decision["record_binding"]["record_fingerprint"]
    assert summary["decision_fingerprint"] == _sha(
        json.dumps(decision, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    forbidden_result_fields = {
        "pack",
        "model",
        "artifact",
        "evidence",
        "policy",
        "execution_plan",
        "prediction",
    }
    assert forbidden_result_fields.isdisjoint(summary)


def test_rejected_receipt_remains_not_admitted() -> None:
    record, decision = _decision()
    decision["decision"].update(
        {"outcome": "rejected", "reason_codes": ["source_scope_not_authorized"]}
    )

    summary = validate_mic_admission_decision(decision, record)

    assert summary["status"] == "rejected_not_admitted"
    assert summary["admission_status"] == "not_admitted"


def test_negative_decision_accepts_complete_rfc3339_offset() -> None:
    record, decision = _decision()
    decision["decided_at"] = "2026-08-11T08:00:00+08:00"

    assert validate_mic_admission_decision(decision, record)["status"] == "deferred_not_admitted"


def test_negative_decision_rejects_decision_before_split_preregistration() -> None:
    record = _record()
    record["split"]["pre_registered_at"] = "2026-08-12T00:00:00Z"
    record, decision = _decision(record)

    with pytest.raises(MICAdmissionDecisionError) as exc:
        validate_mic_admission_decision(decision, record)

    assert exc.value.code == "decision_precedes_split_preregistration"


def test_negative_decision_freezes_record_before_binding_and_timestamp_checks() -> None:
    class MutatingRecord(dict):
        def __init__(self, value: dict) -> None:
            super().__init__(value)
            self._split_reads = 0

        def __getitem__(self, key):
            value = super().__getitem__(key)
            if key == "split":
                self._split_reads += 1
                if self._split_reads == 2:
                    value["pre_registered_at"] = "2026-08-10T00:00:00Z"
            return value

    record = _record()
    record["split"]["pre_registered_at"] = "2026-08-12T00:00:00Z"
    record, decision = _decision(record)

    with pytest.raises(MICAdmissionDecisionError) as exc:
        validate_mic_admission_decision(decision, MutatingRecord(record))

    assert exc.value.code == "decision_precedes_split_preregistration"


def test_negative_decision_accepts_same_preregistration_in_equivalent_offset() -> None:
    record = _record()
    record["split"]["pre_registered_at"] = "2026-08-11T08:00:00+08:00"
    record, decision = _decision(record)

    assert validate_mic_admission_decision(decision, record)["status"] == "deferred_not_admitted"


def test_negative_decision_normalizes_canonical_fingerprint_failures() -> None:
    class ExplodingItemsDict(dict):
        def items(self):
            raise RuntimeError("json serialization trap")

    record, decision = _decision()

    with pytest.raises(MICAdmissionDecisionError) as exc:
        validate_mic_admission_decision(ExplodingItemsDict(decision), record)

    assert exc.value.code == "schema_invalid"


def test_negative_decision_normalizes_untrusted_mapping_access_failures() -> None:
    class TrapDict(dict):
        def __getitem__(self, key):
            if key == "schema_version":
                raise RuntimeError("mapping access trap")
            return super().__getitem__(key)

    record, decision = _decision()

    with pytest.raises(MICAdmissionDecisionError) as exc:
        validate_mic_admission_decision(TrapDict(decision), record)
    assert exc.value.code == "schema_invalid"


def test_negative_decision_normalizes_injected_public_domain_errors() -> None:
    class TrapDict(dict):
        def __getitem__(self, key):
            if key == "schema_version":
                raise MICAdmissionDecisionError("caller_injected_decision_code")
            return super().__getitem__(key)

    record, decision = _decision()

    with pytest.raises(MICAdmissionDecisionError) as exc:
        validate_mic_admission_decision(TrapDict(decision), record)
    assert exc.value.code == "schema_invalid"


@pytest.mark.parametrize(
    "timestamp",
    (
        "2026-08-11X00:00:00Z",
        "20260811T000000Z",
        "2026-08-11T00:00:00+08:00:30",
        "2026-08-11T00:00:00+08:00.5",
        "2026-08-11T00:00:00-00:00",
    ),
)
def test_negative_decision_rejects_non_rfc3339_timestamp(timestamp: str) -> None:
    record, decision = _decision()
    decision["decided_at"] = timestamp

    with pytest.raises(MICAdmissionDecisionError, match="schema_invalid"):
        validate_mic_admission_decision(decision, record)


@pytest.mark.parametrize(
    ("mutate", "code"),
    (
        pytest.param(
            lambda record, decision: decision["decision"].update({"outcome": "admitted"}),
            "positive_admission_not_supported",
            id="positive-outcome",
        ),
        pytest.param(
            lambda record, decision: decision["decision"].update({"outcome": []}),
            "positive_admission_not_supported",
            id="nontext-outcome",
        ),
        pytest.param(
            lambda record, decision: decision["decision"].update({"pack_authorized": True}),
            "positive_admission_not_supported",
            id="pack-authorization",
        ),
        pytest.param(
            lambda record, decision: decision.update({"pack_id": "forbidden"}),
            "schema_invalid",
            id="runtime-field",
        ),
        pytest.param(
            lambda record, decision: decision.update({"decision_id": "\ud800"}),
            "schema_invalid",
            id="non-utf8-decision-id",
        ),
        pytest.param(
            lambda record, decision: decision["record_binding"].update(
                {"record_fingerprint": _sha("wrong-record")}
            ),
            "record_binding_mismatch",
            id="record-fingerprint-mismatch",
        ),
        pytest.param(
            lambda record, decision: decision["record_binding"].update(
                {"record_schema_version": "wrong-schema"}
            ),
            "record_binding_mismatch",
            id="record-schema-mismatch",
        ),
        pytest.param(
            lambda record, decision: decision["record_binding"].update({"record_id": "wrong-id"}),
            "record_binding_mismatch",
            id="record-id-mismatch",
        ),
        pytest.param(
            lambda record, decision: decision["record_binding"].update(
                {"structural_status": "approved"}
            ),
            "record_binding_mismatch",
            id="record-structural-status-mismatch",
        ),
        pytest.param(
            lambda record, decision: decision["record_binding"].update(
                {"admission_status_at_screen": "admitted"}
            ),
            "record_binding_mismatch",
            id="record-admission-status-mismatch",
        ),
        pytest.param(
            lambda record, decision: record["review_state"].update({"authority": "approved"}),
            "record_not_structurally_complete",
            id="invalid-structural-record",
        ),
        pytest.param(
            lambda record, decision: decision["decision"].update({"reason_codes": []}),
            "decision_reason_invalid",
            id="empty-reasons",
        ),
        pytest.param(
            lambda record, decision: decision["decision"].update(
                {
                    "reason_codes": [
                        "license_review_unresolved",
                        "authority_not_granted",
                        "authority_not_granted",
                    ]
                }
            ),
            "decision_reason_invalid",
            id="unordered-duplicate-reasons",
        ),
        pytest.param(
            lambda record, decision: decision["governance"].update({"authority_status": "granted"}),
            "positive_admission_not_supported",
            id="granted-authority",
        ),
        pytest.param(
            lambda record, decision: decision.update(
                {"supersedes_decision_fingerprint": "not-a-sha"}
            ),
            "supersession_invalid",
            id="invalid-supersession",
        ),
    ),
)
def test_negative_only_decision_rejects_approval_or_unbound_state(mutate, code):
    record, decision = _decision()
    mutate(record, decision)

    with pytest.raises(MICAdmissionDecisionError, match=code):
        validate_mic_admission_decision(decision, record)


def test_decision_contract_stays_in_research_and_out_of_plugin_distribution() -> None:
    contract = REPO_ROOT / "research" / "mic_admission_decision_contract.py"
    packaging_setup = REPO_ROOT / "packaging" / "praxis_virtualcell_gram_negative_amr" / "setup.py"
    production_roots = (
        REPO_ROOT / "praxis_virtualcell",
        REPO_ROOT / "praxis_vc_api",
        REPO_ROOT / "praxis_virtualcell_gram_negative_amr",
    )

    contract_tree = ast.parse(contract.read_text(encoding="utf-8"))
    for node in ast.walk(contract_tree):
        if isinstance(node, ast.Import):
            assert all(
                name.name.split(".", 1)[0]
                not in {"praxis_virtualcell", "praxis_vc_api", "requests", "urllib"}
                for name in node.names
            )
        if isinstance(node, ast.ImportFrom) and node.module:
            module_root = node.module.split(".", 1)[0]
            assert node.module in {
                "research.mic_admission_contract",
                "__future__",
            } or module_root in {
                "hashlib",
                "json",
                "re",
                "datetime",
                "typing",
            }

    for root in production_roots:
        for path in root.rglob("*.py"):
            if "tests" not in path.parts and not path.name.startswith("._"):
                source = path.read_text(encoding="utf-8")
                assert "mic_admission_decision" not in source
                production_tree = ast.parse(source, filename=str(path))
                for node in ast.walk(production_tree):
                    if isinstance(node, ast.Import):
                        assert all(name.name.split(".", 1)[0] != "research" for name in node.names)
                    if isinstance(node, ast.ImportFrom) and node.module:
                        assert node.module.split(".", 1)[0] != "research"
    assert "research/" not in packaging_setup.read_text(encoding="utf-8")
