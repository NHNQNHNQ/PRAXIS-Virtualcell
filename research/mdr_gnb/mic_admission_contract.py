"""Offline structural screen for future exact-isolate quantitative MIC data.

This is research tooling, not a Pack, model, adapter, or runtime contract.
Its only positive outcome is ``structurally_complete_unreviewed``.  A later,
independent governance decision is required before any M2 Pack binding.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = "gnb.mic-admission-record.v1"
EXPECTED_TAXON = "NCBITaxon:562"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RFC3339_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
_CANONICAL_DRUG_BINDING_SCHEMA_VERSION = "gnb.mic-canonical-drug-binding.v1"
_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "record_id",
        "target",
        "source",
        "taxon",
        "isolate_profile",
        "drug",
        "quantitative_mic",
        "assay",
        "observed_omics",
        "perturbation_scope",
        "profile_toolchain",
        "split",
        "provenance",
        "review_state",
    }
)
_FORBIDDEN_SOURCE_KINDS = frozenset(
    {"aggregate_activity", "aggregate_peptide_activity", "experimental_gem", "sir_table"}
)


class MICAdmissionRecordError(ValueError):
    """A fail-closed structural data-admission error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"invalid MIC admission record: {code}")


class _InternalMICAdmissionRecordError(MICAdmissionRecordError):
    """Marks errors created by this module's validator."""


def _fail(code: str) -> None:
    raise _InternalMICAdmissionRecordError(code)


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


def _identifier(value: Any, code: str) -> str:
    value = _text(value, code)
    if value.casefold() == "null":
        _fail(code)
    return value


def _sha256(value: Any, code: str) -> str:
    value = _text(value, code)
    if _SHA256.fullmatch(value) is None:
        _fail(code)
    return value


def _positive_number(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(code)
    try:
        value = float(value)
    except (OverflowError, ValueError):
        _fail(code)
    if not math.isfinite(value) or value <= 0:
        _fail(code)
    return value


def _positive_decimal(value: Any, code: str) -> Decimal:
    value = _text(value, code)
    try:
        number = Decimal(value)
    except InvalidOperation:
        _fail(code)
    if not number.is_finite() or number <= 0:
        _fail(code)
    return number


def _finite_decimal(value: Any, code: str) -> Decimal:
    value = _text(value, code)
    try:
        number = Decimal(value)
    except InvalidOperation:
        _fail(code)
    if not number.is_finite():
        _fail(code)
    return number


def _parse_rfc3339_timestamp(value: str) -> datetime:
    if _RFC3339_TIMESTAMP.fullmatch(value) is None or value.endswith("-00:00"):
        raise ValueError
    return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    try:
        return hashlib.sha256(
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
    except Exception:  # noqa: BLE001 - canonical identity must fail closed
        _fail("schema_invalid")


def _frozen_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _frozen_value(value[key]) for key, _ in value.items()}
    if isinstance(value, list):
        return [_frozen_value(item) for item in value]
    return value


def _plain_mapping(value: Any) -> dict[str, Any]:
    """Freeze an untrusted record without changing invalid-value error codes."""

    if not isinstance(value, dict):
        _fail("schema_invalid")
    try:
        frozen = _frozen_value(value)
    except Exception:  # noqa: BLE001 - public research boundary must fail closed
        _fail("schema_invalid")
    if not isinstance(frozen, dict):
        _fail("schema_invalid")
    return frozen


def _canonical_drug_binding_fingerprint(
    *,
    canonical_drug_id: str,
    standardized_smiles: str,
    standardizer_id: str,
    standardizer_version: str,
    standardizer_fingerprint: str,
) -> str:
    """Bind the declared drug identity, not a claimed chemical canonicalization.

    The exact canonical JSON payload is schema version, canonical drug ID,
    standardized SMILES, and standardizer ID/version/fingerprint.
    """

    return _canonical_fingerprint(
        {
            "schema_version": _CANONICAL_DRUG_BINDING_SCHEMA_VERSION,
            "canonical_drug_id": canonical_drug_id,
            "standardized_smiles": standardized_smiles,
            "standardizer_id": standardizer_id,
            "standardizer_version": standardizer_version,
            "standardizer_fingerprint": standardizer_fingerprint,
        }
    )


def _target(value: Any) -> None:
    target = _exact_fields(
        value,
        frozenset({"schema_version", "task", "intended_use", "clinical_interpretation"}),
        "schema_invalid",
    )
    if target["schema_version"] != "gnb.mic-admission-target.v1":
        _fail("schema_invalid")
    if target["task"] != "predict_mic":
        _fail("target_not_predict_mic")
    if target["intended_use"] != "research_only":
        _fail("target_not_research_only")
    if target["clinical_interpretation"] != "prohibited":
        _fail("clinical_interpretation_not_prohibited")


def _source(value: Any) -> str:
    source = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "source_kind",
                "provider",
                "release_id",
                "source_record_id",
                "content_sha256",
            }
        ),
        "provenance_incomplete",
    )
    if source["schema_version"] != "gnb.mic-admission-source.v1":
        _fail("provenance_incomplete")
    source_kind = _text(source["source_kind"], "provenance_incomplete")
    if source_kind in _FORBIDDEN_SOURCE_KINDS:
        _fail("aggregate_or_sir_reference_forbidden")
    if source_kind != "experimental_exact_isolate_mic":
        _fail("provenance_incomplete")
    for field in ("provider", "release_id", "source_record_id"):
        _identifier(source[field], "provenance_incomplete")
    return _sha256(source["content_sha256"], "content_or_transformation_identity_missing")


