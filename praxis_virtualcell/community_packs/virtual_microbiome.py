"""P25E fixed-scope virtual microbiome contracts with value-free abstention.

The module freezes engineering identities only.  It deliberately contains no
P24 adapter implementation, model loader, biological data, scoring formula,
scientific evidence, operator decision, or prediction path.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.data_packs.errors import PackRegistryError, VirtualCellPackError
from praxis_virtualcell.data_packs.registry import PackRegistry

from .contracts import (
    CommunityContractError,
    RegisteredCommunityPack,
    _Contract,
    _curie,
    _decimal,
    _fingerprint,
    _identifier,
    _number,
    _text,
    register_community,
)

_PLAN_ID = re.compile(r"^vm_plan_[0-9a-f]{24}$")
_BASELINES = ("persistence", "independent_monoculture", "no_interaction")
_OOD_AXES = ("member", "medium", "initial_abundance", "time", "condition", "batch")
# Audited, repository-local synthetic fixtures only.  This is not a taxonomy
# database or a production capability allowlist; real P25 bindings need a new
# authorized record that does not claim this contract-only role.
_P25E_CONFORMANCE_MEMBERS = {
    "8600261ad68302432186e7107f053a7a0fdf0e3dbc61dc9754a502b20a95b1fe": (
        "NCBITaxon:562",
        "GCF_000005845.2",
        "PRAXISCELL:ecoli_k12",
    ),
    "7f3bc08f6fd64209683603b1fc93b38a5e646b866eb05878160ec69a755b9ff1": (
        "NCBITaxon:4932",
        "GCF_000146045.2",
        "PRAXISCELL:yeast_s288c",
    ),
}
_GATE_REASONS = (
    "p24_adapter_unavailable",
    "model_identity_unavailable",
    "environment_identity_unavailable",
    "metabolite_mapping_identity_unavailable",
    "benchmark_protocol_unavailable",
    "real_execution_binding_unavailable",
    "scientific_evidence_unavailable",
    "production_policy_unavailable",
)
_REASON_ORDER = (
    "member_pack_revalidation_failed",
    "stale_community_identity",
    "unsupported_virtual_microbiome_scope",
    *_GATE_REASONS,
)


class VirtualMicrobiomeContractError(ValueError):
    """A P25E identity is malformed or cannot be frozen safely."""


class _VirtualMicrobiomeContract(_Contract):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )


def _json_array(value: Any, field: str) -> list[Any]:
    if type(value) is not list or not value:
        raise ValueError(f"{field} must be a non-empty JSON array")
    return value


def _canonical_id(prefix: str, value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return f"{prefix}{hashlib.sha256(payload).hexdigest()[:24]}"


def _exact_bool(value: Any, field: str, expected: bool) -> bool:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{field} must be exactly {expected}")
    return value


class VirtualMicrobiomeScopeV1(_VirtualMicrobiomeContract):
    """One exact 2–3-member, medium, compartment, and time scope."""

    schema_version: Literal["vc.virtual-microbiome-scope.v1"]
    task: Literal["virtual_microbiome_abundance_dynamics"]
    community_id: str
    community_version: str
    community_fingerprint: str
    member_ids: tuple[str, ...]
    member_pack_fingerprints: tuple[str, ...]
    member_taxonomy_ids: tuple[str, ...]
    member_scientific_names: tuple[str, ...]
    member_assembly_accessions: tuple[str, ...]
    member_strain_identity_term_ids: tuple[str, ...]
    initial_abundances: tuple[str, ...]
    medium_id: str
    medium_fingerprint: str
    compartment_id: str
    time_start: str
    time_end: str
    time_unit: str
    time_fingerprint: str
    space: Literal["well_mixed"]

    @field_validator(
        "community_id",
        "community_version",
        "medium_id",
        "compartment_id",
        mode="before",
    )
    @classmethod
    def _valid_identifiers(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator(
        "community_fingerprint",
        "medium_fingerprint",
        "time_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("member_ids", mode="before")
    @classmethod
    def _valid_member_ids(cls, value):
        return tuple(_identifier(item, "member_ids") for item in _json_array(value, "member_ids"))

    @field_validator("member_pack_fingerprints", mode="before")
    @classmethod
    def _valid_member_pack_fingerprints(cls, value):
        return tuple(
            _fingerprint(item, "member_pack_fingerprints") for item in _json_array(value, "member_pack_fingerprints")
        )

    @field_validator("member_taxonomy_ids", mode="before")
    @classmethod
    def _valid_member_taxonomy_ids(cls, value):
        values = tuple(_curie(item, "member_taxonomy_ids") for item in _json_array(value, "member_taxonomy_ids"))
        if any(not item.startswith("NCBITaxon:") for item in values):
            raise ValueError("member_taxonomy_ids must use NCBITaxon CURIEs")
        return values

    @field_validator("member_scientific_names", mode="before")
    @classmethod
    def _valid_member_scientific_names(cls, value):
        return tuple(_text(item, "member_scientific_names") for item in _json_array(value, "member_scientific_names"))

    @field_validator("member_assembly_accessions", mode="before")
    @classmethod
    def _valid_member_assembly_accessions(cls, value):
        return tuple(
            _identifier(item, "member_assembly_accessions") for item in _json_array(value, "member_assembly_accessions")
        )

    @field_validator("member_strain_identity_term_ids", mode="before")
    @classmethod
    def _valid_member_strain_identity_term_ids(cls, value):
        return tuple(
            _curie(item, "member_strain_identity_term_ids")
            for item in _json_array(value, "member_strain_identity_term_ids")
        )

    @field_validator("initial_abundances", mode="before")
    @classmethod
    def _valid_initial_abundances(cls, value):
        values = tuple(_decimal(item, "initial_abundances") for item in _json_array(value, "initial_abundances"))
        if any(not 0 < _number(item) <= 1 for item in values):
            raise ValueError("initial_abundances must be greater than zero and at most one")
        return values

    @field_validator("time_start", "time_end", mode="before")
    @classmethod
    def _valid_time(cls, value, info):
        value = _decimal(value, info.field_name)
        if _number(value) < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return value

    @field_validator("time_unit", mode="before")
    @classmethod
    def _valid_time_unit(cls, value):
        return _identifier(value, "time_unit")

    @model_validator(mode="after")
    def _exact_member_and_time_scope(self):
        member_count = len(self.member_ids)
        if member_count not in (2, 3):
            raise ValueError("virtual microbiome scope requires exactly 2 or 3 members")
        if any(
            len(values) != member_count
            for values in (
                self.member_pack_fingerprints,
                self.member_taxonomy_ids,
                self.member_scientific_names,
                self.member_assembly_accessions,
                self.member_strain_identity_term_ids,
                self.initial_abundances,
            )
        ):
            raise ValueError("all ordered member identities must match member_ids")
        if len(set(self.member_ids)) != member_count:
            raise ValueError("member_ids must be unique")
        if len(set(self.member_pack_fingerprints)) != member_count:
            raise ValueError("member Pack fingerprints must be unique")
        if len(set(self.member_strain_identity_term_ids)) != member_count:
            raise ValueError("member strain identity terms must be unique")
        if sum((_number(item) for item in self.initial_abundances), start=_number("0")) != 1:
            raise ValueError("initial_abundances must sum exactly to one")
        if _number(self.time_end) <= _number(self.time_start):
            raise ValueError("time_end must be greater than time_start")
        return self

    @classmethod
    def from_registered(cls, community: RegisteredCommunityPack) -> VirtualMicrobiomeScopeV1:
        _validate_registered_community(community)
        manifest = community.manifest
        if len(manifest.members) not in (2, 3):
            raise VirtualMicrobiomeContractError("virtual microbiome scope requires exactly 2 or 3 members")
        strain_ids = []
        for record in community.members:
            semantics = record.manifest.cell_semantics
            terms = tuple(
                term.id for term in (() if semantics is None else semantics.local_terms) if term.role == "identity"
            )
            if len(terms) != 1:
                raise VirtualMicrobiomeContractError(
                    "each virtual microbiome member requires exactly one explicit strain identity term"
                )
            observed = (
                record.manifest.taxon.ontology_id,
                record.manifest.assembly.accession,
                terms[0],
            )
            if _P25E_CONFORMANCE_MEMBERS.get(record.fingerprint) != observed:
                raise VirtualMicrobiomeContractError(
                    "P25E contract-only freeze accepts only audited synthetic microbial member identities"
                )
            strain_ids.append(terms[0])
        return cls(
            schema_version="vc.virtual-microbiome-scope.v1",
            task="virtual_microbiome_abundance_dynamics",
            community_id=manifest.community_id,
            community_version=manifest.community_version,
            community_fingerprint=community.fingerprint,
            member_ids=[member.member_id for member in manifest.members],
            member_pack_fingerprints=[member.fingerprint for member in community.members],
            member_taxonomy_ids=[member.manifest.taxon.ontology_id for member in community.members],
            member_scientific_names=[member.manifest.taxon.scientific_name for member in community.members],
            member_assembly_accessions=[member.manifest.assembly.accession for member in community.members],
            member_strain_identity_term_ids=strain_ids,
            initial_abundances=[member.abundance.value for member in manifest.members],
            medium_id=manifest.medium.medium_id,
            medium_fingerprint=manifest.medium.fingerprint(),
            compartment_id=manifest.medium.compartment_id,
            time_start=manifest.time.start,
            time_end=manifest.time.end,
            time_unit=manifest.time.unit,
            time_fingerprint=manifest.time.fingerprint(),
            space=manifest.space.representation,
        )


class VirtualMicrobiomePrimaryEndpointV1(_VirtualMicrobiomeContract):
    """The sole primary endpoint; secondary outputs cannot alter its gate."""

    schema_version: Literal["vc.virtual-microbiome-primary-endpoint.v1"]
    endpoint_id: Literal["strain_level_abundance_at_end_time"]
    task: Literal["virtual_microbiome_abundance_dynamics"]
    output: Literal["strain_level_abundance_at_end_time"]
    endpoint_role: Literal["primary"]
    member_ids: tuple[str, ...]
    time_fingerprint: str
    value_type: Literal["ordered_fraction_vector"]
    value_unit: Literal["fraction"]
    metric: Literal["mean_absolute_error"]
    metric_direction: Literal["lower_is_better"]
    scientific_gate_threshold: str
    secondary_may_override_primary: Literal[False]

    @field_validator("member_ids", mode="before")
    @classmethod
    def _valid_member_ids(cls, value):
        values = tuple(_identifier(item, "endpoint.member_ids") for item in _json_array(value, "member_ids"))
        if len(values) not in (2, 3) or len(set(values)) != len(values):
            raise ValueError("endpoint member_ids must contain 2 or 3 unique ordered members")
        return values

    @field_validator("time_fingerprint", mode="before")
    @classmethod
    def _valid_time_fingerprint(cls, value):
        return _fingerprint(value, "endpoint.time_fingerprint")

    @field_validator("scientific_gate_threshold", mode="before")
    @classmethod
    def _valid_threshold(cls, value):
        value = _decimal(value, "scientific_gate_threshold")
        if not 0 < _number(value) <= 1:
            raise ValueError("scientific_gate_threshold must be greater than zero and at most one")
        return value

    @field_validator("secondary_may_override_primary", mode="before")
    @classmethod
    def _secondary_cannot_override(cls, value):
        return _exact_bool(value, "secondary_may_override_primary", False)

    @classmethod
    def for_scope(
        cls,
        scope: VirtualMicrobiomeScopeV1,
        scientific_gate_threshold: str,
    ) -> VirtualMicrobiomePrimaryEndpointV1:
        if type(scope) is not VirtualMicrobiomeScopeV1:
            raise TypeError("scope must be exact VirtualMicrobiomeScopeV1")
        return cls(
            schema_version="vc.virtual-microbiome-primary-endpoint.v1",
            endpoint_id="strain_level_abundance_at_end_time",
            task=scope.task,
            output="strain_level_abundance_at_end_time",
            endpoint_role="primary",
            member_ids=list(scope.member_ids),
            time_fingerprint=scope.time_fingerprint,
            value_type="ordered_fraction_vector",
            value_unit="fraction",
            metric="mean_absolute_error",
            metric_direction="lower_is_better",
            scientific_gate_threshold=scientific_gate_threshold,
            secondary_may_override_primary=False,
        )


class VirtualMicrobiomeAdapterRequirementV1(_VirtualMicrobiomeContract):
    """Typed negative adapter closure until an authorized real P24 adapter exists."""

    schema_version: Literal["vc.virtual-microbiome-adapter-requirement.v1"]
    task: Literal["virtual_microbiome_abundance_dynamics"]
    output: Literal["strain_level_abundance_at_end_time"]
    scope_fingerprint: str
    primary_endpoint_fingerprint: str
    required_adapter_origin: Literal["p24_real_community_adapter"]
    required_adapter_identity: Literal["independently_versioned_and_fingerprinted"]
    record_role: Literal["p25e_contract_only_missing_bindings"]
    required_baselines: tuple[str, ...]
    required_ood_axes: tuple[str, ...]
    implementation_available: Literal[False]
    p24_adapter_fingerprint: None
    model_fingerprint: None
    environment_fingerprint: None
    metabolite_mapping_fingerprint: None
    benchmark_protocol_fingerprint: None
    evidence_fingerprint: None
    policy_fingerprint: None

    @field_validator("scope_fingerprint", "primary_endpoint_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("required_baselines", mode="before")
    @classmethod
    def _valid_baselines(cls, value):
        if type(value) is not list or tuple(value) != _BASELINES:
            raise ValueError(f"required_baselines must equal {list(_BASELINES)}")
        return tuple(value)

    @field_validator("required_ood_axes", mode="before")
    @classmethod
    def _valid_ood_axes(cls, value):
        if type(value) is not list or tuple(value) != _OOD_AXES:
            raise ValueError(f"required_ood_axes must equal {list(_OOD_AXES)}")
        return tuple(value)

    @field_validator(
        "implementation_available",
        mode="before",
    )
    @classmethod
    def _negative_status(cls, value, info):
        return _exact_bool(value, info.field_name, False)

    @classmethod
    def for_contract(
        cls,
        scope: VirtualMicrobiomeScopeV1,
        endpoint: VirtualMicrobiomePrimaryEndpointV1,
    ) -> VirtualMicrobiomeAdapterRequirementV1:
        if type(scope) is not VirtualMicrobiomeScopeV1 or type(endpoint) is not VirtualMicrobiomePrimaryEndpointV1:
            raise TypeError("adapter requirement needs exact scope and endpoint contracts")
        return cls(
            schema_version="vc.virtual-microbiome-adapter-requirement.v1",
            task=scope.task,
            output=endpoint.output,
            scope_fingerprint=scope.fingerprint(),
            primary_endpoint_fingerprint=endpoint.fingerprint(),
            required_adapter_origin="p24_real_community_adapter",
            required_adapter_identity="independently_versioned_and_fingerprinted",
            record_role="p25e_contract_only_missing_bindings",
            required_baselines=list(_BASELINES),
            required_ood_axes=list(_OOD_AXES),
            implementation_available=False,
            p24_adapter_fingerprint=None,
            model_fingerprint=None,
            environment_fingerprint=None,
            metabolite_mapping_fingerprint=None,
            benchmark_protocol_fingerprint=None,
            evidence_fingerprint=None,
            policy_fingerprint=None,
        )


class VirtualMicrobiomeContractV1(_VirtualMicrobiomeContract):
    schema_version: Literal["vc.virtual-microbiome-contract.v1"]
    scope: VirtualMicrobiomeScopeV1
    scope_fingerprint: str
    endpoint: VirtualMicrobiomePrimaryEndpointV1
    endpoint_fingerprint: str
    adapter_requirement: VirtualMicrobiomeAdapterRequirementV1
    adapter_requirement_fingerprint: str
    record_role: Literal["p25e_contract_only"]

    @field_validator(
        "scope_fingerprint",
        "endpoint_fingerprint",
        "adapter_requirement_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _exact_closure(self):
        scope = VirtualMicrobiomeScopeV1.model_validate(self.scope.to_dict())
        endpoint = VirtualMicrobiomePrimaryEndpointV1.model_validate(self.endpoint.to_dict())
        adapter = VirtualMicrobiomeAdapterRequirementV1.model_validate(self.adapter_requirement.to_dict())
        if (scope, endpoint, adapter) != (
            self.scope,
            self.endpoint,
            self.adapter_requirement,
        ):
            raise ValueError("contract contains non-canonical nested identities")
        if self.scope.fingerprint() != self.scope_fingerprint:
            raise ValueError("scope_fingerprint is stale")
        if self.endpoint.fingerprint() != self.endpoint_fingerprint:
            raise ValueError("endpoint_fingerprint is stale")
        if self.adapter_requirement.fingerprint() != self.adapter_requirement_fingerprint:
            raise ValueError("adapter_requirement_fingerprint is stale")
        if self.endpoint.member_ids != self.scope.member_ids:
            raise ValueError("endpoint member order does not match scope")
        if self.endpoint.time_fingerprint != self.scope.time_fingerprint:
            raise ValueError("endpoint time does not match scope")
        if self.adapter_requirement.scope_fingerprint != self.scope_fingerprint:
            raise ValueError("adapter requirement scope is stale")
        if self.adapter_requirement.primary_endpoint_fingerprint != self.endpoint_fingerprint:
            raise ValueError("adapter requirement endpoint is stale")
        return self


class VirtualMicrobiomeRequestV1(_VirtualMicrobiomeContract):
    schema_version: Literal["vc.virtual-microbiome-request.v1"]
    task: Literal["virtual_microbiome_abundance_dynamics"]
    requested_output: Literal["strain_level_abundance_at_end_time"]
    community_fingerprint: str
    member_pack_fingerprints: tuple[str, ...]
    medium_fingerprint: str
    time_fingerprint: str
    scope_fingerprint: str
    primary_endpoint_fingerprint: str
    adapter_requirement_fingerprint: str

    @field_validator(
        "community_fingerprint",
        "medium_fingerprint",
        "time_fingerprint",
        "scope_fingerprint",
        "primary_endpoint_fingerprint",
        "adapter_requirement_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("member_pack_fingerprints", mode="before")
    @classmethod
    def _valid_member_pack_fingerprints(cls, value):
        values = tuple(
            _fingerprint(item, "request.member_pack_fingerprints")
            for item in _json_array(value, "member_pack_fingerprints")
        )
        if len(values) not in (2, 3) or len(set(values)) != len(values):
            raise ValueError("request needs 2 or 3 unique member Pack fingerprints")
        return values

    @classmethod
    def for_contract(cls, contract: VirtualMicrobiomeContractV1) -> VirtualMicrobiomeRequestV1:
        if type(contract) is not VirtualMicrobiomeContractV1:
            raise TypeError("contract must be exact VirtualMicrobiomeContractV1")
        return cls(
            schema_version="vc.virtual-microbiome-request.v1",
            task=contract.scope.task,
            requested_output=contract.endpoint.output,
            community_fingerprint=contract.scope.community_fingerprint,
            member_pack_fingerprints=list(contract.scope.member_pack_fingerprints),
            medium_fingerprint=contract.scope.medium_fingerprint,
            time_fingerprint=contract.scope.time_fingerprint,
            scope_fingerprint=contract.scope_fingerprint,
            primary_endpoint_fingerprint=contract.endpoint_fingerprint,
            adapter_requirement_fingerprint=contract.adapter_requirement_fingerprint,
        )


VirtualMicrobiomeAbstainReason = Literal[
    "member_pack_revalidation_failed",
    "stale_community_identity",
    "unsupported_virtual_microbiome_scope",
    "p24_adapter_unavailable",
    "model_identity_unavailable",
    "environment_identity_unavailable",
    "metabolite_mapping_identity_unavailable",
    "benchmark_protocol_unavailable",
    "real_execution_binding_unavailable",
    "scientific_evidence_unavailable",
    "production_policy_unavailable",
]


class VirtualMicrobiomePlanV1(_VirtualMicrobiomeContract):
    schema_version: Literal["vc.virtual-microbiome-plan.v1"]
    plan_id: str
    contract_fingerprint: str
    request_fingerprint: str
    scope_fingerprint: str
    primary_endpoint_fingerprint: str
    adapter_requirement_fingerprint: str
    community_fingerprint: str
    member_pack_fingerprints: tuple[str, ...]
    executable: Literal[False]
    steps: tuple[dict[str, str], ...]
    abstain_reasons: tuple[VirtualMicrobiomeAbstainReason, ...]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator("plan_id", mode="before")
    @classmethod
    def _valid_plan_id(cls, value):
        if not isinstance(value, str) or not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be vm_plan_ plus 24 lowercase hex")
        return value

    @field_validator(
        "contract_fingerprint",
        "request_fingerprint",
        "scope_fingerprint",
        "primary_endpoint_fingerprint",
        "adapter_requirement_fingerprint",
        "community_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("member_pack_fingerprints", mode="before")
    @classmethod
    def _valid_member_pack_fingerprints(cls, value):
        return tuple(
            _fingerprint(item, "plan.member_pack_fingerprints")
            for item in _json_array(value, "member_pack_fingerprints")
        )

    @field_validator("steps", mode="before")
    @classmethod
    def _valid_steps(cls, value):
        if type(value) is not list or value:
            raise ValueError("P25E plan steps must be an empty JSON array")
        return ()

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        if type(value) is not list or not value or any(type(item) is not str for item in value):
            raise ValueError("abstain_reasons must be a non-empty string JSON array")
        if len(set(value)) != len(value):
            raise ValueError("abstain_reasons must be a non-empty unique JSON array")
        unknown = set(value).difference(_REASON_ORDER)
        if unknown:
            raise ValueError(f"unknown abstain reasons: {sorted(unknown)}")
        expected = tuple(reason for reason in _REASON_ORDER if reason in value)
        if tuple(value) != expected:
            raise ValueError("abstain_reasons must use canonical order")
        return tuple(value)

    @field_validator(
        "executable",
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
        mode="before",
    )
    @classmethod
    def _negative_status(cls, value, info):
        return _exact_bool(value, info.field_name, False)

    @model_validator(mode="after")
    def _identity_is_current(self):
        identity = self.model_dump(mode="json", exclude={"plan_id"})
        if self.plan_id != _canonical_id("vm_plan_", identity):
            raise ValueError("plan_id is stale")
        return self


class VirtualMicrobiomeResultV1(_VirtualMicrobiomeContract):
    schema_version: Literal["vc.virtual-microbiome-result.v1"]
    contract_fingerprint: str
    request_fingerprint: str
    execution_plan: VirtualMicrobiomePlanV1
    execution_plan_fingerprint: str
    abstain: Literal[True]
    prediction: None
    secondary_predictions: None
    abstain_reasons: tuple[VirtualMicrobiomeAbstainReason, ...]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator(
        "contract_fingerprint",
        "request_fingerprint",
        "execution_plan_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        if type(value) is not list or not value or any(type(item) is not str for item in value):
            raise ValueError("abstain_reasons must be a non-empty string JSON array")
        return tuple(value)

    @field_validator("abstain", mode="before")
    @classmethod
    def _must_abstain(cls, value):
        return _exact_bool(value, "abstain", True)

    @field_validator(
        "scientifically_validated",
        "promotion_eligible",
        "production_promoted",
        mode="before",
    )
    @classmethod
    def _negative_status(cls, value, info):
        return _exact_bool(value, info.field_name, False)

    @model_validator(mode="after")
    def _honest_abstention(self):
        plan = VirtualMicrobiomePlanV1.model_validate(self.execution_plan.to_dict())
        if plan != self.execution_plan:
            raise ValueError("result contains a non-canonical execution plan")
        if self.execution_plan.fingerprint() != self.execution_plan_fingerprint:
            raise ValueError("execution_plan_fingerprint is stale")
        if self.execution_plan.contract_fingerprint != self.contract_fingerprint:
            raise ValueError("result contract does not match plan")
        if self.execution_plan.request_fingerprint != self.request_fingerprint:
            raise ValueError("result request does not match plan")
        if self.abstain_reasons != self.execution_plan.abstain_reasons:
            raise ValueError("result abstain reasons do not match plan")
        return self


def _validate_registered_community(community: RegisteredCommunityPack) -> None:
    if type(community) is not RegisteredCommunityPack:
        raise TypeError("community must be exact RegisteredCommunityPack")
    manifest = community.manifest
    if community.fingerprint != manifest.fingerprint():
        raise VirtualMicrobiomeContractError("registered community fingerprint is stale")
    if len(community.members) != len(manifest.members):
        raise VirtualMicrobiomeContractError("registered community member closure is incomplete")
    for member, record in zip(manifest.members, community.members, strict=True):
        if (
            record.fingerprint != record.manifest.fingerprint()
            or record.fingerprint != member.pack_fingerprint
            or record.manifest.pack_id != member.pack_id
            or record.manifest.pack_version != member.pack_version
        ):
            raise VirtualMicrobiomeContractError("registered community member Pack identity is stale")


def _revalidate_member_bytes(community: RegisteredCommunityPack) -> RegisteredCommunityPack:
    registry = PackRegistry()
    for member in community.members:
        registry.register(member.root)
    return register_community(community.manifest, registry)


def freeze_virtual_microbiome_contract(
    community: RegisteredCommunityPack,
    *,
    scientific_gate_threshold: str,
) -> VirtualMicrobiomeContractV1:
    """Freeze P25E identities without authorizing or implementing execution."""

    try:
        _validate_registered_community(community)
        current = _revalidate_member_bytes(community)
        scope = VirtualMicrobiomeScopeV1.from_registered(current)
        endpoint = VirtualMicrobiomePrimaryEndpointV1.for_scope(
            scope,
            scientific_gate_threshold,
        )
        adapter = VirtualMicrobiomeAdapterRequirementV1.for_contract(scope, endpoint)
        return VirtualMicrobiomeContractV1(
            schema_version="vc.virtual-microbiome-contract.v1",
            scope=scope,
            scope_fingerprint=scope.fingerprint(),
            endpoint=endpoint,
            endpoint_fingerprint=endpoint.fingerprint(),
            adapter_requirement=adapter,
            adapter_requirement_fingerprint=adapter.fingerprint(),
            record_role="p25e_contract_only",
        )
    except VirtualMicrobiomeContractError:
        raise
    except (TypeError, ValidationError, ValueError) as exc:
        raise VirtualMicrobiomeContractError(f"cannot freeze virtual microbiome contract: {exc}") from exc


def plan_virtual_microbiome(
    community: RegisteredCommunityPack,
    contract: VirtualMicrobiomeContractV1,
    request: VirtualMicrobiomeRequestV1,
) -> VirtualMicrobiomePlanV1:
    """Revalidate local identities, then return a value-free P25E plan."""

    _validate_registered_community(community)
    if type(contract) is not VirtualMicrobiomeContractV1:
        raise TypeError("contract must be exact VirtualMicrobiomeContractV1")
    if type(request) is not VirtualMicrobiomeRequestV1:
        raise TypeError("request must be exact VirtualMicrobiomeRequestV1")
    contract = VirtualMicrobiomeContractV1.model_validate(contract.to_dict())
    request = VirtualMicrobiomeRequestV1.model_validate(request.to_dict())

    reasons: list[VirtualMicrobiomeAbstainReason] = []
    try:
        current = _revalidate_member_bytes(community)
    except (CommunityContractError, PackRegistryError, VirtualCellPackError, OSError, ValueError):
        current = community
        reasons.append("member_pack_revalidation_failed")

    scope = contract.scope
    try:
        current_scope = VirtualMicrobiomeScopeV1.from_registered(current)
    except (TypeError, ValueError):
        current_scope = None
    if current_scope != scope:
        reasons.append("stale_community_identity")

    request_identity = (
        request.task,
        request.requested_output,
        request.community_fingerprint,
        request.member_pack_fingerprints,
        request.medium_fingerprint,
        request.time_fingerprint,
        request.scope_fingerprint,
        request.primary_endpoint_fingerprint,
        request.adapter_requirement_fingerprint,
    )
    contract_identity = (
        scope.task,
        contract.endpoint.output,
        scope.community_fingerprint,
        scope.member_pack_fingerprints,
        scope.medium_fingerprint,
        scope.time_fingerprint,
        contract.scope_fingerprint,
        contract.endpoint_fingerprint,
        contract.adapter_requirement_fingerprint,
    )
    if request_identity != contract_identity:
        reasons.append("unsupported_virtual_microbiome_scope")
    reasons.extend(_GATE_REASONS)
    reasons = [reason for reason in _REASON_ORDER if reason in reasons]

    identity = {
        "schema_version": "vc.virtual-microbiome-plan.v1",
        "contract_fingerprint": contract.fingerprint(),
        "request_fingerprint": request.fingerprint(),
        "scope_fingerprint": contract.scope_fingerprint,
        "primary_endpoint_fingerprint": contract.endpoint_fingerprint,
        "adapter_requirement_fingerprint": contract.adapter_requirement_fingerprint,
        "community_fingerprint": current.fingerprint,
        "member_pack_fingerprints": [member.fingerprint for member in current.members],
        "executable": False,
        "steps": [],
        "abstain_reasons": reasons,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }
    return VirtualMicrobiomePlanV1(plan_id=_canonical_id("vm_plan_", identity), **identity)


def run_virtual_microbiome(
    community: RegisteredCommunityPack,
    contract: VirtualMicrobiomeContractV1,
    request: VirtualMicrobiomeRequestV1,
) -> VirtualMicrobiomeResultV1:
    """Return the only locally authorized P25E outcome: immutable abstention."""

    plan = plan_virtual_microbiome(community, contract, request)
    return VirtualMicrobiomeResultV1(
        schema_version="vc.virtual-microbiome-result.v1",
        contract_fingerprint=contract.fingerprint(),
        request_fingerprint=request.fingerprint(),
        execution_plan=plan,
        execution_plan_fingerprint=plan.fingerprint(),
        abstain=True,
        prediction=None,
        secondary_predictions=None,
        abstain_reasons=list(plan.abstain_reasons),
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )
