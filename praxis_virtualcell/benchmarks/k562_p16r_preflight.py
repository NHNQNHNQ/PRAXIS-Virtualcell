"""Value-free identity preflight for a future authorized P16R K562 run.

This module binds already-declared identities only.  It deliberately performs
no asset I/O, model execution, leakage audit, evidence creation, or policy
decision.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.benchmarks.system import (
    BenchmarkProtocolV1,
    DatasetBindingV1,
    GroupIdentityV1,
)
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterContractError,
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
)
from praxis_virtualcell.model_zoo.capability_registry import ModelCard
from praxis_virtualcell.model_zoo.k562_golden_delta_contract import (
    K562GoldenCompatibilityBinding,
    K562GoldenDataBinding,
    K562GoldenExecutionBinding,
    K562GoldenPerturbationAdapter,
    K562GoldenPerturbationBinding,
    K562GoldenPerturbationScope,
    K562GoldenValidationProtocol,
)
from praxis_virtualcell.model_zoo.registry_v2 import ModelRegistryV2

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PARTITION_ORDER = {"train": 0, "validation": 1, "test": 2, "external": 3}
_REASONS = (
    "p16r_authorization_missing",
    "p16r_asset_bytes_unverified",
    "p16r_record_membership_unverified",
    "p16r_science_not_run",
)


class P16RPreflightError(ValueError):
    """A future P16R identity declaration is incomplete or incompatible."""


def _canonical(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _fingerprint(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _normalise(value: Any, expected_type: type[BaseModel], field: str):
    if type(value) is not expected_type:
        raise P16RPreflightError(f"{field} must be an exact {expected_type.__name__}")
    try:
        _reject_undeclared_model_fields(value, field)
        payload = (
            value.to_dict() if expected_type is PackManifest else value.model_dump(mode="python", serialize_as_any=True)
        )
        normalised = expected_type.model_validate(payload)
        _reject_model_type_drift(value, normalised, field)
        return normalised
    except (AdapterContractError, AttributeError, TypeError, ValidationError, ValueError) as exc:
        raise P16RPreflightError(f"invalid {field}") from exc


def _normalise_groups(value: Sequence[GroupIdentityV1]) -> tuple[GroupIdentityV1, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
        raise P16RPreflightError("group_records must be a non-empty sequence")
    groups = tuple(_normalise(item, GroupIdentityV1, "group_records") for item in value)
    ordered = tuple(sorted(groups, key=lambda item: (_PARTITION_ORDER[item.partition], item.group_id)))
    if (
        groups != ordered
        or len({(item.partition, item.group_id) for item in groups}) != len(groups)
        or {item.partition for item in groups} != set(_PARTITION_ORDER)
    ):
        raise P16RPreflightError("group_records must be canonically ordered with unique partition/group IDs")
    return groups


class K562P16RExternalScopeDeclarationV1(BaseModel):
    """Exact external target declaration, intentionally not a byte receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["vc.k562-p16r-external-scope-declaration.v1"]
    declaration_id: str
    pack_fingerprint: str
    dataset_fingerprint: str
    platform_fingerprint: str
    scope_manifest_fingerprint: str
    taxonomy_id: Literal["NCBITaxon:9606"]
    scientific_name: Literal["Homo sapiens"]
    cell_identity_name: Literal["K562"]
    cell_identity_id: Literal["CVCL_0004"]
    assembly_name: Literal["GRCh38"]
    assembly_accession: Literal["GCA_000001405.15"]
    modality_name: Literal["scRNA"]
    modality_id: Literal["EFO:0008913"]
    feature_namespace: Literal["EnsemblGene"]
    feature_namespace_version: Literal["Ensembl 84"]
    feature_id_format: Literal["ensembl_gene"]
    feature_ids_sha256: str
    feature_records_sha256: str
    feature_mapping_fingerprint: str | None
    value_semantics: Literal["condition_mean_X_minus_matched_split_control_mean_X"]
    reference: Literal["matched_split_control_mean_X"]
    output_unit: None
    independent_from_golden: Literal[True]
    adaptation_steps: Literal[0]
    record_role: Literal["unverified_external_scope_declaration"]
    asset_bytes_verified: Literal[False]
    record_membership_verified: Literal[False]

    @field_validator(
        "pack_fingerprint",
        "dataset_fingerprint",
        "platform_fingerprint",
        "scope_manifest_fingerprint",
        "feature_ids_sha256",
        "feature_records_sha256",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("feature_mapping_fingerprint", mode="before")
    @classmethod
    def _optional_fingerprint(cls, value):
        return None if value is None else _fingerprint(value, "feature_mapping_fingerprint")

    @field_validator("declaration_id", mode="before")
    @classmethod
    def _declaration_id(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"p16r_external_scope_[0-9a-f]{24}", value):
            raise ValueError("declaration_id must be a canonical external-scope ID")
        return value

    @model_validator(mode="after")
    def _closed_unverified_declaration(self):
        identity = self.model_dump(mode="json")
        identity.pop("declaration_id")
        if self.declaration_id != f"p16r_external_scope_{_canonical(identity)[:24]}":
            raise ValueError("declaration_id does not bind the external scope declaration")
        return self

    def to_dict(self) -> dict[str, Any]:
        if type(self) is not K562P16RExternalScopeDeclarationV1:
            raise P16RPreflightError("external scope must have the exact canonical type")
        try:
            _reject_undeclared_model_fields(self, "external_scope")
            normalised = K562P16RExternalScopeDeclarationV1.model_validate(
                self.model_dump(mode="python", serialize_as_any=True)
            )
            _reject_model_type_drift(self, normalised, "external_scope")
            return normalised.model_dump(mode="json")
        except (AdapterContractError, AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise P16RPreflightError("invalid external_scope") from exc

    def fingerprint(self) -> str:
        return _canonical(self.to_dict())


class K562P16RAuthorizationPreflightV1(BaseModel):
    """An immutable identity binder, never P16R evidence or an execution plan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["vc.k562-p16r-authorization-preflight.v1"]
    preflight_id: str
    evaluation_scope: Literal["single_gene", "combination"]
    source_per_condition_scope_fingerprint: str
    source_perturbation_binding_fingerprint: str
    golden_data_binding_fingerprint: str
    golden_pack_fingerprint: str
    golden_h5ad_sha256: str
    golden_feature_ids_sha256: str
    golden_feature_records_sha256: str
    execution_binding_fingerprint: str
    p16_preregistration_fingerprint: str
    candidate_card_fingerprint: str
    candidate_model_fingerprint: str
    candidate_release_fingerprint: str
    candidate_artifact_fingerprints: tuple[str, ...]
    candidate_environment_fingerprint: str
    candidate_adapter_fingerprints: tuple[str, ...]
    candidate_provenance_manifest_fingerprint: str
    external_pack_fingerprint: str
    external_dataset_fingerprint: str
    external_platform_fingerprint: str
    external_scope_declaration_fingerprint: str
    external_scope_manifest_fingerprint: str
    external_feature_ids_sha256: str
    external_feature_records_sha256: str
    external_feature_mapping_fingerprint: str | None
    group_records_fingerprint: str
    benchmark_protocol_fingerprint: str
    benchmark_scope_fingerprint: str
    benchmark_split_fingerprint: str
    benchmark_baseline_fingerprint: str
    benchmark_feature_contract_fingerprint: str
    benchmark_output_contract_fingerprint: str
    asset_set_fingerprint: str
    record_role: Literal["authorization_preflight_not_evidence"]
    authorization_fingerprint: None
    asset_verification_receipt_fingerprints: tuple[str, ...]
    assets_verified: Literal[False]
    record_membership_verified: Literal[False]
    leakage_audit_fingerprint: None
    benchmark_passed: None
    scientifically_validated: Literal[False]
    promotion_eligible: None
    evidence_fingerprints: tuple[str, ...]
    policy_fingerprint: None
    production_promoted: Literal[False]
    executable: Literal[False]
    abstain: Literal[True]
    prediction: None
    abstain_reasons: tuple[str, ...]

    @field_validator(
        "source_per_condition_scope_fingerprint",
        "source_perturbation_binding_fingerprint",
        "golden_data_binding_fingerprint",
        "golden_pack_fingerprint",
        "golden_h5ad_sha256",
        "golden_feature_ids_sha256",
        "golden_feature_records_sha256",
        "execution_binding_fingerprint",
        "p16_preregistration_fingerprint",
        "candidate_card_fingerprint",
        "candidate_model_fingerprint",
        "candidate_release_fingerprint",
        "candidate_environment_fingerprint",
        "candidate_provenance_manifest_fingerprint",
        "external_pack_fingerprint",
        "external_dataset_fingerprint",
        "external_platform_fingerprint",
        "external_scope_declaration_fingerprint",
        "external_scope_manifest_fingerprint",
        "external_feature_ids_sha256",
        "external_feature_records_sha256",
        "group_records_fingerprint",
        "benchmark_protocol_fingerprint",
        "benchmark_scope_fingerprint",
        "benchmark_split_fingerprint",
        "benchmark_baseline_fingerprint",
        "benchmark_feature_contract_fingerprint",
        "benchmark_output_contract_fingerprint",
        "asset_set_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("external_feature_mapping_fingerprint", mode="before")
    @classmethod
    def _optional_fingerprint(cls, value):
        return None if value is None else _fingerprint(value, "external_feature_mapping_fingerprint")

    @field_validator(
        "candidate_artifact_fingerprints",
        "candidate_adapter_fingerprints",
        "asset_verification_receipt_fingerprints",
        "evidence_fingerprints",
        "abstain_reasons",
        mode="before",
    )
    @classmethod
    def _fingerprint_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        values = tuple(value)
        if info.field_name == "abstain_reasons":
            return values
        if any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in values):
            raise ValueError(f"{info.field_name} must contain SHA-256 fingerprints")
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return values

    @field_validator("preflight_id", mode="before")
    @classmethod
    def _preflight_id(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"p16r_preflight_[0-9a-f]{24}", value):
            raise ValueError("preflight_id must be a canonical P16R preflight ID")
        return value

    @model_validator(mode="after")
    def _closed_negative_record(self):
        if (
            self.asset_verification_receipt_fingerprints
            or self.evidence_fingerprints
            or self.abstain_reasons != _REASONS
            or self.candidate_card_fingerprint != self.candidate_model_fingerprint
            or len(self.candidate_artifact_fingerprints) != 1
            or len(self.candidate_adapter_fingerprints) != 1
        ):
            raise ValueError("preflight must retain the fixed value-free abstention closure")
        asset_payload = {
            "candidate_card_fingerprint": self.candidate_card_fingerprint,
            "candidate_model_fingerprint": self.candidate_model_fingerprint,
            "candidate_release_fingerprint": self.candidate_release_fingerprint,
            "candidate_artifact_fingerprints": list(self.candidate_artifact_fingerprints),
            "candidate_environment_fingerprint": self.candidate_environment_fingerprint,
            "candidate_adapter_fingerprints": list(self.candidate_adapter_fingerprints),
            "candidate_provenance_manifest_fingerprint": self.candidate_provenance_manifest_fingerprint,
            "golden_data_binding_fingerprint": self.golden_data_binding_fingerprint,
            "execution_binding_fingerprint": self.execution_binding_fingerprint,
            "external_pack_fingerprint": self.external_pack_fingerprint,
            "external_dataset_fingerprint": self.external_dataset_fingerprint,
            "external_platform_fingerprint": self.external_platform_fingerprint,
            "external_scope_declaration_fingerprint": self.external_scope_declaration_fingerprint,
            "external_scope_manifest_fingerprint": self.external_scope_manifest_fingerprint,
            "external_feature_ids_sha256": self.external_feature_ids_sha256,
            "external_feature_records_sha256": self.external_feature_records_sha256,
            "external_feature_mapping_fingerprint": self.external_feature_mapping_fingerprint,
            "group_records_fingerprint": self.group_records_fingerprint,
            "benchmark_protocol_fingerprint": self.benchmark_protocol_fingerprint,
        }
        if self.asset_set_fingerprint != _canonical(asset_payload):
            raise ValueError("asset_set_fingerprint does not bind the selected identities")
        identity = self.model_dump(mode="json")
        identity.pop("preflight_id")
        if self.preflight_id != f"p16r_preflight_{_canonical(identity)[:24]}":
            raise ValueError("preflight_id does not bind the complete preflight")
        return self

    def to_dict(self) -> dict[str, Any]:
        if type(self) is not K562P16RAuthorizationPreflightV1:
            raise P16RPreflightError("preflight must have the exact canonical type")
        try:
            _reject_undeclared_model_fields(self, "preflight")
            normalised = K562P16RAuthorizationPreflightV1.model_validate(
                self.model_dump(mode="python", serialize_as_any=True)
            )
            _reject_model_type_drift(self, normalised, "preflight")
            return normalised.model_dump(mode="json")
        except (AdapterContractError, AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise P16RPreflightError("invalid preflight") from exc

    def fingerprint(self) -> str:
        return _canonical(self.to_dict())


def compile_k562_p16r_preflight(
    *,
    evaluation_scope: Literal["single_gene", "combination"],
    golden_data: K562GoldenDataBinding,
    p16_scope: K562GoldenPerturbationScope,
    p16_perturbation: K562GoldenPerturbationBinding,
    p16_compatibility: K562GoldenCompatibilityBinding,
    execution: K562GoldenExecutionBinding,
    p16_preregistration: K562GoldenValidationProtocol,
    candidate_card: ModelCard,
    candidate_registry: ModelRegistryV2,
    candidate_release_fingerprint: str,
    candidate_provenance_manifest_fingerprint: str,
    external_pack: PackManifest,
    external_dataset: DatasetBindingV1,
    external_scope: K562P16RExternalScopeDeclarationV1,
    group_records: Sequence[GroupIdentityV1],
    protocol: BenchmarkProtocolV1,
) -> K562P16RAuthorizationPreflightV1:
    """Compile exact identities for a future authorization; never run P16R."""

    if evaluation_scope not in {"single_gene", "combination"}:
        raise P16RPreflightError("evaluation_scope must be single_gene or combination")
    golden_data = _normalise(golden_data, K562GoldenDataBinding, "golden_data")
    p16_scope = _normalise(p16_scope, K562GoldenPerturbationScope, "p16_scope")
    p16_perturbation = _normalise(p16_perturbation, K562GoldenPerturbationBinding, "p16_perturbation")
    p16_compatibility = _normalise(p16_compatibility, K562GoldenCompatibilityBinding, "p16_compatibility")
    execution = _normalise(execution, K562GoldenExecutionBinding, "execution")
    p16_preregistration = _normalise(p16_preregistration, K562GoldenValidationProtocol, "p16_preregistration")
    candidate_card = _normalise(candidate_card, ModelCard, "candidate_card")
    candidate_registry = _normalise(candidate_registry, ModelRegistryV2, "candidate_registry")
    external_pack = _normalise(external_pack, PackManifest, "external_pack")
    external_dataset = _normalise(external_dataset, DatasetBindingV1, "external_dataset")
    external_scope = _normalise(external_scope, K562P16RExternalScopeDeclarationV1, "external_scope")
    protocol = _normalise(protocol, BenchmarkProtocolV1, "protocol")
    try:
        candidate_release_fingerprint = _fingerprint(candidate_release_fingerprint, "candidate_release_fingerprint")
        candidate_provenance_manifest_fingerprint = _fingerprint(
            candidate_provenance_manifest_fingerprint, "candidate_provenance_manifest_fingerprint"
        )
    except ValueError as exc:
        raise P16RPreflightError("invalid candidate identity fingerprint") from exc
    groups = _normalise_groups(group_records)

    expected_kind = "gene" if evaluation_scope == "single_gene" else "gene_combination"
    adapter = K562GoldenPerturbationAdapter()
    adapter_fingerprint = adapter.fingerprint()
    if (
        p16_scope.evaluation_scope != evaluation_scope
        or p16_perturbation.evaluation_scope != evaluation_scope
        or p16_perturbation.perturbation_kind != expected_kind
        or p16_scope.perturbation_binding_fingerprint != p16_perturbation.fingerprint()
        or p16_scope.data_binding_fingerprint != golden_data.fingerprint()
        or p16_scope.execution_binding_fingerprint != execution.fingerprint()
        or p16_scope.compatibility_fingerprint != p16_compatibility.fingerprint()
        or p16_scope.pack_fingerprint != golden_data.pack_fingerprint
        or p16_preregistration.scope_fingerprint != p16_scope.fingerprint()
        or p16_preregistration.data_binding_fingerprint != golden_data.fingerprint()
    ):
        raise P16RPreflightError("P16 per-condition scope closure is inconsistent")
    if (
        p16_compatibility.pack_fingerprint != golden_data.pack_fingerprint
        or p16_compatibility.data_binding_fingerprint != golden_data.fingerprint()
        or p16_compatibility.execution_binding_fingerprint != execution.fingerprint()
        or p16_compatibility.assets_verified
        or p16_compatibility.executable
    ):
        raise P16RPreflightError("P16 compatibility must remain the fixed negative declaration")
    if (
        execution.feature_ids_sha256 != golden_data.feature_ids_sha256
        or execution.feature_records_sha256 != golden_data.feature_records_sha256
        or execution.execution_mode != "native_delta_expression"
    ):
        raise P16RPreflightError("execution binding does not preserve native Golden delta semantics")

    releases = {release.fingerprint(): release for release in candidate_registry.releases}
    try:
        release = releases[candidate_release_fingerprint]
    except KeyError as exc:
        raise P16RPreflightError("selected candidate release is absent from the registry") from exc
    lifecycle = candidate_registry.state(release.fingerprint())
    artifacts = {item.fingerprint(): item for item in candidate_registry.artifacts}
    environments = {item.fingerprint(): item for item in candidate_registry.environments}
    adapters = {item.fingerprint(): item for item in candidate_registry.adapters}
    if (
        release.migration_status != "native"
        or release.evidence_fingerprints
        or release.policy_fingerprint is not None
        or release.pack_fingerprints != (golden_data.pack_fingerprint,)
        or release.model_fingerprint != candidate_card.fingerprint()
        or (release.model_name, release.model_version) != (candidate_card.name, candidate_card.version)
        or release.environment_fingerprint is None
        or release.adapter_fingerprints != (adapter_fingerprint,)
        or release.artifact_fingerprints != (p16_scope.model_artifact_fingerprint,)
        or lifecycle.revoked
        or lifecycle.superseded_by is not None
    ):
        raise P16RPreflightError("candidate release does not exactly match the P16 scope")
    try:
        artifact = artifacts[p16_scope.model_artifact_fingerprint]
        environment = environments[release.environment_fingerprint]
        registered_adapter = adapters[adapter_fingerprint]
    except KeyError as exc:
        raise P16RPreflightError("candidate release closure is incomplete") from exc
    if (
        artifact.model_fingerprint != candidate_card.fingerprint()
        or artifact.safe_load_policy != "data_only"
        or artifact.media_type != "application/json"
        or environment.legacy_incomplete
        or environment.adapter_fingerprints != (adapter_fingerprint,)
        or registered_adapter.legacy_incomplete
        or registered_adapter.task != "predict_delta_expression"
        or registered_adapter.outputs != ("delta_expression",)
        or registered_adapter.input_contract_fingerprint != adapter.input_contract.fingerprint()
        or registered_adapter.output_contract_fingerprint != adapter.output_contract.fingerprint()
        or p16_scope.model_fingerprint != candidate_card.fingerprint()
        or p16_scope.model_release_fingerprint != release.fingerprint()
        or p16_scope.environment_fingerprint != environment.fingerprint()
        or p16_scope.adapter_fingerprint != adapter_fingerprint
        or p16_compatibility.model_fingerprint != candidate_card.fingerprint()
        or p16_compatibility.model_release_fingerprint != release.fingerprint()
        or p16_compatibility.artifact_fingerprint != artifact.fingerprint()
        or p16_compatibility.environment_fingerprint != environment.fingerprint()
        or p16_compatibility.adapter_fingerprint != adapter_fingerprint
    ):
        raise P16RPreflightError("candidate artifact, environment, or adapter closure is inconsistent")
    if (
        candidate_card.status != "available"
        or candidate_card.species != ("human",)
        or candidate_card.taxon != ("NCBITaxon:9606",)
        or candidate_card.assay != ("EFO:0008913",)
        or tuple((item.name, item.ontology_id) for item in candidate_card.modality) != (("scRNA", "EFO:0008913"),)
        or candidate_card.cell_domain.cell_type_names != ("K562",)
        or candidate_card.cell_domain.cell_type_ids != ("CVCL_0004",)
        or candidate_card.perturbation != (expected_kind,)
        or candidate_card.task != "predict_delta_expression"
        or candidate_card.output != ("delta_expression",)
        or len(candidate_card.feature_namespace) != 1
        or (
            candidate_card.feature_namespace[0].name,
            candidate_card.feature_namespace[0].version,
            candidate_card.feature_namespace[0].id_format,
        )
        != ("EnsemblGene", "Ensembl 84", "ensembl_gene")
    ):
        raise P16RPreflightError("candidate card is not an exact K562 P16 candidate declaration")
    card_assets = sorted((item.sha256, item.media_type) for item in candidate_card.assets)
    release_assets = sorted((item.sha256, item.media_type) for item in (artifact,))
    if card_assets != release_assets:
        raise P16RPreflightError("candidate card assets do not bind the selected release artifact")

    if (
        external_pack.fingerprint() == golden_data.pack_fingerprint
        or external_pack.schema_version != "vc.pack.v0.2"
        or external_pack.taxon.ontology_id != golden_data.taxonomy_id
        or external_pack.taxon.scientific_name != golden_data.scientific_name
        or external_pack.assembly.name != golden_data.assembly_name
        or external_pack.assembly.accession != golden_data.assembly_accession
        or external_pack.modality is None
        or (external_pack.modality.name, external_pack.modality.ontology_id)
        != (golden_data.modality_name, golden_data.modality_id)
        or external_pack.feature_namespace is None
        or (
            external_pack.feature_namespace.name,
            external_pack.feature_namespace.version,
        )
        != (golden_data.feature_namespace, golden_data.feature_namespace_version)
        or external_pack.feature_semantics is None
        or external_pack.feature_semantics.id_format != golden_data.feature_id_format
    ):
        raise P16RPreflightError("external Pack is not an independent compatible human scRNA declaration")
    if (
        external_scope.pack_fingerprint != external_pack.fingerprint()
        or external_scope.dataset_fingerprint != external_dataset.dataset_fingerprint
        or external_scope.platform_fingerprint != external_dataset.platform_fingerprint
        or external_scope.feature_namespace != external_pack.feature_namespace.name
        or external_scope.feature_namespace_version != external_pack.feature_namespace.version
        or external_scope.feature_id_format != external_pack.feature_semantics.id_format
        or external_scope.adaptation_steps != 0
        or external_scope.asset_bytes_verified
        or external_scope.record_membership_verified
    ):
        raise P16RPreflightError("external K562 scope declaration is not bound to the selected identities")

    if (
        protocol.task != "predict_delta_expression"
        or protocol.pack_fingerprint != golden_data.pack_fingerprint
        # P16R v1 explicitly defines the P21 internal dataset/platform and
        # feature/output identities as these frozen P16 identities.
        or protocol.dataset.dataset_fingerprint != golden_data.h5ad_sha256
        or protocol.dataset.platform_fingerprint != golden_data.artifact_manifest_sha256
        or protocol.feature_contract_fingerprint != adapter.input_contract.fingerprint()
        or protocol.output_contract_fingerprint != adapter.output_contract.fingerprint()
        or (
            protocol.scope.organism,
            protocol.scope.cell_type,
            protocol.scope.intervention,
            protocol.scope.endpoint,
        )
        != (
            golden_data.scientific_name,
            "K562",
            f"CRISPR activation:{evaluation_scope}",
            p16_preregistration.primary_metric,
        )
        or protocol.baseline.baseline_id != p16_preregistration.primary_comparator
        or protocol.baseline.kind != "declared_simple"
        or not protocol.baseline.simple
        or protocol.primary_metric.name != p16_preregistration.primary_metric
        or protocol.primary_metric.direction != p16_preregistration.metric_direction
        or protocol.confidence_interval.group_unit != p16_preregistration.bootstrap_unit
        or protocol.confidence_interval.rng != p16_preregistration.bootstrap_rng
        or protocol.confidence_interval.replicates != p16_preregistration.bootstrap_replicates
        or protocol.confidence_interval.seed != p16_preregistration.bootstrap_seed
        or protocol.seeds != p16_preregistration.stochastic_seeds
        or tuple(item.axis for item in protocol.ood_policy) != p16_preregistration.ood_axes
        or protocol.external_policy.dataset_fingerprint != external_dataset.dataset_fingerprint
        or protocol.external_policy.platform_fingerprint != external_dataset.platform_fingerprint
        or protocol.external_policy.adaptation_steps != p16_preregistration.external_adaptation_steps
    ):
        raise P16RPreflightError("P21 protocol does not preserve the frozen P16 scope")

    group_rows = [item.to_dict() for item in groups]
    if (
        len(groups) != protocol.split.leakage_record_count
        or _canonical(group_rows) != protocol.split.leakage_records_fingerprint
        or tuple(item.group_id for item in groups if item.partition == "validation")
        != protocol.split.validation_group_ids
        or tuple(item.group_id for item in groups if item.partition == "test") != protocol.split.test_group_ids
        or tuple(item.group_id for item in groups if item.partition == "external") != protocol.split.external_group_ids
    ):
        raise P16RPreflightError("group identities do not bind the frozen P21 split")

    values = {
        "schema_version": "vc.k562-p16r-authorization-preflight.v1",
        "evaluation_scope": evaluation_scope,
        "source_per_condition_scope_fingerprint": p16_scope.fingerprint(),
        "source_perturbation_binding_fingerprint": p16_perturbation.fingerprint(),
        "golden_data_binding_fingerprint": golden_data.fingerprint(),
        "golden_pack_fingerprint": golden_data.pack_fingerprint,
        "golden_h5ad_sha256": golden_data.h5ad_sha256,
        "golden_feature_ids_sha256": golden_data.feature_ids_sha256,
        "golden_feature_records_sha256": golden_data.feature_records_sha256,
        "execution_binding_fingerprint": execution.fingerprint(),
        "p16_preregistration_fingerprint": p16_preregistration.fingerprint(),
        "candidate_card_fingerprint": candidate_card.fingerprint(),
        "candidate_model_fingerprint": candidate_card.fingerprint(),
        "candidate_release_fingerprint": release.fingerprint(),
        "candidate_artifact_fingerprints": [artifact.fingerprint()],
        "candidate_environment_fingerprint": environment.fingerprint(),
        "candidate_adapter_fingerprints": [adapter_fingerprint],
        "candidate_provenance_manifest_fingerprint": candidate_provenance_manifest_fingerprint,
        "external_pack_fingerprint": external_pack.fingerprint(),
        "external_dataset_fingerprint": external_dataset.dataset_fingerprint,
        "external_platform_fingerprint": external_dataset.platform_fingerprint,
        "external_scope_declaration_fingerprint": external_scope.fingerprint(),
        "external_scope_manifest_fingerprint": external_scope.scope_manifest_fingerprint,
        "external_feature_ids_sha256": external_scope.feature_ids_sha256,
        "external_feature_records_sha256": external_scope.feature_records_sha256,
        "external_feature_mapping_fingerprint": external_scope.feature_mapping_fingerprint,
        "group_records_fingerprint": _canonical(group_rows),
        "benchmark_protocol_fingerprint": protocol.fingerprint(),
        "benchmark_scope_fingerprint": protocol.scope.fingerprint(),
        "benchmark_split_fingerprint": protocol.split.fingerprint(),
        "benchmark_baseline_fingerprint": protocol.baseline.fingerprint(),
        "benchmark_feature_contract_fingerprint": protocol.feature_contract_fingerprint,
        "benchmark_output_contract_fingerprint": protocol.output_contract_fingerprint,
        "record_role": "authorization_preflight_not_evidence",
        "authorization_fingerprint": None,
        "asset_verification_receipt_fingerprints": [],
        "assets_verified": False,
        "record_membership_verified": False,
        "leakage_audit_fingerprint": None,
        "benchmark_passed": None,
        "scientifically_validated": False,
        "promotion_eligible": None,
        "evidence_fingerprints": [],
        "policy_fingerprint": None,
        "production_promoted": False,
        "executable": False,
        "abstain": True,
        "prediction": None,
        "abstain_reasons": list(_REASONS),
    }
    values["asset_set_fingerprint"] = _canonical(
        {
            key: values[key]
            for key in (
                "candidate_card_fingerprint",
                "candidate_model_fingerprint",
                "candidate_release_fingerprint",
                "candidate_artifact_fingerprints",
                "candidate_environment_fingerprint",
                "candidate_adapter_fingerprints",
                "candidate_provenance_manifest_fingerprint",
                "golden_data_binding_fingerprint",
                "execution_binding_fingerprint",
                "external_pack_fingerprint",
                "external_dataset_fingerprint",
                "external_platform_fingerprint",
                "external_scope_declaration_fingerprint",
                "external_scope_manifest_fingerprint",
                "external_feature_ids_sha256",
                "external_feature_records_sha256",
                "external_feature_mapping_fingerprint",
                "group_records_fingerprint",
                "benchmark_protocol_fingerprint",
            )
        }
    )
    values["preflight_id"] = f"p16r_preflight_{_canonical(values)[:24]}"
    return K562P16RAuthorizationPreflightV1.model_validate(values)