def _taxon(value: Any) -> None:
    taxon = _exact_fields(
        value,
        frozenset({"schema_version", "taxonomy_id", "evidence_fingerprint"}),
        "taxon_not_exact_ecoli",
    )
    if (
        taxon["schema_version"] != "gnb.mic-admission-taxon.v1"
        or taxon["taxonomy_id"] != EXPECTED_TAXON
    ):
        _fail("taxon_not_exact_ecoli")
    _sha256(taxon["evidence_fingerprint"], "taxon_not_exact_ecoli")


def _isolate_profile(value: Any) -> tuple[str, str]:
    isolate = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "isolate_id",
                "profile_id",
                "biosample_id",
                "assembly_accession",
                "assembly_fingerprint",
                "profile_payload_fingerprint",
                "isolate_profile_linkage_fingerprint",
            }
        ),
        "isolate_profile_or_assembly_unbound",
    )
    if isolate["schema_version"] != "gnb.mic-admission-isolate-profile.v1":
        _fail("isolate_profile_or_assembly_unbound")
    isolate_id = _identifier(isolate["isolate_id"], "isolate_identity_missing")
    profile_id = _identifier(isolate["profile_id"], "isolate_profile_or_assembly_unbound")
    _identifier(isolate["biosample_id"], "isolate_identity_missing")
    accession = _identifier(isolate["assembly_accession"], "isolate_profile_or_assembly_unbound")
    if "." not in accession or not accession.rsplit(".", 1)[1].isdigit():
        _fail("isolate_profile_or_assembly_unbound")
    for field in (
        "assembly_fingerprint",
        "profile_payload_fingerprint",
        "isolate_profile_linkage_fingerprint",
    ):
        _sha256(isolate[field], "isolate_profile_or_assembly_unbound")
    return isolate_id, profile_id


