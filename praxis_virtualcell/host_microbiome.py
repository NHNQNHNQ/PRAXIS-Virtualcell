"""P26E host–microbiome requirements with deterministic abstention.

P22 v1 does not bind a complete P26 host request and P25E is not a community
release.  This module therefore records typed requirements and a time-unrolled
DAG, audits an optional P22 context candidate, and always returns a value-free
negative compilation.  It performs no model execution, evidence derivation,
policy decision, mediator inference, or external I/O.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.benchmarks.system import BenchmarkScopeV1
from praxis_virtualcell.community_packs.contracts import RegisteredCommunityPack
from praxis_virtualcell.community_packs.virtual_microbiome import (
    VirtualMicrobiomeContractV1,
    VirtualMicrobiomeRequestV1,
    plan_virtual_microbiome,
)
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _Contract as _AdapterContract,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _fingerprint as _canonical_fingerprint,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
    _strict_fingerprint,
    _strict_text,
)
from praxis_virtualcell.model_zoo.curated_registry import (
    CuratedRegistryError,
    CuratedVirtualCellRegistry,
    VirtualCellContextV1,
)

_COMPILATION_ID = re.compile(r"^hm_comp_[0-9a-f]{24}$")
_INTERFACE_ENTITIES = ("metabolite", "cytokine", "receptor")
_IDENTITY_DIMENSIONS = (
    "namespace",
    "namespace_version",
    "identifier",
    "compartment",
    "dose_value",
    "dose_unit",
    "time_value",
    "time_unit",
)
_DIRECTIONS = ("microbe_to_mediator_to_host", "host_to_community")
_NODES = (
    "community_state_t0",
    "mediator_state_t1",
    "host_state_t2",
    "community_state_t3",
)
_EDGES = (
    "community_state_t0|microbe_to_mediator|mediator_state_t1",
    "mediator_state_t1|mediator_to_host|host_state_t2",
    "host_state_t2|host_to_community|community_state_t3",
)
_REASON_ORDER = (
    "unsupported_host_microbiome_scope",
    "matching_host_release_unavailable",
    "matching_community_release_unavailable",
    "matching_release_unavailable",
    "cross_domain_interface_unavailable",
    "p26_real_execution_not_authorized",
)
_MANDATORY_REASONS = _REASON_ORDER[1:]
_P25_SCOPE_FAILURES = {
    "member_pack_revalidation_failed",
    "stale_community_identity",
    "unsupported_virtual_microbiome_scope",
}


class HostMicrobiomeContractError(ValueError):
    """A P26E identity is malformed or cannot be verified safely."""


def _optional_fingerprint(value: Any, field: str) -> str | None:
    return None if value is None else _strict_fingerprint(value, field)


def _exact_bool(value: Any, field: str, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{field} must be exactly {expected}")
    return value


def _exact_array(value: Any, expected: tuple[str, ...], field: str) -> tuple[str, ...]:
    if type(value) is not list or tuple(value) != expected:
        raise ValueError(f"{field} must equal {list(expected)}")
    return tuple(value)


def _content_id(prefix: str, value: dict[str, Any]) -> str:
    return f"{prefix}{_canonical_fingerprint(value)[:24]}"


class _P26Contract(_AdapterContract):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if type(value) is not dict:
            raise HostMicrobiomeContractError(f"{cls.__name__} must be an exact JSON object")
        try:
            return cls.model_validate(value)
        except (TypeError, ValidationError, ValueError) as exc:
            raise HostMicrobiomeContractError(f"invalid {cls.__name__}: {exc}") from exc


def _host_request(value: Any) -> VirtualCellRequestV2:
    try:
        _reject_undeclared_model_fields(value, "host_request")
        if type(value) is not VirtualCellRequestV2:
            raise TypeError("host_request must be exact VirtualCellRequestV2")
        request = VirtualCellRequestV2.from_dict(value.to_dict())
        _reject_model_type_drift(value, request, "host_request")
    except (InputValidationError, TypeError, ValidationError, ValueError) as exc:
        raise HostMicrobiomeContractError(f"invalid host request: {exc}") from exc
    if (
        request.cell_context.cell_type_name is None
        or request.cell_context.cell_type_id is None
        or request.cell_context.tissue_name is None
        or request.cell_context.tissue_id is None
        or len(request.task.requested_outputs) != 1
    ):
        raise HostMicrobiomeContractError("host request needs exact cell type, tissue, and one requested output")
    return request


def _community_contract(value: Any) -> VirtualMicrobiomeContractV1:
    try:
        _reject_undeclared_model_fields(value, "community_contract")
        if type(value) is not VirtualMicrobiomeContractV1:
            raise TypeError("community_contract must be exact VirtualMicrobiomeContractV1")
        contract = VirtualMicrobiomeContractV1.model_validate(value.to_dict())
        _reject_model_type_drift(value, contract, "community_contract")
    except (TypeError, ValidationError, ValueError) as exc:
        raise HostMicrobiomeContractError(f"invalid community contract: {exc}") from exc
    if contract.record_role != "p25e_contract_only":
        raise HostMicrobiomeContractError("P26E accepts only the explicit P25E contract-only role")
    return contract


def _host_request_fingerprint(request: VirtualCellRequestV2) -> str:
    return _canonical_fingerprint(request.to_dict())


def _host_context_for_request(request: VirtualCellRequestV2) -> VirtualCellContextV1:
    assert request.cell_context.cell_type_name is not None
    intervention = json.dumps(
        request.perturbation.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    scope = BenchmarkScopeV1.from_dict(
        {
            "schema_version": "vc.benchmark-scope.v1",
            "organism": request.species.scientific_name,
            "cell_type": request.cell_context.cell_type_name,
            "intervention": intervention,
            "endpoint": request.task.requested_outputs[0],
        }
    )
    return VirtualCellContextV1.from_dict(
        {
            "schema_version": "vc.virtual-cell-context.v1",
            "context_id": f"p26e-{_host_request_fingerprint(request)[:16]}",
            "organism": scope.organism,
            "cell_type": scope.cell_type,
            "intervention": scope.intervention,
            "endpoint": scope.endpoint,
            "benchmark_scope_fingerprint": scope.fingerprint(),
        }
    )


class HostMicrobiomeInterfaceRequirementV1(_P26Contract):
    """Typed interface requirements with every real binding explicitly absent."""

    schema_version: Literal["vc.host-microbiome-interface-requirement.v1"]
    community_scope_fingerprint: str
    compartment_id: str
    medium_fingerprint: str
    time_fingerprint: str
    interface_entity_kinds: tuple[str, ...]
    identity_dimensions: tuple[str, ...]
    directions: tuple[str, ...]
    mapping_fingerprint: None
    source_output_contract_fingerprint: None
    target_input_contract_fingerprint: None
    implementation_available: Literal[False]
    implicit_unit_conversion_allowed: Literal[False]
    imputation_allowed: Literal[False]
    causal_claim_allowed: Literal[False]
    record_role: Literal["p26e_typed_missing_interface"]

    @field_validator(
        "community_scope_fingerprint",
        "medium_fingerprint",
        "time_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("compartment_id", mode="before")
    @classmethod
    def _compartment(cls, value):
        return _strict_text(value, "compartment_id")

    @field_validator("interface_entity_kinds", mode="before")
    @classmethod
    def _entities(cls, value):
        return _exact_array(value, _INTERFACE_ENTITIES, "interface_entity_kinds")

    @field_validator("identity_dimensions", mode="before")
    @classmethod
    def _dimensions(cls, value):
        return _exact_array(value, _IDENTITY_DIMENSIONS, "identity_dimensions")

    @field_validator("directions", mode="before")
    @classmethod
    def _directions(cls, value):
        return _exact_array(value, _DIRECTIONS, "directions")

    @field_validator(
        "implementation_available",
        "implicit_unit_conversion_allowed",
        "imputation_allowed",
        "causal_claim_allowed",
        mode="before",
    )
    @classmethod
    def _negative(cls, value, info):
        return _exact_bool(value, info.field_name, False)

    @classmethod
    def for_community(
        cls,
        contract: VirtualMicrobiomeContractV1,
    ) -> HostMicrobiomeInterfaceRequirementV1:
        return cls(
            schema_version="vc.host-microbiome-interface-requirement.v1",
            community_scope_fingerprint=contract.scope_fingerprint,
            compartment_id=contract.scope.compartment_id,
            medium_fingerprint=contract.scope.medium_fingerprint,
            time_fingerprint=contract.scope.time_fingerprint,
            interface_entity_kinds=list(_INTERFACE_ENTITIES),
            identity_dimensions=list(_IDENTITY_DIMENSIONS),
            directions=list(_DIRECTIONS),
            mapping_fingerprint=None,
            source_output_contract_fingerprint=None,
            target_input_contract_fingerprint=None,
            implementation_available=False,
            implicit_unit_conversion_allowed=False,
            imputation_allowed=False,
            causal_claim_allowed=False,
            record_role="p26e_typed_missing_interface",
        )


class HostMicrobiomeDAGV1(_P26Contract):
    """A fixed time-forward topology of required, non-executable states."""

    schema_version: Literal["vc.host-microbiome-dag.v1"]
    host_request_fingerprint: str
    host_context_fingerprint: str
    community_contract_fingerprint: str
    community_scope_fingerprint: str
    interface_requirement_fingerprint: str
    compartment_id: str
    time_fingerprint: str
    nodes: tuple[str, ...]
    edges: tuple[str, ...]
    time_unrolled: Literal[True]
    record_role: Literal["p26e_required_topology_only"]

    @field_validator(
        "host_request_fingerprint",
        "host_context_fingerprint",
        "community_contract_fingerprint",
        "community_scope_fingerprint",
        "interface_requirement_fingerprint",
        "time_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("compartment_id", mode="before")
    @classmethod
    def _compartment(cls, value):
        return _strict_text(value, "compartment_id")

    @field_validator("nodes", mode="before")
    @classmethod
    def _nodes(cls, value):
        return _exact_array(value, _NODES, "nodes")

    @field_validator("edges", mode="before")
    @classmethod
    def _edges(cls, value):
        return _exact_array(value, _EDGES, "edges")

    @field_validator("time_unrolled", mode="before")
    @classmethod
    def _time_unrolled(cls, value):
        return _exact_bool(value, "time_unrolled", True)

    @classmethod
    def for_bindings(
        cls,
        host_request: VirtualCellRequestV2,
        host_context: VirtualCellContextV1,
        community_contract: VirtualMicrobiomeContractV1,
        interface: HostMicrobiomeInterfaceRequirementV1,
    ) -> HostMicrobiomeDAGV1:
        return cls(
            schema_version="vc.host-microbiome-dag.v1",
            host_request_fingerprint=_host_request_fingerprint(host_request),
            host_context_fingerprint=host_context.fingerprint(),
            community_contract_fingerprint=community_contract.fingerprint(),
            community_scope_fingerprint=community_contract.scope_fingerprint,
            interface_requirement_fingerprint=interface.fingerprint(),
            compartment_id=community_contract.scope.compartment_id,
            time_fingerprint=community_contract.scope.time_fingerprint,
            nodes=list(_NODES),
            edges=list(_EDGES),
            time_unrolled=True,
            record_role="p26e_required_topology_only",
        )


def _joint_scope_fingerprint(
    *,
    host_request_fingerprint: str,
    host_context_fingerprint: str,
    host_pack_fingerprint: str | None,
    community_scope_fingerprint: str,
    interface_fingerprint: str,
    dag_fingerprint: str,
) -> str:
    return _canonical_fingerprint(
        {
            "schema_version": "vc.host-microbiome-joint-scope.v1",
            "task": "host_microbiome_joint_response",
            "host_request_fingerprint": host_request_fingerprint,
            "host_context_fingerprint": host_context_fingerprint,
            "host_pack_fingerprint": host_pack_fingerprint,
            "community_scope_fingerprint": community_scope_fingerprint,
            "interface_requirement_fingerprint": interface_fingerprint,
            "dag_fingerprint": dag_fingerprint,
        }
    )


class HostMicrobiomeContractV1(_P26Contract):
    schema_version: Literal["vc.host-microbiome-contract.v1"]
    task: Literal["host_microbiome_joint_response"]
    host_request: VirtualCellRequestV2
    host_request_fingerprint: str
    host_context: VirtualCellContextV1
    host_context_fingerprint: str
    required_host_pack_fingerprint: str | None
    required_host_release_fingerprint: str | None
    required_host_request_binding_fingerprint: None
    community_contract: VirtualMicrobiomeContractV1
    community_contract_fingerprint: str
    community_scope_fingerprint: str
    interface_requirement: HostMicrobiomeInterfaceRequirementV1
    interface_requirement_fingerprint: str
    dag: HostMicrobiomeDAGV1
    dag_fingerprint: str
    joint_scope_fingerprint: str
    required_community_release_schema_version: None
    required_community_release_fingerprint: None
    required_matching_release_fingerprint: None
    record_role: Literal["p26e_contract_only_missing_releases"]

    @field_validator(
        "host_request_fingerprint",
        "host_context_fingerprint",
        "community_contract_fingerprint",
        "community_scope_fingerprint",
        "interface_requirement_fingerprint",
        "dag_fingerprint",
        "joint_scope_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "required_host_pack_fingerprint",
        "required_host_release_fingerprint",
        mode="before",
    )
    @classmethod
    def _optional_fingerprints(cls, value, info):
        return _optional_fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _closure(self):
        request = _host_request(self.host_request)
        community = _community_contract(self.community_contract)
        try:
            _reject_undeclared_model_fields(self.host_context, "host_context")
            if type(self.host_context) is not VirtualCellContextV1:
                raise TypeError("host_context must be exact VirtualCellContextV1")
            context = VirtualCellContextV1.from_dict(self.host_context.to_dict())
            if type(self.interface_requirement) is not HostMicrobiomeInterfaceRequirementV1:
                raise TypeError("interface_requirement must be exact HostMicrobiomeInterfaceRequirementV1")
            interface = HostMicrobiomeInterfaceRequirementV1.model_validate(self.interface_requirement.to_dict())
            if type(self.dag) is not HostMicrobiomeDAGV1:
                raise TypeError("dag must be exact HostMicrobiomeDAGV1")
            dag = HostMicrobiomeDAGV1.model_validate(self.dag.to_dict())
        except (TypeError, ValidationError, ValueError) as exc:
            raise ValueError("contract contains a non-canonical nested identity") from exc
        if (self.required_host_release_fingerprint is None) != (self.required_host_pack_fingerprint is None):
            raise ValueError("host Pack and release fingerprints must be supplied together")
        if _host_request_fingerprint(request) != self.host_request_fingerprint:
            raise ValueError("host_request_fingerprint is stale")
        if context.fingerprint() != self.host_context_fingerprint:
            raise ValueError("host_context_fingerprint is stale")
        if _host_context_for_request(request) != context:
            raise ValueError("host context does not match the exact host request")
        if community.fingerprint() != self.community_contract_fingerprint:
            raise ValueError("community_contract_fingerprint is stale")
        if community.scope_fingerprint != self.community_scope_fingerprint:
            raise ValueError("community_scope_fingerprint is stale")
        expected_interface = HostMicrobiomeInterfaceRequirementV1.for_community(community)
        if interface != expected_interface or interface.fingerprint() != self.interface_requirement_fingerprint:
            raise ValueError("interface requirement does not match the P25 scope")
        expected_dag = HostMicrobiomeDAGV1.for_bindings(request, context, community, interface)
        if dag != expected_dag or dag.fingerprint() != self.dag_fingerprint:
            raise ValueError("DAG does not match the exact contract bindings")
        expected_joint = _joint_scope_fingerprint(
            host_request_fingerprint=self.host_request_fingerprint,
            host_context_fingerprint=self.host_context_fingerprint,
            host_pack_fingerprint=self.required_host_pack_fingerprint,
            community_scope_fingerprint=self.community_scope_fingerprint,
            interface_fingerprint=self.interface_requirement_fingerprint,
            dag_fingerprint=self.dag_fingerprint,
        )
        if self.joint_scope_fingerprint != expected_joint:
            raise ValueError("joint_scope_fingerprint is stale")
        return self


HostReleaseAuditStatus = Literal[
    "required_release_unbound",
    "registry_unavailable",
    "registry_verification_failed",
    "registry_checkpoint_unverified",
    "release_not_found",
    "release_mismatch",
    "release_inactive",
    "release_not_positive",
    "p22_context_matched_request_binding_insufficient",
]


class HostReleaseAuditSnapshotV1(_P26Contract):
    """Negative audit of one P22 catalog read, never an execution authority."""

    schema_version: Literal["vc.host-release-audit-snapshot.v1"]
    expected_release_fingerprint: str | None
    expected_context_fingerprint: str
    expected_benchmark_scope_fingerprint: str
    expected_pack_fingerprint: str | None
    expected_full_host_request_fingerprint: str
    full_host_request_binding_fingerprint: None
    registry_fingerprint: str | None
    catalog_row_fingerprint: str | None
    revocation_checkpointed: bool | None
    audit_status: HostReleaseAuditStatus
    scientifically_validated_for_full_request: None
    production_promoted_for_full_request: None
    exact_request_match_verified: Literal[False]

    @field_validator(
        "expected_context_fingerprint",
        "expected_benchmark_scope_fingerprint",
        "expected_full_host_request_fingerprint",
        mode="before",
    )
    @classmethod
    def _required_fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "expected_release_fingerprint",
        "expected_pack_fingerprint",
        "registry_fingerprint",
        "catalog_row_fingerprint",
        mode="before",
    )
    @classmethod
    def _optional_fingerprints(cls, value, info):
        return _optional_fingerprint(value, info.field_name)

    @field_validator("revocation_checkpointed", mode="before")
    @classmethod
    def _checkpointed(cls, value):
        if value is not None and type(value) is not bool:
            raise ValueError("revocation_checkpointed must be boolean or null")
        return value

    @field_validator("exact_request_match_verified", mode="before")
    @classmethod
    def _never_exact(cls, value):
        return _exact_bool(value, "exact_request_match_verified", False)

    @model_validator(mode="after")
    def _negative_closure(self):
        if (self.expected_release_fingerprint is None) != (self.expected_pack_fingerprint is None):
            raise ValueError("expected host Pack and release identities must be absent together")
        if self.audit_status == "required_release_unbound":
            if self.expected_release_fingerprint is not None:
                raise ValueError("unbound audit cannot contain an expected release")
        elif self.expected_release_fingerprint is None:
            raise ValueError("bound audit status requires an expected release")
        if self.audit_status == "p22_context_matched_request_binding_insufficient":
            if (
                self.registry_fingerprint is None
                or self.catalog_row_fingerprint is None
                or self.revocation_checkpointed is not True
            ):
                raise ValueError("matched P22 context audit is missing its catalog snapshot")
        return self


def _audit_snapshot(
    contract: HostMicrobiomeContractV1,
    status: HostReleaseAuditStatus,
    *,
    registry_fingerprint: str | None = None,
    catalog_row_fingerprint: str | None = None,
    checkpointed: bool | None = None,
) -> HostReleaseAuditSnapshotV1:
    return HostReleaseAuditSnapshotV1(
        schema_version="vc.host-release-audit-snapshot.v1",
        expected_release_fingerprint=contract.required_host_release_fingerprint,
        expected_context_fingerprint=contract.host_context_fingerprint,
        expected_benchmark_scope_fingerprint=contract.host_context.benchmark_scope_fingerprint,
        expected_pack_fingerprint=contract.required_host_pack_fingerprint,
        expected_full_host_request_fingerprint=contract.host_request_fingerprint,
        full_host_request_binding_fingerprint=None,
        registry_fingerprint=registry_fingerprint,
        catalog_row_fingerprint=catalog_row_fingerprint,
        revocation_checkpointed=checkpointed,
        audit_status=status,
        scientifically_validated_for_full_request=None,
        production_promoted_for_full_request=None,
        exact_request_match_verified=False,
    )


def audit_host_release_candidate(
    contract: HostMicrobiomeContractV1,
    registry: CuratedVirtualCellRegistry | None,
) -> HostReleaseAuditSnapshotV1:
    """Audit one exact P22 release candidate without promoting it to a P26 match."""

    contract = _normalize_contract(contract)
    if contract.required_host_release_fingerprint is None:
        return _audit_snapshot(contract, "required_release_unbound")
    if registry is None:
        return _audit_snapshot(contract, "registry_unavailable")
    if type(registry) is not CuratedVirtualCellRegistry:
        raise TypeError("host_registry must be exact CuratedVirtualCellRegistry or None")
    try:
        catalog = registry.public_catalog(include_inactive=True)
        if (
            type(catalog) is not dict
            or catalog.get("schema_version") != "vc.curated-virtual-cell-catalog.v1"
            or catalog.get("write_api_enabled") is not False
            or type(catalog.get("releases")) is not list
        ):
            raise ValueError("invalid curated catalog response")
        registry_fingerprint = _strict_fingerprint(catalog.get("registry_fingerprint"), "registry_fingerprint")
        checkpointed = catalog.get("revocation_checkpointed")
        if type(checkpointed) is not bool:
            raise ValueError("revocation_checkpointed must be boolean")
    except (CuratedRegistryError, OSError, TypeError, ValueError):
        return _audit_snapshot(contract, "registry_verification_failed")
    if not checkpointed:
        return _audit_snapshot(
            contract,
            "registry_checkpoint_unverified",
            registry_fingerprint=registry_fingerprint,
            checkpointed=False,
        )

    rows = [
        item
        for item in catalog["releases"]
        if type(item) is dict and item.get("release_fingerprint") == contract.required_host_release_fingerprint
    ]
    if len(rows) != 1:
        return _audit_snapshot(
            contract,
            "release_not_found",
            registry_fingerprint=registry_fingerprint,
            checkpointed=True,
        )
    row = rows[0]
    row_fingerprint = _canonical_fingerprint(row)
    context = contract.host_context
    available_identity_matches = (
        row.get("capability_scope_fingerprint") == context.benchmark_scope_fingerprint
        and row.get("pack_fingerprint") == contract.required_host_pack_fingerprint
        and (
            row.get("organism"),
            row.get("cell_type"),
            row.get("intervention"),
            row.get("endpoint"),
        )
        == (context.organism, context.cell_type, context.intervention, context.endpoint)
    )
    if not available_identity_matches:
        return _audit_snapshot(
            contract,
            "release_mismatch",
            registry_fingerprint=registry_fingerprint,
            catalog_row_fingerprint=row_fingerprint,
            checkpointed=True,
        )
    if not (
        row.get("cataloged") is True
        and row.get("quarantined") is False
        and row.get("revoked") is False
        and row.get("superseded_by") is None
    ):
        return _audit_snapshot(
            contract,
            "release_inactive",
            registry_fingerprint=registry_fingerprint,
            catalog_row_fingerprint=row_fingerprint,
            checkpointed=True,
        )
    if not (
        row.get("benchmark_passed") is True
        and row.get("scientifically_validated") is True
        and row.get("promotion_eligible") is True
        and row.get("production_promoted") is True
    ):
        return _audit_snapshot(
            contract,
            "release_not_positive",
            registry_fingerprint=registry_fingerprint,
            catalog_row_fingerprint=row_fingerprint,
            checkpointed=True,
        )
    return _audit_snapshot(
        contract,
        "p22_context_matched_request_binding_insufficient",
        registry_fingerprint=registry_fingerprint,
        catalog_row_fingerprint=row_fingerprint,
        checkpointed=True,
    )


class HostMicrobiomeCompilationV1(_P26Contract):
    """The sole P26E output: full provenance plus immutable abstention."""

    schema_version: Literal["vc.host-microbiome-compilation.v1"]
    compilation_id: str
    contract: HostMicrobiomeContractV1
    contract_fingerprint: str
    host_release_audit: HostReleaseAuditSnapshotV1
    host_release_audit_fingerprint: str
    current_community_fingerprint: str
    current_member_pack_fingerprints: tuple[str, ...]
    community_release_fingerprint: None
    community_scientifically_validated: None
    community_production_promoted: None
    matching_release_fingerprint: None
    matching_release_verified: Literal[False]
    steps: tuple[dict[str, str], ...]
    executable: Literal[False]
    abstain: Literal[True]
    prediction: None
    host_result: None
    community_result: None
    mediator_trace: None
    abstain_reasons: tuple[str, ...]
    execution_performed: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator("compilation_id", mode="before")
    @classmethod
    def _compilation_id(cls, value):
        if type(value) is not str or not _COMPILATION_ID.fullmatch(value):
            raise ValueError("compilation_id must be hm_comp_ plus 24 lowercase hex")
        return value

    @field_validator(
        "contract_fingerprint",
        "host_release_audit_fingerprint",
        "current_community_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("current_member_pack_fingerprints", mode="before")
    @classmethod
    def _member_packs(cls, value):
        if type(value) is not list or len(value) not in (2, 3):
            raise ValueError("current_member_pack_fingerprints must contain 2 or 3 items")
        values = tuple(_strict_fingerprint(item, "current_member_pack_fingerprints") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("current member Pack fingerprints must be unique")
        return values

    @field_validator("steps", mode="before")
    @classmethod
    def _empty_steps(cls, value):
        if type(value) is not list or value:
            raise ValueError("P26E steps must be an empty JSON array")
        return ()

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _reasons(cls, value):
        if type(value) is not list or not value or any(type(item) is not str for item in value):
            raise ValueError("abstain_reasons must be a non-empty string JSON array")
        if len(set(value)) != len(value) or any(item not in _REASON_ORDER for item in value):
            raise ValueError("abstain_reasons must contain unique known reasons")
        expected = tuple(reason for reason in _REASON_ORDER if reason in value)
        if tuple(value) != expected or not all(reason in value for reason in _MANDATORY_REASONS):
            raise ValueError("abstain_reasons must contain mandatory reasons in canonical order")
        return tuple(value)

    @field_validator("abstain", mode="before")
    @classmethod
    def _abstain(cls, value):
        return _exact_bool(value, "abstain", True)

    @field_validator(
        "matching_release_verified",
        "executable",
        "execution_performed",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
        mode="before",
    )
    @classmethod
    def _negative(cls, value, info):
        return _exact_bool(value, info.field_name, False)

    @model_validator(mode="after")
    def _closure(self):
        contract = _normalize_contract(self.contract)
        _reject_undeclared_model_fields(self.host_release_audit, "host_release_audit")
        if type(self.host_release_audit) is not HostReleaseAuditSnapshotV1:
            raise ValueError("host_release_audit must be exact HostReleaseAuditSnapshotV1")
        audit = HostReleaseAuditSnapshotV1.model_validate(self.host_release_audit.to_dict())
        if contract.fingerprint() != self.contract_fingerprint:
            raise ValueError("contract_fingerprint is stale")
        if audit.fingerprint() != self.host_release_audit_fingerprint:
            raise ValueError("host_release_audit_fingerprint is stale")
        if (
            audit.expected_release_fingerprint != contract.required_host_release_fingerprint
            or audit.expected_context_fingerprint != contract.host_context_fingerprint
            or audit.expected_benchmark_scope_fingerprint != contract.host_context.benchmark_scope_fingerprint
            or audit.expected_pack_fingerprint != contract.required_host_pack_fingerprint
            or audit.expected_full_host_request_fingerprint != contract.host_request_fingerprint
        ):
            raise ValueError("host release audit does not match the contract")
        identity = self.model_dump(mode="json", exclude={"compilation_id"})
        if self.compilation_id != _content_id("hm_comp_", identity):
            raise ValueError("compilation_id is stale")
        return self

    @property
    def dag(self) -> HostMicrobiomeDAGV1:
        return self.contract.dag

    @property
    def dag_fingerprint(self) -> str:
        return self.contract.dag_fingerprint


def _normalize_contract(value: Any) -> HostMicrobiomeContractV1:
    try:
        _reject_undeclared_model_fields(value, "contract")
        if type(value) is not HostMicrobiomeContractV1:
            raise TypeError("contract must be exact HostMicrobiomeContractV1")
        return HostMicrobiomeContractV1.model_validate(value.to_dict())
    except (TypeError, ValidationError, ValueError) as exc:
        raise HostMicrobiomeContractError(f"invalid host-microbiome contract: {exc}") from exc


def _p25_plan(community: RegisteredCommunityPack, contract: VirtualMicrobiomeContractV1):
    return plan_virtual_microbiome(
        community,
        contract,
        VirtualMicrobiomeRequestV1.for_contract(contract),
    )


def freeze_host_microbiome_contract(
    *,
    host_request: VirtualCellRequestV2,
    community: RegisteredCommunityPack,
    community_contract: VirtualMicrobiomeContractV1,
    required_host_pack_fingerprint: str | None = None,
    required_host_release_fingerprint: str | None = None,
) -> HostMicrobiomeContractV1:
    """Freeze one exact request and P25 scope without inventing host identities."""

    try:
        request = _host_request(host_request)
        p25 = _community_contract(community_contract)
        host_pack = _optional_fingerprint(required_host_pack_fingerprint, "required_host_pack_fingerprint")
        host_release = _optional_fingerprint(
            required_host_release_fingerprint,
            "required_host_release_fingerprint",
        )
        if (host_release is None) != (host_pack is None):
            raise ValueError("host Pack and release fingerprints must be supplied together")
        if type(community) is not RegisteredCommunityPack:
            raise TypeError("community must be exact RegisteredCommunityPack")
        current_p25 = _p25_plan(community, p25)
        if _P25_SCOPE_FAILURES.intersection(current_p25.abstain_reasons):
            raise HostMicrobiomeContractError("current P25 community bytes or scope are stale")
        context = _host_context_for_request(request)
        interface = HostMicrobiomeInterfaceRequirementV1.for_community(p25)
        dag = HostMicrobiomeDAGV1.for_bindings(request, context, p25, interface)
        request_fingerprint = _host_request_fingerprint(request)
        joint_scope = _joint_scope_fingerprint(
            host_request_fingerprint=request_fingerprint,
            host_context_fingerprint=context.fingerprint(),
            host_pack_fingerprint=host_pack,
            community_scope_fingerprint=p25.scope_fingerprint,
            interface_fingerprint=interface.fingerprint(),
            dag_fingerprint=dag.fingerprint(),
        )
        return HostMicrobiomeContractV1(
            schema_version="vc.host-microbiome-contract.v1",
            task="host_microbiome_joint_response",
            host_request=request,
            host_request_fingerprint=request_fingerprint,
            host_context=context,
            host_context_fingerprint=context.fingerprint(),
            required_host_pack_fingerprint=host_pack,
            required_host_release_fingerprint=host_release,
            required_host_request_binding_fingerprint=None,
            community_contract=p25,
            community_contract_fingerprint=p25.fingerprint(),
            community_scope_fingerprint=p25.scope_fingerprint,
            interface_requirement=interface,
            interface_requirement_fingerprint=interface.fingerprint(),
            dag=dag,
            dag_fingerprint=dag.fingerprint(),
            joint_scope_fingerprint=joint_scope,
            required_community_release_schema_version=None,
            required_community_release_fingerprint=None,
            required_matching_release_fingerprint=None,
            record_role="p26e_contract_only_missing_releases",
        )
    except HostMicrobiomeContractError:
        raise
    except (TypeError, ValidationError, ValueError, OSError) as exc:
        raise HostMicrobiomeContractError(f"cannot freeze host-microbiome contract: {exc}") from exc


def compile_host_microbiome(
    community: RegisteredCommunityPack,
    contract: HostMicrobiomeContractV1,
    *,
    host_registry: CuratedVirtualCellRegistry | None = None,
) -> HostMicrobiomeCompilationV1:
    """Revalidate live P25 bytes and emit the sole authorized P26E result."""

    contract = _normalize_contract(contract)
    if type(community) is not RegisteredCommunityPack:
        raise TypeError("community must be exact RegisteredCommunityPack")
    unsupported = False
    try:
        current_p25 = _p25_plan(community, contract.community_contract)
        unsupported = bool(_P25_SCOPE_FAILURES.intersection(current_p25.abstain_reasons))
        current_community_fingerprint = current_p25.community_fingerprint
        current_member_pack_fingerprints = current_p25.member_pack_fingerprints
    except (TypeError, ValueError, OSError):
        unsupported = True
        current_community_fingerprint = contract.community_contract.scope.community_fingerprint
        current_member_pack_fingerprints = contract.community_contract.scope.member_pack_fingerprints

    audit = audit_host_release_candidate(contract, host_registry)
    reasons = ["unsupported_host_microbiome_scope"] if unsupported else []
    reasons.extend(_MANDATORY_REASONS)
    identity = {
        "schema_version": "vc.host-microbiome-compilation.v1",
        "contract": contract.to_dict(),
        "contract_fingerprint": contract.fingerprint(),
        "host_release_audit": audit.to_dict(),
        "host_release_audit_fingerprint": audit.fingerprint(),
        "current_community_fingerprint": current_community_fingerprint,
        "current_member_pack_fingerprints": list(current_member_pack_fingerprints),
        "community_release_fingerprint": None,
        "community_scientifically_validated": None,
        "community_production_promoted": None,
        "matching_release_fingerprint": None,
        "matching_release_verified": False,
        "steps": [],
        "executable": False,
        "abstain": True,
        "prediction": None,
        "host_result": None,
        "community_result": None,
        "mediator_trace": None,
        "abstain_reasons": reasons,
        "execution_performed": False,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }
    return HostMicrobiomeCompilationV1(
        compilation_id=_content_id("hm_comp_", identity),
        **identity,
    )
