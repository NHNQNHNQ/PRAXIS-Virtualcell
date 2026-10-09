"""Strict, hash-only domain context and veto contracts for direct-v2 runs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, _freeze_json, _json_value

_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_TAXON = re.compile(r"^NCBITaxon:[0-9]+$")
_REASON = re.compile(r"^[a-z][a-z0-9_.-]*$")
_PUBLIC_ID = re.compile(r"^[a-z][a-z0-9_.-]*$")
_PUBLIC_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]*$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be non-empty text without surrounding whitespace")
    return value


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if _FINGERPRINT.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _public_id(value: Any, field: str) -> str:
    value = _text(value, field)
    if _PUBLIC_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a canonical path-safe public identifier")
    return value


def _public_version(value: Any, field: str) -> str:
    value = _text(value, field)
    if _PUBLIC_VERSION.fullmatch(value) is None:
        raise ValueError(f"{field} must be a canonical path-safe public version")
    return value


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


class _DomainContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            messages = "; ".join(
                f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
                for error in exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                )
            )
            raise ValueError(f"{cls.__name__} validation failed: {messages}") from None

    def model_post_init(self, __context: Any) -> None:
        for field, value in self.__dict__.items():
            if isinstance(value, dict):
                object.__setattr__(self, field, _freeze_json(value))

    def to_dict(self) -> dict[str, Any]:
        value = self.model_dump(mode="json")
        _json_value(value)
        return value

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class DomainBrainContextV1(_DomainContract):
    schema_version: Literal["vc.domain-brain-context.v1"]
    brain_id: str
    brain_version: str
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("brain_id", mode="before")
    @classmethod
    def _valid_brain_id(cls, value):
        return _public_id(value, "brain_id")

    @field_validator("brain_version", mode="before")
    @classmethod
    def _valid_brain_version(cls, value):
        return _public_version(value, "brain_version")

    @field_validator("context", mode="before")
    @classmethod
    def _valid_context(cls, value):
        if not isinstance(value, dict):
            raise ValueError("context must be a JSON object")
        return _json_value(value, "context")


class DomainModulePolicyV1(_DomainContract):
    schema_version: Literal["vc.domain-module-policy.v1"]
    policy_id: str
    policy_version: str
    allow_execution: bool
    reasons: tuple[str, ...]
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("policy_id", mode="before")
    @classmethod
    def _valid_policy_id(cls, value):
        return _public_id(value, "policy_id")

    @field_validator("policy_version", mode="before")
    @classmethod
    def _valid_policy_version(cls, value):
        return _public_version(value, "policy_version")

    @field_validator("reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("reasons must be an array")
        values = tuple(_text(item, "reasons") for item in value)
        if len(values) != len(set(values)) or any(
            _REASON.fullmatch(item) is None for item in values
        ):
            raise ValueError("reasons must be unique canonical codes")
        return values

    @field_validator("context", mode="before")
    @classmethod
    def _valid_context(cls, value):
        if not isinstance(value, dict):
            raise ValueError("context must be a JSON object")
        return _json_value(value, "context")

    @model_validator(mode="after")
    def _consistent_decision(self):
        if self.allow_execution and self.reasons:
            raise ValueError("an allow decision cannot carry denial reasons")
        if not self.allow_execution and not self.reasons:
            raise ValueError("a deny decision requires at least one reason")
        return self


class DomainExtensionIdentityV1(_DomainContract):
    schema_version: Literal["vc.domain-extension-identity.v1"]
    domain_id: str
    taxonomy_id: str
    brain_id: str | None
    brain_version: str | None
    brain_context_fingerprint: str | None
    policy_id: str | None
    policy_version: str | None
    module_policy_fingerprint: str | None
    allow_execution: bool
    reasons: tuple[str, ...]

    @field_validator("domain_id", mode="before")
    @classmethod
    def _valid_domain(cls, value):
        return _public_id(value, "domain_id")

    @field_validator("taxonomy_id", mode="before")
    @classmethod
    def _valid_taxonomy(cls, value):
        value = _text(value, "taxonomy_id")
        if _TAXON.fullmatch(value) is None:
            raise ValueError("taxonomy_id must be an exact NCBITaxon identifier")
        return value

    @field_validator("brain_id", "policy_id", mode="before")
    @classmethod
    def _valid_optional_id(cls, value, info):
        return None if value is None else _public_id(value, info.field_name)

    @field_validator("brain_version", "policy_version", mode="before")
    @classmethod
    def _valid_optional_version(cls, value, info):
        return None if value is None else _public_version(value, info.field_name)

    @field_validator(
        "brain_context_fingerprint",
        "module_policy_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @field_validator("reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return DomainModulePolicyV1._valid_reasons(value)

    @model_validator(mode="after")
    def _consistent_identity(self):
        brain = (self.brain_id, self.brain_version, self.brain_context_fingerprint)
        policy = (self.policy_id, self.policy_version, self.module_policy_fingerprint)
        if any(item is None for item in brain) != all(item is None for item in brain):
            raise ValueError("brain identity fields must be all present or all absent")
        if any(item is None for item in policy) != all(item is None for item in policy):
            raise ValueError("policy identity fields must be all present or all absent")
        if self.allow_execution and self.reasons:
            raise ValueError("an allow identity cannot carry denial reasons")
        if not self.allow_execution and not self.reasons:
            raise ValueError("a deny identity requires at least one reason")
        return self


BrainProvider = Callable[[VirtualCellRequestV2], DomainBrainContextV1]
ModulePolicyProvider = Callable[[VirtualCellRequestV2, DomainBrainContextV1], DomainModulePolicyV1]


@dataclass(frozen=True)
class DomainExtension:
    """A domain-owned context/policy pair that can veto, never alter, execution."""

    domain_id: str
    taxon_ids: tuple[str, ...]
    brain_provider: BrainProvider
    module_policy_provider: ModulePolicyProvider

    def __post_init__(self) -> None:
        domain_id = _public_id(self.domain_id, "domain_id")
        if not isinstance(self.taxon_ids, tuple) or not self.taxon_ids:
            raise ValueError("taxon_ids must be a non-empty tuple")
        taxon_ids = tuple(_text(item, "taxon_ids") for item in self.taxon_ids)
        if len(taxon_ids) != len(set(taxon_ids)) or any(
            _TAXON.fullmatch(item) is None for item in taxon_ids
        ):
            raise ValueError("taxon_ids must contain unique exact NCBITaxon identifiers")
        if not callable(self.brain_provider) or not callable(self.module_policy_provider):
            raise TypeError("domain extension providers must be callable")
        object.__setattr__(self, "domain_id", domain_id)
        object.__setattr__(self, "taxon_ids", taxon_ids)

    def evaluate(self, request: VirtualCellRequestV2) -> DomainExtensionIdentityV1:
        if not isinstance(request, VirtualCellRequestV2):
            raise TypeError("domain extensions require VirtualCellRequestV2")
        if request.species.taxonomy_id not in self.taxon_ids:
            raise ValueError("domain extension taxon does not match the request")
        try:
            brain = self.brain_provider(request)
            if not isinstance(brain, DomainBrainContextV1):
                raise TypeError("brain_provider must return DomainBrainContextV1")
            policy = self.module_policy_provider(request, brain)
            if not isinstance(policy, DomainModulePolicyV1):
                raise TypeError("module_policy_provider must return DomainModulePolicyV1")
        except Exception:  # noqa: BLE001 - untrusted domain providers must fail closed
            return DomainExtensionIdentityV1(
                schema_version="vc.domain-extension-identity.v1",
                domain_id=self.domain_id,
                taxonomy_id=request.species.taxonomy_id,
                brain_id=None,
                brain_version=None,
                brain_context_fingerprint=None,
                policy_id=None,
                policy_version=None,
                module_policy_fingerprint=None,
                allow_execution=False,
                reasons=("provider_invalid",),
            )
        return DomainExtensionIdentityV1(
            schema_version="vc.domain-extension-identity.v1",
            domain_id=self.domain_id,
            taxonomy_id=request.species.taxonomy_id,
            brain_id=brain.brain_id,
            brain_version=brain.brain_version,
            brain_context_fingerprint=brain.fingerprint(),
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            module_policy_fingerprint=policy.fingerprint(),
            allow_execution=policy.allow_execution,
            reasons=policy.reasons,
        )