def _drug(value: Any) -> str:
    drug = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "drug_cardinality",
                "canonical_drug_id",
                "standardized_smiles",
                "standardized_smiles_fingerprint",
                "canonical_structure_fingerprint",
                "standardizer",
            }
        ),
        "drug_standardization_missing",
    )
    if drug["schema_version"] != "gnb.mic-admission-drug.v1":
        _fail("drug_standardization_missing")
    if type(drug["drug_cardinality"]) is not int or drug["drug_cardinality"] != 1:
        _fail("single_drug_required")
    smiles = _text(drug["standardized_smiles"], "drug_standardization_missing")
    if any(character.isspace() for character in smiles):
        _fail("drug_standardization_missing")
    if (
        _sha256(drug["standardized_smiles_fingerprint"], "drug_standardization_missing")
        != hashlib.sha256(smiles.encode("utf-8")).hexdigest()
    ):
        _fail("fingerprint_mismatch")
    canonical_drug_id = _identifier(drug["canonical_drug_id"], "drug_standardization_missing")
    standardizer = _exact_fields(
        drug["standardizer"],
        frozenset({"schema_version", "id", "version", "fingerprint"}),
        "drug_standardization_missing",
    )
    if standardizer["schema_version"] != "gnb.mic-admission-standardizer.v1":
        _fail("drug_standardization_missing")
    standardizer_id = _text(standardizer["id"], "drug_standardization_missing")
    standardizer_version = _text(standardizer["version"], "drug_standardization_missing")
    standardizer_fingerprint = _sha256(standardizer["fingerprint"], "drug_standardization_missing")
    if _sha256(
        drug["canonical_structure_fingerprint"], "drug_standardization_missing"
    ) != _canonical_drug_binding_fingerprint(
        canonical_drug_id=canonical_drug_id,
        standardized_smiles=smiles,
        standardizer_id=standardizer_id,
        standardizer_version=standardizer_version,
        standardizer_fingerprint=standardizer_fingerprint,
    ):
        _fail("canonical_drug_binding_mismatch")
    return canonical_drug_id


def _quantitative_mic(value: Any, *, source_content_sha256: str) -> None:
    measurement = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "quantity",
                "raw_value_decimal",
                "raw_unit",
                "reported_scale",
                "relation",
                "censoring",
                "censor_bound_decimal",
                "normalized_value_decimal",
                "normalized_unit",
                "normalized_scale",
                "conversion_fingerprint",
                "raw_record_fingerprint",
            }
        ),
        "mic_value_invalid",
    )
    if (
        measurement["schema_version"] != "gnb.mic-admission-measurement.v1"
        or measurement["quantity"] != "minimum_inhibitory_concentration"
    ):
        _fail("mic_value_invalid")
    raw_value = _positive_decimal(measurement["raw_value_decimal"], "mic_value_invalid")
    _finite_decimal(measurement["normalized_value_decimal"], "mic_value_invalid")
    for field in ("raw_unit", "reported_scale", "normalized_unit", "normalized_scale"):
        _text(measurement[field], "mic_unit_or_scale_missing")
    relation = measurement["relation"]
    censoring = measurement["censoring"]
    if relation == "=":
        if censoring != "none" or measurement["censor_bound_decimal"] is not None:
            _fail("mic_relation_censoring_inconsistent")
    elif relation in {"<", ">"}:
        expected = "left" if relation == "<" else "right"
        if censoring != expected:
            _fail("mic_relation_censoring_inconsistent")
        if (
            _positive_decimal(
                measurement["censor_bound_decimal"], "mic_relation_censoring_inconsistent"
            )
            != raw_value
        ):
            _fail("mic_relation_censoring_inconsistent")
    else:
        _fail("mic_relation_censoring_inconsistent")
    _sha256(measurement["conversion_fingerprint"], "content_or_transformation_identity_missing")
    if (
        _sha256(measurement["raw_record_fingerprint"], "content_or_transformation_identity_missing")
        != source_content_sha256
    ):
        _fail("cross_source_join_unproven")


