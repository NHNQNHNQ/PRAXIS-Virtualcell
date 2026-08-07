"""P23A evidence-only contracts for one directed sender/receiver pair.

This module validates immutable identities and normalizes a supplied contract
fixture.  It has no asset loader, biological scoring formula, model runtime,
registry mutation, scientific-evidence derivation, or policy action.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.exceptions import InputValidationError
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
)
from praxis_virtualcell.model_zoo.curated_registry import VirtualCellReleaseV1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*:[^\s:]+$")
_TAXONOMY = re.compile(r"^NCBITaxon:[1-9][0-9]*$")
_MAX_SAFE_INTEGER = 2**53 - 1
_BASELINES = ("no_interaction", "receiver_only", "lr_coexpression")
_OOD_AXES = (
    "sender",
    "receiver",
    "ligand",
    "donor",
    "dataset",
    "platform",
    "dose_time",
)
_ABSTAIN_REASON_BY_STATUS = {
    "missing_paired_evidence": "missing_paired_evidence",
    "baseline_gate_failed": "baseline_gate_not_met",
    "unsupported_scope": "unsupported_interaction_scope",
    "execution_not_authorized": "p23a_real_execution_not_authorized",
    "registry_state_unverified": "curated_release_state_unverified",
}
_UNCERTAINTY_REASON = "p23a_contract_fixture_no_calibrated_uncertainty"
_RECORD_ROLE = "synthetic_conformance_not_evidence"


def _reject_undeclared_model_fields(
    value: Any,
    path: str,
    active: set[int] | None = None,
) -> None:
    active = set() if active is None else active
    traversable = isinstance(value, (BaseModel, Mapping, list, tuple))
    marker = id(value)
    if traversable and marker in active:
        raise ValueError(f"{path} contains a cyclic value")
    if traversable:
        active.add(marker)
    try:
        if isinstance(value, BaseModel):
            declared = type(value).model_fields
            unexpected = set(value.__dict__).difference(declared)
            extra = getattr(value, "__pydantic_extra__", None)
            if extra:
                unexpected.update(extra)
            if unexpected:
                raise ValueError(f"{path} contains undeclared fields: {sorted(unexpected)}")
            for name in declared:
                _reject_undeclared_model_fields(
                    getattr(value, name),
                    f"{path}.{name}",
                    active,
                )
        elif isinstance(value, Mapping):
            for key, item in value.items():
                _reject_undeclared_model_fields(item, f"{path}.{key}", active)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                _reject_undeclared_model_fields(item, f"{path}[{index}]", active)
    finally:
        if traversable:
            active.remove(marker)


def _plain_value(value: Any, active: set[int] | None = None) -> Any:
    """Preserve subclass fields while crossing into an exact Pydantic contract."""

    active = set() if active is None else active
    traversable = isinstance(value, (BaseModel, Mapping, list, tuple))
    marker = id(value)
    if traversable and marker in active:
        raise ValueError("value contains a cycle")
    if traversable:
        active.add(marker)
    try:
        if isinstance(value, BaseModel):
            dumped = value.model_dump(mode="python", serialize_as_any=True)
            return _plain_value(dumped, active)
        if isinstance(value, Mapping):
            return {key: _plain_value(item, active) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_plain_value(item, active) for item in value]
        return value
    finally:
        if traversable:
            active.remove(marker)


def _canonical_fingerprint(value: Any) -> str:
    if isinstance(value, BaseModel):
        _reject_undeclared_model_fields(value, type(value).__name__)
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


def _finite_nonnegative(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite non-negative number")
    if isinstance(value, int) and abs(value) > _MAX_SAFE_INTEGER:
        raise ValueError(f"{field} must be safely representable in JSON")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} must be a finite non-negative number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be a finite non-negative number")
    return number


def _score(value: Any) -> float:
    try:
        number = _finite_nonnegative(value, "interaction_evidence_score")
    except ValueError as exc:
        raise AdapterContractError("interaction_evidence_score must be a finite JSON-safe score") from exc
    if number > 1:
        raise AdapterContractError("interaction_evidence_score must use the unit_interval score scale")
    return number


def _exact_keys(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise AdapterContractError(f"{name} must be an exact JSON object")
    if any(not isinstance(key, str) for key in value):
        raise AdapterContractError(f"{name} keys must be strings")
    unknown = set(value).difference(fields)
    if unknown:
        raise AdapterContractError(f"unknown {name} fields: {sorted(unknown)}")
    missing = fields.difference(value)
    if missing:
        raise AdapterContractError(f"{name} is missing fields: {sorted(missing)}")
    return value


class _P23Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def to_dict(self) -> dict[str, Any]:
        _reject_undeclared_model_fields(self, type(self).__name__)
        return self.model_dump(mode="json", serialize_as_any=True)

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self)


def _p23_contract(value: Any, expected_type, field: str):
    _reject_undeclared_model_fields(value, field)
    if type(value) is expected_type:
        raw = value.to_dict()
    elif isinstance(value, Mapping):
        raw = dict(value)
    else:
        raise TypeError(f"{field} must be an exact {expected_type.__name__}")
    try:
        return expected_type.model_validate(raw)
    except (TypeError, ValidationError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc


def _release(value: Any) -> VirtualCellReleaseV1:
    _reject_undeclared_model_fields(value, "release")
    if type(value) is not VirtualCellReleaseV1 and not isinstance(value, Mapping):
        raise TypeError("release must be an exact VirtualCellReleaseV1")
    raw = _plain_value(value)
    try:
        return VirtualCellReleaseV1.from_dict(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid Virtual Cell release") from exc


class P18EndpointIdentityV1(_P23Contract):
    """Typed, explicitly unverified reference to one P18 model-input view."""

    schema_version: Literal["vc.p23-p18-endpoint-identity.v1"]
    model_input_schema_version: Literal["vc.multiomics-model-input.v1"]
    model_input_fingerprint: str
    pack_fingerprint: str
    view_identity_fingerprint: str
    observation_semantics_fingerprint: str
    join_fingerprint: str
    modality_key: str
    modality_identity_fingerprint: str
    observation_id: str
    taxonomy_id: str
    scientific_name: str
    identity_role: Literal["declared_p18_contract_fixture_reference"]
    p18_contract_verified: Literal[False]
    observation_membership_verified: Literal[False]

    @field_validator(
        "model_input_fingerprint",
        "pack_fingerprint",
        "view_identity_fingerprint",
        "observation_semantics_fingerprint",
        "join_fingerprint",
        "modality_identity_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("modality_key", "observation_id", "scientific_name", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("taxonomy_id", mode="before")
    @classmethod
    def _valid_taxonomy(cls, value):
        value = _text(value, "taxonomy_id")
        if not _TAXONOMY.fullmatch(value):
            raise ValueError("taxonomy_id must be an NCBITaxon CURIE")
        return value


class InteractionEndpointV1(_P23Contract):
    """One role-bound P22 release plus its exact Pack/context references."""

    schema_version: Literal["vc.interaction-endpoint.v1"]
    role: Literal["sender", "receiver"]
    release: VirtualCellReleaseV1
    release_fingerprint: str
    context_fingerprint: str
    pack_registration_fingerprint: str
    pack_fingerprint: str
    p18_identity: P18EndpointIdentityV1
    p18_identity_fingerprint: str
    registry_state_verified: Literal[False]

    @field_validator("release", mode="before")
    @classmethod
    def _valid_release(cls, value):
        return _release(value)

    @field_validator(
        "release_fingerprint",
        "context_fingerprint",
        "pack_registration_fingerprint",
        "pack_fingerprint",
        "p18_identity_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("p18_identity", mode="before")
    @classmethod
    def _valid_p18_identity(cls, value):
        return _p23_contract(value, P18EndpointIdentityV1, "p18_identity")

    @model_validator(mode="after")
    def _release_closure_is_exact(self):
        release = self.release
        if release.fingerprint() != self.release_fingerprint:
            raise ValueError("release_fingerprint is stale")
        if release.context.fingerprint() != self.context_fingerprint:
            raise ValueError("context_fingerprint is stale")
        if release.pack_registration.fingerprint() != self.pack_registration_fingerprint:
            raise ValueError("pack_registration_fingerprint is stale")
        if release.pack_registration.pack_fingerprint != self.pack_fingerprint:
            raise ValueError("pack_fingerprint does not match the release")
        if self.p18_identity.fingerprint() != self.p18_identity_fingerprint:
            raise ValueError("p18_identity_fingerprint is stale")
        if self.p18_identity.pack_fingerprint != self.pack_fingerprint:
            raise ValueError("P18 Pack fingerprint does not match the P22 release")
        if self.p18_identity.scientific_name != release.context.organism:
            raise ValueError("P18 scientific_name does not match the P22 release")
        return self


class SameExperimentInteractionEvidenceV1(_P23Contract):
    """One indivisible paired-evidence identity; cross-dataset pairing has no field."""

    schema_version: Literal["vc.same-experiment-interaction-evidence.v1"]
    dataset_fingerprint: str
    platform_fingerprint: str
    evidence_asset_fingerprint: str
    evidence_record_fingerprint: str
    experiment_id: str
    donor_id: str
    sample_id: str
    well_id: str
    condition_id: str
    dose_value: float
    dose_unit: str
    time_value: float
    time_unit: str
    sender_role: Literal["sender"]
    sender_observation_id: str
    receiver_role: Literal["receiver"]
    receiver_observation_id: str
    ligand_id: str
    ligand_namespace: str
    ligand_namespace_version: str
    ligand_namespace_fingerprint: str
    receptor_id: str
    receptor_namespace: str
    receptor_namespace_version: str
    receptor_namespace_fingerprint: str
    evidence_namespace: str
    evidence_namespace_version: str
    evidence_namespace_fingerprint: str
    mapping_asset_fingerprint: str
    evidence_asset_verified: Literal[False]
    paired_linkage_verified: Literal[False]

    @field_validator(
        "dataset_fingerprint",
        "platform_fingerprint",
        "evidence_asset_fingerprint",
        "evidence_record_fingerprint",
        "ligand_namespace_fingerprint",
        "receptor_namespace_fingerprint",
        "evidence_namespace_fingerprint",
        "mapping_asset_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "experiment_id",
        "donor_id",
        "sample_id",
        "well_id",
        "condition_id",
        "dose_unit",
        "time_unit",
        "sender_observation_id",
        "receiver_observation_id",
        "ligand_namespace",
        "ligand_namespace_version",
        "receptor_namespace",
        "receptor_namespace_version",
        "evidence_namespace",
        "evidence_namespace_version",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("ligand_id", "receptor_id", mode="before")
    @classmethod
    def _valid_curie(cls, value, info):
        value = _text(value, info.field_name)
        if not _CURIE.fullmatch(value):
            raise ValueError(f"{info.field_name} must be a CURIE")
        return value

    @field_validator("dose_value", "time_value", mode="before")
    @classmethod
    def _valid_quantity(cls, value, info):
        return _finite_nonnegative(value, info.field_name)

    @model_validator(mode="after")
    def _curie_namespaces_are_exact(self):
        if self.ligand_id.partition(":")[0] != self.ligand_namespace:
            raise ValueError("ligand CURIE prefix does not match ligand_namespace")
        if self.receptor_id.partition(":")[0] != self.receptor_namespace:
            raise ValueError("receptor CURIE prefix does not match receptor_namespace")
        return self


class InteractionScorerFixtureV1(_P23Contract):
    """Untrusted fixed-scorer identities for local contract conformance only."""

    schema_version: Literal["vc.interaction-scorer-fixture.v1"]
    adapter_fingerprint: str
    model_release_fingerprint: str
    model_artifact_fingerprint: str
    benchmark_bundle_fingerprint: str
    benchmark_protocol_fingerprint: str
    benchmark_run_fingerprint: str
    benchmark_result_fingerprint: str
    p21b_execution_identity_fingerprint: str
    baselines: tuple[str, ...]
    ood_axes: tuple[str, ...]
    record_role: Literal["contract_fixture"]
    p20_p21_bindings_verified: Literal[False]
    trusted_p21b_execution: Literal[False]
    model_artifact_verified: Literal[False]
    real_model_execution_authorized: Literal[False]
    real_model_execution_performed: Literal[False]

    @field_validator(
        "adapter_fingerprint",
        "model_release_fingerprint",
        "model_artifact_fingerprint",
        "benchmark_bundle_fingerprint",
        "benchmark_protocol_fingerprint",
        "benchmark_run_fingerprint",
        "benchmark_result_fingerprint",
        "p21b_execution_identity_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("baselines", mode="before")
    @classmethod
    def _valid_baselines(cls, value):
        if not isinstance(value, (list, tuple)) or tuple(value) != _BASELINES:
            raise ValueError(f"baselines must equal the canonical order: {list(_BASELINES)}")
        return tuple(value)

    @field_validator("ood_axes", mode="before")
    @classmethod
    def _valid_ood_axes(cls, value):
        if not isinstance(value, (list, tuple)) or tuple(value) != _OOD_AXES:
            raise ValueError(f"ood_axes must equal the canonical order: {list(_OOD_AXES)}")
        return tuple(value)


class InteractionEvidenceInputV1(_P23Contract):
    """Complete directed pair, linkage, and untrusted scorer fixture binding."""

    schema_version: Literal["vc.cell-interaction-evidence-input.v1"]
    task: Literal["cell_interaction_evidence"]
    output: Literal["interaction_evidence_score"]
    direction: Literal["sender_to_receiver"]
    score_scale: Literal["unit_interval"]
    score_semantics: Literal["association_evidence_only"]
    sender: InteractionEndpointV1
    receiver: InteractionEndpointV1
    paired_evidence: SameExperimentInteractionEvidenceV1
    scorer: InteractionScorerFixtureV1
    p18_role_semantics: Literal["p23_roles_over_p18_identity_state_context"]
    real_data_authorized: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator("sender", "receiver", mode="before")
    @classmethod
    def _valid_endpoint(cls, value, info):
        return _p23_contract(value, InteractionEndpointV1, info.field_name)

    @field_validator("paired_evidence", mode="before")
    @classmethod
    def _valid_evidence(cls, value):
        return _p23_contract(value, SameExperimentInteractionEvidenceV1, "paired_evidence")

    @field_validator("scorer", mode="before")
    @classmethod
    def _valid_scorer(cls, value):
        return _p23_contract(value, InteractionScorerFixtureV1, "scorer")

    @model_validator(mode="after")
    def _directed_pair_is_exact(self):
        if self.sender.role != "sender":
            raise ValueError("sender role must be sender")
        if self.receiver.role != "receiver":
            raise ValueError("receiver role must be receiver")
        if self.sender.release.context.organism != self.receiver.release.context.organism:
            raise ValueError("sender and receiver organism must match")
        if self.sender.p18_identity.taxonomy_id != self.receiver.p18_identity.taxonomy_id:
            raise ValueError("sender and receiver P18 taxonomy must match")
        if self.paired_evidence.sender_observation_id != self.sender.p18_identity.observation_id:
            raise ValueError("sender observation does not match paired evidence")
        if self.paired_evidence.receiver_observation_id != self.receiver.p18_identity.observation_id:
            raise ValueError("receiver observation does not match paired evidence")
        return self


class InteractionEvidenceAdapterInputContract(AdapterInputContract):
    schema_version: Literal["vc.interaction-evidence-adapter-input-contract.v1"]
    direction: Literal["sender_to_receiver"]
    score_scale: Literal["unit_interval"]
    record_role: Literal["contract_fixture"]
    required_bindings: tuple[str, ...]


class InteractionEvidenceAdapterOutputContract(AdapterOutputContract):
    schema_version: Literal["vc.interaction-evidence-adapter-output-contract.v1"]
    score_scale: Literal["unit_interval"]
    score_semantics: Literal["association_evidence_only"]
    receiver_response_allowed: Literal[False]
    causal_claim_allowed: Literal[False]


class CellInteractionEvidenceAdapter(VirtualCellModelAdapter):
    """P13-shaped pass-through for a synthetic scalar evidence fixture."""

    adapter_id = "cell-interaction-evidence-contract"
    version = "1.0.0"
    input_contract = InteractionEvidenceAdapterInputContract(
        schema_version="vc.interaction-evidence-adapter-input-contract.v1",
        task="cell_interaction_evidence",
        output="interaction_evidence_score",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        pack_data_required=False,
        alignment_required=False,
        direction="sender_to_receiver",
        score_scale="unit_interval",
        record_role="contract_fixture",
        required_bindings=(
            "sender_release_pack_context_and_typed_p18_identity",
            "receiver_release_pack_context_and_typed_p18_identity",
            "same_experiment_donor_sample_well_condition_dose_time_roles",
            "ligand_receptor_evidence_namespaces_and_mapping",
            "fixed_p20_p21_scorer_identity",
            "baselines_and_ood_axes",
        ),
    )
    output_contract = InteractionEvidenceAdapterOutputContract(
        schema_version="vc.interaction-evidence-adapter-output-contract.v1",
        task="cell_interaction_evidence",
        output="interaction_evidence_score",
        value_type="float",
        shape=(1,),
        unit="dimensionless",
        uncertainty_required=True,
        ood_required=True,
        abstain_allowed=True,
        score_scale="unit_interval",
        score_semantics="association_evidence_only",
        receiver_response_allowed=False,
        causal_claim_allowed=False,
    )

    def _validate_request(
        self,
        request: VirtualCellRequestV2,
        interaction: InteractionEvidenceInputV1,
    ) -> str:
        if type(request) is not VirtualCellRequestV2:
            raise TypeError("request must be exact VirtualCellRequestV2")
        try:
            _reject_undeclared_model_fields(request, "request")
            request = VirtualCellRequestV2.from_dict(_plain_value(request))
        except (InputValidationError, TypeError, ValueError) as exc:
            raise AdapterContractError("invalid request") from exc
        if request.task.task_type != self.input_contract.task or request.task.requested_outputs != (
            self.input_contract.output,
        ):
            raise AdapterContractError("request task/output does not match P23A")
        sender_p18 = interaction.sender.p18_identity
        receiver_p18 = interaction.receiver.p18_identity
        organism = interaction.sender.release.context.organism
        if (
            request.species.taxonomy_id != sender_p18.taxonomy_id
            or receiver_p18.taxonomy_id != sender_p18.taxonomy_id
            or request.species.scientific_name != organism
            or receiver_p18.scientific_name != organism
            or interaction.receiver.release.context.organism != organism
            or request.species.common_name is not None
        ):
            raise AdapterContractError("request organism does not match sender/receiver")
        expected_attributes = {
            "interaction_input_fingerprint": interaction.fingerprint(),
            "receiver_release_fingerprint": interaction.receiver.release_fingerprint,
            "sender_release_fingerprint": interaction.sender.release_fingerprint,
        }
        if (
            request.cell_context.cell_type_name != "directed_sender_receiver_pair"
            or request.cell_context.cell_type_id is not None
            or request.cell_context.tissue_name is not None
            or request.cell_context.tissue_id is not None
            or dict(request.cell_context.attributes) != expected_attributes
        ):
            raise AdapterContractError("request cell context does not bind the directed pair")
        if (
            request.input_modality.name != "paired_cell_interaction_evidence"
            or request.input_modality.ontology_id is not None
            or request.input_modality.unit is not None
            or request.input_modality.feature_namespace is not None
        ):
            raise AdapterContractError("request input modality is not paired interaction evidence")
        if (
            request.output_modality.name != self.output_contract.output
            or request.output_modality.ontology_id is not None
            or request.output_modality.unit != self.output_contract.unit
            or request.output_modality.feature_namespace is not None
        ):
            raise AdapterContractError("request output modality is not the evidence score")
        if (
            request.perturbation.kind != "medium"
            or request.perturbation.targets
            or request.perturbation.dose_value is not None
            or request.perturbation.dose_unit is not None
            or request.perturbation.timepoint is not None
        ):
            raise AdapterContractError("P23A request must not encode a receiver intervention")
        if request.baseline_context is None or dict(request.baseline_context) != {"baselines": _BASELINES}:
            raise AdapterContractError("request baseline binding is not canonical")
        if dict(request.constraints) != {
            "direction": "sender_to_receiver",
            "interaction_input_fingerprint": interaction.fingerprint(),
            "score_scale": "unit_interval",
        }:
            raise AdapterContractError("request constraints do not match the directed pair")
        if request.metadata:
            raise AdapterContractError("request metadata must remain empty")
        return _canonical_fingerprint(request.to_dict())

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        interaction_input: InteractionEvidenceInputV1,
    ) -> PreparedAdapterInput:
        try:
            interaction = _p23_contract(
                interaction_input,
                InteractionEvidenceInputV1,
                "interaction_input",
            )
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("invalid interaction input") from exc
        if interaction.scorer.adapter_fingerprint != self.fingerprint():
            raise AdapterContractError("interaction scorer does not bind this adapter")
        request_fingerprint = self._validate_request(request, interaction)
        prepared = PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=request_fingerprint,
            pack_fingerprint=None,
            compatibility_fingerprint=interaction.fingerprint(),
            model_input=interaction.to_dict(),
            values=None,
            shape=None,
            unit=self.input_contract.unit,
            feature_contract=None,
            feature_contract_fingerprint=None,
            alignment_report=None,
        )
        return self.validate_prepared_input(prepared)

    def validate_prepared_input(self, prepared: PreparedAdapterInput) -> PreparedAdapterInput:
        prepared = super().validate_prepared_input(prepared)
        try:
            interaction = _p23_contract(
                prepared.model_input,
                InteractionEvidenceInputV1,
                "prepared interaction input",
            )
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("prepared interaction input is invalid") from exc
        if (
            prepared.pack_fingerprint is not None
            or prepared.feature_contract is not None
            or prepared.feature_contract_fingerprint is not None
            or prepared.alignment_report is not None
        ):
            raise AdapterContractError("contract fixture cannot bind loaded Pack values or alignment")
        if (
            interaction.fingerprint() != prepared.compatibility_fingerprint
            or interaction.scorer.adapter_fingerprint != self.fingerprint()
        ):
            raise AdapterContractError("prepared interaction identity has drifted")
        return prepared

    def _validate_uncertainty(self, raw: Any) -> AdapterUncertainty:
        _exact_keys(
            raw,
            {"available", "method", "calibrated", "value", "sigma", "reason"},
            "uncertainty",
        )
        try:
            uncertainty = AdapterUncertainty.model_validate(raw)
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid uncertainty") from exc
        if (
            uncertainty.available
            or uncertainty.method != "not_available"
            or uncertainty.calibrated
            or uncertainty.value is not None
            or uncertainty.sigma is not None
            or uncertainty.reason != _UNCERTAINTY_REASON
        ):
            raise AdapterContractError("interaction uncertainty must use the contract-fixture reason enum")
        return uncertainty

    def _validate_ood(self, raw: Any) -> AdapterOOD:
        _exact_keys(raw, {"detected", "dimensions", "reason"}, "OOD")
        try:
            ood = AdapterOOD.model_validate(raw)
        except (TypeError, ValidationError) as exc:
            raise AdapterContractError("invalid OOD status") from exc
        if set(ood.dimensions).difference(_OOD_AXES):
            raise AdapterContractError("OOD contains an unknown interaction axis")
        if ood.dimensions != tuple(axis for axis in _OOD_AXES if axis in ood.dimensions):
            raise AdapterContractError("OOD dimensions are not in canonical order")
        if ood.detected:
            if not ood.dimensions or ood.reason != "unsupported_interaction_scope":
                raise AdapterContractError("detected OOD requires the exact unsupported-scope reason")
        elif ood.dimensions or ood.reason is not None:
            raise AdapterContractError("non-detected OOD cannot contain dimensions or reason")
        return ood

    def _validate_envelope_structure(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        envelope = VirtualCellModelAdapter.validate_envelope(self, envelope)
        uncertainty = self._validate_uncertainty(envelope.uncertainty.to_dict())
        ood = self._validate_ood(envelope.ood.to_dict())
        if envelope.abstain:
            if envelope.projection_metadata:
                raise AdapterContractError("abstaining interaction output cannot contain projection metadata")
            return envelope.model_copy(update={"uncertainty": uncertainty, "ood": ood})
        if envelope.values is None or len(envelope.values) != 1:
            raise AdapterContractError("interaction output must contain one score")
        _score(envelope.values[0])
        expected_metadata = {
            "baseline_comparison_performed": False,
            "causal_claim_included": False,
            "evidence_asset_verified": False,
            "interaction_input_fingerprint": envelope.projection_metadata.get("interaction_input_fingerprint"),
            "p20_p21_bindings_verified": False,
            "paired_ci_performed": False,
            "paired_linkage_verified": False,
            "real_data_authorized": False,
            "real_model_execution_performed": False,
            "receiver_registry_state_verified": False,
            "receiver_response_included": False,
            "record_role": _RECORD_ROLE,
            "score_scale": "unit_interval",
            "score_semantics": "association_evidence_only",
            "score_source": "supplied_contract_fixture_not_model_output",
            "sender_registry_state_verified": False,
        }
        if envelope.projection_metadata != expected_metadata:
            raise AdapterContractError("interaction projection metadata is not exact")
        try:
            _fingerprint(
                envelope.projection_metadata["interaction_input_fingerprint"],
                "interaction_input_fingerprint",
            )
        except (KeyError, ValueError) as exc:
            raise AdapterContractError("interaction projection metadata fingerprint is invalid") from exc
        return envelope.model_copy(update={"uncertainty": uncertainty, "ood": ood})

    def validate_envelope(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        del envelope
        raise AdapterContractError("interaction envelopes require an exact prepared input binding")

    def validate_prepared_envelope(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        envelope = self._validate_envelope_structure(envelope)
        expected_compatibility = (prepared.compatibility_fingerprint,)
        if (
            envelope.provenance.input_fingerprints != (prepared.fingerprint(),)
            or envelope.provenance.request_fingerprints != (prepared.request_fingerprint,)
            or envelope.provenance.pack_fingerprints
            or envelope.provenance.compatibility_fingerprints != expected_compatibility
        ):
            raise AdapterContractError("interaction output provenance does not match prepared input")
        if not envelope.abstain and (
            envelope.projection_metadata["interaction_input_fingerprint"] != prepared.compatibility_fingerprint
        ):
            raise AdapterContractError("interaction output does not bind the prepared input")
        return envelope

    def aggregate(self, envelopes: tuple[AdapterOutputEnvelope, ...]) -> AdapterOutputEnvelope:
        del envelopes
        raise AdapterContractError("P23A declares no aggregation policy")

    def project_output(self, envelope: AdapterOutputEnvelope) -> dict[str, Any]:
        del envelope
        raise AdapterContractError("interaction projection requires an exact prepared input binding")

    def project_prepared_output(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> dict[str, Any]:
        envelope = self.validate_prepared_envelope(prepared, envelope)
        if envelope.abstain or envelope.values is None:
            raise AdapterContractError("cannot project an abstaining interaction output")
        return self.validate_projection({self.output_contract.output: [envelope.values[0]]})

    def validate_projection(self, projection: dict[str, Any]) -> dict[str, Any]:
        if type(projection) is not dict:
            raise AdapterContractError("interaction projection must be an exact object")
        projection = super().validate_projection(projection)
        if set(projection) != {self.output_contract.output}:
            raise AdapterContractError("projection may contain only interaction_evidence_score")
        values = projection[self.output_contract.output]
        if not isinstance(values, (list, tuple)) or len(values) != 1:
            raise AdapterContractError("interaction_evidence_score projection must contain one score")
        return {self.output_contract.output: [_score(values[0])]}

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        prepared = self.validate_prepared_input(prepared)
        fields = {
            "prediction",
            "prediction_status",
            "interaction_input_fingerprint",
            "uncertainty",
            "ood",
            "abstain",
            "abstain_reasons",
            "record_role",
        }
        raw_output = _exact_keys(raw_output, fields, "wrapper output")
        try:
            interaction_fingerprint = _fingerprint(
                raw_output["interaction_input_fingerprint"],
                "interaction_input_fingerprint",
            )
        except ValueError as exc:
            raise AdapterContractError("wrapper interaction fingerprint is invalid") from exc
        if interaction_fingerprint != prepared.compatibility_fingerprint:
            raise AdapterContractError("wrapper output does not match the prepared input")
        status = raw_output["prediction_status"]
        if not isinstance(status, str) or status not in {
            "synthetic_conformance",
            *_ABSTAIN_REASON_BY_STATUS,
        }:
            raise AdapterContractError("unknown interaction prediction status")
        if raw_output["record_role"] != _RECORD_ROLE:
            raise AdapterContractError("wrapper record role is not synthetic conformance")
        abstain = raw_output["abstain"]
        if not isinstance(abstain, bool):
            raise AdapterContractError("abstain must be a boolean")
        reasons_raw = raw_output["abstain_reasons"]
        if not isinstance(reasons_raw, (list, tuple)) or any(not isinstance(item, str) for item in reasons_raw):
            raise AdapterContractError("abstain reasons must use exact reason enums")
        reasons = tuple(reasons_raw)
        if len(set(reasons)) != len(reasons):
            raise AdapterContractError("abstain reasons must not contain duplicates")
        uncertainty = self._validate_uncertainty(raw_output["uncertainty"])
        ood = self._validate_ood(raw_output["ood"])

        prediction = raw_output["prediction"]
        if status == "synthetic_conformance":
            if abstain or reasons or ood.detected:
                raise AdapterContractError("successful interaction fixture cannot abstain or be OOD")
            prediction = _exact_keys(
                prediction,
                {"interaction_evidence_score", "score_scale", "score_semantics"},
                "prediction",
            )
            if (
                prediction["score_scale"] != self.output_contract.score_scale
                or prediction["score_semantics"] != self.output_contract.score_semantics
            ):
                raise AdapterContractError("prediction score semantics do not match P23A")
            values = (_score(prediction["interaction_evidence_score"]),)
            shape = (1,)
            metadata: dict[str, Any] = {
                "baseline_comparison_performed": False,
                "causal_claim_included": False,
                "evidence_asset_verified": False,
                "interaction_input_fingerprint": interaction_fingerprint,
                "p20_p21_bindings_verified": False,
                "paired_ci_performed": False,
                "paired_linkage_verified": False,
                "real_data_authorized": False,
                "real_model_execution_performed": False,
                "receiver_registry_state_verified": False,
                "receiver_response_included": False,
                "record_role": _RECORD_ROLE,
                "score_scale": "unit_interval",
                "score_semantics": "association_evidence_only",
                "score_source": "supplied_contract_fixture_not_model_output",
                "sender_registry_state_verified": False,
            }
        else:
            expected_reason = _ABSTAIN_REASON_BY_STATUS[status]
            if not abstain or prediction is not None or reasons != (expected_reason,):
                raise AdapterContractError("abstaining interaction status requires its exact reason enum")
            if status == "unsupported_scope":
                if not ood.detected:
                    raise AdapterContractError("unsupported interaction scope requires detected OOD")
            elif ood.detected:
                raise AdapterContractError("only unsupported interaction scope may carry OOD")
            values = None
            shape = None
            metadata = {}

        provenance = AdapterExecutionProvenance(
            schema_version="vc.adapter-execution-provenance.v1",
            adapter_fingerprint=self.fingerprint(),
            input_fingerprints=(prepared.fingerprint(),),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            output_contract_fingerprint=self.output_contract.fingerprint(),
            request_fingerprints=(prepared.request_fingerprint,),
            pack_fingerprints=(),
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
