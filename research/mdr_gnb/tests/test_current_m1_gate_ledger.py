"""Contract checks for the current, identity-only M1 gate ledger."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "research/mdr_gnb/mic_discovery/2026-08-14-m1b1-current-gate-ledger-ecoli-meropenem"
    / "derived/build_current_m1_gate_ledger_v1.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("current_m1_gate_ledger", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def test_current_gate_rows_keep_only_identity_allocation_and_unresolved_gate_fields() -> None:
    module = _module()
    source_rows = [
        {
            "schema_version": "gnb.mic-pre-governance-identity-allocation.v1",
            "candidate_id": "candidate-a",
            "biosample_accession": "SAMN00000001",
            "assembly_accession": "GCA_000000001.1",
            "profile_toolchain_status": "local_dirty_legacy_source_observation",
            "allocation_protocol_fingerprint": "a" * 64,
            "allocation_protocol_id": "protocol-a",
            "allocation_protocol_version": "v1",
            "leakage_unit": "ST-blocked",
            "leakage_group_fingerprint": "b" * 64,
            "assignment": "train",
            "allocation_status": "identity_only_pre_governance_not_admitted",
            "candidate_status": "record_level_quantitative_mic_candidate_unverified",
            "data_admission_status": "not_admitted",
            "scientific_status": "unverified",
            "pack_authorized": False,
            "training_authorized": False,
            "evaluation_authorized": False,
            "prediction_authorized": False,
            "profile_payload_sha256": "c" * 64,
            "lineage_st": "ST131",
        }
    ]

    ledger = module.build_current_gate_rows(source_rows)

    assert ledger == [
        {
            "candidate_id": "candidate-a",
            "biosample_accession": "SAMN00000001",
            "assembly_accession": "GCA_000000001.1",
            "identity_qualification_status": "007_exact_identity_candidate_not_admitted",
            "allocation_protocol_fingerprint": "a" * 64,
            "leakage_unit": "ST-blocked",
            "leakage_group_fingerprint": "b" * 64,
            "assignment": "train",
            "allocation_status": "identity_only_pre_governance_not_admitted",
            "unresolved_gate_codes": [
                "assay_protocol_unresolved",
                "canonical_drug_structure_receipt_unbound",
                "governance_not_granted",
                "negative_call_semantics_missing",
                "observed_omics_missing",
                "record_level_rights_unresolved",
            ],
            "next_gate": "pubmed_citation_metadata_authorization_required",
            "candidate_status": "record_level_quantitative_mic_candidate_unverified",
            "data_admission_status": "not_admitted",
            "scientific_status": "unverified",
            "pack_authorized": False,
            "training_authorized": False,
            "evaluation_authorized": False,
            "prediction_authorized": False,
        }
    ]
    forbidden = {"mic", "measurement", "sir", "assay", "publication", "profile", "lineage"}
    assert all(
        not any(token in key.lower() for token in forbidden) for row in ledger for key in row
    )