def _assay(value: Any) -> None:
    assay = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "assay_id",
                "method_kind",
                "method_id",
                "standard_id",
                "protocol_fingerprint",
                "conditions",
            }
        ),
        "assay_contract_incomplete",
    )
    if (
        assay["schema_version"] != "gnb.mic-admission-assay.v1"
        or assay["method_kind"] != "broth_microdilution"
    ):
        _fail("assay_contract_incomplete")
    for field in ("assay_id", "method_id", "standard_id"):
        _text(assay[field], "assay_contract_incomplete")
    _sha256(assay["protocol_fingerprint"], "assay_contract_incomplete")
    conditions = _exact_fields(
        assay["conditions"],
        frozenset(
            {
                "schema_version",
                "medium_id",
                "inoculum_value_decimal",
                "inoculum_unit",
                "incubation_temperature_c",
                "incubation_duration_h",
                "atmosphere",
                "dilution_series_id",
                "dilution_factor",
                "dilution_lower_bound",
                "dilution_upper_bound",
                "dilution_unit",
                "endpoint",
            }
        ),
        "assay_contract_incomplete",
    )
    if conditions["schema_version"] != "gnb.mic-admission-assay-conditions.v1":
        _fail("assay_contract_incomplete")
    for field in (
        "medium_id",
        "inoculum_unit",
        "atmosphere",
        "dilution_series_id",
        "dilution_unit",
        "endpoint",
    ):
        _text(conditions[field], "assay_contract_incomplete")
    _positive_decimal(conditions["inoculum_value_decimal"], "assay_contract_incomplete")
    temperature = _positive_number(
        conditions["incubation_temperature_c"], "assay_contract_incomplete"
    )
    duration = _positive_number(conditions["incubation_duration_h"], "assay_contract_incomplete")
    factor = _positive_number(conditions["dilution_factor"], "assay_contract_incomplete")
    lower = _positive_number(conditions["dilution_lower_bound"], "assay_contract_incomplete")
    upper = _positive_number(conditions["dilution_upper_bound"], "assay_contract_incomplete")
    if temperature <= 0 or duration <= 0 or factor <= 1 or lower > upper:
        _fail("assay_contract_incomplete")


def _observed_omics(value: Any) -> None:
    omics = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "observation_mode",
                "source_asset",
                "payload_fingerprint",
                "feature_vocabulary_fingerprint",
                "feature_contract_fingerprint",
                "feature_mapping_fingerprint",
                "negative_call_semantics",
            }
        ),
        "omics_identity_or_feature_contract_missing",
    )
    if omics["schema_version"] != "gnb.mic-admission-observed-omics.v1":
        _fail("omics_identity_or_feature_contract_missing")
    if omics["observation_mode"] != "observed_isolate_omics":
        _fail("omics_not_observed")
    asset = _exact_fields(
        omics["source_asset"],
        frozenset({"schema_version", "sha256", "size_bytes", "media_type"}),
        "omics_identity_or_feature_contract_missing",
    )
    if asset["schema_version"] != "gnb.mic-admission-source-asset.v1":
        _fail("omics_identity_or_feature_contract_missing")
    _sha256(asset["sha256"], "omics_identity_or_feature_contract_missing")
    if (
        isinstance(asset["size_bytes"], bool)
        or not isinstance(asset["size_bytes"], int)
        or asset["size_bytes"] <= 0
    ):
        _fail("omics_identity_or_feature_contract_missing")
    _text(asset["media_type"], "omics_identity_or_feature_contract_missing")
    for field in (
        "payload_fingerprint",
        "feature_vocabulary_fingerprint",
        "feature_contract_fingerprint",
        "feature_mapping_fingerprint",
    ):
        _sha256(omics[field], "omics_identity_or_feature_contract_missing")
    negative = _exact_fields(
        omics["negative_call_semantics"],
        frozenset({"schema_version", "status", "fingerprint"}),
        "negative_call_semantics_unverified",
    )
    if (
        negative["schema_version"] != "gnb.mic-admission-negative-call.v1"
        or negative["status"] != "documented"
    ):
        _fail("negative_call_semantics_unverified")
    _sha256(negative["fingerprint"], "negative_call_semantics_unverified")


def _perturbation_scope(value: Any) -> None:
    scope = _exact_fields(
        value,
        frozenset({"schema_version", "in_scope", "mode", "observed_perturbation_fingerprint"}),
        "perturbation_in_silico_or_unobserved",
    )
    if (
        scope["schema_version"] != "gnb.mic-admission-perturbation-scope.v1"
        or type(scope["in_scope"]) is not bool
    ):
        _fail("perturbation_in_silico_or_unobserved")
    if scope["in_scope"] is False:
        if (
            scope["mode"] != "not_in_scope"
            or scope["observed_perturbation_fingerprint"] is not None
        ):
            _fail("perturbation_in_silico_or_unobserved")
        return
    if scope["mode"] != "observed_gene_state":
        _fail("perturbation_in_silico_or_unobserved")
    _sha256(scope["observed_perturbation_fingerprint"], "perturbation_in_silico_or_unobserved")


def _profile_toolchain(value: Any) -> None:
    toolchain = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "tool_id",
                "tool_version",
                "binary_fingerprint",
                "database_id",
                "database_fingerprint",
                "parameters_fingerprint",
                "result_fingerprint",
            }
        ),
        "tool_database_identity_missing",
    )
    if toolchain["schema_version"] != "gnb.mic-admission-profile-toolchain.v1":
        _fail("tool_database_identity_missing")
    for field in ("tool_id", "tool_version", "database_id"):
        _text(toolchain[field], "tool_database_identity_missing")
    for field in (
        "binary_fingerprint",
        "database_fingerprint",
        "parameters_fingerprint",
        "result_fingerprint",
    ):
        _sha256(toolchain[field], "tool_database_identity_missing")


def _split(value: Any) -> None:
    split = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "protocol_id",
                "protocol_version",
                "protocol_fingerprint",
                "pre_registered_at",
                "assignment",
                "leakage_unit",
                "leakage_group_fingerprint",
            }
        ),
        "split_assignment_or_leakage_unit_invalid",
    )
    if split["schema_version"] != "gnb.mic-admission-split.v1":
        _fail("split_assignment_or_leakage_unit_invalid")
    for field in ("protocol_id", "protocol_version", "leakage_unit"):
        _text(split[field], "split_assignment_or_leakage_unit_invalid")
    _sha256(split["protocol_fingerprint"], "split_assignment_or_leakage_unit_invalid")
    _sha256(split["leakage_group_fingerprint"], "split_assignment_or_leakage_unit_invalid")
    try:
        parsed = _parse_rfc3339_timestamp(
            _text(split["pre_registered_at"], "split_not_preregistered")
        )
    except ValueError:
        _fail("split_not_preregistered")
    if parsed.tzinfo is None:
        _fail("split_not_preregistered")
    assignment = _text(split["assignment"], "split_assignment_or_leakage_unit_invalid")
    if assignment not in {"train", "dev", "held_out"}:
        _fail("split_assignment_or_leakage_unit_invalid")


def _provenance(value: Any, *, source_content_sha256: str) -> None:
    provenance = _exact_fields(
        value,
        frozenset(
            {
                "schema_version",
                "source_snapshot_fingerprint",
                "license",
                "access_basis",
                "transformation",
            }
        ),
        "provenance_incomplete",
    )
    if provenance["schema_version"] != "gnb.mic-admission-provenance.v1":
        _fail("provenance_incomplete")
    _sha256(provenance["source_snapshot_fingerprint"], "provenance_incomplete")
    _text(provenance["access_basis"], "license_or_access_unverified")
    license_record = _exact_fields(
        provenance["license"],
        frozenset({"schema_version", "expression", "terms_fingerprint", "evidence_fingerprint"}),
        "license_or_access_unverified",
    )
    if license_record["schema_version"] != "gnb.mic-admission-license.v1":
        _fail("license_or_access_unverified")
    _text(license_record["expression"], "license_or_access_unverified")
    _sha256(license_record["terms_fingerprint"], "license_or_access_unverified")
    _sha256(license_record["evidence_fingerprint"], "license_or_access_unverified")
    transformation = _exact_fields(
        provenance["transformation"],
        frozenset(
            {
                "schema_version",
                "kind",
                "code_fingerprint",
                "input_fingerprints",
                "output_fingerprint",
            }
        ),
        "content_or_transformation_identity_missing",
    )
    if transformation["schema_version"] != "gnb.mic-admission-transformation.v1":
        _fail("content_or_transformation_identity_missing")
    if transformation["kind"] != "record_preserving_normalization":
        _fail("cross_source_join_unproven")
    _sha256(transformation["code_fingerprint"], "content_or_transformation_identity_missing")
    inputs = transformation["input_fingerprints"]
    if not isinstance(inputs, list) or len(inputs) != 1:
        _fail("cross_source_join_unproven")
    if _sha256(inputs[0], "content_or_transformation_identity_missing") != source_content_sha256:
        _fail("cross_source_join_unproven")
    _sha256(transformation["output_fingerprint"], "content_or_transformation_identity_missing")


