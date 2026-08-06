"""P15E contract-only S. cerevisiae deletion-to-fitness adapter.

This module validates immutable identities and synthetic wrapper dictionaries.
It deliberately has no asset reader, model runtime, default registration,
scientific evidence, or policy path. Real assets and runs belong to P15R.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.data_packs.feature_alignment import MappingAssetRef
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
_SGD_SYSTEMATIC = re.compile(r"^Y[A-P][LR][0-9]{3}[CW](?:-[A-Z])?$")
_MAX_SAFE_INTEGER = 2**53 - 1
_PREDICTION_STATUSES = frozenset({"success", "target_not_found", "unsupported_scope", "error"})
_OOD_AXIS_ORDER = (
    "strain",
    "assembly",
    "assay",
    "condition",
    "control",
    "platform",
    "gene_namespace",
    "target_universe",
    "target",
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
        raise AdapterContractError(f"{field} must be a finite JSON-safe number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise AdapterContractError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise AdapterContractError(f"{field} must be a finite number")
    return number


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


class _P15Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def to_dict(self) -> dict[str, Any]:
        _reject_undeclared_model_fields(self, type(self).__name__)
        return self.model_dump(mode="json", serialize_as_any=True)

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class YeastDeletionFitnessScope(_P15Contract):
    """Exact model, biological context, and identifier bindings for one run."""

    schema_version: Literal["vc.yeast-deletion-fitness-scope.v1"]
    taxonomy_id: Literal["NCBITaxon:4932"]
    scientific_name: Literal["Saccharomyces cerevisiae"]
    strain_id: Literal["NCBITaxon:559292"]
    strain_name: Literal["Saccharomyces cerevisiae S288C"]
    assembly_name: Literal["R64"]
    assembly_accession: Literal["GCF_000146045.2"]
    model_fingerprint: str
    model_release_fingerprint: str
    model_artifact_fingerprint: str
    environment_fingerprint: str
    adapter_fingerprint: str
    pack_fingerprint: str
    data_binding_fingerprint: str
    compatibility_fingerprint: str
    mapping_asset_fingerprint: str
    execution_binding_fingerprint: str
    condition_id: str
    condition_fingerprint: str
    control_id: str
    control_fingerprint: str
    assay_id: str
    assay_fingerprint: str
    platform_id: str
    platform_fingerprint: str
    fitness_semantics_id: str
    fitness_semantics_fingerprint: str
    target_universe_id: str
    target_universe_fingerprint: str
    inference_configuration_fingerprint: str
    request_gene_namespace: Literal["SGD"]
    request_gene_namespace_version: str
    request_gene_namespace_version_fingerprint: str
    request_gene_id_format: Literal["sgd_systematic"]
    model_gene_namespace: str
    output: Literal["fitness"]
    output_unit: Literal["dimensionless"]
    reference: Literal["matched_non_deletion_control_same_condition_platform"]

    @field_validator(
        "model_fingerprint",
        "model_release_fingerprint",
        "model_artifact_fingerprint",
        "environment_fingerprint",
        "adapter_fingerprint",
        "pack_fingerprint",
        "data_binding_fingerprint",
        "compatibility_fingerprint",
        "mapping_asset_fingerprint",
        "execution_binding_fingerprint",
        "condition_fingerprint",
        "control_fingerprint",
        "assay_fingerprint",
        "platform_fingerprint",
        "fitness_semantics_fingerprint",
        "target_universe_fingerprint",
        "inference_configuration_fingerprint",
        "request_gene_namespace_version_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "condition_id",
        "control_id",
        "assay_id",
        "platform_id",
        "fitness_semantics_id",
        "target_universe_id",
        "request_gene_namespace_version",
        "model_gene_namespace",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)


class YeastFitnessValidationProtocol(_P15Contract):
    """A future P15R protocol binding, never a result or evidence record."""

    schema_version: Literal["vc.yeast-deletion-fitness-validation-protocol.v1"]
    scope_fingerprint: str
    deletion_data_fingerprint: str
    baseline_fingerprint: str
    split_unit: Literal["held_out_biological_group"]
    biological_group_keys: tuple[str, ...]
    baseline: Literal["training_mean_fitness_same_condition"]
    primary_metric: Literal["mean_squared_error_fitness"]
    metric_direction: Literal["lower_is_better"]
    paired_ci_required: Literal[True]
    independent_condition_required: Literal[True]
    independent_platform_required: Literal[True]
    external_adaptation_steps: Literal[0]
    validation_only_tuning: Literal[True]
    stochastic_seeds: tuple[int, ...]
    record_role: Literal["preregistration_not_evidence"]
    ood_axes: tuple[str, ...]

    @field_validator(
        "scope_fingerprint",
        "deletion_data_fingerprint",
        "baseline_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("biological_group_keys", "ood_axes", mode="before")
    @classmethod
    def _text_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be a non-empty array")
        values = tuple(_text(item, info.field_name) for item in value)
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return values

    @field_validator("external_adaptation_steps", mode="before")
    @classmethod
    def _zero_adaptation(cls, value):
        if isinstance(value, bool) or value != 0:
            raise ValueError("external_adaptation_steps must be integer zero")
        return value

    @field_validator("stochastic_seeds", mode="before")
    @classmethod
    def _stochastic_seeds(cls, value):
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ValueError("stochastic_seeds must contain at least three seeds")
        if any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 or seed > _MAX_SAFE_INTEGER
            for seed in value
        ):
            raise ValueError("stochastic_seeds must be non-negative JSON-safe integers")
        seeds = tuple(value)
        if len(set(seeds)) != len(seeds):
            raise ValueError("stochastic_seeds must not contain duplicates")
        return seeds

    @model_validator(mode="after")
    def _complete_ood_scope(self):
        if self.ood_axes != _OOD_AXIS_ORDER:
            raise ValueError(f"ood_axes must equal the canonical exact-scope order: {list(_OOD_AXIS_ORDER)}")
        if self.biological_group_keys != (
            "target_gene_id",
            "condition_id",
            "replicate_group_id",
        ):
            raise ValueError("biological_group_keys must equal the canonical target/condition/replicate order")
        return self


class YeastFitnessDataBinding(_P15Contract):
    """Identity-only binding for the future P15R deletion-screen Pack."""

    schema_version: Literal["vc.yeast-deletion-fitness-data-binding.v1"]
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    data_kind: Literal["deletion_fitness_screen"]
    taxonomy_id: Literal["NCBITaxon:4932"]
    strain_id: Literal["NCBITaxon:559292"]
    assembly_name: Literal["R64"]
    assembly_accession: Literal["GCF_000146045.2"]
    condition_id: str
    condition_fingerprint: str
    control_id: str
    control_fingerprint: str
    assay_id: str
    assay_fingerprint: str
    platform_id: str
    platform_fingerprint: str
    fitness_semantics_id: str
    fitness_semantics_fingerprint: str
    target_universe_id: str
    target_universe_fingerprint: str

    @field_validator(
        "pack_id",
        "pack_version",
        "condition_id",
        "control_id",
        "assay_id",
        "platform_id",
        "fitness_semantics_id",
        "target_universe_id",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "pack_fingerprint",
        "condition_fingerprint",
        "control_fingerprint",
        "assay_fingerprint",
        "platform_fingerprint",
        "fitness_semantics_fingerprint",
        "target_universe_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class YeastFitnessExecutionBinding(_P15Contract):
    """Exact condition, control, assay, platform, and inference identity."""

    schema_version: Literal["vc.yeast-deletion-fitness-execution-binding.v1"]
    condition_id: str
    condition_fingerprint: str
    control_id: str
    control_fingerprint: str
    assay_id: str
    assay_fingerprint: str
    platform_id: str
    platform_fingerprint: str
    fitness_semantics_id: str
    fitness_semantics_fingerprint: str
    target_universe_id: str
    target_universe_fingerprint: str
    runner_id: str
    runner_version: str
    inference_configuration_fingerprint: str

    @field_validator(
        "condition_id",
        "control_id",
        "assay_id",
        "platform_id",
        "fitness_semantics_id",
        "target_universe_id",
        "runner_id",
        "runner_version",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "condition_fingerprint",
        "control_fingerprint",
        "assay_fingerprint",
        "platform_fingerprint",
        "fitness_semantics_fingerprint",
        "target_universe_fingerprint",
        "inference_configuration_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class YeastFitnessGeneMappingBinding(_P15Contract):
    """Exact SGD-systematic mapping identity; no symbol or case guessing."""

    schema_version: Literal["vc.yeast-deletion-fitness-gene-mapping-binding.v1"]
    asset: MappingAssetRef
    source_namespace: Literal["SGD"]
    source_namespace_version: str
    source_namespace_version_fingerprint: str
    source_id_format: Literal["sgd_systematic"]
    target_namespace: str
    target_universe_id: str
    target_universe_fingerprint: str
    exact_mapping_required: Literal[True]

    @field_validator(
        "source_namespace_version",
        "target_namespace",
        "target_universe_id",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "source_namespace_version_fingerprint",
        "target_universe_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class YeastFitnessCompatibilityBinding(_P15Contract):
    """P15E-only negative preflight; it cannot declare executable assets."""

    schema_version: Literal["vc.yeast-deletion-fitness-compatibility-binding.v1"]
    model_release_fingerprint: str
    model_fingerprint: str
    artifact_fingerprint: str
    environment_fingerprint: str
    adapter_fingerprint: str
    pack_fingerprint: str
    data_binding_fingerprint: str
    mapping_asset_fingerprint: str
    execution_binding_fingerprint: str
    assets_verified: Literal[False]
    executable: Literal[False]
    reason: Literal["p15r_not_authorized"]

    @field_validator(
        "model_release_fingerprint",
        "model_fingerprint",
        "artifact_fingerprint",
        "environment_fingerprint",
        "adapter_fingerprint",
        "pack_fingerprint",
        "data_binding_fingerprint",
        "mapping_asset_fingerprint",
        "execution_binding_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class YeastDeletionFitnessAdapterInputContract(AdapterInputContract):
    schema_version: Literal["vc.yeast-deletion-fitness-adapter-input-contract.v1"]
    taxonomy_id: Literal["NCBITaxon:4932"]
    strain_id: Literal["NCBITaxon:559292"]
    assembly_name: Literal["R64"]
    assembly_accession: Literal["GCF_000146045.2"]
    perturbation_kind: Literal["gene"]
    perturbation_semantics: Literal["complete_gene_deletion"]
    target_count: Literal[1]
    gene_namespace: Literal["SGD"]
    gene_id_format: Literal["sgd_systematic"]
    fitness_semantics: Literal["prepared_scope_assay_defined_scalar"]
    reference: Literal["matched_non_deletion_control_same_condition_platform"]
    required_bindings: tuple[str, ...]


class YeastDeletionFitnessAdapterOutputContract(AdapterOutputContract):
    schema_version: Literal["vc.yeast-deletion-fitness-adapter-output-contract.v1"]
    fitness_semantics: Literal["prepared_scope_assay_defined_scalar"]
    reference: Literal["matched_non_deletion_control_same_condition_platform"]


class YeastDeletionFitnessPreparedModelInput(_P15Contract):
    """The complete structured input placed in ``PreparedAdapterInput``."""

    schema_version: Literal["vc.yeast-deletion-fitness-prepared-model-input.v1"]
    request_id: str
    request_fingerprint: str
    scope: YeastDeletionFitnessScope
    scope_fingerprint: str
    validation_protocol: YeastFitnessValidationProtocol
    validation_protocol_fingerprint: str
    execution_binding_fingerprint: str
    target_gene_id: str
    adapter_fingerprint: str
    input_contract_fingerprint: str
    data_binding: YeastFitnessDataBinding
    data_binding_fingerprint: str
    pack_fingerprint: str
    compatibility_fingerprint: str

    @field_validator("request_id", mode="before")
    @classmethod
    def _request_id(cls, value):
        return _text(value, "request_id")

    @field_validator(
        "request_fingerprint",
        "scope_fingerprint",
        "validation_protocol_fingerprint",
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

    @field_validator("target_gene_id", mode="before")
    @classmethod
    def _gene(cls, value):
        value = _text(value, "target_gene_id")
        if not _SGD_SYSTEMATIC.fullmatch(value):
            raise ValueError("target_gene_id must be a canonical SGD systematic ID")
        return value

    @model_validator(mode="after")
    def _scope_bindings(self):
        if self.scope_fingerprint != self.scope.fingerprint():
            raise ValueError("scope fingerprint does not match the embedded scope")
        if (
            self.validation_protocol_fingerprint != self.validation_protocol.fingerprint()
            or self.validation_protocol.scope_fingerprint != self.scope_fingerprint
        ):
            raise ValueError("validation protocol fingerprint does not match the exact scope")
        if self.execution_binding_fingerprint != self.scope.execution_binding_fingerprint:
            raise ValueError("execution binding fingerprint does not match the exact scope")
        if (
            self.data_binding_fingerprint != self.data_binding.fingerprint()
            or self.data_binding_fingerprint != self.scope.data_binding_fingerprint
            or self.data_binding.pack_fingerprint != self.pack_fingerprint
        ):
            raise ValueError("deletion-data binding does not match the exact scope")
        for field in ("adapter_fingerprint", "pack_fingerprint", "compatibility_fingerprint"):
            if getattr(self, field) != getattr(self.scope, field):
                raise ValueError(f"{field} does not match the exact scope")
        return self


class YeastDeletionFitnessAdapter(VirtualCellModelAdapter):
    """Single-output contract adapter; intentionally absent from the default registry."""

    adapter_id = "yeast-s288c-deletion-fitness-contract"
    version = "1.0.0"
    input_contract = YeastDeletionFitnessAdapterInputContract(
        schema_version="vc.yeast-deletion-fitness-adapter-input-contract.v1",
        task="predict_deletion_fitness",
        output="fitness",
        value_type="float",
        shape=(1,),
        unit=None,
        pack_data_required=False,
        alignment_required=False,
        taxonomy_id="NCBITaxon:4932",
        strain_id="NCBITaxon:559292",
        assembly_name="R64",
        assembly_accession="GCF_000146045.2",
        perturbation_kind="gene",
        perturbation_semantics="complete_gene_deletion",
        target_count=1,
        gene_namespace="SGD",
        gene_id_format="sgd_systematic",
        fitness_semantics="prepared_scope_assay_defined_scalar",
        reference="matched_non_deletion_control_same_condition_platform",
        required_bindings=(
            "model_release",
            "model_artifact",
            "environment",
            "adapter",
            "pack",
            "compatibility",
            "mapping_asset",
            "condition",
            "control",
            "assay",
            "platform",
            "fitness_semantics",
            "target_universe",
            "inference_configuration",
            "validation_protocol",
        ),
    )
    output_contract = YeastDeletionFitnessAdapterOutputContract(
        schema_version="vc.yeast-deletion-fitness-adapter-output-contract.v1",
        task="predict_deletion_fitness",
        output="fitness",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        uncertainty_required=True,
        ood_required=True,
        abstain_allowed=True,
        fitness_semantics="prepared_scope_assay_defined_scalar",
        reference="matched_non_deletion_control_same_condition_platform",
    )

    def _validate_request(
        self,
        request: VirtualCellRequestV2,
        scope: YeastDeletionFitnessScope,
        protocol: YeastFitnessValidationProtocol,
    ) -> str:
        outputs = request.task.requested_outputs or (request.output_modality.name,)
        if (
            request.task.task_type != self.input_contract.task
            or tuple(outputs) != (self.input_contract.output,)
            or request.output_modality.name != self.input_contract.output
        ):
            raise AdapterContractError("request task/output does not match the adapter")
        if request.output_modality.unit != scope.output_unit:
            raise AdapterContractError("request output unit does not match the exact scope")
        if (
            request.output_modality.ontology_id != "PRAXISOUTPUT:fitness"
            or request.output_modality.feature_namespace is not None
        ):
            raise AdapterContractError("request output modality does not match fitness")
        if request.species.taxonomy_id != scope.taxonomy_id:
            raise AdapterContractError("request taxonomy does not match the exact scope")
        if request.species.scientific_name != scope.scientific_name or request.species.common_name != "yeast":
            raise AdapterContractError("request species does not match the exact scope")
        if request.cell_context.cell_type_name != scope.strain_name:
            raise AdapterContractError("request strain does not match the exact scope")
        if any(
            value is not None
            for value in (
                request.cell_context.cell_type_id,
                request.cell_context.tissue_name,
                request.cell_context.tissue_id,
            )
        ):
            raise AdapterContractError("request cell context contains unsupported scope fields")
        expected_attributes = {
            "strain_id": scope.strain_id,
            "assembly_name": scope.assembly_name,
            "assembly_accession": scope.assembly_accession,
            "gene_namespace_version": scope.request_gene_namespace_version,
            "gene_namespace_version_fingerprint": (scope.request_gene_namespace_version_fingerprint),
            "condition_id": scope.condition_id,
            "condition_fingerprint": scope.condition_fingerprint,
            "control_id": scope.control_id,
            "control_fingerprint": scope.control_fingerprint,
            "assay_id": scope.assay_id,
            "assay_fingerprint": scope.assay_fingerprint,
            "platform_id": scope.platform_id,
            "platform_fingerprint": scope.platform_fingerprint,
            "fitness_semantics_id": scope.fitness_semantics_id,
            "fitness_semantics_fingerprint": scope.fitness_semantics_fingerprint,
            "target_universe_id": scope.target_universe_id,
            "target_universe_fingerprint": scope.target_universe_fingerprint,
        }
        if dict(request.cell_context.attributes) != expected_attributes:
            raise AdapterContractError("request scope attributes do not match the exact scope")
        if (
            request.input_modality.name != "deletion_screen"
            or request.input_modality.ontology_id != "PRAXISASSAY:deletion_screen"
            or request.input_modality.unit is not None
        ):
            raise AdapterContractError("request input modality must be the exact deletion screen")
        if request.input_modality.feature_namespace != scope.request_gene_namespace:
            raise AdapterContractError("request gene namespace does not match the exact scope")
        if (
            request.perturbation.kind != "gene"
            or len(request.perturbation.targets) != 1
            or request.perturbation.dose_value is not None
            or request.perturbation.dose_unit is not None
            or request.perturbation.timepoint is not None
        ):
            raise AdapterContractError("request must contain one exact complete gene deletion")
        target = request.perturbation.targets[0]
        if not _SGD_SYSTEMATIC.fullmatch(target):
            raise AdapterContractError("deletion target must be a canonical SGD systematic ID")
        expected_baseline = {
            "reference": scope.reference,
            "control_id": scope.control_id,
            "control_fingerprint": scope.control_fingerprint,
            "scope_fingerprint": scope.fingerprint(),
        }
        if request.baseline_context is None or dict(request.baseline_context) != expected_baseline:
            raise AdapterContractError("request baseline does not match the matched non-deletion reference")
        expected_constraints = {
            "perturbation_semantics": self.input_contract.perturbation_semantics,
            "scope_fingerprint": scope.fingerprint(),
            "validation_protocol_fingerprint": protocol.fingerprint(),
        }
        if dict(request.constraints) != expected_constraints:
            raise AdapterContractError("request scope/protocol constraints do not match exact bindings")
        if request.metadata:
            raise AdapterContractError("request metadata contains undeclared fields")
        return target

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        scope: YeastDeletionFitnessScope,
        model_artifact: ArtifactIdentity,
        environment: EnvironmentIdentity,
        model_release: ModelReleaseRecord,
        mapping_asset: YeastFitnessGeneMappingBinding,
        execution_binding: YeastFitnessExecutionBinding,
        validation_protocol: YeastFitnessValidationProtocol,
        pack: YeastFitnessDataBinding,
        compatibility_report: YeastFitnessCompatibilityBinding,
    ) -> PreparedAdapterInput:
        request = _revalidate_contract(request, VirtualCellRequestV2, "request")
        scope = _revalidate_contract(scope, YeastDeletionFitnessScope, "scope binding")
        model_artifact = _revalidate_contract(model_artifact, ArtifactIdentity, "model artifact binding")
        environment = _revalidate_contract(environment, EnvironmentIdentity, "environment binding")
        model_release = _revalidate_contract(model_release, ModelReleaseRecord, "model release binding")
        mapping_asset = _revalidate_contract(mapping_asset, YeastFitnessGeneMappingBinding, "mapping binding")
        execution_binding = _revalidate_contract(execution_binding, YeastFitnessExecutionBinding, "execution binding")
        validation_protocol = _revalidate_contract(
            validation_protocol, YeastFitnessValidationProtocol, "protocol binding"
        )
        pack = _revalidate_contract(pack, YeastFitnessDataBinding, "Pack binding")
        compatibility_report = _revalidate_contract(
            compatibility_report,
            YeastFitnessCompatibilityBinding,
            "compatibility binding",
        )

        pack_fingerprint = pack.pack_fingerprint
        compatibility_fingerprint = compatibility_report.fingerprint()
        if scope.adapter_fingerprint != self.fingerprint():
            raise AdapterContractError("scope adapter fingerprint does not match this adapter")
        if (
            model_artifact.fingerprint() != scope.model_artifact_fingerprint
            or model_artifact.model_fingerprint != scope.model_fingerprint
            or model_artifact.legacy_incomplete
        ):
            raise AdapterContractError("model artifact identity does not match the exact scope")
        if model_artifact.safe_load_policy != "data_only":
            raise AdapterContractError("model artifact safe_load_policy must be data_only")
        if model_artifact.media_type != "application/json":
            raise AdapterContractError("model artifact media_type must be application/json")
        if environment.fingerprint() != scope.environment_fingerprint or environment.legacy_incomplete:
            raise AdapterContractError("environment identity does not match the exact scope")
        if self.fingerprint() not in environment.adapter_fingerprints:
            raise AdapterContractError("environment does not bind this adapter fingerprint")
        if mapping_asset.fingerprint() != scope.mapping_asset_fingerprint:
            raise AdapterContractError("mapping asset identity does not match the exact scope")
        if mapping_asset.target_namespace != scope.model_gene_namespace:
            raise AdapterContractError("mapping target namespace does not match the exact scope")
        if (
            mapping_asset.source_namespace_version != scope.request_gene_namespace_version
            or mapping_asset.source_namespace_version_fingerprint != scope.request_gene_namespace_version_fingerprint
            or mapping_asset.target_universe_id != scope.target_universe_id
            or mapping_asset.target_universe_fingerprint != scope.target_universe_fingerprint
        ):
            raise AdapterContractError("mapping namespace/universe does not match the exact scope")
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
            raise AdapterContractError("model release identity does not match the exact P15E scope")
        if execution_binding.fingerprint() != scope.execution_binding_fingerprint:
            raise AdapterContractError("execution binding fingerprint does not match the exact scope")
        execution_fields = (
            "condition_id",
            "condition_fingerprint",
            "control_id",
            "control_fingerprint",
            "assay_id",
            "assay_fingerprint",
            "platform_id",
            "platform_fingerprint",
            "fitness_semantics_id",
            "fitness_semantics_fingerprint",
            "target_universe_id",
            "target_universe_fingerprint",
            "inference_configuration_fingerprint",
        )
        if any(getattr(execution_binding, field) != getattr(scope, field) for field in execution_fields):
            raise AdapterContractError("condition/control/assay/platform/fitness execution binding drift")
        if (
            pack.taxonomy_id != scope.taxonomy_id
            or pack.strain_id != scope.strain_id
            or pack.assembly_name != scope.assembly_name
            or pack.assembly_accession != scope.assembly_accession
        ):
            raise AdapterContractError("deletion-fitness Pack scope does not match the exact scope")
        data_fields = (
            "condition_id",
            "condition_fingerprint",
            "control_id",
            "control_fingerprint",
            "assay_id",
            "assay_fingerprint",
            "platform_id",
            "platform_fingerprint",
            "fitness_semantics_id",
            "fitness_semantics_fingerprint",
            "target_universe_id",
            "target_universe_fingerprint",
        )
        if any(getattr(pack, field) != getattr(scope, field) for field in data_fields):
            raise AdapterContractError("deletion-fitness data binding drift")
        if pack_fingerprint != scope.pack_fingerprint:
            raise AdapterContractError("Pack fingerprint does not match the exact scope")
        if pack.fingerprint() != scope.data_binding_fingerprint:
            raise AdapterContractError("deletion-data binding fingerprint does not match the exact scope")
        if compatibility_fingerprint != scope.compatibility_fingerprint:
            raise AdapterContractError("compatibility fingerprint does not match the exact scope")
        expected_compatibility = {
            "model_release_fingerprint": scope.model_release_fingerprint,
            "model_fingerprint": scope.model_fingerprint,
            "artifact_fingerprint": scope.model_artifact_fingerprint,
            "environment_fingerprint": scope.environment_fingerprint,
            "adapter_fingerprint": self.fingerprint(),
            "pack_fingerprint": scope.pack_fingerprint,
            "data_binding_fingerprint": scope.data_binding_fingerprint,
            "mapping_asset_fingerprint": scope.mapping_asset_fingerprint,
            "execution_binding_fingerprint": scope.execution_binding_fingerprint,
        }
        if any(getattr(compatibility_report, field) != value for field, value in expected_compatibility.items()):
            raise AdapterContractError("compatibility identity does not match the exact scope")
        if (
            validation_protocol.scope_fingerprint != scope.fingerprint()
            or validation_protocol.baseline != "training_mean_fitness_same_condition"
        ):
            raise AdapterContractError("validation protocol does not match the exact scope")
        if validation_protocol.deletion_data_fingerprint != pack_fingerprint:
            raise AdapterContractError("validation protocol deletion-data Pack fingerprint drift")

        target = self._validate_request(request, scope, validation_protocol)
        request_fingerprint = _canonical_fingerprint(request.to_dict())
        model_input = YeastDeletionFitnessPreparedModelInput(
            schema_version="vc.yeast-deletion-fitness-prepared-model-input.v1",
            request_id=request.request_id,
            request_fingerprint=request_fingerprint,
            scope=scope,
            scope_fingerprint=scope.fingerprint(),
            validation_protocol=validation_protocol,
            validation_protocol_fingerprint=validation_protocol.fingerprint(),
            execution_binding_fingerprint=execution_binding.fingerprint(),
            target_gene_id=target,
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            data_binding=pack,
            data_binding_fingerprint=pack.fingerprint(),
            pack_fingerprint=pack_fingerprint,
            compatibility_fingerprint=compatibility_fingerprint,
        )
        prepared = PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=request_fingerprint,
            pack_fingerprint=pack_fingerprint,
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
            model_input = YeastDeletionFitnessPreparedModelInput.model_validate(prepared.model_input)
        except ValidationError as exc:
            raise AdapterContractError("prepared yeast fitness input is invalid") from exc
        if model_input.request_fingerprint != prepared.request_fingerprint:
            raise AdapterContractError("prepared request fingerprint does not match model input")
        if (
            model_input.adapter_fingerprint != self.fingerprint()
            or model_input.input_contract_fingerprint != self.input_contract.fingerprint()
        ):
            raise AdapterContractError("prepared adapter contract fingerprint drift")
        if (
            model_input.pack_fingerprint != prepared.pack_fingerprint
            or model_input.compatibility_fingerprint != prepared.compatibility_fingerprint
        ):
            raise AdapterContractError("prepared Pack/compatibility binding drift")
        return prepared

    def _validate_envelope_structure(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        envelope = VirtualCellModelAdapter.validate_envelope(self, envelope)
        try:
            _reject_undeclared_model_fields(envelope.uncertainty, "fitness output uncertainty")
            uncertainty = AdapterUncertainty.model_validate(
                envelope.uncertainty.model_dump(mode="python", serialize_as_any=True)
            )
            _reject_model_type_drift(envelope.uncertainty, uncertainty, "fitness output uncertainty")
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid fitness output uncertainty") from exc
        try:
            _reject_undeclared_model_fields(envelope.ood, "fitness output OOD status")
            ood = AdapterOOD.model_validate(envelope.ood.model_dump(mode="python", serialize_as_any=True))
            _reject_model_type_drift(envelope.ood, ood, "fitness output OOD status")
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid fitness output OOD status") from exc
        try:
            _reject_undeclared_model_fields(envelope.provenance, "fitness output provenance")
            provenance = AdapterExecutionProvenance.model_validate(
                envelope.provenance.model_dump(mode="python", serialize_as_any=True)
            )
            _reject_model_type_drift(envelope.provenance, provenance, "fitness output provenance")
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid fitness output provenance") from exc
        envelope = envelope.model_copy(update={"uncertainty": uncertainty, "ood": ood, "provenance": provenance})
        if (
            uncertainty.available
            or uncertainty.calibrated
            or uncertainty.value is not None
            or uncertainty.sigma is not None
            or uncertainty.method != "not_available"
            or uncertainty.reason != "no_calibrated_uncertainty_declared"
        ):
            raise AdapterContractError("fitness uncertainty must remain unavailable and uncalibrated")
        if set(ood.dimensions).difference(_OOD_AXES):
            raise AdapterContractError("fitness output contains unknown OOD dimensions")
        if ood.dimensions != tuple(axis for axis in _OOD_AXIS_ORDER if axis in ood.dimensions):
            raise AdapterContractError("fitness OOD dimensions are not in canonical order")
        if not ood.detected and (ood.dimensions or ood.reason is not None):
            raise AdapterContractError("non-detected OOD must not contain dimensions or reason")
        if ood.detected and (not ood.dimensions or ood.reason is None):
            raise AdapterContractError("detected OOD must identify a dimension and reason")
        if envelope.abstain:
            if envelope.projection_metadata:
                raise AdapterContractError("abstaining fitness output cannot contain projection metadata")
            return envelope
        if envelope.values is None or len(envelope.values) != 1:
            raise AdapterContractError("fitness output must contain one value")
        _finite_number(envelope.values[0], "fitness")
        expected_keys = {
            "fitness_semantics_id",
            "prediction_status",
            "reference",
            "scope_fingerprint",
            "unit",
        }
        if set(envelope.projection_metadata) != expected_keys:
            raise AdapterContractError("fitness output projection metadata is not exact")
        if (
            envelope.projection_metadata["reference"] != self.output_contract.reference
            or envelope.projection_metadata["prediction_status"] != "success"
            or envelope.projection_metadata["unit"] != self.output_contract.unit
        ):
            raise AdapterContractError("fitness output projection metadata has contract drift")
        try:
            _fingerprint(
                envelope.projection_metadata["scope_fingerprint"],
                "scope_fingerprint",
            )
            _text(
                envelope.projection_metadata["fitness_semantics_id"],
                "fitness_semantics_id",
            )
        except ValueError as exc:
            raise AdapterContractError("fitness output projection metadata is invalid") from exc
        return envelope

    def validate_envelope(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        del envelope
        raise AdapterContractError("yeast fitness envelopes require an exact prepared input binding")

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
            raise AdapterContractError("adapter output provenance does not match prepared input")
        if envelope.abstain:
            return envelope
        model_input = YeastDeletionFitnessPreparedModelInput.model_validate(prepared.model_input)
        metadata = envelope.projection_metadata
        if (
            metadata["scope_fingerprint"] != model_input.scope_fingerprint
            or metadata["fitness_semantics_id"] != model_input.scope.fitness_semantics_id
            or metadata["reference"] != model_input.scope.reference
            or metadata["unit"] != model_input.scope.output_unit
        ):
            raise AdapterContractError("fitness output scope metadata does not match prepared input")
        return envelope

    def aggregate(self, envelopes: tuple[AdapterOutputEnvelope, ...]) -> AdapterOutputEnvelope:
        del envelopes
        raise AdapterContractError("P15E yeast fitness declares no standalone aggregation policy")

    def project_output(self, envelope: AdapterOutputEnvelope) -> dict[str, Any]:
        del envelope
        raise AdapterContractError("yeast fitness projection requires an exact prepared input binding")

    def project_prepared_output(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> dict[str, Any]:
        envelope = self.validate_prepared_envelope(prepared, envelope)
        if envelope.abstain or envelope.values is None:
            raise AdapterContractError("cannot project an abstaining fitness output")
        return self.validate_projection({self.output_contract.output: list(envelope.values)})

    def validate_projection(self, projection: dict[str, Any]) -> dict[str, Any]:
        if type(projection) is not dict:
            raise AdapterContractError("fitness projection must be an exact object")
        projection = super().validate_projection(projection)
        if set(projection) != {self.output_contract.output}:
            raise AdapterContractError("fitness projection may contain only fitness")
        values = projection[self.output_contract.output]
        if not isinstance(values, (list, tuple)) or len(values) != 1:
            raise AdapterContractError("fitness projection must contain one value")
        fitness = _finite_number(values[0], "fitness")
        return {self.output_contract.output: [fitness]}

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        model_input = YeastDeletionFitnessPreparedModelInput.model_validate(prepared.model_input)
        if type(raw_output) is not dict:
            raise AdapterContractError("wrapper output must be an exact JSON object")
        if any(not isinstance(key, str) for key in raw_output):
            raise AdapterContractError("wrapper output keys must be strings")
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
            raise AdapterContractError("abstain_reasons must not contain duplicates")

        if type(raw_output["uncertainty"]) is not dict:
            raise AdapterContractError("uncertainty must be an exact JSON object")
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
            raise AdapterContractError("fitness uncertainty must remain unavailable and uncalibrated")
        if type(raw_output["ood"]) is not dict:
            raise AdapterContractError("OOD status must be an exact JSON object")
        try:
            ood = AdapterOOD.model_validate(raw_output["ood"])
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid OOD status") from exc

        prediction = raw_output["prediction"]
        if status == "unsupported_scope" and not ood.detected:
            raise AdapterContractError("unsupported scope status requires detected OOD")
        if status != "success" and not abstain:
            raise AdapterContractError("non-success prediction status must abstain")
        if ood.detected and not abstain:
            raise AdapterContractError("OOD output must abstain")
        if abstain:
            if prediction is not None:
                raise AdapterContractError("abstain output must not contain prediction values")
            if not reasons:
                raise AdapterContractError("abstain output requires reasons")
            if status == "success" and not ood.detected:
                raise AdapterContractError("success status may abstain only for detected OOD")
            values = None
            shape = None
            metadata: dict[str, Any] = {}
        else:
            if reasons:
                raise AdapterContractError("non-abstain output cannot contain abstain reasons")
            if type(prediction) is not dict:
                raise AdapterContractError("non-abstain output requires an exact prediction object")
            if any(not isinstance(key, str) for key in prediction):
                raise AdapterContractError("prediction keys must be strings")
            prediction_fields = {
                "fitness",
                "fitness_semantics_id",
                "reference",
                "unit",
            }
            unknown_prediction = set(prediction).difference(prediction_fields)
            if unknown_prediction:
                raise AdapterContractError(f"unknown prediction fields: {sorted(unknown_prediction)}")
            missing_prediction = prediction_fields.difference(prediction)
            if missing_prediction:
                raise AdapterContractError(f"prediction is missing fields: {sorted(missing_prediction)}")
            fitness = _finite_number(prediction["fitness"], "fitness")
            if (
                prediction["fitness_semantics_id"] != model_input.scope.fitness_semantics_id
                or prediction["reference"] != model_input.scope.reference
                or prediction["unit"] != model_input.scope.output_unit
            ):
                raise AdapterContractError("prediction semantics do not match the exact scope")
            values = (fitness,)
            shape = (1,)
            metadata = {
                "fitness_semantics_id": model_input.scope.fitness_semantics_id,
                "prediction_status": status,
                "reference": model_input.scope.reference,
                "scope_fingerprint": model_input.scope_fingerprint,
                "unit": model_input.scope.output_unit,
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
            unit=self.output_contract.unit,
            values=values,
            uncertainty=uncertainty,
            ood=ood,
            abstain=abstain,
            abstain_reasons=reasons,
            projection_metadata=metadata,
            provenance=provenance,
        )
        return self.validate_prepared_envelope(prepared, envelope)
