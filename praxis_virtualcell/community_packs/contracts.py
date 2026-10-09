"""Strict, model-free contracts for virtual microbial communities."""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError, field_validator, model_validator

from praxis_virtualcell.data_packs.errors import (
    PackRegistryError,
    VirtualCellPackError,
)
from praxis_virtualcell.data_packs.registry import PackRegistry, RegisteredPack
from praxis_virtualcell.data_packs.schema import SchemaObject

_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PLAN_ID = re.compile(r"^community_plan_[0-9a-f]{24}$")


class CommunityContractError(ValueError):
    """A CommunityPack reference or deterministic contract is invalid."""


def _text(value: Any, field: str, *, limit: int = 256) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a non-empty unpadded string")
    return value


def _identifier(value: Any, field: str) -> str:
    value = _text(value, field, limit=128)
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a safe identifier")
    return value


def _curie(value: Any, field: str) -> str:
    value = _text(value, field, limit=128)
    if not _CURIE.fullmatch(value):
        raise ValueError(f"{field} must be a CURIE")
    return value


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field, limit=64)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _decimal(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > 128 or not _DECIMAL.fullmatch(value):
        raise ValueError(f"{field} must be an explicit base-10 decimal string")
    return value


def _number(value: str) -> Fraction:
    return Fraction(value)


def _json_array(value: Any, field: str, *, allow_empty: bool = False):
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "" if allow_empty else " non-empty"
        raise ValueError(f"{field} must be a{qualifier} JSON array")
    return value


class _Contract(SchemaObject):
    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class AbundanceSpec(_Contract):
    value: str
    unit: Literal["fraction"]

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        value = _decimal(value, "abundance.value")
        if not 0 < _number(value) <= 1:
            raise ValueError("abundance.value must be greater than zero and at most one")
        return value


class NonNegativeQuantitySpec(_Contract):
    value: str
    unit: str

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        value = _decimal(value, "quantity.value")
        if _number(value) < 0:
            raise ValueError("quantity.value must be non-negative")
        return value

    @field_validator("unit", mode="before")
    @classmethod
    def _valid_unit(cls, value):
        return _text(value, "quantity.unit", limit=64)


class SignedQuantitySpec(_Contract):
    value: str
    unit: str

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        return _decimal(value, "amount.value")

    @field_validator("unit", mode="before")
    @classmethod
    def _valid_unit(cls, value):
        return _text(value, "amount.unit", limit=64)


class ExchangeSpec(_Contract):
    metabolite_ids: tuple[str, ...]
    amount_unit: str

    @field_validator("metabolite_ids", mode="before")
    @classmethod
    def _valid_metabolites(cls, value):
        return _json_array(value, "exchange.metabolite_ids")

    @field_validator("metabolite_ids")
    @classmethod
    def _valid_metabolite_ids(cls, value):
        values = tuple(_curie(item, "exchange.metabolite_ids") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("duplicate exchange metabolite ids are not allowed")
        return values

    @field_validator("amount_unit", mode="before")
    @classmethod
    def _valid_unit(cls, value):
        return _text(value, "exchange.amount_unit", limit=64)


class CommunityMemberSpec(_Contract):
    member_id: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    abundance: AbundanceSpec
    compartment_id: str
    exchange: ExchangeSpec

    @field_validator(
        "member_id",
        "pack_id",
        "pack_version",
        "compartment_id",
        mode="before",
    )
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("pack_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _fingerprint(value, "member.pack_fingerprint")


class MediumComponentSpec(_Contract):
    metabolite_id: str
    concentration: NonNegativeQuantitySpec

    @field_validator("metabolite_id", mode="before")
    @classmethod
    def _valid_metabolite(cls, value):
        return _curie(value, "medium.components.metabolite_id")


class MediumSpec(_Contract):
    medium_id: str
    compartment_id: str
    components: tuple[MediumComponentSpec, ...]

    @field_validator("medium_id", "compartment_id", mode="before")
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("components", mode="before")
    @classmethod
    def _valid_components(cls, value):
        return _json_array(value, "medium.components")

    @model_validator(mode="after")
    def _unique_components(self):
        ids = [component.metabolite_id for component in self.components]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate medium metabolite ids are not allowed")
        return self


class CompartmentSpec(_Contract):
    id: str
    role: Literal["shared_medium"]

    @field_validator("id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _identifier(value, "compartment.id")


class TimeSpec(_Contract):
    start: str
    end: str
    unit: str

    @field_validator("start", "end", mode="before")
    @classmethod
    def _valid_times(cls, value, info):
        value = _decimal(value, f"time.{info.field_name}")
        if _number(value) < 0:
            raise ValueError(f"time.{info.field_name} must be non-negative")
        return value

    @field_validator("unit", mode="before")
    @classmethod
    def _valid_unit(cls, value):
        return _text(value, "time.unit", limit=64)

    @model_validator(mode="after")
    def _ordered_time(self):
        if _number(self.end) <= _number(self.start):
            raise ValueError("time.end must be greater than time.start")
        return self


class SpaceSpec(_Contract):
    representation: Literal["well_mixed"]


class SharedMetaboliteSpec(_Contract):
    id: str
    label: str

    @field_validator("id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _curie(value, "shared metabolite id")

    @field_validator("label", mode="before")
    @classmethod
    def _valid_label(cls, value):
        return _text(value, "shared metabolite label")


class SharedMetaboliteNamespaceSpec(_Contract):
    name: str
    version: str
    id_format: Literal["curie"]
    amount_unit: str
    metabolites: tuple[SharedMetaboliteSpec, ...]

    @field_validator("name", "version", mode="before")
    @classmethod
    def _valid_identity(cls, value, info):
        return _identifier(value, f"shared_metabolite_namespace.{info.field_name}")

    @field_validator("amount_unit", mode="before")
    @classmethod
    def _valid_unit(cls, value):
        return _text(value, "shared_metabolite_namespace.amount_unit", limit=64)

    @field_validator("metabolites", mode="before")
    @classmethod
    def _valid_metabolites(cls, value):
        return _json_array(value, "shared_metabolite_namespace.metabolites")

    @model_validator(mode="after")
    def _unique_metabolites(self):
        ids = [metabolite.id for metabolite in self.metabolites]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate metabolite ids are not allowed")
        if any(metabolite_id.split(":", 1)[0] != self.name for metabolite_id in ids):
            raise ValueError("shared metabolite id prefix conflicts with declared namespace")
        return self


class InteractionEvidenceSpec(_Contract):
    evidence_id: str
    source_member_id: str
    target_member_id: str
    metabolite_id: str
    evidence_type: Literal["contract_fixture", "experimental", "literature"]
    reference: str

    @field_validator(
        "evidence_id",
        "source_member_id",
        "target_member_id",
        mode="before",
    )
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("metabolite_id", mode="before")
    @classmethod
    def _valid_metabolite(cls, value):
        return _curie(value, "interaction_evidence.metabolite_id")

    @field_validator("reference", mode="before")
    @classmethod
    def _valid_reference(cls, value):
        return _text(value, "interaction_evidence.reference", limit=512)

    @model_validator(mode="after")
    def _different_members(self):
        if self.source_member_id == self.target_member_id:
            raise ValueError("interaction evidence source and target members must differ")
        return self


class CommunityPack(_Contract):
    schema_version: Literal["vc.community-pack.v1"]
    community_id: str
    community_version: str
    members: tuple[CommunityMemberSpec, ...]
    medium: MediumSpec
    compartments: tuple[CompartmentSpec, ...]
    time: TimeSpec
    space: SpaceSpec
    shared_metabolite_namespace: SharedMetaboliteNamespaceSpec
    interaction_evidence: tuple[InteractionEvidenceSpec, ...]
    scientifically_validated: Literal[False]

    @field_validator("community_id", "community_version", mode="before")
    @classmethod
    def _valid_identity(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("members", "compartments", mode="before")
    @classmethod
    def _valid_non_empty_arrays(cls, value, info):
        return _json_array(value, info.field_name)

    @field_validator("interaction_evidence", mode="before")
    @classmethod
    def _valid_evidence_array(cls, value):
        return _json_array(value, "interaction_evidence", allow_empty=True)

    @model_validator(mode="after")
    def _validate_references(self):
        member_ids = [member.member_id for member in self.members]
        if len(set(member_ids)) != len(member_ids):
            raise ValueError("duplicate member ids are not allowed")
        pack_ids = [(member.pack_id, member.pack_version, member.pack_fingerprint) for member in self.members]
        if len(set(pack_ids)) != len(pack_ids):
            raise ValueError("duplicate Pack references are not allowed")
        if sum((_number(member.abundance.value) for member in self.members), Fraction()) != 1:
            raise ValueError("member abundance values must sum exactly to one")

        compartment_ids = [compartment.id for compartment in self.compartments]
        if len(set(compartment_ids)) != len(compartment_ids):
            raise ValueError("duplicate compartment ids are not allowed")
        compartment_set = set(compartment_ids)
        if self.medium.compartment_id not in compartment_set:
            raise ValueError("medium references an unknown compartment")
        if any(member.compartment_id not in compartment_set for member in self.members):
            raise ValueError("member references an unknown compartment")

        namespace = self.shared_metabolite_namespace
        metabolite_ids = {metabolite.id for metabolite in namespace.metabolites}
        if any(component.metabolite_id not in metabolite_ids for component in self.medium.components):
            raise ValueError("medium references an unknown shared metabolite")
        for member in self.members:
            if member.exchange.amount_unit != namespace.amount_unit:
                raise ValueError("member exchange unit conflicts with shared amount unit")
            if any(metabolite_id not in metabolite_ids for metabolite_id in member.exchange.metabolite_ids):
                raise ValueError("member exchange references an unknown metabolite")

        evidence_ids = [item.evidence_id for item in self.interaction_evidence]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("duplicate interaction evidence ids are not allowed")
        member_set = set(member_ids)
        member_exchange = {member.member_id: set(member.exchange.metabolite_ids) for member in self.members}
        for item in self.interaction_evidence:
            if item.source_member_id not in member_set or item.target_member_id not in member_set:
                raise ValueError("interaction evidence references an unknown member")
            if item.metabolite_id not in metabolite_ids:
                raise ValueError("interaction evidence references an unknown metabolite")
            if (
                item.metabolite_id not in member_exchange[item.source_member_id]
                or item.metabolite_id not in member_exchange[item.target_member_id]
            ):
                raise ValueError("interaction evidence conflicts with member exchange declarations")
        return self

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CommunityPack:
        if not isinstance(value, dict):
            raise CommunityContractError("CommunityPack must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise CommunityContractError(f"invalid CommunityPack: {exc}") from exc


@dataclass(frozen=True)
class RegisteredCommunityPack:
    manifest: CommunityPack
    members: tuple[RegisteredPack, ...]
    fingerprint: str


def register_community(
    manifest: CommunityPack,
    registry: PackRegistry,
) -> RegisteredCommunityPack:
    if not isinstance(manifest, CommunityPack) or not isinstance(registry, PackRegistry):
        raise TypeError("register_community requires CommunityPack and PackRegistry")
    records: list[RegisteredPack] = []
    for member in manifest.members:
        try:
            record = registry.record(member.pack_id, member.pack_version)
        except PackRegistryError as exc:
            raise CommunityContractError(f"unregistered member Pack: {member.pack_id}@{member.pack_version}") from exc
        try:
            registry.register(record.root)
        except VirtualCellPackError as exc:
            raise CommunityContractError(f"member Pack no longer validates: {member.member_id}") from exc
        record = registry.record(member.pack_id, member.pack_version)
        if record.fingerprint != member.pack_fingerprint:
            raise CommunityContractError(f"member Pack fingerprint mismatch: {member.member_id}")
        records.append(record)
    return RegisteredCommunityPack(
        manifest=manifest,
        members=tuple(records),
        fingerprint=manifest.fingerprint(),
    )


def single_member_equivalent(community: RegisteredCommunityPack) -> RegisteredPack:
    if not isinstance(community, RegisteredCommunityPack):
        raise TypeError("single_member_equivalent requires RegisteredCommunityPack")
    if len(community.members) != 1:
        raise CommunityContractError("single-member equivalence requires exactly one member")
    if community.manifest.interaction_evidence:
        raise CommunityContractError("single-member equivalence forbids interaction evidence")
    return community.members[0]


class ExchangeEntrySpec(_Contract):
    participant_type: Literal["member", "medium"]
    participant_id: str
    compartment_id: str
    metabolite_id: str
    amount: SignedQuantitySpec

    @field_validator("participant_id", "compartment_id", mode="before")
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("metabolite_id", mode="before")
    @classmethod
    def _valid_metabolite(cls, value):
        return _curie(value, "exchange ledger metabolite_id")


class ToyExchangeLedger(_Contract):
    schema_version: Literal["vc.community-exchange-ledger.v1"]
    community_fingerprint: str
    entries: tuple[ExchangeEntrySpec, ...]
    scientifically_validated: Literal[False]

    @field_validator("community_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _fingerprint(value, "ledger.community_fingerprint")

    @field_validator("entries", mode="before")
    @classmethod
    def _valid_entries(cls, value):
        return _json_array(value, "ledger.entries")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ToyExchangeLedger:
        if not isinstance(value, dict):
            raise CommunityContractError("exchange ledger must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise CommunityContractError(f"invalid exchange ledger: {exc}") from exc


class ExchangeBalanceSpec(_Contract):
    metabolite_id: str
    value: Literal["0"]
    unit: str


class ToyExchangeValidation(_Contract):
    schema_version: Literal["vc.community-exchange-validation.v1"]
    community_fingerprint: str
    mass_conserved: Literal[True]
    balances: tuple[ExchangeBalanceSpec, ...]
    scientifically_validated: Literal[False]


def validate_toy_exchange(
    community: RegisteredCommunityPack,
    ledger: ToyExchangeLedger,
) -> ToyExchangeValidation:
    if not isinstance(community, RegisteredCommunityPack) or not isinstance(ledger, ToyExchangeLedger):
        raise TypeError("validate_toy_exchange requires RegisteredCommunityPack and ToyExchangeLedger")
    if ledger.community_fingerprint != community.fingerprint:
        raise CommunityContractError("exchange ledger community fingerprint mismatch")

    manifest = community.manifest
    namespace = manifest.shared_metabolite_namespace
    metabolite_ids = {metabolite.id for metabolite in namespace.metabolites}
    member_compartments = {member.member_id: member.compartment_id for member in manifest.members}
    member_exchange = {member.member_id: set(member.exchange.metabolite_ids) for member in manifest.members}
    balances = {metabolite_id: Fraction() for metabolite_id in metabolite_ids}
    seen_metabolites: set[str] = set()
    for entry in ledger.entries:
        if entry.metabolite_id not in metabolite_ids:
            raise CommunityContractError("exchange ledger references an unknown metabolite")
        if entry.amount.unit != namespace.amount_unit:
            raise CommunityContractError("exchange ledger amount unit conflict")
        if entry.participant_type == "member":
            expected_compartment = member_compartments.get(entry.participant_id)
            if expected_compartment is None:
                raise CommunityContractError("exchange ledger references an unknown participant")
            if entry.metabolite_id not in member_exchange[entry.participant_id]:
                raise CommunityContractError("exchange ledger violates the member exchange contract")
        else:
            if entry.participant_id != manifest.medium.medium_id:
                raise CommunityContractError("exchange ledger references an unknown participant")
            expected_compartment = manifest.medium.compartment_id
        if entry.compartment_id != expected_compartment:
            raise CommunityContractError("exchange ledger participant compartment conflict")
        balances[entry.metabolite_id] += _number(entry.amount.value)
        seen_metabolites.add(entry.metabolite_id)

    if seen_metabolites != metabolite_ids:
        raise CommunityContractError("exchange ledger must explicitly cover every shared metabolite")
    residuals = {metabolite_id: value for metabolite_id, value in balances.items() if value != 0}
    if residuals:
        raise CommunityContractError(f"toy exchange mass is not conserved for {sorted(residuals)}")
    return ToyExchangeValidation(
        schema_version="vc.community-exchange-validation.v1",
        community_fingerprint=community.fingerprint,
        mass_conserved=True,
        balances=[
            ExchangeBalanceSpec(
                metabolite_id=metabolite_id,
                value="0",
                unit=namespace.amount_unit,
            )
            for metabolite_id in sorted(metabolite_ids)
        ],
        scientifically_validated=False,
    )


class CommunityExecutionPlan(_Contract):
    schema_version: Literal["vc.community-execution-plan.v1"]
    plan_id: str
    community_id: str
    community_version: str
    community_fingerprint: str
    member_pack_fingerprints: tuple[str, ...]
    executable: Literal[False]
    steps: tuple[dict[str, str], ...]
    reasons: tuple[Literal["community_model_unavailable"], ...]
    scientifically_validated: Literal[False]

    @field_validator("plan_id", mode="before")
    @classmethod
    def _valid_plan_id(cls, value):
        value = _text(value, "plan_id", limit=39)
        if not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be community_plan_ plus 24 lowercase hex")
        return value

    @field_validator("community_id", "community_version", mode="before")
    @classmethod
    def _valid_identity(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("community_fingerprint", mode="before")
    @classmethod
    def _valid_community_fingerprint(cls, value):
        return _fingerprint(value, "plan.community_fingerprint")

    @field_validator("member_pack_fingerprints")
    @classmethod
    def _valid_member_fingerprints(cls, value):
        if not value:
            raise ValueError("plan must bind at least one member Pack fingerprint")
        values = tuple(_fingerprint(item, "plan.member_pack_fingerprints") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("plan member Pack fingerprints must be unique")
        return values

    @model_validator(mode="after")
    def _no_model_content(self):
        if self.steps:
            raise ValueError("no-model execution plan steps must be empty")
        if self.reasons != ("community_model_unavailable",):
            raise ValueError("no-model execution plan must report community_model_unavailable")
        return self


class CommunityRunResult(_Contract):
    schema_version: Literal["vc.community-run-result.v1"]
    community_fingerprint: str
    abstain: Literal[True]
    prediction: None
    models_used: tuple[str, ...]
    abstain_reasons: tuple[Literal["community_model_unavailable"], ...]
    execution_plan: CommunityExecutionPlan
    scientifically_validated: Literal[False]

    @field_validator("community_fingerprint", mode="before")
    @classmethod
    def _valid_community_fingerprint(cls, value):
        return _fingerprint(value, "result.community_fingerprint")

    @model_validator(mode="after")
    def _honest_abstention(self):
        if self.models_used:
            raise ValueError("no-model abstention models_used must be empty")
        if self.abstain_reasons != ("community_model_unavailable",):
            raise ValueError("no-model abstention must report community_model_unavailable")
        if self.execution_plan.community_fingerprint != self.community_fingerprint:
            raise ValueError("run result and execution plan community fingerprints must match")
        return self


class CommunityModelAdapter(ABC):
    """Future real-model boundary; P10 deliberately ships no implementation."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the stable model name."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the explicit model revision."""

    @property
    @abstractmethod
    def model_fingerprint(self) -> str:
        """Return the content-bound model fingerprint."""

    @abstractmethod
    def plan(self, community: RegisteredCommunityPack) -> dict[str, Any]:
        """Return a compatibility-bound step without executing a prediction."""

    @abstractmethod
    def run(self, community: RegisteredCommunityPack) -> dict[str, Any]:
        """Run a real community model after an executable plan exists."""


def plan_community(community: RegisteredCommunityPack) -> CommunityExecutionPlan:
    if not isinstance(community, RegisteredCommunityPack):
        raise TypeError("plan_community requires RegisteredCommunityPack")
    identity = {
        "schema_version": "vc.community-execution-plan.v1",
        "community_fingerprint": community.fingerprint,
        "member_pack_fingerprints": [record.fingerprint for record in community.members],
        "steps": [],
        "reasons": ["community_model_unavailable"],
    }
    digest = hashlib.sha256(
        json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return CommunityExecutionPlan(
        schema_version="vc.community-execution-plan.v1",
        plan_id=f"community_plan_{digest[:24]}",
        community_id=community.manifest.community_id,
        community_version=community.manifest.community_version,
        community_fingerprint=community.fingerprint,
        member_pack_fingerprints=[record.fingerprint for record in community.members],
        executable=False,
        steps=[],
        reasons=["community_model_unavailable"],
        scientifically_validated=False,
    )


def run_community(community: RegisteredCommunityPack) -> CommunityRunResult:
    plan = plan_community(community)
    return CommunityRunResult(
        schema_version="vc.community-run-result.v1",
        community_fingerprint=community.fingerprint,
        abstain=True,
        prediction=None,
        models_used=[],
        abstain_reasons=["community_model_unavailable"],
        execution_plan=plan,
        scientifically_validated=False,
    )


def tiny_microbial_pack_roots() -> dict[str, Path]:
    examples = Path(__file__).resolve().parents[1] / "example_packs"
    return {
        "ecoli": examples / "bacteria",
        "yeast": examples / "yeast",
    }