def _review_state(value: Any) -> None:
    review = _exact_fields(
        value,
        frozenset({"schema_version", "license", "provenance", "authority"}),
        "review_state_invalid",
    )
    if (
        review["schema_version"] != "gnb.mic-admission-review-state.v1"
        or review["license"] != "unreviewed"
        or review["provenance"] != "unreviewed"
        or review["authority"] != "unapproved"
    ):
        _fail("review_state_invalid")


def validate_mic_admission_record(value: Any) -> dict[str, str]:
    """Validate one offline candidate without approving it for a Pack or model."""

    try:
        return _validate_mic_admission_record(value)
    except _InternalMICAdmissionRecordError:
        raise
    except Exception:  # noqa: BLE001 - public research boundary must fail closed
        _fail("schema_invalid")


def _validate_mic_admission_record(value: Any) -> dict[str, str]:
    record = _exact_fields(_plain_mapping(value), _TOP_LEVEL_FIELDS, "schema_invalid")
    if record["schema_version"] != SCHEMA_VERSION:
        _fail("schema_invalid")
    record_id = _identifier(record["record_id"], "schema_invalid")
    _target(record["target"])
    source_content_sha256 = _source(record["source"])
    _taxon(record["taxon"])
    isolate_id, profile_id = _isolate_profile(record["isolate_profile"])
    canonical_drug_id = _drug(record["drug"])
    _quantitative_mic(record["quantitative_mic"], source_content_sha256=source_content_sha256)
    _assay(record["assay"])
    _observed_omics(record["observed_omics"])
    _perturbation_scope(record["perturbation_scope"])
    _profile_toolchain(record["profile_toolchain"])
    profile_payload_fingerprints = {
        record["isolate_profile"]["profile_payload_fingerprint"],
        record["observed_omics"]["payload_fingerprint"],
        record["profile_toolchain"]["result_fingerprint"],
    }
    if len(profile_payload_fingerprints) != 1:
        _fail("profile_payload_identity_mismatch")
    _split(record["split"])
    _provenance(record["provenance"], source_content_sha256=source_content_sha256)
    _review_state(record["review_state"])
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "record_fingerprint": _canonical_fingerprint(record),
        "task": "predict_mic",
        "taxonomy_id": EXPECTED_TAXON,
        "isolate_id": isolate_id,
        "profile_id": profile_id,
        "canonical_drug_id": canonical_drug_id,
        "status": "structurally_complete_unreviewed",
        "admission_status": "not_admitted",
    }


def mic_admission_preflight(value: Any) -> tuple[dict[str, str] | None, tuple[str, ...]]:
    """Return a safe structural-screen result; this never grants approval."""

    try:
        return (
            validate_mic_admission_record(value),
            ("gnb_mic_admission_not_admitted_pending_governance",),
        )
    except MICAdmissionRecordError as exc:
        return None, (f"gnb_mic_admission_{exc.code}",)
    except Exception:  # noqa: BLE001 - malformed research input remains fail-closed
        return None, ("gnb_mic_admission_schema_invalid",)


__all__ = [
    "EXPECTED_TAXON",
    "MICAdmissionRecordError",
    "SCHEMA_VERSION",
    "mic_admission_preflight",
    "validate_mic_admission_record",
]
