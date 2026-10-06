"""Offline structural screen for future exact-isolate MIC data candidates."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

import research.mdr_gnb.mic_pre_governance_identity_binding as identity_binding
from research.mdr_gnb.mic_admission_contract import (
    MICAdmissionRecordError,
    mic_admission_preflight,
    validate_mic_admission_record,
)
from research.mdr_gnb.mic_meropenem_drug_identity import (
    EXPECTED_STANDARDIZED_SMILES,
    meropenem_admission_drug_receipt,
)
from research.mdr_gnb.mic_pre_governance_identity_binding import (
    MICPreGovernanceIdentityBindingError,
    validate_mic_record_identity_allocation_binding,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_drug_binding_fingerprint(
    *,
    canonical_drug_id: str,
    standardized_smiles: str,
    standardizer_id: str,
    standardizer_version: str,
    standardizer_fingerprint: str,
) -> str:
    return _sha(
        json.dumps(
            {
                "schema_version": "gnb.mic-canonical-drug-binding.v1",
                "canonical_drug_id": canonical_drug_id,
                "standardized_smiles": standardized_smiles,
                "standardizer_id": standardizer_id,
                "standardizer_version": standardizer_version,
                "standardizer_fingerprint": standardizer_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )


def _refresh_canonical_drug_binding(record: dict) -> None:
    drug = record["drug"]
    standardizer = drug["standardizer"]
    drug["canonical_structure_fingerprint"] = _canonical_drug_binding_fingerprint(
        canonical_drug_id=drug["canonical_drug_id"],
        standardized_smiles=drug["standardized_smiles"],
        standardizer_id=standardizer["id"],
        standardizer_version=standardizer["version"],
        standardizer_fingerprint=standardizer["fingerprint"],
    )


def _record() -> dict:
    standardized_smiles = "CCO"
    profile_payload = _sha("profile-payload")
    canonical_drug_id = "synthetic-drug"
    standardizer_id = "synthetic-standardizer"
    standardizer_version = "1.0.0"
    standardizer_fingerprint = _sha("standardizer")
    return {
        "schema_version": "gnb.mic-admission-record.v1",
        "record_id": "synthetic-mic-record-1",
        "target": {
            "schema_version": "gnb.mic-admission-target.v1",
            "task": "predict_mic",
            "intended_use": "research_only",
            "clinical_interpretation": "prohibited",
        },
        "source": {
            "schema_version": "gnb.mic-admission-source.v1",
            "source_kind": "experimental_exact_isolate_mic",
            "provider": "synthetic-test-provider",
            "release_id": "synthetic-r1",
            "source_record_id": "source-row-1",
            "content_sha256": _sha("source-row-1"),
        },
        "taxon": {
            "schema_version": "gnb.mic-admission-taxon.v1",
            "taxonomy_id": "NCBITaxon:562",
            "evidence_fingerprint": _sha("taxon-evidence"),
        },
        "isolate_profile": {
            "schema_version": "gnb.mic-admission-isolate-profile.v1",
            "isolate_id": "synthetic-isolate-1",
            "profile_id": "synthetic-profile-1",
            "biosample_id": "SAMN00000001",
            "assembly_accession": "GCF_000000001.1",
            "assembly_fingerprint": _sha("assembly"),
            "profile_payload_fingerprint": profile_payload,
            "isolate_profile_linkage_fingerprint": _sha("isolate-profile-linkage"),
        },
        "drug": {
            "schema_version": "gnb.mic-admission-drug.v1",
            "drug_cardinality": 1,
            "canonical_drug_id": canonical_drug_id,
            "standardized_smiles": standardized_smiles,
            "standardized_smiles_fingerprint": _sha(standardized_smiles),
            "canonical_structure_fingerprint": _canonical_drug_binding_fingerprint(
                canonical_drug_id=canonical_drug_id,
                standardized_smiles=standardized_smiles,
                standardizer_id=standardizer_id,
                standardizer_version=standardizer_version,
                standardizer_fingerprint=standardizer_fingerprint,
            ),
            "standardizer": {
                "schema_version": "gnb.mic-admission-standardizer.v1",
                "id": standardizer_id,
                "version": standardizer_version,
                "fingerprint": standardizer_fingerprint,
            },
        },
        "quantitative_mic": {
            "schema_version": "gnb.mic-admission-measurement.v1",
            "quantity": "minimum_inhibitory_concentration",
            "raw_value_decimal": "1.0",
            "raw_unit": "ug/mL",
            "reported_scale": "linear",
            "relation": "=",
            "censoring": "none",
            "censor_bound_decimal": None,
            "normalized_value_decimal": "0.0",
            "normalized_unit": "ug/mL",
            "normalized_scale": "log2",
            "conversion_fingerprint": _sha("mic-conversion"),
            "raw_record_fingerprint": _sha("source-row-1"),
        },
        "assay": {
            "schema_version": "gnb.mic-admission-assay.v1",
            "assay_id": "synthetic-assay",
            "method_kind": "broth_microdilution",
            "method_id": "synthetic-method",
            "standard_id": "synthetic-standard",
            "protocol_fingerprint": _sha("protocol"),
            "conditions": {
                "schema_version": "gnb.mic-admission-assay-conditions.v1",
                "medium_id": "MHB",
                "inoculum_value_decimal": "500000",
                "inoculum_unit": "CFU/mL",
                "incubation_temperature_c": 35.0,
                "incubation_duration_h": 18.0,
                "atmosphere": "aerobic",
                "dilution_series_id": "twofold",
                "dilution_factor": 2.0,
                "dilution_lower_bound": 0.125,
                "dilution_upper_bound": 64.0,
                "dilution_unit": "ug/mL",
                "endpoint": "visible_growth_inhibition",
            },
        },
        "observed_omics": {
            "schema_version": "gnb.mic-admission-observed-omics.v1",
            "observation_mode": "observed_isolate_omics",
            "source_asset": {
                "schema_version": "gnb.mic-admission-source-asset.v1",
                "sha256": _sha("omics-asset"),
                "size_bytes": 1,
                "media_type": "text/csv",
            },
            "payload_fingerprint": profile_payload,
            "feature_vocabulary_fingerprint": _sha("feature-vocabulary"),
            "feature_contract_fingerprint": _sha("feature-contract"),
            "feature_mapping_fingerprint": _sha("feature-mapping"),
            "negative_call_semantics": {
                "schema_version": "gnb.mic-admission-negative-call.v1",
                "status": "documented",
                "fingerprint": _sha("negative-call"),
            },
        },
        "perturbation_scope": {
            "schema_version": "gnb.mic-admission-perturbation-scope.v1",
            "in_scope": False,
            "mode": "not_in_scope",
            "observed_perturbation_fingerprint": None,
        },
        "profile_toolchain": {
            "schema_version": "gnb.mic-admission-profile-toolchain.v1",
            "tool_id": "synthetic-caller",
            "tool_version": "1.0.0",
            "binary_fingerprint": _sha("tool-binary"),
            "database_id": "synthetic-db",
            "database_fingerprint": _sha("tool-database"),
            "parameters_fingerprint": _sha("tool-parameters"),
            "result_fingerprint": profile_payload,
        },
        "split": {
            "schema_version": "gnb.mic-admission-split.v1",
            "protocol_id": "synthetic-split",
            "protocol_version": "1.0.0",
            "protocol_fingerprint": _sha("split-protocol"),
            "pre_registered_at": "2026-08-11T00:00:00Z",
            "assignment": "held_out",
            "leakage_unit": "isolate_assembly_lineage",
            "leakage_group_fingerprint": _sha("leakage-group"),
        },
        "provenance": {
            "schema_version": "gnb.mic-admission-provenance.v1",
            "source_snapshot_fingerprint": _sha("source-snapshot"),
            "license": {
                "schema_version": "gnb.mic-admission-license.v1",
                "expression": "CC0-1.0",
                "terms_fingerprint": _sha("license-terms"),
                "evidence_fingerprint": _sha("license-evidence"),
            },
            "access_basis": "research-permitted",
            "transformation": {
                "schema_version": "gnb.mic-admission-transformation.v1",
                "kind": "record_preserving_normalization",
                "code_fingerprint": _sha("transform-code"),
                "input_fingerprints": [_sha("source-row-1")],
                "output_fingerprint": _sha("transformed-row"),
            },
        },
        "review_state": {
            "schema_version": "gnb.mic-admission-review-state.v1",
            "license": "unreviewed",
            "provenance": "unreviewed",
            "authority": "unapproved",
        },
    }


def test_complete_synthetic_record_is_only_structurally_complete_and_unreviewed():
    record = _record()

    summary = validate_mic_admission_record(record)
    preflight_summary, reasons = mic_admission_preflight(record)

    assert summary == preflight_summary
    assert reasons == ("gnb_mic_admission_not_admitted_pending_governance",)
    assert summary["status"] == "structurally_complete_unreviewed"
    assert summary["admission_status"] == "not_admitted"
    assert (
        summary["record_fingerprint"]
        == hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
    )
    assert {
        "pack",
        "model",
        "artifact",
        "evidence",
        "policy",
        "execution_plan",
        "prediction",
    }.isdisjoint(summary)


def test_exact_meropenem_receipt_is_compatible_with_the_generic_admission_contract() -> None:
    record = _record()
    record["drug"] = meropenem_admission_drug_receipt(EXPECTED_STANDARDIZED_SMILES)

    summary = validate_mic_admission_record(record)

    assert summary["status"] == "structurally_complete_unreviewed"
    assert summary["admission_status"] == "not_admitted"


def test_structural_screen_rejects_non_utf8_text_with_a_stable_reason() -> None:
    record = _record()
    record["source"]["provider"] = "\ud800"

    with pytest.raises(MICAdmissionRecordError, match="provenance_incomplete"):
        validate_mic_admission_record(record)

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == ("gnb_mic_admission_provenance_incomplete",)


def test_structural_screen_normalizes_canonical_fingerprint_failures() -> None:
    record = _record()
    record["observed_omics"]["source_asset"]["size_bytes"] = 10**10000

    with pytest.raises(MICAdmissionRecordError) as exc:
        validate_mic_admission_record(record)
    assert exc.value.code == "schema_invalid"

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == ("gnb_mic_admission_schema_invalid",)


def test_structural_screen_normalizes_untrusted_mapping_access_failures() -> None:
    class TrapDict(dict):
        def __getitem__(self, key):
            if key == "schema_version":
                raise RuntimeError("mapping access trap")
            return super().__getitem__(key)

    record = TrapDict(_record())

    with pytest.raises(MICAdmissionRecordError) as exc:
        validate_mic_admission_record(record)
    assert exc.value.code == "schema_invalid"

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == ("gnb_mic_admission_schema_invalid",)


def test_structural_screen_normalizes_injected_public_domain_errors() -> None:
    class TrapDict(dict):
        def __getitem__(self, key):
            if key == "schema_version":
                raise MICAdmissionRecordError("caller_injected_record_code")
            return super().__getitem__(key)

    record = TrapDict(_record())

    with pytest.raises(MICAdmissionRecordError) as exc:
        validate_mic_admission_record(record)
    assert exc.value.code == "schema_invalid"

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == ("gnb_mic_admission_schema_invalid",)


def test_structural_screen_accepts_complete_rfc3339_offset() -> None:
    record = _record()
    record["split"]["pre_registered_at"] = "2026-08-11T08:00:00+08:00"

    assert validate_mic_admission_record(record)["status"] == "structurally_complete_unreviewed"


def test_structural_screen_freezes_record_before_validation_and_fingerprint() -> None:
    class MutatingRecord(dict):
        def __getitem__(self, key):
            value = super().__getitem__(key)
            if key == "review_state":
                self["record_id"] = "synthetic-mutated-record"
            return value

    record = _record()
    expected_fingerprint = _sha(
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )

    summary = validate_mic_admission_record(MutatingRecord(record))

    assert summary["record_id"] == "synthetic-mic-record-1"
    assert summary["record_fingerprint"] == expected_fingerprint


@pytest.mark.parametrize(
    "mutate",
    (
        pytest.param(
            lambda drug: drug.update({"canonical_drug_id": "synthetic-drug-2"}),
            id="canonical-drug-id",
        ),
        pytest.param(
            lambda drug: drug.update(
                {
                    "standardized_smiles": "CCC",
                    "standardized_smiles_fingerprint": _sha("CCC"),
                }
            ),
            id="standardized-smiles",
        ),
        pytest.param(
            lambda drug: drug["standardizer"].update({"id": "synthetic-standardizer-2"}),
            id="standardizer-id",
        ),
        pytest.param(
            lambda drug: drug["standardizer"].update({"version": "2.0.0"}),
            id="standardizer-version",
        ),
        pytest.param(
            lambda drug: drug["standardizer"].update({"fingerprint": _sha("standardizer-2")}),
            id="standardizer-fingerprint",
        ),
    ),
)
def test_structural_screen_binds_canonical_drug_fingerprint_to_all_declared_inputs(mutate) -> None:
    record = _record()
    mutate(record["drug"])

    with pytest.raises(MICAdmissionRecordError, match="canonical_drug_binding_mismatch"):
        validate_mic_admission_record(record)

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == ("gnb_mic_admission_canonical_drug_binding_mismatch",)

    _refresh_canonical_drug_binding(record)
    repaired = validate_mic_admission_record(record)
    assert repaired["status"] == "structurally_complete_unreviewed"
    assert repaired["admission_status"] == "not_admitted"


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
def test_structural_screen_rejects_non_rfc3339_split_timestamp(timestamp: str) -> None:
    record = _record()
    record["split"]["pre_registered_at"] = timestamp

    with pytest.raises(MICAdmissionRecordError, match="split_not_preregistered"):
        validate_mic_admission_record(record)

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == ("gnb_mic_admission_split_not_preregistered",)


@pytest.mark.parametrize(
    ("mutate", "code"),
    (
        pytest.param(
            lambda record: record.update({"pack_id": "forbidden"}),
            "schema_invalid",
            id="pack-field",
        ),
        pytest.param(
            lambda record: record["target"].update({"task": "predict_r_non_r"}),
            "target_not_predict_mic",
            id="wrong-task",
        ),
        pytest.param(
            lambda record: record["taxon"].update({"taxonomy_id": "NCBITaxon:2"}),
            "taxon_not_exact_ecoli",
            id="nonexact-taxon",
        ),
        pytest.param(
            lambda record: record["isolate_profile"].update({"biosample_id": ""}),
            "isolate_identity_missing",
            id="missing-biosample",
        ),
        pytest.param(
            lambda record: record["drug"].update({"drug_cardinality": 2}),
            "single_drug_required",
            id="multi-drug",
        ),
        pytest.param(
            lambda record: record["quantitative_mic"].update({"raw_value_decimal": "0"}),
            "mic_value_invalid",
            id="zero-mic",
        ),
        pytest.param(
            lambda record: record["quantitative_mic"].update({"raw_value_decimal": "NaN"}),
            "mic_value_invalid",
            id="raw-mic-nan",
        ),
        pytest.param(
            lambda record: record["quantitative_mic"].update(
                {"normalized_value_decimal": "Infinity"}
            ),
            "mic_value_invalid",
            id="normalized-mic-infinity",
        ),
        pytest.param(
            lambda record: record["quantitative_mic"].update(
                {"relation": "<", "censoring": "none"}
            ),
            "mic_relation_censoring_inconsistent",
            id="censoring-mismatch",
        ),
        pytest.param(
            lambda record: record["assay"].update({"method_kind": "disk_diffusion"}),
            "assay_contract_incomplete",
            id="wrong-assay-method",
        ),
        pytest.param(
            lambda record: record["assay"]["conditions"].update(
                {"incubation_temperature_c": float("nan")}
            ),
            "assay_contract_incomplete",
            id="assay-temperature-nan",
        ),
        pytest.param(
            lambda record: record["assay"]["conditions"].update(
                {"incubation_duration_h": float("inf")}
            ),
            "assay_contract_incomplete",
            id="assay-duration-infinity",
        ),
        pytest.param(
            lambda record: record["assay"]["conditions"].update(
                {"incubation_temperature_c": 10**10000}
            ),
            "assay_contract_incomplete",
            id="assay-temperature-overflow",
        ),
        pytest.param(
            lambda record: record["assay"]["conditions"].update(
                {"incubation_duration_h": 10**10000}
            ),
            "assay_contract_incomplete",
            id="assay-duration-overflow",
        ),
        pytest.param(
            lambda record: record["observed_omics"]["negative_call_semantics"].update(
                {"status": "unverified"}
            ),
            "negative_call_semantics_unverified",
            id="negative-call-unverified",
        ),
        pytest.param(
            lambda record: record["observed_omics"].update(
                {"payload_fingerprint": _sha("another-profile-payload")}
            ),
            "profile_payload_identity_mismatch",
            id="profile-payload-identity-mismatch",
        ),
        pytest.param(
            lambda record: record["profile_toolchain"].update(
                {"result_fingerprint": _sha("another-profile-payload")}
            ),
            "profile_payload_identity_mismatch",
            id="tool-result-identity-mismatch",
        ),
        pytest.param(
            lambda record: record["perturbation_scope"].update(
                {
                    "in_scope": True,
                    "mode": "observed_gene_state",
                    "observed_perturbation_fingerprint": None,
                }
            ),
            "perturbation_in_silico_or_unobserved",
            id="unobserved-perturbation",
        ),
        pytest.param(
            lambda record: record["profile_toolchain"].update({"database_fingerprint": ""}),
            "tool_database_identity_missing",
            id="missing-tool-database",
        ),
        pytest.param(
            lambda record: record["provenance"]["transformation"].update(
                {"input_fingerprints": [_sha("source-row-1"), _sha("second-source")]}
            ),
            "cross_source_join_unproven",
            id="cross-source-join",
        ),
        pytest.param(
            lambda record: record["quantitative_mic"].update(
                {"raw_record_fingerprint": _sha("different-source-row")}
            ),
            "cross_source_join_unproven",
            id="raw-record-source-mismatch",
        ),
        pytest.param(
            lambda record: record["provenance"]["transformation"].update(
                {"input_fingerprints": [_sha("different-source-row")]}
            ),
            "cross_source_join_unproven",
            id="single-wrong-transform-source",
        ),
        pytest.param(
            lambda record: record["split"].update({"pre_registered_at": "not-a-timestamp"}),
            "split_not_preregistered",
            id="unregistered-split",
        ),
        pytest.param(
            lambda record: record["review_state"].update({"authority": "approved"}),
            "review_state_invalid",
            id="self-approved",
        ),
        pytest.param(
            lambda record: record["source"].update({"source_kind": "aggregate_activity"}),
            "aggregate_or_sir_reference_forbidden",
            id="aggregate-reference",
        ),
        pytest.param(
            lambda record: record["source"].update({"source_kind": "sir_table"}),
            "aggregate_or_sir_reference_forbidden",
            id="sir-reference",
        ),
        pytest.param(
            lambda record: record["source"].update({"source_kind": "aggregate_peptide_activity"}),
            "aggregate_or_sir_reference_forbidden",
            id="aggregate-peptide-reference",
        ),
        pytest.param(
            lambda record: record["source"].update({"source_kind": "experimental_gem"}),
            "aggregate_or_sir_reference_forbidden",
            id="experimental-gem-reference",
        ),
        pytest.param(
            lambda record: record["source"].update({"source_kind": []}),
            "provenance_incomplete",
            id="nonstring-source-kind",
        ),
        pytest.param(
            lambda record: record["split"].update({"assignment": []}),
            "split_assignment_or_leakage_unit_invalid",
            id="nonstring-split-assignment",
        ),
    ),
)
def test_structural_screen_rejects_missing_or_non_authoritative_bindings(mutate, code):
    record = _record()
    mutate(record)

    with pytest.raises(MICAdmissionRecordError, match=code):
        validate_mic_admission_record(record)

    summary, reasons = mic_admission_preflight(record)
    assert summary is None
    assert reasons == (f"gnb_mic_admission_{code}",)


def test_research_contracts_stay_outside_plugin_runtime_and_distribution() -> None:
    research_contracts = (
        REPO_ROOT / "research" / "mic_admission_contract.py",
        REPO_ROOT / "research" / "mic_pre_governance_identity_binding.py",
    )
    plugin_root = REPO_ROOT / "praxis_virtualcell_gram_negative_amr"
    packaging_setup = REPO_ROOT / "packaging" / "praxis_virtualcell_gram_negative_amr" / "setup.py"

    for research_contract in research_contracts:
        contract_tree = ast.parse(research_contract.read_text(encoding="utf-8"))
        for node in ast.walk(contract_tree):
            if isinstance(node, ast.Import):
                assert all(
                    name.name.split(".", 1)[0] not in {"praxis_virtualcell", "requests", "urllib"}
                    for name in node.names
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] not in {
                    "praxis_virtualcell",
                    "requests",
                    "urllib",
                }

    for path in plugin_root.rglob("*.py"):
        if "tests" not in path.parts and not path.name.startswith("._"):
            assert "research.mic_" not in path.read_text(encoding="utf-8")
    assert "research/" not in packaging_setup.read_text(encoding="utf-8")


def _identity_only_allocation(record: dict) -> dict:
    return {
        "schema_version": "gnb.mic-pre-governance-identity-allocation.v1",
        "candidate_id": "synthetic-candidate-1",
        "biosample_accession": record["isolate_profile"]["biosample_id"],
        "assembly_accession": record["isolate_profile"]["assembly_accession"],
        "profile_payload_sha256": record["isolate_profile"]["profile_payload_fingerprint"],
        "profile_toolchain_status": "synthetic-observation",
        "lineage_st": "synthetic-lineage",
        "allocation_protocol_id": record["split"]["protocol_id"],
        "allocation_protocol_version": record["split"]["protocol_version"],
        "allocation_protocol_fingerprint": record["split"]["protocol_fingerprint"],
        "leakage_unit": record["split"]["leakage_unit"],
        "leakage_group_fingerprint": record["split"]["leakage_group_fingerprint"],
        "assignment": record["split"]["assignment"],
        "allocation_status": "identity_only_pre_governance_not_admitted",
        "candidate_status": "record_level_quantitative_mic_candidate_unverified",
        "data_admission_status": "not_admitted",
        "scientific_status": "unverified",
        "pack_authorized": False,
        "training_authorized": False,
        "evaluation_authorized": False,
        "prediction_authorized": False,
    }


def _candidate_record_binding(record: dict, allocation: dict) -> dict:
    return {
        "schema_version": "gnb.mic-pre-governance-candidate-record-binding.v1",
        "candidate_id": allocation["candidate_id"],
        "source_record_id": record["source"]["source_record_id"],
        "biosample_id": record["isolate_profile"]["biosample_id"],
        "assembly_accession": record["isolate_profile"]["assembly_accession"],
        "profile_payload_fingerprint": record["isolate_profile"]["profile_payload_fingerprint"],
    }


def test_structural_record_must_match_the_frozen_identity_only_allocation() -> None:
    record = _record()
    allocation = _identity_only_allocation(record)
    candidate_binding = _candidate_record_binding(record, allocation)

    summary = validate_mic_record_identity_allocation_binding(record, allocation, candidate_binding)

    assert summary["status"] == "not_admitted"
    assert summary["admission_status"] == "not_admitted"
    assert summary["record_id"] == record["record_id"]
    assert set(summary) == {
        "schema_version",
        "record_id",
        "record_fingerprint",
        "candidate_record_binding_fingerprint",
        "allocation_row_fingerprint",
        "status",
        "admission_status",
    }


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("biosample_accession", "SAMN00000002"),
        ("assembly_accession", "GCF_000000002.1"),
        ("profile_payload_sha256", _sha("different-profile")),
        ("allocation_protocol_id", "different-protocol"),
        ("allocation_protocol_version", "v2"),
        ("allocation_protocol_fingerprint", _sha("different-protocol")),
        ("leakage_unit", "different-unit"),
        ("leakage_group_fingerprint", _sha("different-group")),
        ("assignment", "dev"),
    ),
)
def test_identity_allocation_binding_rejects_any_identity_or_split_drift(
    field: str, replacement: str
) -> None:
    record = _record()
    allocation = _identity_only_allocation(record)
    candidate_binding = _candidate_record_binding(record, allocation)
    allocation[field] = replacement

    with pytest.raises(MICPreGovernanceIdentityBindingError) as exc:
        validate_mic_record_identity_allocation_binding(record, allocation, candidate_binding)
    assert exc.value.code == "identity_allocation_binding_mismatch"


def test_identity_allocation_binding_never_treats_a_positive_flag_as_pre_governance() -> None:
    record = _record()
    allocation = _identity_only_allocation(record)
    candidate_binding = _candidate_record_binding(record, allocation)
    allocation["training_authorized"] = True

    with pytest.raises(MICPreGovernanceIdentityBindingError) as exc:
        validate_mic_record_identity_allocation_binding(record, allocation, candidate_binding)
    assert exc.value.code == "allocation_not_pre_governance_not_admitted"


def test_identity_allocation_binding_normalizes_untrusted_mapping_access_failures() -> None:
    class TrapDict(dict):
        def items(self):
            raise RuntimeError("mapping access trap")

    record = _record()
    allocation = _identity_only_allocation(record)
    candidate_binding = _candidate_record_binding(record, allocation)

    with pytest.raises(MICPreGovernanceIdentityBindingError) as exc:
        validate_mic_record_identity_allocation_binding(
            TrapDict(record), allocation, candidate_binding
        )
    assert exc.value.code == "schema_invalid"


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("candidate_id", "synthetic-candidate-2"),
        ("source_record_id", "source-row-2"),
        ("biosample_id", "SAMN00000002"),
        ("assembly_accession", "GCF_000000002.1"),
        ("profile_payload_fingerprint", _sha("different-profile")),
    ),
)
def test_identity_allocation_binding_requires_an_explicit_candidate_record_binding(
    field: str, replacement: str
) -> None:
    record = _record()
    allocation = _identity_only_allocation(record)
    candidate_binding = _candidate_record_binding(record, allocation)
    candidate_binding[field] = replacement

    with pytest.raises(MICPreGovernanceIdentityBindingError) as exc:
        validate_mic_record_identity_allocation_binding(record, allocation, candidate_binding)
    assert exc.value.code == "candidate_record_binding_mismatch"


def test_identity_allocation_binding_rejects_a_future_positive_record_summary(monkeypatch) -> None:
    record = _record()
    allocation = _identity_only_allocation(record)
    candidate_binding = _candidate_record_binding(record, allocation)
    monkeypatch.setattr(
        identity_binding,
        "validate_mic_admission_record",
        lambda _: {
            "record_id": record["record_id"],
            "record_fingerprint": _sha("record"),
            "status": "admitted",
            "admission_status": "admitted",
        },
    )

    with pytest.raises(MICPreGovernanceIdentityBindingError) as exc:
        validate_mic_record_identity_allocation_binding(record, allocation, candidate_binding)
    assert exc.value.code == "record_not_structurally_complete"
