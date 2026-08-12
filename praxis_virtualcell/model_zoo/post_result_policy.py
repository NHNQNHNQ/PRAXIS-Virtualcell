"""Explicit, fail-closed identities for generic multi-model output reduction.

This module owns only the identity and in-process registration of a numerical
post-result reducer.  It does not decide evidence, promotion, domain policy,
or product presentation.  A reducer is never discovered from a request: the
host must register an exact, source-fingerprinted implementation.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.model_zoo.adapter_sdk import AdapterOutputEnvelope

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY = re.compile(r"^[a-z][a-z0-9._-]*$")
_MODEL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_PUBLIC_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]*$")
_ENTRYPOINT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")

OutputReducerCallable = Callable[[tuple[AdapterOutputEnvelope, ...]], AdapterOutputEnvelope]


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be UTF-8 encodable") from exc
    return value


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _model_name(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _MODEL_NAME.fullmatch(value):
        raise ValueError(f"{field} must be a canonical path-safe model identifier")
    return value


def _public_version(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _PUBLIC_VERSION.fullmatch(value):
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


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError(f"{cls.__name__} must be a JSON object")
        return cls.model_validate(value)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class OutputReducerModelAdapterBindingV1(_Contract):
    """One ordered model-to-adapter binding consumed by a reducer."""

    schema_version: Literal["vc.output-reducer-model-adapter-binding.v1"]
    model_name: str
    model_fingerprint: str
    release_fingerprint: str
    adapter_fingerprint: str

    @field_validator("model_name", mode="before")
    @classmethod
    def _valid_model_name(cls, value):
        return _model_name(value, "model_name")

    @field_validator(
        "model_fingerprint",
        "release_fingerprint",
        "adapter_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)


class OutputReducerBindingV1(_Contract):
    """Public, callable-free binding embedded in an execution plan."""

    schema_version: Literal["vc.output-reducer-binding.v1"]
    policy_id: str
    policy_version: str
    policy_fingerprint: str

    @field_validator("policy_id", mode="before")
    @classmethod
    def _valid_policy_id(cls, value):
        value = _text(value, "policy_id")
        if not _IDENTITY.fullmatch(value):
            raise ValueError("policy_id must be a canonical identifier")
        return value

    @field_validator("policy_version", mode="before")
    @classmethod
    def _valid_policy_version(cls, value):
        return _public_version(value, "policy_version")

    @field_validator("policy_fingerprint", mode="before")
    @classmethod
    def _valid_policy_fingerprint(cls, value):
        return _fingerprint(value, "policy_fingerprint")


class OutputReducerPolicySpecV1(_Contract):
    """Versioned identity of one exact generic reducer implementation."""

    schema_version: Literal["vc.output-reducer-policy.v1"]
    policy_id: str
    policy_version: str
    entrypoint: str
    implementation_fingerprint: str
    task: str
    output_contract_fingerprint: str
    model_adapter_bindings: tuple[OutputReducerModelAdapterBindingV1, ...]
    model_count: int

    @field_validator("policy_id", mode="before")
    @classmethod
    def _valid_policy_id(cls, value):
        value = _text(value, "policy_id")
        if not _IDENTITY.fullmatch(value):
            raise ValueError("policy_id must be a canonical identifier")
        return value

    @field_validator("task", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("policy_version", mode="before")
    @classmethod
    def _valid_policy_version(cls, value):
        return _public_version(value, "policy_version")

    @field_validator("entrypoint", mode="before")
    @classmethod
    def _valid_entrypoint(cls, value):
        value = _text(value, "entrypoint")
        if not _ENTRYPOINT.fullmatch(value):
            raise ValueError("entrypoint must be a fully-qualified Python path")
        return value

    @field_validator("implementation_fingerprint", "output_contract_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("model_adapter_bindings", mode="before")
    @classmethod
    def _valid_bindings(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("model_adapter_bindings must be a non-empty array")
        return tuple(
            item
            if isinstance(item, OutputReducerModelAdapterBindingV1)
            else OutputReducerModelAdapterBindingV1.from_dict(item)
            for item in value
        )

    @field_validator("model_count")
    @classmethod
    def _valid_count(cls, value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError("model_count must be an integer of at least two")
        return value

    @model_validator(mode="after")
    def _exact_ordered_composition(self):
        if len(self.model_adapter_bindings) != self.model_count:
            raise ValueError("model_adapter_bindings must have exactly model_count entries")
        names = tuple(binding.model_name for binding in self.model_adapter_bindings)
        if len(names) != len(set(names)):
            raise ValueError("model_adapter_bindings must have unique model names")
        adapters = {binding.adapter_fingerprint for binding in self.model_adapter_bindings}
        if len(adapters) != 1:
            raise ValueError("U2 v1 requires one exact shared adapter fingerprint")
        return self

    def binding(self) -> OutputReducerBindingV1:
        return OutputReducerBindingV1(
            schema_version="vc.output-reducer-binding.v1",
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            policy_fingerprint=self.fingerprint(),
        )


class OutputReducerStepReceiptV1(_Contract):
    """Public hash receipt for one reducer input in declared policy order."""

    schema_version: Literal["vc.output-reducer-step-receipt.v1"]
    model_name: str
    execution_step_fingerprint: str
    input_hash: str
    output_hash: str

    @field_validator("model_name", mode="before")
    @classmethod
    def _valid_model_name(cls, value):
        return _model_name(value, "model_name")

    @field_validator("execution_step_fingerprint", "input_hash", "output_hash", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)


class OutputReducerReceiptV1(_Contract):
    """Public proof linking a reduced output to every executed input."""

    schema_version: Literal["vc.output-reducer-receipt.v1"]
    output_reducer: OutputReducerBindingV1
    step_receipts: tuple[OutputReducerStepReceiptV1, ...]
    reduced_output_hash: str

    @field_validator("step_receipts", mode="before")
    @classmethod
    def _valid_step_receipts(cls, value):
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            raise ValueError("step_receipts must contain at least two entries")
        return tuple(
            item if isinstance(item, OutputReducerStepReceiptV1) else OutputReducerStepReceiptV1.from_dict(item)
            for item in value
        )

    @field_validator("reduced_output_hash", mode="before")
    @classmethod
    def _valid_reduced_hash(cls, value):
        return _fingerprint(value, "reduced_output_hash")

    @model_validator(mode="after")
    def _unique_step_names(self):
        names = tuple(item.model_name for item in self.step_receipts)
        if len(names) != len(set(names)):
            raise ValueError("step_receipts must have unique model names")
        return self


class OutputReducerPolicyConflictError(ValueError):
    """Two different policies attempted to own one exact selector."""


class OutputReducerPolicyNotFoundError(LookupError):
    """No exact policy is registered for a multi-model plan."""


def reducer_implementation_fingerprint(reducer: OutputReducerCallable) -> str:
    """Fingerprint a stable module-level reducer implementation source."""

    if not inspect.isfunction(reducer):
        raise TypeError("output reducer implementation must be a Python function")
    module = getattr(reducer, "__module__", None)
    qualname = getattr(reducer, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str) or "<locals>" in qualname:
        raise TypeError("output reducer must have a stable module-level entrypoint")
    entrypoint = f"{module}.{qualname}"
    if not _ENTRYPOINT.fullmatch(entrypoint):
        raise ValueError("output reducer entrypoint is invalid")
    try:
        source = inspect.getsource(reducer)
    except (OSError, TypeError) as exc:
        raise ValueError("output reducer implementation source is unavailable") from exc
    if not source:
        raise ValueError("output reducer implementation source is empty")
    return _canonical_fingerprint(
        {
            "schema_version": "vc.output-reducer-implementation.v1",
            "entrypoint": entrypoint,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }
    )


@dataclass(frozen=True)
class ResolvedOutputReducerPolicy:
    spec: OutputReducerPolicySpecV1
    reducer: OutputReducerCallable

    def binding(self) -> OutputReducerBindingV1:
        return self.spec.binding()


class OutputReducerPolicyRegistry:
    """Explicit in-process policy allowlist with no fallback or discovery."""

    def __init__(self) -> None:
        self._by_selector: dict[tuple, ResolvedOutputReducerPolicy] = {}
        self._by_fingerprint: dict[str, ResolvedOutputReducerPolicy] = {}

    @staticmethod
    def _selector(
        *,
        task: str,
        output_contract_fingerprint: str,
        model_adapter_bindings: tuple[OutputReducerModelAdapterBindingV1, ...],
    ) -> tuple:
        task = _text(task, "task")
        output_contract_fingerprint = _fingerprint(
            output_contract_fingerprint,
            "output_contract_fingerprint",
        )
        if not isinstance(model_adapter_bindings, tuple) or len(model_adapter_bindings) < 2:
            raise ValueError("model_adapter_bindings must be an ordered tuple of at least two entries")
        if any(type(item) is not OutputReducerModelAdapterBindingV1 for item in model_adapter_bindings):
            raise TypeError("model_adapter_bindings must contain exact reducer binding contracts")
        return (
            task,
            output_contract_fingerprint,
            tuple(
                (
                    item.model_name,
                    item.model_fingerprint,
                    item.release_fingerprint,
                    item.adapter_fingerprint,
                )
                for item in model_adapter_bindings
            ),
        )

    @classmethod
    def _selector_for_spec(cls, spec: OutputReducerPolicySpecV1) -> tuple:
        return cls._selector(
            task=spec.task,
            output_contract_fingerprint=spec.output_contract_fingerprint,
            model_adapter_bindings=spec.model_adapter_bindings,
        )

    def register(
        self,
        spec: OutputReducerPolicySpecV1,
        reducer: OutputReducerCallable,
    ) -> None:
        if not isinstance(spec, OutputReducerPolicySpecV1):
            raise TypeError("spec must be OutputReducerPolicySpecV1")
        if not callable(reducer):
            raise TypeError("reducer must be callable")
        entrypoint = f"{getattr(reducer, '__module__', '')}.{getattr(reducer, '__qualname__', '')}"
        if entrypoint != spec.entrypoint:
            raise ValueError("reducer callable does not match policy entrypoint")
        if reducer_implementation_fingerprint(reducer) != spec.implementation_fingerprint:
            raise ValueError("reducer callable does not match policy implementation fingerprint")
        selector = self._selector_for_spec(spec)
        candidate = ResolvedOutputReducerPolicy(spec=spec, reducer=reducer)
        existing = self._by_selector.get(selector)
        if existing is None:
            self._by_selector[selector] = candidate
            self._by_fingerprint[spec.fingerprint()] = candidate
            return
        if existing.spec.to_dict() == spec.to_dict() and existing.reducer is reducer:
            return
        raise OutputReducerPolicyConflictError("output reducer policy conflicts with an exact selector")

    def resolve(
        self,
        *,
        task: str,
        output_contract_fingerprint: str,
        model_adapter_bindings: tuple[OutputReducerModelAdapterBindingV1, ...],
    ) -> ResolvedOutputReducerPolicy:
        selector = self._selector(
            task=task,
            output_contract_fingerprint=output_contract_fingerprint,
            model_adapter_bindings=model_adapter_bindings,
        )
        try:
            return self._by_selector[selector]
        except KeyError as exc:
            raise OutputReducerPolicyNotFoundError("no exact output reducer policy is registered") from exc

    def resolve_binding(self, binding: OutputReducerBindingV1) -> ResolvedOutputReducerPolicy:
        if not isinstance(binding, OutputReducerBindingV1):
            raise TypeError("binding must be OutputReducerBindingV1")
        try:
            resolved = self._by_fingerprint[binding.policy_fingerprint]
        except KeyError as exc:
            raise OutputReducerPolicyNotFoundError("output reducer policy fingerprint is not registered") from exc
        if resolved.binding().to_dict() != binding.to_dict():
            raise OutputReducerPolicyNotFoundError("output reducer policy binding drifted")
        if reducer_implementation_fingerprint(resolved.reducer) != (resolved.spec.implementation_fingerprint):
            raise OutputReducerPolicyNotFoundError("output reducer implementation fingerprint drifted")
        return resolved


def _normalize_envelope(value: Any) -> AdapterOutputEnvelope:
    if not isinstance(value, AdapterOutputEnvelope):
        raise TypeError("output reducer must receive AdapterOutputEnvelope values")
    try:
        return AdapterOutputEnvelope.model_validate(value.model_dump(mode="python", serialize_as_any=True))
    except (TypeError, ValueError, ValidationError) as exc:
        raise ValueError("output reducer envelope is invalid") from exc


def _unique_ordered(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def reduce_adapter_outputs(
    envelopes: tuple[AdapterOutputEnvelope, ...],
    *,
    resolved: ResolvedOutputReducerPolicy,
) -> AdapterOutputEnvelope:
    """Run one private reducer and strictly bind its returned envelope.

    The runtime supplies envelopes in the policy-declared model order.  The
    reducer callable itself never becomes part of public plan/provenance bytes.
    """

    if not isinstance(resolved, ResolvedOutputReducerPolicy):
        raise TypeError("output reducer must be a resolved registered policy")
    if not isinstance(envelopes, tuple) or len(envelopes) != resolved.spec.model_count:
        raise ValueError("output reducer input count does not match its policy")
    normalized = tuple(_normalize_envelope(item) for item in envelopes)
    bindings = resolved.spec.model_adapter_bindings
    for envelope, binding in zip(normalized, bindings, strict=True):
        if envelope.abstain or envelope.values is None:
            raise ValueError("output reducer cannot consume an abstaining envelope")
        if not (
            envelope.task == resolved.spec.task
            and envelope.provenance.adapter_fingerprint == binding.adapter_fingerprint
            and envelope.provenance.output_contract_fingerprint == resolved.spec.output_contract_fingerprint
        ):
            raise ValueError("output reducer input does not match the exact policy")
    try:
        reduced = _normalize_envelope(resolved.reducer(normalized))
    except Exception as exc:  # noqa: BLE001 - reducer implementation is a hard boundary
        raise ValueError("output reducer implementation failed") from exc
    adapter_fingerprint = bindings[0].adapter_fingerprint
    expected_inputs = tuple(item.provenance.input_fingerprints[0] for item in normalized)
    expected_requests = _unique_ordered(tuple(item.provenance.request_fingerprints[0] for item in normalized))
    expected_packs = _unique_ordered(
        tuple(fingerprint for item in normalized for fingerprint in item.provenance.pack_fingerprints)
    )
    expected_compatibility = tuple(item.provenance.compatibility_fingerprints[0] for item in normalized)
    if not (
        reduced.task == resolved.spec.task
        and reduced.provenance.adapter_fingerprint == adapter_fingerprint
        and reduced.provenance.input_contract_fingerprint == normalized[0].provenance.input_contract_fingerprint
        and reduced.provenance.output_contract_fingerprint == resolved.spec.output_contract_fingerprint
        and reduced.provenance.input_fingerprints == expected_inputs
        and reduced.provenance.request_fingerprints == expected_requests
        and reduced.provenance.pack_fingerprints == expected_packs
        and reduced.provenance.compatibility_fingerprints == expected_compatibility
    ):
        raise ValueError("reduced output provenance does not match all reducer inputs")
    return reduced
