"""P14E contract-only E. coli K-12 knockout-to-growth adapter.

This module validates immutable identities and synthetic wrapper dictionaries.
It deliberately has no GEM loader, solver, asset reader, default registration,
scientific evidence, or policy path.  Real assets and runs belong to P14R.
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
)
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelReleaseRecord,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NCBI_GENE = re.compile(r"^NCBIGene:[1-9][0-9]*$")
_MAX_SAFE_INTEGER = 2**53 - 1
_SOLVER_STATUSES = frozenset({"optimal", "infeasible", "unbounded", "target_not_found", "error"})
_OOD_AXIS_ORDER = (
    "strain",
    "assembly",
    "gem",
    "medium",
    "condition",
    "gene_namespace",
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


def _reject_undeclared_model_fields(value: Any, path: str) -> None:
    if isinstance(value, BaseModel):
        declared = type(value).model_fields
        unexpected = set(value.__dict__).difference(declared)
        pydantic_extra = getattr(value, "__pydantic_extra__", None)
        if pydantic_extra:
            unexpected.update(pydantic_extra)
        if unexpected:
            raise ValueError(
                f"{path} contains undeclared fields: {sorted(unexpected)}"
            )
        for name in declared:
            _reject_undeclared_model_fields(getattr(value, name), f"{path}.{name}")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_undeclared_model_fields(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            _reject_undeclared_model_fields(item, f"{path}[{index}]")


def _revalidate_contract(value: Any, expected_type, field: str):
    if not isinstance(value, expected_type):
        raise TypeError(f"{field} must be {expected_type.__name__}")
    try:
        _reject_undeclared_model_fields(value, field)
        normalized = expected_type.model_validate(
            value.model_dump(mode="python", serialize_as_any=True)
        )
        _reject_model_type_drift(value, normalized, field)
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise AdapterContractError(f"invalid {field}") from exc


class _P14Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", serialize_as_any=True)

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self)


class EcoliGrowthScope(_P14Contract):
    """Exact model, biological context, and identifier bindings for one run."""

    schema_version: Literal["vc.ecoli-growth-scope.v1"]
    taxonomy_id: Literal["NCBITaxon:562"]
    scientific_name: Literal["Escherichia coli"]
    strain_id: Literal["NCBITaxon:511145"]
    strain_name: Literal["Escherichia coli K-12 MG1655"]
    assembly_accession: Literal["GCF_000005845.2"]
    gem_model_fingerprint: str
    model_release_fingerprint: str
    gem_artifact_fingerprint: str
    environment_fingerprint: str
    adapter_fingerprint: str
    pack_fingerprint: str
    data_binding_fingerprint: str
    compatibility_fingerprint: str
    mapping_asset_fingerprint: str
    execution_binding_fingerprint: str
    medium_id: str
    medium_fingerprint: str
    condition_id: str
    condition_fingerprint: str
    objective_id: str
    objective_fingerprint: str
    objective_unit: str
    solver_configuration_fingerprint: str
    request_gene_namespace: Literal["NCBIGene"]
    request_gene_namespace_version: Literal["GCF_000005845.2"]
    request_gene_id_format: Literal["ncbi_gene_curie"]
    gem_gene_namespace: str
    output: Literal["growth_ratio"]
    output_unit: Literal["dimensionless"]
    reference: Literal["wild_type_same_gem_medium_condition"]

    @field_validator(
        "gem_model_fingerprint",
        "model_release_fingerprint",
        "gem_artifact_fingerprint",
        "environment_fingerprint",
        "adapter_fingerprint",
        "pack_fingerprint",
        "data_binding_fingerprint",
        "compatibility_fingerprint",
        "mapping_asset_fingerprint",
        "execution_binding_fingerprint",
        "medium_fingerprint",
        "condition_fingerprint",
        "objective_fingerprint",
        "solver_configuration_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "medium_id",
        "condition_id",
        "objective_id",
        "objective_unit",
        "gem_gene_namespace",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

class EcoliGrowthValidationProtocol(_P14Contract):
    """A future P14R protocol binding, never a result or evidence record."""

    schema_version: Literal["vc.ecoli-growth-validation-protocol.v1"]
    scope_fingerprint: str
    condition_data_fingerprint: str
    baseline_fingerprint: str
    split_unit: Literal["held_out_gene"]
    biological_group_keys: tuple[str, ...]
    baseline: Literal["wild_type_same_gem_medium_condition"]
    primary_metric: Literal["mean_absolute_error_growth_ratio"]
    metric_direction: Literal["lower_is_better"]
    paired_ci_required: Literal[True]
    independent_cohort_required: Literal[True]
    external_adaptation_steps: Literal[0]
    ood_axes: tuple[str, ...]

    @field_validator(
        "scope_fingerprint",
        "condition_data_fingerprint",
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

    @model_validator(mode="after")
    def _complete_ood_scope(self):
        if self.ood_axes != _OOD_AXIS_ORDER:
            raise ValueError(
                "ood_axes must equal the canonical exact-scope order: "
                f"{list(_OOD_AXIS_ORDER)}"
            )
        if self.biological_group_keys != ("target_gene_id", "condition_id"):
            raise ValueError(
                "biological_group_keys must equal the canonical target/condition order"
            )
        return self


class EcoliGrowthDataBinding(_P14Contract):
    """Identity-only binding for the future P14R condition/growth Pack."""

    schema_version: Literal["vc.ecoli-growth-data-binding.v1"]
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    data_kind: Literal["growth_condition"]
    taxonomy_id: Literal["NCBITaxon:562"]
    strain_id: Literal["NCBITaxon:511145"]
    assembly_accession: Literal["GCF_000005845.2"]

    @field_validator("pack_id", "pack_version", mode="before")
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("pack_fingerprint", mode="before")
    @classmethod
    def _pack_fingerprint(cls, value):
        return _fingerprint(value, "pack_fingerprint")


class EcoliGrowthExecutionBinding(_P14Contract):
    """Exact medium, condition, objective, and deterministic solver identity."""

    schema_version: Literal["vc.ecoli-growth-execution-binding.v1"]
    medium_id: str
    medium_fingerprint: str
    condition_id: str
    condition_fingerprint: str
    objective_id: str
    objective_fingerprint: str
    objective_unit: str
    solver_id: str
    solver_version: str
    solver_configuration_fingerprint: str
    deterministic: Literal[True]

    @field_validator(
        "medium_id",
        "condition_id",
        "objective_id",
        "objective_unit",
        "solver_id",
        "solver_version",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "medium_fingerprint",
        "condition_fingerprint",
        "objective_fingerprint",
        "solver_configuration_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class EcoliGrowthGeneMappingBinding(_P14Contract):
    """Exact NCBIGene-to-GEM mapping identity; no symbol or case guessing."""

    schema_version: Literal["vc.ecoli-growth-gene-mapping-binding.v1"]
    asset: MappingAssetRef
    source_namespace: Literal["NCBIGene"]
    source_namespace_version: Literal["GCF_000005845.2"]
    source_id_format: Literal["ncbi_gene_curie"]
    target_namespace: str
    exact_mapping_required: Literal[True]

    @field_validator("target_namespace", mode="before")
    @classmethod
    def _target_namespace(cls, value):
        return _text(value, "target_namespace")


class EcoliGrowthCompatibilityBinding(_P14Contract):
    """P14E-only negative preflight; it cannot declare executable assets."""

    schema_version: Literal["vc.ecoli-growth-compatibility-binding.v1"]
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
    reason: Literal["p14r_not_authorized"]

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


class EcoliGrowthAdapterInputContract(AdapterInputContract):
    schema_version: Literal["vc.ecoli-growth-adapter-input-contract.v1"]
    taxonomy_id: Literal["NCBITaxon:562"]
    perturbation_kind: Literal["gene"]
    target_count: Literal[1]
    gene_namespace: Literal["NCBIGene"]
    gene_id_format: Literal["ncbi_gene_curie"]
    reference: Literal["wild_type_same_gem_medium_condition"]
    required_bindings: tuple[str, ...]


class EcoliGrowthAdapterOutputContract(AdapterOutputContract):
    schema_version: Literal["vc.ecoli-growth-adapter-output-contract.v1"]
    reference: Literal["wild_type_same_gem_medium_condition"]
    minimum_value: Literal[0.0]
    trace_only: tuple[Literal["flux"], ...]


class EcoliK12KnockoutGrowthInput(_P14Contract):
    """The complete structured input placed in ``PreparedAdapterInput``."""

    schema_version: Literal["vc.ecoli-growth-prepared-model-input.v1"]
    request_id: str
    request_fingerprint: str
    scope: EcoliGrowthScope
    scope_fingerprint: str
    validation_protocol: EcoliGrowthValidationProtocol
    validation_protocol_fingerprint: str
    execution_binding_fingerprint: str
    target_gene_id: str
    adapter_fingerprint: str
    input_contract_fingerprint: str
    data_binding: EcoliGrowthDataBinding
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
        if not _NCBI_GENE.fullmatch(value):
            raise ValueError("target_gene_id must be a canonical NCBIGene CURIE")
        return value

    @model_validator(mode="after")
    def _scope_bindings(self):
        if self.scope_fingerprint != self.scope.fingerprint():
            raise ValueError("scope fingerprint does not match the embedded scope")
        if (
            self.validation_protocol_fingerprint
            != self.validation_protocol.fingerprint()
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
            raise ValueError("growth-data binding does not match the exact scope")
        for field in ("adapter_fingerprint", "pack_fingerprint", "compatibility_fingerprint"):
            if getattr(self, field) != getattr(self.scope, field):
                raise ValueError(f"{field} does not match the exact scope")
        return self


class EcoliK12KnockoutGrowthAdapter(VirtualCellModelAdapter):
    """Single-output contract adapter; intentionally absent from the default registry."""

    adapter_id = "ecoli-k12-knockout-growth-contract"
    version = "1.0.0"
    input_contract = EcoliGrowthAdapterInputContract(
        schema_version="vc.ecoli-growth-adapter-input-contract.v1",
        task="predict_knockout_growth",
        output="growth_ratio",
        value_type="float",
        shape=(1,),
        unit=None,
        pack_data_required=False,
        alignment_required=False,
        taxonomy_id="NCBITaxon:562",
        perturbation_kind="gene",
        target_count=1,
        gene_namespace="NCBIGene",
        gene_id_format="ncbi_gene_curie",
        reference="wild_type_same_gem_medium_condition",
        required_bindings=(
            "model_release",
            "gem_artifact",
            "environment",
            "adapter",
            "pack",
            "compatibility",
            "mapping_asset",
            "medium",
            "condition",
            "objective",
            "solver_configuration",
            "validation_protocol",
        ),
    )
    output_contract = EcoliGrowthAdapterOutputContract(
        schema_version="vc.ecoli-growth-adapter-output-contract.v1",
        task="predict_knockout_growth",
        output="growth_ratio",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        uncertainty_required=True,
        ood_required=True,
        abstain_allowed=True,
        reference="wild_type_same_gem_medium_condition",
        minimum_value=0.0,
        trace_only=("flux",),
    )

    def _validate_request(
        self,
        request: VirtualCellRequestV2,
        scope: EcoliGrowthScope,
        protocol: EcoliGrowthValidationProtocol,
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
            request.output_modality.ontology_id != "PRAXISOUTPUT:growth_ratio"
            or request.output_modality.feature_namespace is not None
        ):
            raise AdapterContractError("request output modality does not match growth_ratio")
        if request.species.taxonomy_id != scope.taxonomy_id:
            raise AdapterContractError("request taxonomy does not match the exact scope")
        if (
            request.species.scientific_name != scope.scientific_name
            or request.species.common_name != "E. coli"
        ):
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
            "assembly_accession": scope.assembly_accession,
            "medium_id": scope.medium_id,
            "medium_fingerprint": scope.medium_fingerprint,
            "condition_id": scope.condition_id,
            "condition_fingerprint": scope.condition_fingerprint,
        }
        if dict(request.cell_context.attributes) != expected_attributes:
            raise AdapterContractError("request scope attributes do not match the exact scope")
        if (
            request.input_modality.name != "GEM"
            or request.input_modality.ontology_id != "PRAXISMODALITY:FBA"
            or request.input_modality.unit is not None
        ):
            raise AdapterContractError("request input modality must be exact GEM/FBA")
        if request.input_modality.feature_namespace != scope.request_gene_namespace:
            raise AdapterContractError("request gene namespace does not match the exact scope")
        if (
            request.perturbation.kind != "gene"
            or len(request.perturbation.targets) != 1
            or request.perturbation.dose_value is not None
            or request.perturbation.dose_unit is not None
            or request.perturbation.timepoint is not None
        ):
            raise AdapterContractError("request must contain one exact single gene knockout")
        target = request.perturbation.targets[0]
        if not _NCBI_GENE.fullmatch(target):
            raise AdapterContractError("knockout target must be a canonical NCBIGene CURIE")
        expected_baseline = {
            "reference": scope.reference,
            "scope_fingerprint": scope.fingerprint(),
        }
        if request.baseline_context is None or dict(request.baseline_context) != expected_baseline:
            raise AdapterContractError("request baseline does not match the exact wild-type reference")
        expected_constraints = {
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
        scope: EcoliGrowthScope,
        gem_artifact: ArtifactIdentity,
        environment: EnvironmentIdentity,
        model_release: ModelReleaseRecord,
        mapping_asset: EcoliGrowthGeneMappingBinding,
        execution_binding: EcoliGrowthExecutionBinding,
        validation_protocol: EcoliGrowthValidationProtocol,
        pack: EcoliGrowthDataBinding,
        compatibility_report: EcoliGrowthCompatibilityBinding,
    ) -> PreparedAdapterInput:
        request = _revalidate_contract(request, VirtualCellRequestV2, "request")
        scope = _revalidate_contract(scope, EcoliGrowthScope, "scope binding")
        gem_artifact = _revalidate_contract(
            gem_artifact, ArtifactIdentity, "GEM artifact binding"
        )
        environment = _revalidate_contract(
            environment, EnvironmentIdentity, "environment binding"
        )
        model_release = _revalidate_contract(
            model_release, ModelReleaseRecord, "model release binding"
        )
        mapping_asset = _revalidate_contract(
            mapping_asset, EcoliGrowthGeneMappingBinding, "mapping binding"
        )
        execution_binding = _revalidate_contract(
            execution_binding, EcoliGrowthExecutionBinding, "execution binding"
        )
        validation_protocol = _revalidate_contract(
            validation_protocol, EcoliGrowthValidationProtocol, "protocol binding"
        )
        pack = _revalidate_contract(pack, EcoliGrowthDataBinding, "Pack binding")
        compatibility_report = _revalidate_contract(
            compatibility_report,
            EcoliGrowthCompatibilityBinding,
            "compatibility binding",
        )

        pack_fingerprint = pack.pack_fingerprint
        compatibility_fingerprint = compatibility_report.fingerprint()
        if scope.adapter_fingerprint != self.fingerprint():
            raise AdapterContractError("scope adapter fingerprint does not match this adapter")
        if (
            gem_artifact.fingerprint() != scope.gem_artifact_fingerprint
            or gem_artifact.model_fingerprint != scope.gem_model_fingerprint
            or gem_artifact.legacy_incomplete
        ):
            raise AdapterContractError("GEM artifact identity does not match the exact scope")
        if gem_artifact.safe_load_policy != "data_only":
            raise AdapterContractError("GEM artifact safe_load_policy must be data_only")
        if gem_artifact.media_type != "application/sbml+xml":
            raise AdapterContractError("GEM artifact media_type must be application/sbml+xml")
        if environment.fingerprint() != scope.environment_fingerprint or environment.legacy_incomplete:
            raise AdapterContractError("environment identity does not match the exact scope")
        if self.fingerprint() not in environment.adapter_fingerprints:
            raise AdapterContractError("environment does not bind this adapter fingerprint")
        if mapping_asset.fingerprint() != scope.mapping_asset_fingerprint:
            raise AdapterContractError("mapping asset identity does not match the exact scope")
        if mapping_asset.target_namespace != scope.gem_gene_namespace:
            raise AdapterContractError("mapping target namespace does not match the exact scope")
        if (
            model_release.fingerprint() != scope.model_release_fingerprint
            or model_release.migration_status != "native"
            or model_release.model_fingerprint != scope.gem_model_fingerprint
            or model_release.pack_fingerprints != (scope.pack_fingerprint,)
            or model_release.artifact_fingerprints != (scope.gem_artifact_fingerprint,)
            or model_release.environment_fingerprint != scope.environment_fingerprint
            or model_release.adapter_fingerprints != (self.fingerprint(),)
            or model_release.evidence_fingerprints
            or model_release.policy_fingerprint is not None
        ):
            raise AdapterContractError("model release identity does not match the exact P14E scope")
        if execution_binding.fingerprint() != scope.execution_binding_fingerprint:
            raise AdapterContractError("execution binding fingerprint does not match the exact scope")
        execution_fields = (
            "medium_id",
            "medium_fingerprint",
            "condition_id",
            "condition_fingerprint",
            "objective_id",
            "objective_fingerprint",
            "objective_unit",
            "solver_configuration_fingerprint",
        )
        if any(
            getattr(execution_binding, field) != getattr(scope, field)
            for field in execution_fields
        ):
            raise AdapterContractError("medium/condition/objective/solver binding drift")
        if (
            pack.taxonomy_id != scope.taxonomy_id
            or pack.strain_id != scope.strain_id
            or pack.assembly_accession != scope.assembly_accession
        ):
            raise AdapterContractError("growth condition Pack scope does not match the exact scope")
        if pack_fingerprint != scope.pack_fingerprint:
            raise AdapterContractError("Pack fingerprint does not match the exact scope")
        if pack.fingerprint() != scope.data_binding_fingerprint:
            raise AdapterContractError("growth-data binding fingerprint does not match the exact scope")
        if compatibility_fingerprint != scope.compatibility_fingerprint:
            raise AdapterContractError("compatibility fingerprint does not match the exact scope")
        expected_compatibility = {
            "model_release_fingerprint": scope.model_release_fingerprint,
            "model_fingerprint": scope.gem_model_fingerprint,
            "artifact_fingerprint": scope.gem_artifact_fingerprint,
            "environment_fingerprint": scope.environment_fingerprint,
            "adapter_fingerprint": self.fingerprint(),
            "pack_fingerprint": scope.pack_fingerprint,
            "data_binding_fingerprint": scope.data_binding_fingerprint,
            "mapping_asset_fingerprint": scope.mapping_asset_fingerprint,
            "execution_binding_fingerprint": scope.execution_binding_fingerprint,
        }
        if any(
            getattr(compatibility_report, field) != value
            for field, value in expected_compatibility.items()
        ):
            raise AdapterContractError("compatibility identity does not match the exact scope")
        if (
            validation_protocol.scope_fingerprint != scope.fingerprint()
            or validation_protocol.baseline != scope.reference
        ):
            raise AdapterContractError("validation protocol does not match the exact scope")
        if validation_protocol.condition_data_fingerprint != pack_fingerprint:
            raise AdapterContractError("validation protocol condition-data Pack fingerprint drift")

        target = self._validate_request(request, scope, validation_protocol)
        request_fingerprint = _canonical_fingerprint(request.to_dict())
        model_input = EcoliK12KnockoutGrowthInput(
            schema_version="vc.ecoli-growth-prepared-model-input.v1",
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
            model_input = EcoliK12KnockoutGrowthInput.model_validate(prepared.model_input)
        except ValidationError as exc:
            raise AdapterContractError("prepared E. coli growth input is invalid") from exc
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

    def _validate_envelope_structure(
        self, envelope: AdapterOutputEnvelope
    ) -> AdapterOutputEnvelope:
        envelope = VirtualCellModelAdapter.validate_envelope(self, envelope)
        try:
            _reject_undeclared_model_fields(
                envelope.uncertainty, "growth output uncertainty"
            )
            uncertainty = AdapterUncertainty.model_validate(
                envelope.uncertainty.model_dump(
                    mode="python", serialize_as_any=True
                )
            )
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid growth output uncertainty") from exc
        try:
            _reject_undeclared_model_fields(envelope.ood, "growth output OOD status")
            ood = AdapterOOD.model_validate(
                envelope.ood.model_dump(mode="python", serialize_as_any=True)
            )
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid growth output OOD status") from exc
        try:
            _reject_undeclared_model_fields(
                envelope.provenance, "growth output provenance"
            )
            provenance = AdapterExecutionProvenance.model_validate(
                envelope.provenance.model_dump(
                    mode="python", serialize_as_any=True
                )
            )
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid growth output provenance") from exc
        envelope = envelope.model_copy(
            update={"uncertainty": uncertainty, "ood": ood, "provenance": provenance}
        )
        if (
            uncertainty.available
            or uncertainty.calibrated
            or uncertainty.value is not None
            or uncertainty.sigma is not None
            or uncertainty.method != "deterministic_fba"
        ):
            raise AdapterContractError(
                "deterministic FBA uncertainty unavailable; it must remain uncalibrated"
            )
        if set(envelope.ood.dimensions).difference(_OOD_AXES):
            raise AdapterContractError("growth output contains unknown OOD dimensions")
        if not envelope.ood.detected and (
            envelope.ood.dimensions or envelope.ood.reason is not None
        ):
            raise AdapterContractError("non-detected OOD must not contain dimensions or reason")
        if envelope.ood.detected and not envelope.ood.dimensions:
            raise AdapterContractError("detected OOD must identify an exact-scope dimension")
        if envelope.abstain:
            if envelope.projection_metadata:
                raise AdapterContractError("abstaining growth output cannot contain projection metadata")
            return envelope
        if envelope.values is None or len(envelope.values) != 1:
            raise AdapterContractError("growth ratio output must contain one value")
        ratio = _finite_number(envelope.values[0], "growth ratio")
        if ratio < self.output_contract.minimum_value:
            raise AdapterContractError("growth ratio must be non-negative")
        expected_keys = {"objective_unit", "reference", "scope_fingerprint", "solver_status"}
        if set(envelope.projection_metadata) != expected_keys:
            raise AdapterContractError("growth output projection metadata is not exact")
        if (
            envelope.projection_metadata["reference"] != self.output_contract.reference
            or envelope.projection_metadata["solver_status"] != "optimal"
        ):
            raise AdapterContractError("growth output projection metadata has contract drift")
        try:
            _fingerprint(envelope.projection_metadata["scope_fingerprint"], "scope_fingerprint")
            _text(envelope.projection_metadata["objective_unit"], "objective_unit")
        except ValueError as exc:
            raise AdapterContractError("growth output projection metadata is invalid") from exc
        return envelope

    def validate_envelope(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        del envelope
        raise AdapterContractError(
            "E. coli growth envelopes require an exact prepared input binding"
        )

    def validate_prepared_envelope(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        envelope = self._validate_envelope_structure(envelope)
        expected_pack = (prepared.pack_fingerprint,)
        expected_compatibility = (prepared.compatibility_fingerprint,)
        if (
            envelope.provenance.input_fingerprints != (prepared.fingerprint(),)
            or envelope.provenance.request_fingerprints
            != (prepared.request_fingerprint,)
            or envelope.provenance.pack_fingerprints != expected_pack
            or envelope.provenance.compatibility_fingerprints
            != expected_compatibility
        ):
            raise AdapterContractError(
                "adapter output provenance does not match prepared input"
            )
        if envelope.abstain:
            return envelope
        model_input = EcoliK12KnockoutGrowthInput.model_validate(prepared.model_input)
        metadata = envelope.projection_metadata
        if (
            metadata["scope_fingerprint"] != model_input.scope_fingerprint
            or metadata["objective_unit"] != model_input.scope.objective_unit
            or metadata["reference"] != model_input.scope.reference
        ):
            raise AdapterContractError("growth output scope metadata does not match prepared input")
        return envelope

    def aggregate(
        self, envelopes: tuple[AdapterOutputEnvelope, ...]
    ) -> AdapterOutputEnvelope:
        del envelopes
        raise AdapterContractError(
            "P14E E. coli growth declares no standalone aggregation policy"
        )

    def project_output(self, envelope: AdapterOutputEnvelope) -> dict[str, Any]:
        del envelope
        raise AdapterContractError(
            "E. coli growth projection requires an exact prepared input binding"
        )

    def project_prepared_output(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> dict[str, Any]:
        envelope = self.validate_prepared_envelope(prepared, envelope)
        if envelope.abstain or envelope.values is None:
            raise AdapterContractError("cannot project an abstaining growth output")
        return self.validate_projection(
            {self.output_contract.output: list(envelope.values)}
        )

    def validate_projection(self, projection: dict[str, Any]) -> dict[str, Any]:
        projection = super().validate_projection(projection)
        if set(projection) != {self.output_contract.output}:
            raise AdapterContractError("growth projection may contain only growth_ratio")
        values = projection[self.output_contract.output]
        if not isinstance(values, (list, tuple)) or len(values) != 1:
            raise AdapterContractError("growth projection must contain one value")
        ratio = _finite_number(values[0], "growth ratio")
        if ratio < self.output_contract.minimum_value:
            raise AdapterContractError("growth ratio must be non-negative")
        return {self.output_contract.output: [ratio]}

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        model_input = EcoliK12KnockoutGrowthInput.model_validate(prepared.model_input)
        if not isinstance(raw_output, dict):
            raise AdapterContractError("wrapper output must be a JSON object")
        required = {
            "prediction",
            "solver_status",
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
        status = raw_output["solver_status"]
        if not isinstance(status, str) or status not in _SOLVER_STATUSES:
            raise AdapterContractError("unknown solver status")
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

        try:
            uncertainty = AdapterUncertainty.model_validate(raw_output["uncertainty"])
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid uncertainty") from exc
        if (
            uncertainty.available
            or uncertainty.calibrated
            or uncertainty.value is not None
            or uncertainty.sigma is not None
            or uncertainty.method != "deterministic_fba"
        ):
            raise AdapterContractError(
                "deterministic FBA uncertainty unavailable; it must remain uncalibrated"
            )
        try:
            ood = AdapterOOD.model_validate(raw_output["ood"])
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid OOD status") from exc

        prediction = raw_output["prediction"]
        if status != "optimal" and not abstain:
            raise AdapterContractError("non-optimal solver status must abstain")
        if ood.detected and not abstain:
            raise AdapterContractError("OOD output must abstain")
        if abstain:
            if prediction is not None:
                raise AdapterContractError("abstain output must not contain prediction values")
            if not reasons:
                raise AdapterContractError("abstain output requires reasons")
            values = None
            shape = None
            metadata: dict[str, Any] = {}
        else:
            if reasons:
                raise AdapterContractError("non-abstain output cannot contain abstain reasons")
            if not isinstance(prediction, dict):
                raise AdapterContractError("non-abstain output requires a prediction object")
            prediction_fields = {"knockout_objective", "wild_type_objective", "objective_unit"}
            unknown_prediction = set(prediction).difference(prediction_fields)
            if unknown_prediction:
                raise AdapterContractError(f"unknown prediction fields: {sorted(unknown_prediction)}")
            missing_prediction = prediction_fields.difference(prediction)
            if missing_prediction:
                raise AdapterContractError(
                    f"prediction is missing fields: {sorted(missing_prediction)}"
                )
            knockout = _finite_number(prediction["knockout_objective"], "knockout objective")
            wild_type = _finite_number(prediction["wild_type_objective"], "wild-type objective")
            if knockout < 0:
                raise AdapterContractError("knockout objective must be non-negative")
            if wild_type <= 0:
                raise AdapterContractError("wild-type objective must be positive")
            if prediction["objective_unit"] != model_input.scope.objective_unit:
                raise AdapterContractError("prediction objective unit does not match the exact scope")
            ratio = knockout / wild_type
            if not math.isfinite(ratio):
                raise AdapterContractError("growth ratio must be a finite number")
            values = (ratio,)
            shape = (1,)
            metadata = {
                "objective_unit": model_input.scope.objective_unit,
                "reference": model_input.scope.reference,
                "scope_fingerprint": model_input.scope_fingerprint,
                "solver_status": status,
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
