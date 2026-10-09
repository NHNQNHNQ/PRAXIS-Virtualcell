"""P16E contract-only K562 Golden Norman perturbation adapter.

The module validates immutable identities and synthetic wrapper dictionaries.
It performs no asset I/O, model execution, scientific validation, or policy.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterContractError,
    AdapterExecutionProvenance,
    AdapterInputContract,
    AdapterOOD,
    AdapterOutputContract,
    AdapterOutputEnvelope,
    AdapterUncertainty,
    PreparedAdapterInput,
    VirtualCellModelAdapter,
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
)
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelReleaseRecord,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ENSEMBL_GENE = re.compile(r"^ENSG[0-9]{11}$")
_MAX_SAFE_INTEGER = 2**53 - 1
_PREDICTION_STATUSES = frozenset({"success", "target_not_found", "unsupported_scope", "error"})
_OOD_AXIS_ORDER = (
    "iid",
    "perturbation",
    "combination",
    "cell_type",
    "donor",
    "dataset_platform",
    "species",
    "dose_time",
)
_OOD_AXES = frozenset(_OOD_AXIS_ORDER)


def _canonical_fingerprint(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", serialize_as_any=True)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterContractError(f"{field} must be a finite number")
    if isinstance(value, int) and abs(value) > _MAX_SAFE_INTEGER:
        raise AdapterContractError(f"{field} must be JSON-safe")
    number = float(value)
    if not math.isfinite(number):
        raise AdapterContractError(f"{field} must be finite")
    return number


def _finite_vector(value: Any, field: str) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != 5045:
        raise AdapterContractError(f"{field} must contain exactly 5045 values")
    return tuple(_finite_number(item, field) for item in value)


def _revalidate_contract(value: Any, expected_type, field: str):
    if not isinstance(value, expected_type):
        raise TypeError(f"{field} must be {expected_type.__name__}")
    try:
        _reject_undeclared_model_fields(value, field)
        normalized = expected_type.model_validate(value.model_dump(mode="python", serialize_as_any=True))
        _reject_model_type_drift(value, normalized, field)
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise AdapterContractError(f"invalid {field}") from exc


class _P16Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def to_dict(self) -> dict[str, Any]:
        _reject_undeclared_model_fields(self, type(self).__name__)
        return self.model_dump(mode="json", serialize_as_any=True)

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class K562GoldenDataBinding(_P16Contract):
    """Exact checked-in text identities; no asset-access claim."""

    schema_version: Literal["vc.k562-golden-data-binding.v1"]
    pack_id: Literal["norman-2019-k562-golden"]
    pack_version: Literal["1.0.0"]
    pack_fingerprint: Literal["42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee"]
    canonical_contract_fingerprint: Literal["f34afa761239abc97033c78bb9d0c29a1c36a4c7d1a106a9cbbaa805a5196ff5"]
    contract_yaml_sha256: Literal["6bfc46e23e55e05a2c87dcdac9bd48da6c1f6bd2240742dc18f73ec963cf0d76"]
    contract_yaml_size_bytes: Literal[4749]
    pack_manifest_sha256: Literal["704b81da74fd96907b7e6012757b2c12104fcf3a2a3ae56af52c76d7f2c163a6"]
    pack_manifest_size_bytes: Literal[30074]
    artifact_manifest_sha256: Literal["110276ce9cc74caaf396448319579ec0e1414dc7470ea31f9170a5d62ca4784c"]
    artifact_manifest_size_bytes: Literal[4140]
    h5ad_path: Literal["norman_k562_golden.h5ad"]
    h5ad_media_type: Literal["application/vnd.anndata+hdf5"]
    h5ad_sha256: Literal["43da7aeeaca2a3ceb00ec6e9ee983b9b708b01f85922cc7afee229225a66792a"]
    h5ad_size_bytes: Literal[2285816806]
    golden_contract_path: Literal["golden_contract.json"]
    golden_contract_media_type: Literal["application/json"]
    golden_contract_sha256: Literal["456242651b50a87f507c6e9787999d4fd325beec82106363c7261cbdaa744521"]
    golden_contract_size_bytes: Literal[4663]
    matrix_shape: tuple[Literal[91205], Literal[5045]]
    license_id: Literal["CC0-1.0"]
    taxonomy_id: Literal["NCBITaxon:9606"]
    scientific_name: Literal["Homo sapiens"]
    cell_identity_id: Literal["CVCL_0004"]
    assembly_name: Literal["GRCh38"]
    assembly_accession: Literal["GCA_000001405.15"]
    modality_name: Literal["scRNA"]
    modality_id: Literal["EFO:0008913"]
    feature_namespace: Literal["EnsemblGene"]
    feature_namespace_version: Literal["Ensembl 84"]
    feature_id_format: Literal["ensembl_gene"]
    source_cell_type_value: Literal["A549"]
    source_cell_type_interpretation: Literal["upstream_metadata_error_preserved"]
    feature_ids_sha256: Literal["ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"]
    feature_records_sha256: Literal["1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747"]
    split_sha256: Literal["c501e8a05514b914b216ddb2dbe0a94e709fa7a1e2214d727b831102503f956e"]
    condition_ids_sha256: Literal["6f41dd46159a926ad476152d20c2f82e5def422f16a8213b0918af48594cabb3"]
    matched_control_sha256: Literal["2fc6ba835e3a9353345651b9369abdd189c6017a854932c038b157faa4b378ae"]
    perturbation_ids_sha256: Literal["e69d8b83e3f69a628c545b3c44f6ad694d8406619451f1db1b6489be33fc9e21"]
    condition_values_sha256: Literal["7f3e175c495bc9499d852965869bafc23249948e0be5c87eb89e5d01befc44c9"]
    perturbation_records_sha256: Literal["0a43f9c57560f7192c0a848cb1ec044a9bf2bfdbc20d6405f98d73b3ca04d1e9"]
    target_ids_sha256: Literal["4f58ed5c3ad7355ccba64eed0dd95e02cbcbf75a977d6aec2a1cfd5357abd64c"]
    control_assignment_sha256: Literal["8f09650026e297ce0e010120814230bc7de306364ab49316b7c102e836c6e3d5"]
    unseen_train_target_ids_sha256: Literal["3bec2a15f4c5965dd32112c3508e4b70ead1724f308d597ab61e9b6210587de3"]
    source_control_condition: Literal["ctrl"]
    train_control_condition_id: Literal["norman.control.train"]
    validation_control_condition_id: Literal["norman.control.validation"]
    test_control_condition_id: Literal["norman.control.test"]
    train_control_guide: Literal["NegCtrl0_NegCtrl0__NegCtrl0_NegCtrl0"]
    validation_control_guide: Literal["NegCtrl10_NegCtrl0__NegCtrl10_NegCtrl0"]
    test_control_guide: Literal["NegCtrl11_NegCtrl0__NegCtrl11_NegCtrl0"]

    @field_validator("matrix_shape", mode="before")
    @classmethod
    def _matrix_shape(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("matrix_shape must be an array")
        values = tuple(value)
        if len(values) != 2 or any(type(item) is not int for item in values):
            raise ValueError("matrix_shape must contain exact integers")
        return values

    @field_validator(
        "contract_yaml_size_bytes",
        "pack_manifest_size_bytes",
        "artifact_manifest_size_bytes",
        "h5ad_size_bytes",
        "golden_contract_size_bytes",
        mode="before",
    )
    @classmethod
    def _exact_sizes(cls, value, info):
        if type(value) is not int:
            raise ValueError(f"{info.field_name} must be an exact integer")
        return value


class K562GoldenPerturbationBinding(_P16Contract):
    """One canonical record proposal, without a runtime membership claim."""

    schema_version: Literal["vc.k562-golden-perturbation-binding.v1"]
    evaluation_scope: Literal["single_gene", "combination"]
    condition_id: str
    condition_record_fingerprint: str
    perturbation_kind: Literal["gene", "gene_combination"]
    ordered_target_ids: tuple[str, ...]
    pack_fingerprint: str
    artifact_manifest_sha256: str
    condition_values_sha256: str
    perturbation_records_sha256: str
    target_ids_sha256: str
    record_membership_verified: Literal[False]
    reason: Literal["p16r_not_authorized"]

    @field_validator(
        "condition_record_fingerprint",
        "pack_fingerprint",
        "artifact_manifest_sha256",
        "condition_values_sha256",
        "perturbation_records_sha256",
        "target_ids_sha256",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("condition_id", mode="before")
    @classmethod
    def _condition(cls, value):
        return _text(value, "condition_id")

    @field_validator("record_membership_verified", mode="before")
    @classmethod
    def _membership_bool(cls, value):
        if type(value) is not bool:
            raise ValueError("record_membership_verified must be an exact boolean")
        return value

    @field_validator("ordered_target_ids", mode="before")
    @classmethod
    def _targets(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("ordered_target_ids must be a non-empty array")
        values = tuple(_text(item, "ordered_target_ids") for item in value)
        if any(not _ENSEMBL_GENE.fullmatch(item) for item in values):
            raise ValueError("ordered_target_ids must use exact unversioned Ensembl gene IDs")
        if len(set(values)) != len(values):
            raise ValueError("ordered_target_ids must be unique")
        return values

    @model_validator(mode="after")
    def _exact_record(self):
        expected_kind, expected_count = (
            ("gene", 1) if self.evaluation_scope == "single_gene" else ("gene_combination", 2)
        )
        if self.perturbation_kind != expected_kind or len(self.ordered_target_ids) != expected_count:
            raise ValueError("evaluation scope, perturbation kind, and ordered target count disagree")
        record = {
            "id": self.condition_id,
            "kind": "genetic",
            "targets": list(self.ordered_target_ids),
        }
        if self.condition_record_fingerprint != _canonical_fingerprint(record):
            raise ValueError("condition_record_fingerprint does not match the exact ordered record")
        return self


class K562GoldenExecutionBinding(_P16Contract):
    schema_version: Literal["vc.k562-golden-execution-binding.v1"]
    runner_id: str
    runner_version: str
    execution_mode: Literal["native_delta_expression"]
    feature_count: Literal[5045]
    feature_ids_sha256: Literal["ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"]
    feature_records_sha256: Literal["1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747"]
    value_semantics: Literal["condition_mean_X_minus_matched_split_control_mean_X"]
    reference: Literal["matched_split_control_mean_X"]
    output_unit: None
    inference_configuration_fingerprint: str
    preserve_feature_order: Literal[True]
    absolute_to_delta_conversion_allowed: Literal[False]
    normalization_allowed: Literal[False]
    reordering_allowed: Literal[False]
    fill_allowed: Literal[False]
    imputation_allowed: Literal[False]
    deduplication_allowed: Literal[False]

    @field_validator("runner_id", "runner_version", mode="before")
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("inference_configuration_fingerprint", mode="before")
    @classmethod
    def _inference(cls, value):
        return _fingerprint(value, "inference_configuration_fingerprint")

    @field_validator("feature_count", mode="before")
    @classmethod
    def _feature_count(cls, value):
        if type(value) is not int:
            raise ValueError("feature_count must be an exact integer")
        return value

    @field_validator(
        "preserve_feature_order",
        "absolute_to_delta_conversion_allowed",
        "normalization_allowed",
        "reordering_allowed",
        "fill_allowed",
        "imputation_allowed",
        "deduplication_allowed",
        mode="before",
    )
    @classmethod
    def _exact_bools(cls, value, info):
        if type(value) is not bool:
            raise ValueError(f"{info.field_name} must be an exact boolean")
        return value


class K562GoldenCompatibilityBinding(_P16Contract):
    schema_version: Literal["vc.k562-golden-compatibility-binding.v1"]
    model_release_fingerprint: str
    model_fingerprint: str
    artifact_fingerprint: str
    environment_fingerprint: str
    adapter_fingerprint: str
    pack_fingerprint: str
    data_binding_fingerprint: str
    perturbation_binding_fingerprint: str
    execution_binding_fingerprint: str
    assets_verified: Literal[False]
    executable: Literal[False]
    reason: Literal["p16r_not_authorized"]

    @field_validator(
        "model_release_fingerprint",
        "model_fingerprint",
        "artifact_fingerprint",
        "environment_fingerprint",
        "adapter_fingerprint",
        "pack_fingerprint",
        "data_binding_fingerprint",
        "perturbation_binding_fingerprint",
        "execution_binding_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("assets_verified", "executable", mode="before")
    @classmethod
    def _exact_bools(cls, value, info):
        if type(value) is not bool:
            raise ValueError(f"{info.field_name} must be an exact boolean")
        return value


class K562GoldenPerturbationScope(_P16Contract):
    schema_version: Literal["vc.k562-golden-perturbation-scope.v1"]
    taxonomy_id: Literal["NCBITaxon:9606"]
    scientific_name: Literal["Homo sapiens"]
    cell_identity_name: Literal["K562"]
    cell_identity_id: Literal["CVCL_0004"]
    assembly_name: Literal["GRCh38"]
    assembly_accession: Literal["GCA_000001405.15"]
    assay_name: Literal["scRNA"]
    assay_id: Literal["EFO:0008913"]
    feature_namespace: Literal["EnsemblGene"]
    feature_namespace_version: Literal["Ensembl 84"]
    feature_id_format: Literal["ensembl_gene"]
    feature_count: Literal[5045]
    feature_ids_sha256: Literal["ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"]
    feature_records_sha256: Literal["1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747"]
    perturbation_action: Literal["CRISPR activation"]
    dose_value: Literal[1.0]
    dose_unit: Literal["1"]
    time_value: Literal[5.0]
    time_unit: Literal["d"]
    request_timepoint: Literal["5d"]
    evaluation_scope: Literal["single_gene", "combination"]
    model_fingerprint: str
    model_release_fingerprint: str
    model_artifact_fingerprint: str
    environment_fingerprint: str
    adapter_fingerprint: str
    pack_fingerprint: str
    data_binding_fingerprint: str
    perturbation_binding_fingerprint: str
    execution_binding_fingerprint: str
    compatibility_fingerprint: str
    output: Literal["delta_expression"]
    value_semantics: Literal["condition_mean_X_minus_matched_split_control_mean_X"]
    reference: Literal["matched_split_control_mean_X"]
    output_unit: None

    @field_validator("dose_value", "time_value", mode="before")
    @classmethod
    def _exact_floats(cls, value, info):
        if type(value) is not float:
            raise ValueError(f"{info.field_name} must be an exact float")
        return value

    @field_validator("feature_count", mode="before")
    @classmethod
    def _feature_count(cls, value):
        if type(value) is not int:
            raise ValueError("feature_count must be an exact integer")
        return value

    @field_validator(
        "model_fingerprint",
        "model_release_fingerprint",
        "model_artifact_fingerprint",
        "environment_fingerprint",
        "adapter_fingerprint",
        "pack_fingerprint",
        "data_binding_fingerprint",
        "perturbation_binding_fingerprint",
        "execution_binding_fingerprint",
        "compatibility_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class K562GoldenValidationProtocol(_P16Contract):
    """Future P16R preregistration, not a result or decision record."""

    schema_version: Literal["vc.k562-golden-validation-protocol.v1"]
    scope_fingerprint: str
    data_binding_fingerprint: str
    split_name: Literal["norman-condition-holdout-v1"]
    source_train_role: Literal["train"]
    source_test_role: Literal["validation"]
    source_ood_role: Literal["test"]
    train_noncontrol_conditions: Literal[137]
    validation_noncontrol_conditions: Literal[30]
    test_noncontrol_conditions: Literal[116]
    leakage_guard: tuple[str, ...]
    primary_metric: Literal["condition_macro_full_feature_delta_mse"]
    metric_direction: Literal["lower_is_better"]
    truth_semantics: Literal["condition_mean_X_minus_matched_split_control_mean_X"]
    primary_comparator: Literal["condition_level_additive_ridge"]
    historical_additive_result_sha256: Literal["b82dc7ab26c6f6fdef4414f6b05c51edb32b2a35e4c00f45824cc839ab9cf1a9"]
    historical_additive_test_mse: Literal[0.0032570634320908554]
    historical_no_change_result_sha256: Literal["38182a3fdb24666b8d76d9b118d2de4fd8cfd998ae025a54d7fecc42e09f7b5e"]
    historical_global_mean_result_sha256: Literal["2b757d3e2d4e657f9bdc3aa890ee6d84ae5096661246ff4f881045676bb98d3a"]
    historical_evaluation_result_sha256: Literal["1cc1110a75183f1b271a8caf34db9998046f93bd42abda278f725879d38eb79c"]
    same_runtime_required: Literal[True]
    historical_comparator_role: Literal["checked_in_historical_reference_only"]
    contamination_audit_required: Literal[True]
    paired_comparison: Literal[True]
    paired_difference: Literal["candidate_mse_minus_additive_ridge_mse"]
    bootstrap_unit: Literal["held_out_perturbation_condition"]
    bootstrap_method: Literal["paired_percentile"]
    bootstrap_rng: Literal["numpy.PCG64"]
    bootstrap_seed: Literal[0]
    bootstrap_replicates: Literal[2000]
    bootstrap_interval: tuple[Literal[0.025], Literal[0.975]]
    candidate_superiority_requirement: Literal["paired_difference_ci_upper_below_zero"]
    stochastic_seeds: tuple[int, ...]
    validation_only_tuning: Literal[True]
    independent_k562_dataset_required: Literal[True]
    independent_platform_required: Literal[True]
    external_dataset_requirement: Literal["independent_semantically_compatible_k562_dataset_platform"]
    non_k562_or_donor_external_as_ood_only: Literal[True]
    external_adaptation_steps: Literal[0]
    separate_scope_evaluation_required: Literal[True]
    record_role: Literal["preregistration_not_evidence"]
    ood_axes: tuple[str, ...]

    @field_validator("scope_fingerprint", "data_binding_fingerprint", mode="before")
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("leakage_guard", "ood_axes", mode="before")
    @classmethod
    def _text_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be a non-empty array")
        values = tuple(_text(item, info.field_name) for item in value)
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must be unique")
        return values

    @field_validator("bootstrap_interval", mode="before")
    @classmethod
    def _interval(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("bootstrap_interval must be an array")
        values = tuple(value)
        if len(values) != 2 or any(type(item) is not float for item in values):
            raise ValueError("bootstrap_interval must contain exact floats")
        return values

    @field_validator(
        "train_noncontrol_conditions",
        "validation_noncontrol_conditions",
        "test_noncontrol_conditions",
        "bootstrap_seed",
        "bootstrap_replicates",
        "external_adaptation_steps",
        mode="before",
    )
    @classmethod
    def _exact_integers(cls, value, info):
        if type(value) is not int:
            raise ValueError(f"{info.field_name} must be an exact integer")
        return value

    @field_validator("historical_additive_test_mse", mode="before")
    @classmethod
    def _historical_float(cls, value):
        if type(value) is not float:
            raise ValueError("historical_additive_test_mse must be an exact float")
        return value

    @field_validator(
        "same_runtime_required",
        "contamination_audit_required",
        "paired_comparison",
        "validation_only_tuning",
        "independent_k562_dataset_required",
        "independent_platform_required",
        "non_k562_or_donor_external_as_ood_only",
        "separate_scope_evaluation_required",
        mode="before",
    )
    @classmethod
    def _exact_bools(cls, value, info):
        if type(value) is not bool:
            raise ValueError(f"{info.field_name} must be an exact boolean")
        return value

    @field_validator("stochastic_seeds", mode="before")
    @classmethod
    def _seeds(cls, value):
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ValueError("stochastic_seeds must contain at least three seeds")
        values = tuple(value)
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0 or item > _MAX_SAFE_INTEGER
            for item in values
        ) or len(set(values)) != len(values):
            raise ValueError("stochastic_seeds must be unique non-negative JSON-safe integers")
        return values

    @model_validator(mode="after")
    def _exact_arrays(self):
        if self.leakage_guard != ("condition_id",):
            raise ValueError("leakage_guard must equal condition_id")
        if self.ood_axes != _OOD_AXIS_ORDER:
            raise ValueError("ood_axes must equal the canonical order")
        return self


class K562GoldenAdapterInputContract(AdapterInputContract):
    schema_version: Literal["vc.k562-golden-adapter-input-contract.v1"]
    taxonomy_id: Literal["NCBITaxon:9606"]
    cell_identity_id: Literal["CVCL_0004"]
    assembly_accession: Literal["GCA_000001405.15"]
    assay_id: Literal["EFO:0008913"]
    feature_namespace: Literal["EnsemblGene"]
    feature_namespace_version: Literal["Ensembl 84"]
    feature_id_format: Literal["ensembl_gene"]
    evaluation_scopes: tuple[Literal["single_gene"], Literal["combination"]]
    value_semantics: Literal["condition_mean_X_minus_matched_split_control_mean_X"]
    reference: Literal["matched_split_control_mean_X"]
    required_bindings: tuple[str, ...]


class K562GoldenAdapterOutputContract(AdapterOutputContract):
    schema_version: Literal["vc.k562-golden-adapter-output-contract.v1"]
    feature_count: Literal[5045]
    feature_ids_sha256: Literal["ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"]
    feature_records_sha256: Literal["1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747"]
    value_semantics: Literal["condition_mean_X_minus_matched_split_control_mean_X"]
    reference: Literal["matched_split_control_mean_X"]


class K562GoldenPreparedModelInput(_P16Contract):
    schema_version: Literal["vc.k562-golden-prepared-model-input.v1"]
    request_id: str
    request_fingerprint: str
    scope: K562GoldenPerturbationScope
    scope_fingerprint: str
    validation_protocol: K562GoldenValidationProtocol
    validation_protocol_fingerprint: str
    perturbation_binding: K562GoldenPerturbationBinding
    perturbation_binding_fingerprint: str
    execution_binding_fingerprint: str
    evaluation_scope: Literal["single_gene", "combination"]
    condition_id: str
    perturbation_kind: Literal["gene", "gene_combination"]
    ordered_target_ids: tuple[str, ...]
    adapter_fingerprint: str
    input_contract_fingerprint: str
    data_binding: K562GoldenDataBinding
    data_binding_fingerprint: str
    pack_fingerprint: str
    compatibility_fingerprint: str

    @field_validator("request_id", "condition_id", mode="before")
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "request_fingerprint",
        "scope_fingerprint",
        "validation_protocol_fingerprint",
        "perturbation_binding_fingerprint",
        "execution_binding_fingerprint",
        "adapter_fingerprint",
        "input_contract_fingerprint",
        "data_binding_fingerprint",
        "pack_fingerprint",
        "compatibility_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("ordered_target_ids", mode="before")
    @classmethod
    def _targets(cls, value):
        return K562GoldenPerturbationBinding._targets(value)

    @model_validator(mode="after")
    def _bindings(self):
        if self.scope_fingerprint != self.scope.fingerprint():
            raise ValueError("scope fingerprint does not match embedded scope")
        if (
            self.validation_protocol_fingerprint != self.validation_protocol.fingerprint()
            or self.validation_protocol.scope_fingerprint != self.scope_fingerprint
            or self.validation_protocol.data_binding_fingerprint != self.data_binding_fingerprint
        ):
            raise ValueError("validation protocol does not match embedded scope")
        if (
            self.perturbation_binding_fingerprint != self.perturbation_binding.fingerprint()
            or self.perturbation_binding_fingerprint != self.scope.perturbation_binding_fingerprint
        ):
            raise ValueError("perturbation binding does not match scope")
        if (
            self.data_binding_fingerprint != self.data_binding.fingerprint()
            or self.data_binding_fingerprint != self.scope.data_binding_fingerprint
            or self.data_binding.pack_fingerprint != self.pack_fingerprint
        ):
            raise ValueError("data binding does not match scope")
        if (
            self.evaluation_scope != self.perturbation_binding.evaluation_scope
            or self.evaluation_scope != self.scope.evaluation_scope
            or self.condition_id != self.perturbation_binding.condition_id
            or self.perturbation_kind != self.perturbation_binding.perturbation_kind
            or self.ordered_target_ids != self.perturbation_binding.ordered_target_ids
        ):
            raise ValueError("prepared perturbation scope is inconsistent")
        for field in (
            "adapter_fingerprint",
            "pack_fingerprint",
            "compatibility_fingerprint",
            "execution_binding_fingerprint",
        ):
            if getattr(self, field) != getattr(self.scope, field):
                raise ValueError(f"{field} does not match scope")
        return self


class K562GoldenPerturbationAdapter(VirtualCellModelAdapter):
    """Exact P16E contract adapter, intentionally absent from the default registry."""

    adapter_id = "k562-golden-perturbation-delta-contract"
    version = "1.0.0"
    input_contract = K562GoldenAdapterInputContract(
        schema_version="vc.k562-golden-adapter-input-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(5045,),
        unit=None,
        pack_data_required=False,
        alignment_required=False,
        taxonomy_id="NCBITaxon:9606",
        cell_identity_id="CVCL_0004",
        assembly_accession="GCA_000001405.15",
        assay_id="EFO:0008913",
        feature_namespace="EnsemblGene",
        feature_namespace_version="Ensembl 84",
        feature_id_format="ensembl_gene",
        evaluation_scopes=("single_gene", "combination"),
        value_semantics="condition_mean_X_minus_matched_split_control_mean_X",
        reference="matched_split_control_mean_X",
        required_bindings=(
            "model_release",
            "model_artifact",
            "environment",
            "adapter",
            "pack",
            "perturbation_record",
            "execution",
            "compatibility",
            "validation_protocol",
        ),
    )
    output_contract = K562GoldenAdapterOutputContract(
        schema_version="vc.k562-golden-adapter-output-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(5045,),
        unit=None,
        uncertainty_required=True,
        ood_required=True,
        abstain_allowed=True,
        feature_count=5045,
        feature_ids_sha256="ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7",
        feature_records_sha256="1cc8b612bef0a0d7daac01bb8cc509346a4a32850f93298f29865bb2328d9747",
        value_semantics="condition_mean_X_minus_matched_split_control_mean_X",
        reference="matched_split_control_mean_X",
    )

    def _validate_request(
        self,
        request: VirtualCellRequestV2,
        scope: K562GoldenPerturbationScope,
        perturbation: K562GoldenPerturbationBinding,
        protocol: K562GoldenValidationProtocol,
        pack: K562GoldenDataBinding,
    ) -> None:
        outputs = request.task.requested_outputs or (request.output_modality.name,)
        if (
            request.task.task_type != self.input_contract.task
            or tuple(outputs) != (self.input_contract.output,)
            or request.output_modality.name != self.input_contract.output
        ):
            raise AdapterContractError("request task/output does not match adapter")
        if (
            request.species.taxonomy_id != scope.taxonomy_id
            or request.species.scientific_name != scope.scientific_name
            or request.species.common_name != "human"
        ):
            raise AdapterContractError("request species does not match exact human scope")
        if (
            request.cell_context.cell_type_name != scope.cell_identity_name
            or request.cell_context.cell_type_id is not None
            or request.cell_context.tissue_name is not None
            or request.cell_context.tissue_id is not None
        ):
            raise AdapterContractError("request cell context must be exact K562")
        expected_attributes = {
            "cell_identity_id": scope.cell_identity_id,
            "assembly_name": scope.assembly_name,
            "assembly_accession": scope.assembly_accession,
            "assay_id": scope.assay_id,
            "feature_namespace_version": scope.feature_namespace_version,
            "feature_ids_sha256": scope.feature_ids_sha256,
            "evaluation_scope": scope.evaluation_scope,
        }
        if dict(request.cell_context.attributes) != expected_attributes:
            raise AdapterContractError("request K562 attributes do not match exact scope")
        if (
            request.input_modality.name != scope.assay_name
            or request.input_modality.ontology_id != scope.assay_id
            or request.input_modality.unit is not None
            or request.input_modality.feature_namespace != scope.feature_namespace
        ):
            raise AdapterContractError("request input modality does not match exact scRNA scope")
        if (
            request.output_modality.ontology_id != "PRAXISOUTPUT:delta_expression"
            or request.output_modality.unit is not None
            or request.output_modality.feature_namespace != scope.feature_namespace
        ):
            raise AdapterContractError("request output modality does not match exact delta scope")
        if (
            request.perturbation.kind != perturbation.perturbation_kind
            or tuple(request.perturbation.targets) != perturbation.ordered_target_ids
            or request.perturbation.dose_value != scope.dose_value
            or request.perturbation.dose_unit != scope.dose_unit
            or request.perturbation.timepoint != scope.request_timepoint
        ):
            raise AdapterContractError("request perturbation does not match exact ordered scope")
        if any(not _ENSEMBL_GENE.fullmatch(target) for target in request.perturbation.targets):
            raise AdapterContractError("request targets must be canonical unversioned Ensembl gene IDs")
        expected_baseline = {
            "reference": scope.reference,
            "source_control_condition": pack.source_control_condition,
            "matched_control_sha256": pack.matched_control_sha256,
            "control_assignment_sha256": pack.control_assignment_sha256,
            "scope_fingerprint": scope.fingerprint(),
        }
        if request.baseline_context is None or dict(request.baseline_context) != expected_baseline:
            raise AdapterContractError("request baseline does not match exact split controls")
        expected_constraints = {
            "condition_id": perturbation.condition_id,
            "value_semantics": scope.value_semantics,
            "perturbation_binding_fingerprint": perturbation.fingerprint(),
            "validation_protocol_fingerprint": protocol.fingerprint(),
            "record_membership_verified": False,
        }
        if dict(request.constraints) != expected_constraints:
            raise AdapterContractError("request constraints do not match exact P16E bindings")
        if request.metadata:
            raise AdapterContractError("request metadata contains undeclared fields")

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        scope: K562GoldenPerturbationScope,
        model_artifact: ArtifactIdentity,
        environment: EnvironmentIdentity,
        model_release: ModelReleaseRecord,
        perturbation_binding: K562GoldenPerturbationBinding,
        execution_binding: K562GoldenExecutionBinding,
        validation_protocol: K562GoldenValidationProtocol,
        pack: K562GoldenDataBinding,
        compatibility_report: K562GoldenCompatibilityBinding,
    ) -> PreparedAdapterInput:
        request = _revalidate_contract(request, VirtualCellRequestV2, "request")
        scope = _revalidate_contract(scope, K562GoldenPerturbationScope, "scope binding")
        model_artifact = _revalidate_contract(model_artifact, ArtifactIdentity, "model artifact binding")
        environment = _revalidate_contract(environment, EnvironmentIdentity, "environment binding")
        model_release = _revalidate_contract(model_release, ModelReleaseRecord, "model release binding")
        perturbation_binding = _revalidate_contract(
            perturbation_binding, K562GoldenPerturbationBinding, "perturbation binding"
        )
        execution_binding = _revalidate_contract(execution_binding, K562GoldenExecutionBinding, "execution binding")
        validation_protocol = _revalidate_contract(
            validation_protocol, K562GoldenValidationProtocol, "validation protocol"
        )
        pack = _revalidate_contract(pack, K562GoldenDataBinding, "Pack binding")
        compatibility_report = _revalidate_contract(
            compatibility_report, K562GoldenCompatibilityBinding, "compatibility binding"
        )

        if scope.adapter_fingerprint != self.fingerprint():
            raise AdapterContractError("scope adapter fingerprint does not match this adapter")
        if (
            model_artifact.fingerprint() != scope.model_artifact_fingerprint
            or model_artifact.model_fingerprint != scope.model_fingerprint
            or model_artifact.legacy_incomplete
            or model_artifact.safe_load_policy != "data_only"
            or model_artifact.media_type != "application/json"
        ):
            raise AdapterContractError("model artifact identity does not match exact P16E scope")
        if (
            environment.fingerprint() != scope.environment_fingerprint
            or environment.legacy_incomplete
            or self.fingerprint() not in environment.adapter_fingerprints
        ):
            raise AdapterContractError("environment identity does not match exact P16E scope")
        if (
            model_release.fingerprint() != scope.model_release_fingerprint
            or model_release.migration_status != "native"
            or model_release.model_fingerprint != scope.model_fingerprint
            or model_release.pack_fingerprints != (scope.pack_fingerprint,)
            or model_release.artifact_fingerprints != (scope.model_artifact_fingerprint,)
            or model_release.environment_fingerprint != scope.environment_fingerprint
            or model_release.adapter_fingerprints != (self.fingerprint(),)
            or model_release.evidence_fingerprints
            or model_release.policy_fingerprint is not None
        ):
            raise AdapterContractError("model release identity does not match exact P16E scope")
        if pack.fingerprint() != scope.data_binding_fingerprint or pack.pack_fingerprint != scope.pack_fingerprint:
            raise AdapterContractError("Pack identity does not match exact P16E scope")
        if (
            perturbation_binding.fingerprint() != scope.perturbation_binding_fingerprint
            or perturbation_binding.pack_fingerprint != pack.pack_fingerprint
            or perturbation_binding.artifact_manifest_sha256 != pack.artifact_manifest_sha256
            or perturbation_binding.condition_values_sha256 != pack.condition_values_sha256
            or perturbation_binding.perturbation_records_sha256 != pack.perturbation_records_sha256
            or perturbation_binding.target_ids_sha256 != pack.target_ids_sha256
            or perturbation_binding.evaluation_scope != scope.evaluation_scope
        ):
            raise AdapterContractError("perturbation record binding does not match exact scope")
        if execution_binding.fingerprint() != scope.execution_binding_fingerprint:
            raise AdapterContractError("execution binding fingerprint does not match exact scope")
        execution_fields = (
            "feature_count",
            "feature_ids_sha256",
            "feature_records_sha256",
            "value_semantics",
            "reference",
            "output_unit",
        )
        if any(getattr(execution_binding, field) != getattr(scope, field) for field in execution_fields):
            raise AdapterContractError("execution feature/semantics binding drift")
        compatibility_fingerprint = compatibility_report.fingerprint()
        expected_compatibility = {
            "model_release_fingerprint": scope.model_release_fingerprint,
            "model_fingerprint": scope.model_fingerprint,
            "artifact_fingerprint": scope.model_artifact_fingerprint,
            "environment_fingerprint": scope.environment_fingerprint,
            "adapter_fingerprint": self.fingerprint(),
            "pack_fingerprint": scope.pack_fingerprint,
            "data_binding_fingerprint": scope.data_binding_fingerprint,
            "perturbation_binding_fingerprint": scope.perturbation_binding_fingerprint,
            "execution_binding_fingerprint": scope.execution_binding_fingerprint,
        }
        if compatibility_fingerprint != scope.compatibility_fingerprint or any(
            getattr(compatibility_report, field) != value for field, value in expected_compatibility.items()
        ):
            raise AdapterContractError("compatibility identity does not match exact scope")
        if (
            validation_protocol.scope_fingerprint != scope.fingerprint()
            or validation_protocol.data_binding_fingerprint != pack.fingerprint()
        ):
            raise AdapterContractError("validation protocol does not match exact scope")

        self._validate_request(request, scope, perturbation_binding, validation_protocol, pack)
        request_fingerprint = _canonical_fingerprint(request.to_dict())
        model_input = K562GoldenPreparedModelInput(
            schema_version="vc.k562-golden-prepared-model-input.v1",
            request_id=request.request_id,
            request_fingerprint=request_fingerprint,
            scope=scope,
            scope_fingerprint=scope.fingerprint(),
            validation_protocol=validation_protocol,
            validation_protocol_fingerprint=validation_protocol.fingerprint(),
            perturbation_binding=perturbation_binding,
            perturbation_binding_fingerprint=perturbation_binding.fingerprint(),
            execution_binding_fingerprint=execution_binding.fingerprint(),
            evaluation_scope=perturbation_binding.evaluation_scope,
            condition_id=perturbation_binding.condition_id,
            perturbation_kind=perturbation_binding.perturbation_kind,
            ordered_target_ids=perturbation_binding.ordered_target_ids,
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            data_binding=pack,
            data_binding_fingerprint=pack.fingerprint(),
            pack_fingerprint=pack.pack_fingerprint,
            compatibility_fingerprint=compatibility_fingerprint,
        )
        prepared = PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=request_fingerprint,
            pack_fingerprint=pack.pack_fingerprint,
            compatibility_fingerprint=compatibility_fingerprint,
            model_input=model_input.to_dict(),
            values=None,
            shape=None,
            unit=None,
            feature_contract=None,
            feature_contract_fingerprint=None,
            alignment_report=None,
        )
        return self.validate_prepared_input(prepared)

    def validate_prepared_input(self, prepared: PreparedAdapterInput) -> PreparedAdapterInput:
        prepared = super().validate_prepared_input(prepared)
        try:
            model_input = K562GoldenPreparedModelInput.model_validate(prepared.model_input)
        except ValidationError as exc:
            raise AdapterContractError("prepared K562 Golden input is invalid") from exc
        if model_input.request_fingerprint != prepared.request_fingerprint:
            raise AdapterContractError("prepared request fingerprint drift")
        if (
            model_input.adapter_fingerprint != self.fingerprint()
            or model_input.input_contract_fingerprint != self.input_contract.fingerprint()
            or model_input.pack_fingerprint != prepared.pack_fingerprint
            or model_input.compatibility_fingerprint != prepared.compatibility_fingerprint
        ):
            raise AdapterContractError("prepared identity binding drift")
        return prepared

    def _validate_envelope_structure(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        envelope = VirtualCellModelAdapter.validate_envelope(self, envelope)
        try:
            _reject_undeclared_model_fields(envelope.uncertainty, "delta output uncertainty")
            uncertainty = AdapterUncertainty.model_validate(
                envelope.uncertainty.model_dump(mode="python", serialize_as_any=True)
            )
            _reject_model_type_drift(envelope.uncertainty, uncertainty, "delta output uncertainty")
            _reject_undeclared_model_fields(envelope.ood, "delta output OOD")
            ood = AdapterOOD.model_validate(envelope.ood.model_dump(mode="python", serialize_as_any=True))
            _reject_model_type_drift(envelope.ood, ood, "delta output OOD")
            _reject_undeclared_model_fields(envelope.provenance, "delta output provenance")
            provenance = AdapterExecutionProvenance.model_validate(
                envelope.provenance.model_dump(mode="python", serialize_as_any=True)
            )
            _reject_model_type_drift(envelope.provenance, provenance, "delta output provenance")
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid nested delta output contract") from exc
        envelope = envelope.model_copy(update={"uncertainty": uncertainty, "ood": ood, "provenance": provenance})
        if (
            uncertainty.available
            or uncertainty.calibrated
            or uncertainty.value is not None
            or uncertainty.sigma is not None
            or uncertainty.method != "not_available"
            or uncertainty.reason != "no_calibrated_uncertainty_declared"
        ):
            raise AdapterContractError("delta uncertainty must remain unavailable and uncalibrated")
        if set(ood.dimensions).difference(_OOD_AXES):
            raise AdapterContractError("delta output contains unknown OOD dimensions")
        if ood.dimensions != tuple(axis for axis in _OOD_AXIS_ORDER if axis in ood.dimensions):
            raise AdapterContractError("delta OOD dimensions are not in canonical order")
        if not ood.detected and (ood.dimensions or ood.reason is not None):
            raise AdapterContractError("non-detected OOD cannot contain details")
        if ood.detected and (not ood.dimensions or ood.reason is None):
            raise AdapterContractError("detected OOD requires dimensions and reason")
        if envelope.abstain:
            if envelope.projection_metadata:
                raise AdapterContractError("abstaining delta output cannot contain metadata")
            return envelope
        if envelope.values is None or len(envelope.values) != 5045:
            raise AdapterContractError("delta output must contain exactly 5045 values")
        _finite_vector(envelope.values, "delta_expression")
        expected_keys = {
            "condition_id",
            "evaluation_scope",
            "feature_ids_sha256",
            "feature_records_sha256",
            "n_features",
            "prediction_status",
            "reference",
            "scope_fingerprint",
            "unit",
            "value_semantics",
        }
        if set(envelope.projection_metadata) != expected_keys:
            raise AdapterContractError("delta projection metadata is not exact")
        return envelope

    def validate_envelope(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        del envelope
        raise AdapterContractError("K562 Golden envelopes require an exact prepared input binding")

    def validate_prepared_envelope(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        envelope = self._validate_envelope_structure(envelope)
        if (
            envelope.provenance.input_fingerprints != (prepared.fingerprint(),)
            or envelope.provenance.request_fingerprints != (prepared.request_fingerprint,)
            or envelope.provenance.pack_fingerprints != (prepared.pack_fingerprint,)
            or envelope.provenance.compatibility_fingerprints != (prepared.compatibility_fingerprint,)
        ):
            raise AdapterContractError("delta output provenance does not match prepared input")
        if envelope.abstain:
            return envelope
        model_input = K562GoldenPreparedModelInput.model_validate(prepared.model_input)
        expected = {
            "condition_id": model_input.condition_id,
            "evaluation_scope": model_input.evaluation_scope,
            "feature_ids_sha256": model_input.scope.feature_ids_sha256,
            "feature_records_sha256": model_input.scope.feature_records_sha256,
            "n_features": model_input.scope.feature_count,
            "prediction_status": "success",
            "reference": model_input.scope.reference,
            "scope_fingerprint": model_input.scope_fingerprint,
            "unit": model_input.scope.output_unit,
            "value_semantics": model_input.scope.value_semantics,
        }
        if dict(envelope.projection_metadata) != expected:
            raise AdapterContractError("delta output metadata does not match prepared input")
        return envelope

    def aggregate(self, envelopes: tuple[AdapterOutputEnvelope, ...]) -> AdapterOutputEnvelope:
        del envelopes
        raise AdapterContractError("P16E declares no standalone aggregation policy")

    def project_output(self, envelope: AdapterOutputEnvelope) -> dict[str, Any]:
        del envelope
        raise AdapterContractError("K562 Golden projection requires exact prepared input")

    def project_prepared_output(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> dict[str, Any]:
        envelope = self.validate_prepared_envelope(prepared, envelope)
        if envelope.abstain or envelope.values is None:
            raise AdapterContractError("cannot project an abstaining delta output")
        return self.validate_projection({self.output_contract.output: list(envelope.values)})

    def validate_projection(self, projection: dict[str, Any]) -> dict[str, Any]:
        if type(projection) is not dict:
            raise AdapterContractError("delta projection must be an exact object")
        projection = super().validate_projection(projection)
        if set(projection) != {self.output_contract.output}:
            raise AdapterContractError("delta projection may contain only delta_expression")
        values = _finite_vector(projection[self.output_contract.output], "delta_expression")
        return {self.output_contract.output: list(values)}

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        model_input = K562GoldenPreparedModelInput.model_validate(prepared.model_input)
        if type(raw_output) is not dict or any(not isinstance(key, str) for key in raw_output):
            raise AdapterContractError("wrapper output must be an exact JSON object")
        required = {
            "prediction",
            "prediction_status",
            "scope_fingerprint",
            "uncertainty",
            "ood",
            "abstain",
            "abstain_reasons",
        }
        unknown = set(raw_output).difference(required)
        if unknown:
            raise AdapterContractError(f"unknown wrapper output fields: {sorted(unknown)}")
        missing = required.difference(raw_output)
        if missing:
            raise AdapterContractError(f"wrapper output is missing fields: {sorted(missing)}")
        try:
            scope_fingerprint = _fingerprint(raw_output["scope_fingerprint"], "scope_fingerprint")
        except ValueError as exc:
            raise AdapterContractError("wrapper scope fingerprint is invalid") from exc
        if scope_fingerprint != model_input.scope_fingerprint:
            raise AdapterContractError("wrapper scope fingerprint does not match prepared input")
        status = raw_output["prediction_status"]
        if not isinstance(status, str) or status not in _PREDICTION_STATUSES:
            raise AdapterContractError("unknown prediction status")
        abstain = raw_output["abstain"]
        if not isinstance(abstain, bool):
            raise AdapterContractError("abstain must be a boolean")
        reasons = raw_output["abstain_reasons"]
        if not isinstance(reasons, (list, tuple)):
            raise AdapterContractError("abstain_reasons must be an array")
        try:
            reasons = tuple(_text(item, "abstain_reasons") for item in reasons)
        except ValueError as exc:
            raise AdapterContractError("abstain_reasons are invalid") from exc
        if len(set(reasons)) != len(reasons):
            raise AdapterContractError("abstain_reasons must be unique")

        if type(raw_output["uncertainty"]) is not dict:
            raise AdapterContractError("uncertainty must be an exact object")
        try:
            uncertainty = AdapterUncertainty.model_validate(raw_output["uncertainty"])
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid uncertainty") from exc
        if (
            uncertainty.available
            or uncertainty.calibrated
            or uncertainty.value is not None
            or uncertainty.sigma is not None
            or uncertainty.method != "not_available"
            or uncertainty.reason != "no_calibrated_uncertainty_declared"
        ):
            raise AdapterContractError("delta uncertainty must remain unavailable and uncalibrated")
        if type(raw_output["ood"]) is not dict:
            raise AdapterContractError("OOD status must be an exact object")
        try:
            ood = AdapterOOD.model_validate(raw_output["ood"])
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid OOD status") from exc

        prediction = raw_output["prediction"]
        if status == "unsupported_scope" and not ood.detected:
            raise AdapterContractError("unsupported scope requires detected OOD")
        if status != "success" and not abstain:
            raise AdapterContractError("non-success prediction must abstain")
        if ood.detected and not abstain:
            raise AdapterContractError("OOD output must abstain")
        if abstain:
            if prediction is not None or not reasons:
                raise AdapterContractError("abstention must be value-free and include reasons")
            if status == "success" and not ood.detected:
                raise AdapterContractError("success may abstain only for detected OOD")
            values = None
            shape = None
            metadata: dict[str, Any] = {}
        else:
            if reasons or type(prediction) is not dict:
                raise AdapterContractError("non-abstain output requires exact prediction and no reasons")
            prediction_fields = {
                "delta_expression",
                "feature_ids_sha256",
                "feature_records_sha256",
                "n_features",
                "value_semantics",
                "reference",
                "condition_id",
                "evaluation_scope",
                "unit",
            }
            if set(prediction) != prediction_fields or any(not isinstance(key, str) for key in prediction):
                raise AdapterContractError("prediction fields are not exact")
            values = _finite_vector(prediction["delta_expression"], "delta_expression")
            scope = model_input.scope
            expected_prediction = {
                "feature_ids_sha256": scope.feature_ids_sha256,
                "feature_records_sha256": scope.feature_records_sha256,
                "n_features": scope.feature_count,
                "value_semantics": scope.value_semantics,
                "reference": scope.reference,
                "condition_id": model_input.condition_id,
                "evaluation_scope": model_input.evaluation_scope,
                "unit": scope.output_unit,
            }
            if type(prediction["n_features"]) is not int:
                raise AdapterContractError("prediction n_features must be an exact integer")
            if any(prediction[field] != value for field, value in expected_prediction.items()):
                raise AdapterContractError("prediction feature order, scope, or semantics drift")
            shape = (5045,)
            metadata = {
                **expected_prediction,
                "prediction_status": status,
                "scope_fingerprint": model_input.scope_fingerprint,
            }

        provenance = AdapterExecutionProvenance(
            schema_version="vc.adapter-execution-provenance.v1",
            adapter_fingerprint=self.fingerprint(),
            input_fingerprints=(prepared.fingerprint(),),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            output_contract_fingerprint=self.output_contract.fingerprint(),
            request_fingerprints=(prepared.request_fingerprint,),
            pack_fingerprints=(prepared.pack_fingerprint,),
            compatibility_fingerprints=(prepared.compatibility_fingerprint,),
        )
        envelope = AdapterOutputEnvelope(
            schema_version="vc.adapter-output-envelope.v1",
            task=self.output_contract.task,
            output=self.output_contract.output,
            shape=shape,
            unit=None,
            values=values,
            uncertainty=uncertainty,
            ood=ood,
            abstain=abstain,
            abstain_reasons=reasons,
            projection_metadata=metadata,
            provenance=provenance,
        )
        return self.validate_prepared_envelope(prepared, envelope)
