"""Strict, versioned model-adapter contracts for Pack-aware execution.

The SDK translates an already governed request into immutable model input and
normalizes a wrapper result into a task/output envelope.  It does not load Pack
matrices, infer feature mappings, create scientific evidence, or make policy
decisions.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, _freeze_json, _json_value
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignmentReport,
    AlignmentStep,
    MappingAssetRef,
    ModelFeatureContract,
)
from praxis_virtualcell.data_packs.selected_content import (
    PreparedSelectedContentV1,
    SelectedContentReceiptV1,
    SelectedContentRequestV1,
)
from praxis_virtualcell.model_zoo.registry_v2 import AdapterIdentity

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_SAFE_INTEGER = 2**53 - 1
_RESERVED_PROJECTION_KEYS = {
    "benchmark_passed",
    "evidence",
    "operator_decision",
    "scientific_evidence",
    "scientifically_validated",
    "production_promoted",
    "promotion_decision",
    "promotion_eligible",
    "policy",
    "policy_verdict",
    "operator_policy",
}


class AdapterContractError(ValueError):
    """An adapter identity, input, or output failed its strict contract."""


def _reject_undeclared_model_fields(
    value: Any,
    path: str,
    seen: set[int] | None = None,
) -> None:
    seen = set() if seen is None else seen
    traversable = isinstance(value, (BaseModel, dict, list, tuple, set, frozenset)) or (
        is_dataclass(value) and not isinstance(value, type)
    )
    if traversable:
        marker = id(value)
        if marker in seen:
            return
        seen.add(marker)
    if isinstance(value, BaseModel):
        declared = type(value).model_fields
        unexpected = set(value.__dict__).difference(declared)
        pydantic_extra = getattr(value, "__pydantic_extra__", None)
        if pydantic_extra:
            unexpected.update(pydantic_extra)
        if unexpected:
            raise AdapterContractError(f"{path} contains unknown fields: {sorted(unexpected)}")
        for name in declared:
            _reject_undeclared_model_fields(getattr(value, name), f"{path}.{name}", seen)
    elif is_dataclass(value) and not isinstance(value, type):
        declared = {field.name for field in dataclass_fields(value)}
        unexpected = set(getattr(value, "__dict__", {})).difference(declared)
        if unexpected:
            raise AdapterContractError(f"{path} contains unknown fields: {sorted(unexpected)}")
        for name in declared:
            _reject_undeclared_model_fields(getattr(value, name), f"{path}.{name}", seen)
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_undeclared_model_fields(item, f"{path}.{key}", seen)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            _reject_undeclared_model_fields(item, f"{path}[{index}]", seen)


def _reject_model_type_drift(
    observed: Any,
    normalized: Any,
    path: str,
    seen: set[tuple[int, int]] | None = None,
) -> None:
    seen = set() if seen is None else seen
    pair = (id(observed), id(normalized))
    if pair in seen:
        return
    seen.add(pair)
    if isinstance(normalized, BaseModel):
        if isinstance(observed, Mapping):
            for name in type(normalized).model_fields:
                if name in observed:
                    _reject_model_type_drift(
                        observed[name],
                        getattr(normalized, name),
                        f"{path}.{name}",
                        seen,
                    )
            return
        if type(observed) is not type(normalized):
            raise AdapterContractError(f"{path} has a non-canonical model type")
        for name in type(normalized).model_fields:
            _reject_model_type_drift(
                getattr(observed, name),
                getattr(normalized, name),
                f"{path}.{name}",
                seen,
            )
    elif is_dataclass(normalized) and not isinstance(normalized, type):
        if type(observed) is not type(normalized):
            raise AdapterContractError(f"{path} has a non-canonical dataclass type")
        for field in dataclass_fields(normalized):
            _reject_model_type_drift(
                getattr(observed, field.name),
                getattr(normalized, field.name),
                f"{path}.{field.name}",
                seen,
            )
    elif isinstance(normalized, Mapping):
        if not isinstance(observed, Mapping):
            raise AdapterContractError(f"{path} has a non-canonical mapping type")
        for key, value in normalized.items():
            if key in observed:
                _reject_model_type_drift(observed[key], value, f"{path}.{key}", seen)
    elif isinstance(normalized, (list, tuple)):
        if not isinstance(observed, (list, tuple)) or len(observed) != len(normalized):
            raise AdapterContractError(f"{path} has a non-canonical sequence type")
        for index, (before, after) in enumerate(zip(observed, normalized, strict=True)):
            _reject_model_type_drift(before, after, f"{path}[{index}]", seen)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        _reject_undeclared_model_fields(value, type(value).__name__)
        return _canonical_value(value.model_dump(mode="json"))
    if isinstance(value, AlignmentReport):
        return _canonical_value(value.to_dict())
    if isinstance(value, dict):
        return {key: _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _fingerprint(value: dict[str, Any]) -> str:
    canonical = json.dumps(
        _canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _strict_fingerprint(value: Any, field: str) -> str:
    value = _strict_text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _strict_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterContractError("adapter values must contain finite numbers")
    if isinstance(value, int) and abs(value) > _MAX_SAFE_INTEGER:
        raise AdapterContractError("adapter values must contain finite numbers safely representable in JSON")
    try:
        number = float(value)
    except OverflowError as exc:
        raise AdapterContractError("adapter values must contain finite numbers") from exc
    if not math.isfinite(number):
        raise AdapterContractError("adapter values must contain finite numbers")
    return number


def _tensor(value: Any) -> tuple[Any, tuple[int, ...]]:
    if not isinstance(value, (list, tuple)) or not value:
        raise AdapterContractError("adapter values must be a non-empty numeric tensor")
    nested = [isinstance(item, (list, tuple)) for item in value]
    if any(nested) and not all(nested):
        raise AdapterContractError("adapter values must be rectangular")
    if not any(nested):
        return tuple(_strict_number(item) for item in value), (len(value),)
    rows = []
    shapes = []
    for item in value:
        row, shape = _tensor(item)
        rows.append(row)
        shapes.append(shape)
    if len(set(shapes)) != 1:
        raise AdapterContractError("adapter values must be rectangular")
    return tuple(rows), (len(rows), *shapes[0])


def _shape_matches(actual: tuple[int, ...], declared: tuple[int | None, ...]) -> bool:
    return len(actual) == len(declared) and all(
        expected is None or expected == observed for observed, expected in zip(actual, declared, strict=True)
    )


def _contains_reserved_projection_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in _RESERVED_PROJECTION_KEYS or _contains_reserved_projection_key(item) for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_reserved_projection_key(item) for item in value)
    return False


def _contains_rooted_local_path(value: Any) -> bool:
    if isinstance(value, str):
        candidate = value.lstrip()
        normalized = candidate.casefold()
        return bool(
            candidate.startswith(("/", "~/", "~\\", "\\"))
            or normalized.startswith("file:")
            or re.match(r"^[A-Za-z]:[\\/]", candidate)
        )
    if isinstance(value, dict):
        return any(_contains_rooted_local_path(key) or _contains_rooted_local_path(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_rooted_local_path(item) for item in value)
    return False


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, arbitrary_types_allowed=True)

    def to_dict(self) -> dict[str, Any]:
        _reject_undeclared_model_fields(self, type(self).__name__)
        value = self.model_dump(mode="json", serialize_as_any=True)
        if isinstance(self, AdapterOutputEnvelope) and _contains_rooted_local_path(value):
            raise ValueError("adapter output envelope must not contain rooted local paths")
        return value

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


class AdapterInputContract(_Contract):
    schema_version: Literal["vc.adapter-input-contract.v1"]
    task: str
    output: str
    value_type: Literal["float"]
    shape: tuple[int | None, ...]
    unit: str | None
    pack_data_required: bool
    alignment_required: bool

    @field_validator("task", "output", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("unit", mode="before")
    @classmethod
    def _unit(cls, value):
        return None if value is None else _strict_text(value, "unit")

    @field_validator("shape", mode="before")
    @classmethod
    def _shape(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("shape must be a non-empty array")
        if any(
            item is not None and (isinstance(item, bool) or not isinstance(item, int) or item <= 0) for item in value
        ):
            raise ValueError("shape dimensions must be positive integers or null")
        return tuple(value)

    @field_validator("pack_data_required", "alignment_required", mode="before")
    @classmethod
    def _bool(cls, value, info):
        if not isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a boolean")
        return value

    @model_validator(mode="after")
    def _alignment_needs_data(self):
        if self.alignment_required and not self.pack_data_required:
            raise ValueError("alignment_required requires pack_data_required")
        return self


class AdapterOutputContract(_Contract):
    schema_version: Literal["vc.adapter-output-contract.v1"]
    task: str
    output: str
    value_type: Literal["float"]
    shape: tuple[int | None, ...]
    unit: str | None
    uncertainty_required: bool
    ood_required: bool
    abstain_allowed: bool

    @field_validator("task", "output", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("unit", mode="before")
    @classmethod
    def _unit(cls, value):
        return None if value is None else _strict_text(value, "unit")

    @field_validator("shape", mode="before")
    @classmethod
    def _shape(cls, value):
        return AdapterInputContract._shape(value)

    @field_validator("uncertainty_required", "ood_required", "abstain_allowed", mode="before")
    @classmethod
    def _bool(cls, value, info):
        if not isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a boolean")
        return value


class PreparedAdapterInput(_Contract):
    schema_version: Literal["vc.prepared-adapter-input.v1"]
    adapter_fingerprint: str
    input_contract_fingerprint: str
    task: str
    output: str
    request_fingerprint: str
    pack_fingerprint: str | None
    compatibility_fingerprint: str | None
    model_input: dict[str, Any]
    values: tuple[Any, ...] | None
    shape: tuple[int, ...] | None
    unit: str | None
    feature_contract: ModelFeatureContract | None
    feature_contract_fingerprint: str | None
    alignment_report: AlignmentReport | None

    @field_validator(
        "adapter_fingerprint",
        "input_contract_fingerprint",
        "request_fingerprint",
        mode="before",
    )
    @classmethod
    def _required_fingerprint(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "pack_fingerprint",
        "compatibility_fingerprint",
        "feature_contract_fingerprint",
        mode="before",
    )
    @classmethod
    def _optional_fingerprint(cls, value, info):
        return None if value is None else _strict_fingerprint(value, info.field_name)

    @field_validator("task", "output", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("unit", mode="before")
    @classmethod
    def _unit(cls, value):
        return None if value is None else _strict_text(value, "unit")

    @field_validator("model_input")
    @classmethod
    def _model_input(cls, value):
        if not isinstance(value, dict):
            raise ValueError("model_input must be a JSON object")
        value = _canonical_value(value)
        _json_value(value, "$.model_input")
        return _freeze_json(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "adapter_fingerprint": self.adapter_fingerprint,
            "input_contract_fingerprint": self.input_contract_fingerprint,
            "task": self.task,
            "output": self.output,
            "request_fingerprint": self.request_fingerprint,
            "pack_fingerprint": self.pack_fingerprint,
            "compatibility_fingerprint": self.compatibility_fingerprint,
            "model_input": _canonical_value(self.model_input),
            "values": _canonical_value(self.values),
            "shape": None if self.shape is None else list(self.shape),
            "unit": self.unit,
            "feature_contract": (
                None if self.feature_contract is None else self.feature_contract.model_dump(mode="json")
            ),
            "feature_contract_fingerprint": self.feature_contract_fingerprint,
            "alignment_report": (None if self.alignment_report is None else self.alignment_report.to_dict()),
        }


class AdapterInputReceipt(_Contract):
    """Public, payload-free identity receipt for one broker-prepared input."""

    schema_version: Literal["vc.adapter-input-receipt.v1"]
    prepared_input_fingerprint: str
    adapter_fingerprint: str
    input_contract_fingerprint: str
    task: str
    output: str
    request_fingerprint: str
    pack_fingerprint: str | None
    compatibility_fingerprint: str | None
    feature_contract_fingerprint: str | None
    alignment_fingerprint: str | None
    shape: tuple[int, ...] | None
    unit: str | None

    @field_validator(
        "prepared_input_fingerprint",
        "adapter_fingerprint",
        "input_contract_fingerprint",
        "request_fingerprint",
        mode="before",
    )
    @classmethod
    def _required_fingerprint(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "pack_fingerprint",
        "compatibility_fingerprint",
        "feature_contract_fingerprint",
        "alignment_fingerprint",
        mode="before",
    )
    @classmethod
    def _optional_fingerprint(cls, value, info):
        return None if value is None else _strict_fingerprint(value, info.field_name)

    @field_validator("task", "output", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("unit", mode="before")
    @classmethod
    def _unit(cls, value):
        return None if value is None else _strict_text(value, "unit")

    @field_validator("shape", mode="before")
    @classmethod
    def _shape(cls, value):
        return None if value is None else AdapterOutputEnvelope._shape(value)

    @classmethod
    def from_prepared(cls, prepared: PreparedAdapterInput) -> AdapterInputReceipt:
        if not isinstance(prepared, PreparedAdapterInput):
            raise TypeError("prepared must be PreparedAdapterInput")
        alignment_fingerprint = (
            None if prepared.alignment_report is None else _fingerprint(prepared.alignment_report.to_dict())
        )
        return cls(
            schema_version="vc.adapter-input-receipt.v1",
            prepared_input_fingerprint=prepared.fingerprint(),
            adapter_fingerprint=prepared.adapter_fingerprint,
            input_contract_fingerprint=prepared.input_contract_fingerprint,
            task=prepared.task,
            output=prepared.output,
            request_fingerprint=prepared.request_fingerprint,
            pack_fingerprint=prepared.pack_fingerprint,
            compatibility_fingerprint=prepared.compatibility_fingerprint,
            feature_contract_fingerprint=prepared.feature_contract_fingerprint,
            alignment_fingerprint=alignment_fingerprint,
            shape=prepared.shape,
            unit=prepared.unit,
        )


class AdapterInputReceiptV2(_Contract):
    """Write-new public receipt binding one prepared input to Pack-derived values."""

    schema_version: Literal["vc.adapter-input-receipt.v2"]
    prepared_input_fingerprint: str
    adapter_fingerprint: str
    input_contract_fingerprint: str
    task: str
    output: str
    request_fingerprint: str
    pack_fingerprint: str | None
    compatibility_fingerprint: str | None
    feature_contract_fingerprint: str | None
    alignment_fingerprint: str | None
    shape: tuple[int, ...] | None
    unit: str | None
    selected_content_receipt: SelectedContentReceiptV1

    @field_validator(
        "prepared_input_fingerprint",
        "adapter_fingerprint",
        "input_contract_fingerprint",
        "request_fingerprint",
        mode="before",
    )
    @classmethod
    def _required_fingerprint(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "pack_fingerprint",
        "compatibility_fingerprint",
        "feature_contract_fingerprint",
        "alignment_fingerprint",
        mode="before",
    )
    @classmethod
    def _optional_fingerprint(cls, value, info):
        return None if value is None else _strict_fingerprint(value, info.field_name)

    @field_validator("task", "output", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("unit", mode="before")
    @classmethod
    def _unit(cls, value):
        return None if value is None else _strict_text(value, "unit")

    @field_validator("shape", mode="before")
    @classmethod
    def _shape(cls, value):
        return None if value is None else AdapterOutputEnvelope._shape(value)

    @model_validator(mode="after")
    def _selected_content_binding(self):
        content = self.selected_content_receipt
        if not (
            self.pack_fingerprint is not None
            and self.feature_contract_fingerprint is not None
            and self.alignment_fingerprint is not None
            and self.shape is not None
            and self.unit is not None
            and content.request_fingerprint == self.request_fingerprint
            and content.pack_fingerprint == self.pack_fingerprint
            and content.feature_contract_fingerprint == self.feature_contract_fingerprint
            and content.alignment_fingerprint == self.alignment_fingerprint
            and content.unit == self.unit
            and content.target_shape == self.shape
        ):
            raise ValueError("selected-content receipt does not bind this prepared input")
        return self

    @classmethod
    def from_prepared(
        cls,
        prepared: PreparedAdapterInput,
        content: PreparedSelectedContentV1,
    ) -> AdapterInputReceiptV2:
        if not isinstance(prepared, PreparedAdapterInput) or not isinstance(content, PreparedSelectedContentV1):
            raise TypeError("selected-content receipt requires prepared input and core content")
        if not (
            prepared.values == content.values
            and prepared.shape == (len(content.values),)
            and prepared.unit == content.receipt.unit
            and prepared.model_input == content.model_input
            and prepared.feature_contract == content.feature_contract
            and prepared.feature_contract_fingerprint == content.feature_contract.fingerprint()
            and prepared.alignment_report is not None
            and prepared.alignment_report.to_dict() == content.alignment_report.to_dict()
        ):
            raise AdapterContractError("prepared input drifted from core selected content")
        base = AdapterInputReceipt.from_prepared(prepared)
        return cls(
            schema_version="vc.adapter-input-receipt.v2",
            prepared_input_fingerprint=base.prepared_input_fingerprint,
            adapter_fingerprint=base.adapter_fingerprint,
            input_contract_fingerprint=base.input_contract_fingerprint,
            task=base.task,
            output=base.output,
            request_fingerprint=base.request_fingerprint,
            pack_fingerprint=base.pack_fingerprint,
            compatibility_fingerprint=base.compatibility_fingerprint,
            feature_contract_fingerprint=base.feature_contract_fingerprint,
            alignment_fingerprint=base.alignment_fingerprint,
            shape=base.shape,
            unit=base.unit,
            selected_content_receipt=content.receipt,
        )


def adapter_input_receipt_from_dict(
    value: dict[str, Any],
) -> AdapterInputReceipt | AdapterInputReceiptV2:
    """Parse an untrusted public receipt without accepting prepared payload."""
    if not isinstance(value, dict):
        raise AdapterContractError("adapter input receipt must be a JSON object")
    try:
        if value.get("schema_version") == "vc.adapter-input-receipt.v1":
            return AdapterInputReceipt.model_validate(value)
        if value.get("schema_version") == "vc.adapter-input-receipt.v2":
            return AdapterInputReceiptV2.model_validate(value)
        raise ValueError("unsupported adapter input receipt schema")
    except (TypeError, ValidationError, ValueError) as exc:
        raise AdapterContractError("adapter input receipt is invalid") from exc


class AdapterUncertainty(_Contract):
    available: bool
    method: str
    calibrated: bool
    value: float | None = None
    sigma: float | None = None
    reason: str | None = None

    @field_validator("available", "calibrated", mode="before")
    @classmethod
    def _bool(cls, value, info):
        if not isinstance(value, bool):
            raise ValueError(f"uncertainty.{info.field_name} must be a boolean")
        return value

    @field_validator("method", mode="before")
    @classmethod
    def _method(cls, value):
        return _strict_text(value, "uncertainty.method")

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, value):
        return None if value is None else _strict_text(value, "uncertainty.reason")

    @field_validator("value", "sigma", mode="before")
    @classmethod
    def _number(cls, value, info):
        number = None if value is None else _strict_number(value)
        if info.field_name == "sigma" and number is not None and number < 0:
            raise ValueError("uncertainty.sigma must be non-negative")
        return number

    @model_validator(mode="after")
    def _availability(self):
        if not self.available and (self.calibrated or self.value is not None or self.sigma is not None):
            raise ValueError("unavailable uncertainty cannot contain numeric or calibrated claims")
        if self.calibrated and self.value is None and self.sigma is None:
            raise ValueError("calibrated uncertainty requires a numeric value or sigma")
        return self


class AdapterOOD(_Contract):
    detected: bool
    dimensions: tuple[str, ...]
    reason: str | None

    @field_validator("detected", mode="before")
    @classmethod
    def _bool(cls, value):
        if not isinstance(value, bool):
            raise ValueError("ood.detected must be a boolean")
        return value

    @field_validator("dimensions", mode="before")
    @classmethod
    def _dimensions(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("ood.dimensions must be an array")
        values = tuple(_strict_text(item, "ood.dimensions") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("ood.dimensions must not contain duplicates")
        return values

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, value):
        return None if value is None else _strict_text(value, "ood.reason")

    @model_validator(mode="after")
    def _detected_detail(self):
        if self.detected and not self.dimensions and self.reason is None:
            raise ValueError("detected OOD requires a dimension or reason")
        return self


class AdapterExecutionProvenance(_Contract):
    schema_version: Literal["vc.adapter-execution-provenance.v1"]
    adapter_fingerprint: str
    input_fingerprints: tuple[str, ...]
    input_contract_fingerprint: str
    output_contract_fingerprint: str
    request_fingerprints: tuple[str, ...]
    pack_fingerprints: tuple[str, ...]
    compatibility_fingerprints: tuple[str, ...]

    @field_validator("adapter_fingerprint", "input_contract_fingerprint", "output_contract_fingerprint", mode="before")
    @classmethod
    def _fingerprint(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "input_fingerprints",
        "request_fingerprints",
        "pack_fingerprints",
        "compatibility_fingerprints",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        values = tuple(_strict_fingerprint(item, info.field_name) for item in value)
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return values


class AdapterOutputEnvelope(_Contract):
    schema_version: Literal["vc.adapter-output-envelope.v1"]
    task: str
    output: str
    shape: tuple[int, ...] | None
    unit: str | None
    values: tuple[Any, ...] | None
    uncertainty: AdapterUncertainty | None
    ood: AdapterOOD | None
    abstain: bool
    abstain_reasons: tuple[str, ...]
    projection_metadata: dict[str, Any]
    provenance: AdapterExecutionProvenance

    @field_validator("task", "output", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("unit", mode="before")
    @classmethod
    def _unit(cls, value):
        return None if value is None else _strict_text(value, "unit")

    @field_validator("shape", mode="before")
    @classmethod
    def _shape(cls, value):
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("shape must be a non-empty array or null")
        if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value):
            raise ValueError("shape dimensions must be positive integers")
        return tuple(value)

    @field_validator("values", mode="before")
    @classmethod
    def _values(cls, value):
        return None if value is None else _tensor(value)[0]

    @field_validator("abstain", mode="before")
    @classmethod
    def _abstain(cls, value):
        if not isinstance(value, bool):
            raise ValueError("abstain must be a boolean")
        return value

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _reasons(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("abstain_reasons must be an array")
        return tuple(_strict_text(item, "abstain_reasons") for item in value)

    @field_validator("projection_metadata")
    @classmethod
    def _metadata(cls, value):
        if not isinstance(value, dict):
            raise ValueError("projection_metadata must be an object")
        value = _canonical_value(value)
        _json_value(value, "$.projection_metadata")
        if _contains_rooted_local_path(value):
            raise ValueError("projection_metadata must not contain rooted local paths")
        return _freeze_json(value)

    @model_validator(mode="after")
    def _consistent_abstention(self):
        if self.abstain:
            if self.values is not None or self.shape is not None:
                raise ValueError("abstain envelope must not contain values or shape")
            if not self.abstain_reasons:
                raise ValueError("abstain envelope requires reasons")
        elif self.values is None or self.shape is None or self.abstain_reasons:
            raise ValueError("non-abstain envelope requires values/shape and no abstain reasons")
        else:
            _, actual_shape = _tensor(self.values)
            if actual_shape != self.shape:
                raise ValueError("adapter output shape does not match its values")
        if self.ood is not None and self.ood.detected and not self.abstain:
            raise ValueError("OOD output must abstain")
        if _contains_rooted_local_path(self.model_dump(mode="python", serialize_as_any=True)):
            raise ValueError("adapter output envelope must not contain rooted local paths")
        return self


class AdapterConformanceReport(_Contract):
    schema_version: Literal["vc.adapter-conformance-report.v1"]
    adapter_fingerprint: str
    input_fingerprint: str
    output_fingerprint: str
    deterministic: bool

    @field_validator("adapter_fingerprint", "input_fingerprint", "output_fingerprint", mode="before")
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)


class VirtualCellModelAdapter(ABC):
    """One registered task/output adapter with immutable contracts."""

    adapter_id: ClassVar[str]
    version: ClassVar[str]
    input_contract: ClassVar[AdapterInputContract]
    output_contract: ClassVar[AdapterOutputContract]

    def identity(self) -> AdapterIdentity:
        if (
            self.input_contract.task != self.output_contract.task
            or self.input_contract.output != self.output_contract.output
        ):
            raise AdapterContractError("adapter input/output contracts disagree")
        return AdapterIdentity.from_dict(
            {
                "schema_version": "vc.model-adapter.v1",
                "adapter_id": self.adapter_id,
                "version": self.version,
                "implementation": f"{type(self).__module__}.{type(self).__qualname__}",
                "task": self.output_contract.task,
                "outputs": [self.output_contract.output],
                "input_contract_fingerprint": self.input_contract.fingerprint(),
                "output_contract_fingerprint": self.output_contract.fingerprint(),
                "legacy_incomplete": False,
            }
        )

    def fingerprint(self) -> str:
        return self.identity().fingerprint()

    def validate_envelope(self, envelope: AdapterOutputEnvelope) -> AdapterOutputEnvelope:
        """Validate one normalized output against this adapter's exact contract."""
        if not isinstance(envelope, AdapterOutputEnvelope):
            raise TypeError("envelope must be AdapterOutputEnvelope")
        _reject_undeclared_model_fields(envelope, "adapter output envelope")
        try:
            observed_envelope = envelope
            fields = AdapterOutputEnvelope.model_fields
            if set(envelope.__dict__).difference(fields):
                raise AdapterContractError("adapter output envelope has unknown fields")
            envelope = AdapterOutputEnvelope.model_validate(envelope.model_dump(mode="python", serialize_as_any=True))
            _reject_model_type_drift(observed_envelope, envelope, "adapter output envelope")
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("invalid adapter output envelope") from exc
        contract = self.output_contract
        provenance = envelope.provenance
        if (
            (envelope.task, envelope.output, envelope.unit) != (contract.task, contract.output, contract.unit)
            or provenance.adapter_fingerprint != self.fingerprint()
            or provenance.input_contract_fingerprint != self.input_contract.fingerprint()
            or provenance.output_contract_fingerprint != contract.fingerprint()
        ):
            raise AdapterContractError("adapter output does not match adapter contracts")
        if not provenance.input_fingerprints or not provenance.request_fingerprints:
            raise AdapterContractError("adapter output provenance is missing input bindings")
        if envelope.output in envelope.projection_metadata or _contains_reserved_projection_key(
            envelope.projection_metadata
        ):
            raise AdapterContractError("projection metadata contains reserved contract fields")
        if _contains_rooted_local_path(
            envelope.model_dump(mode="python", serialize_as_any=True)
        ):
            raise AdapterContractError("adapter output envelope contains rooted local paths")
        if contract.uncertainty_required and envelope.uncertainty is None:
            raise AdapterContractError("output contract requires uncertainty")
        if contract.ood_required and envelope.ood is None:
            raise AdapterContractError("output contract requires OOD status")
        if envelope.abstain:
            if not contract.abstain_allowed:
                raise AdapterContractError("output contract does not allow abstention")
            return envelope
        if envelope.values is None or envelope.shape is None:
            raise AdapterContractError("non-abstain output requires values and shape")
        _, actual_shape = _tensor(envelope.values)
        if actual_shape != envelope.shape or not _shape_matches(actual_shape, contract.shape):
            raise AdapterContractError("adapter output shape does not match the output contract")
        return envelope

    def validate_prepared_input(
        self,
        prepared: PreparedAdapterInput,
    ) -> PreparedAdapterInput:
        """Validate an immutable prepared input against this adapter's declaration."""
        if not isinstance(prepared, PreparedAdapterInput):
            raise TypeError("prepared must be PreparedAdapterInput")
        _reject_undeclared_model_fields(prepared, "prepared input")
        contract = self.input_contract
        if (
            prepared.adapter_fingerprint != self.fingerprint()
            or prepared.input_contract_fingerprint != contract.fingerprint()
            or (prepared.task, prepared.output) != (contract.task, contract.output)
            or prepared.unit != contract.unit
        ):
            raise AdapterContractError("prepared input does not match adapter contracts")
        try:
            _strict_fingerprint(prepared.request_fingerprint, "request_fingerprint")
            for field in (
                "pack_fingerprint",
                "compatibility_fingerprint",
                "feature_contract_fingerprint",
            ):
                value = getattr(prepared, field)
                if value is not None:
                    _strict_fingerprint(value, field)
        except ValueError as exc:
            raise AdapterContractError("prepared input fingerprint is invalid") from exc
        if not isinstance(prepared.model_input, dict):
            raise AdapterContractError("prepared model_input must be an object")
        try:
            _json_value(_canonical_value(prepared.model_input), "$.model_input")
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("prepared model_input must be JSON-safe") from exc
        if prepared.values is None:
            if prepared.shape is not None:
                raise AdapterContractError("prepared input shape requires values")
            normalized_values = None
            actual_shape = None
        else:
            normalized_values, actual_shape = _tensor(prepared.values)
            if prepared.shape != actual_shape or not _shape_matches(actual_shape, contract.shape):
                raise AdapterContractError("prepared values do not match the input contract")
        if prepared.feature_contract is not None and not isinstance(prepared.feature_contract, ModelFeatureContract):
            raise AdapterContractError("prepared feature contract has the wrong type")
        if prepared.alignment_report is not None and not isinstance(prepared.alignment_report, AlignmentReport):
            raise AdapterContractError("prepared alignment report has the wrong type")
        try:
            feature_fingerprint = _alignment_binding(
                actual_shape,
                prepared.feature_contract,
                prepared.alignment_report,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise AdapterContractError("prepared feature alignment is invalid") from exc
        if prepared.feature_contract_fingerprint != feature_fingerprint:
            raise AdapterContractError("prepared feature contract fingerprint drift")
        if contract.pack_data_required and (prepared.values is None or prepared.pack_fingerprint is None):
            raise AdapterContractError("adapter requires explicit fingerprinted Pack data")
        if contract.alignment_required and feature_fingerprint is None:
            raise AdapterContractError("adapter requires a feature contract and alignment report")
        fields = PreparedAdapterInput.model_fields
        if set(prepared.__dict__).difference(fields):
            raise AdapterContractError("prepared input has unknown fields")
        data = {field: getattr(prepared, field) for field in fields}
        data["model_input"] = deepcopy(_canonical_value(prepared.model_input))
        data["values"] = normalized_values
        try:
            normalized = PreparedAdapterInput.model_validate(data)
            _reject_model_type_drift(prepared, normalized, "prepared input")
            return normalized
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("prepared input cannot be normalized") from exc

    def validate_projection(self, projection: dict[str, Any]) -> dict[str, Any]:
        """Keep adapter projections deterministic, JSON-safe, and policy-neutral."""
        if not isinstance(projection, dict) or not projection:
            raise AdapterContractError("adapter projection must be a non-empty object")
        projection = _canonical_value(projection)
        try:
            _json_value(projection, "$.adapter_projection")
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("adapter projection must be JSON-safe") from exc
        if _contains_reserved_projection_key(projection):
            raise AdapterContractError("adapter projection contains reserved science or policy fields")
        return projection

    def validate_prepared_envelope(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> AdapterOutputEnvelope:
        """Bind a valid envelope to the exact input prepared for this execution."""
        prepared = self.validate_prepared_input(prepared)
        envelope = self.validate_envelope(envelope)
        expected_pack = () if prepared.pack_fingerprint is None else (prepared.pack_fingerprint,)
        expected_compatibility = (
            () if prepared.compatibility_fingerprint is None else (prepared.compatibility_fingerprint,)
        )
        if (
            envelope.provenance.input_fingerprints != (prepared.fingerprint(),)
            or envelope.provenance.request_fingerprints != (prepared.request_fingerprint,)
            or envelope.provenance.pack_fingerprints != expected_pack
            or envelope.provenance.compatibility_fingerprints != expected_compatibility
        ):
            raise AdapterContractError("adapter output provenance does not match prepared input")
        return envelope

    def select_content(
        self,
        request: VirtualCellRequestV2,
        **kwargs,
    ) -> SelectedContentRequestV1:
        """Declare a value-free request for a core-owned v0.4 Pack vector.

        Only adapters whose input contract requires Pack data need to override
        this.  Returning values, paths, mappings, or an untyped object is not
        an alternate input route.
        """

        raise AdapterContractError("adapter does not declare selected content")

    @abstractmethod
    def prepare_input(self, request: VirtualCellRequestV2, **kwargs) -> PreparedAdapterInput:
        """Prepare model input without guessing Pack rows, mappings, or transforms."""

    @abstractmethod
    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        """Validate and normalize one wrapper result."""

    def aggregate(self, envelopes: tuple[AdapterOutputEnvelope, ...]) -> AdapterOutputEnvelope:
        if len(envelopes) != 1:
            raise AdapterContractError("adapter has no declared multi-model aggregation policy")
        return self.validate_envelope(envelopes[0])

    def project_output(self, envelope: AdapterOutputEnvelope) -> dict[str, Any]:
        envelope = self.validate_envelope(envelope)
        if envelope.abstain or envelope.values is None:
            raise AdapterContractError("cannot project an abstaining adapter output")
        return {envelope.output: _canonical_value(envelope.values)}

    def project_prepared_output(
        self,
        prepared: PreparedAdapterInput,
        envelope: AdapterOutputEnvelope,
    ) -> dict[str, Any]:
        """Project only after binding an envelope to its exact prepared input."""
        return self.project_output(self.validate_prepared_envelope(prepared, envelope))


class AdapterRegistry:
    """In-process allowlist keyed by exact task/output and P12 identity fingerprint."""

    def __init__(self, adapters=()) -> None:
        self._by_pair: dict[tuple[str, str], VirtualCellModelAdapter] = {}
        self._by_fingerprint: dict[str, VirtualCellModelAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: VirtualCellModelAdapter) -> None:
        if not isinstance(adapter, VirtualCellModelAdapter):
            raise TypeError("adapter must implement VirtualCellModelAdapter")
        pair = (adapter.output_contract.task, adapter.output_contract.output)
        if pair in self._by_pair:
            raise AdapterContractError(f"duplicate task/output adapter: {pair}")
        fingerprint = adapter.fingerprint()
        if fingerprint in self._by_fingerprint:
            raise AdapterContractError("duplicate adapter identity")
        self._by_pair[pair] = adapter
        self._by_fingerprint[fingerprint] = adapter

    def keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._by_pair))

    def resolve(self, task: str, output: str) -> VirtualCellModelAdapter:
        try:
            return self._by_pair[(task, output)]
        except KeyError as exc:
            raise AdapterContractError(f"unregistered task/output adapter: {(task, output)}") from exc

    def resolve_requested(self, task: str, outputs) -> VirtualCellModelAdapter:
        if not isinstance(outputs, (list, tuple)) or len(outputs) != 1:
            raise AdapterContractError("ambiguous requested outputs require an explicit composite adapter")
        return self.resolve(task, outputs[0])

    def resolve_fingerprint(self, fingerprint: str) -> VirtualCellModelAdapter:
        try:
            return self._by_fingerprint[fingerprint]
        except KeyError as exc:
            raise AdapterContractError("unregistered adapter fingerprint") from exc

    def resolve_identity(self, identity: AdapterIdentity) -> VirtualCellModelAdapter:
        if not isinstance(identity, AdapterIdentity):
            raise TypeError("identity must be AdapterIdentity")
        try:
            adapter = self.resolve_fingerprint(identity.fingerprint())
        except AdapterContractError as exc:
            raise AdapterContractError("adapter identity is not registered") from exc
        if adapter.identity().to_dict() != identity.to_dict():
            raise AdapterContractError("adapter identity does not match runtime contracts")
        return adapter


def _bound_fingerprint(value: Any, *, explicit_key: str | None = None) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict) and explicit_key is not None and explicit_key in value:
        return _strict_fingerprint(value[explicit_key], explicit_key)
    candidate = getattr(value, "fingerprint", None)
    if callable(candidate):
        return _strict_fingerprint(candidate(), "fingerprint")
    if isinstance(candidate, str):
        return _strict_fingerprint(candidate, "fingerprint")
    if isinstance(value, dict):
        return _fingerprint(value)
    raise AdapterContractError("binding has no canonical fingerprint")


def _alignment_binding(
    values_shape: tuple[int, ...] | None,
    feature_contract: ModelFeatureContract | None,
    alignment_report: AlignmentReport | None,
) -> str | None:
    _reject_undeclared_model_fields(feature_contract, "feature contract")
    _reject_undeclared_model_fields(alignment_report, "alignment report")
    if (feature_contract is None) != (alignment_report is None):
        raise AdapterContractError("feature contract and alignment report must be provided together")
    if feature_contract is None:
        return None
    if type(feature_contract) is not ModelFeatureContract:
        raise AdapterContractError("feature contract has the wrong type")
    if type(alignment_report) is not AlignmentReport:
        raise AdapterContractError("alignment report has the wrong type")
    if any(type(step) is not AlignmentStep for step in alignment_report.steps):
        raise AdapterContractError("alignment report step has the wrong type")
    for mapping_asset in (
        feature_contract.mapping_asset,
        alignment_report.mapping_asset,
    ):
        if mapping_asset is not None and type(mapping_asset) is not MappingAssetRef:
            raise AdapterContractError("mapping asset has the wrong type")
    try:
        ModelFeatureContract.model_validate(feature_contract.model_dump(mode="python", serialize_as_any=True))
    except (TypeError, ValidationError, ValueError) as exc:
        raise AdapterContractError("feature contract is invalid") from exc
    fingerprint = feature_contract.fingerprint()
    if alignment_report.contract_fingerprint != fingerprint:
        raise AdapterContractError("alignment contract fingerprint drift")
    if alignment_report.target_feature_ids != feature_contract.feature_ids:
        raise AdapterContractError("alignment feature order differs from the model contract")
    if values_shape is not None and alignment_report.target_shape != values_shape:
        raise AdapterContractError("alignment target shape differs from prepared values shape")
    expected_mapping = (
        None if feature_contract.mapping_asset is None else feature_contract.mapping_asset.model_dump(mode="json")
    )
    observed_mapping = (
        None if alignment_report.mapping_asset is None else alignment_report.mapping_asset.model_dump(mode="json")
    )
    if observed_mapping != expected_mapping:
        raise AdapterContractError("alignment mapping asset hash drift")
    return fingerprint


class DeltaExpressionReferenceAdapter(VirtualCellModelAdapter):
    """Reference adapter for the existing delta-expression wrapper contract."""

    adapter_id = "delta-expression-reference"
    version = "1.0.0"
    input_contract = AdapterInputContract(
        schema_version="vc.adapter-input-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(None, None),
        unit=None,
        pack_data_required=False,
        alignment_required=False,
    )
    output_contract = AdapterOutputContract(
        schema_version="vc.adapter-output-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(None,),
        unit=None,
        uncertainty_required=True,
        ood_required=True,
        abstain_allowed=True,
    )

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        pack=None,
        compatibility_report=None,
        values=None,
        unit=None,
        feature_contract: ModelFeatureContract | None = None,
        alignment_report: AlignmentReport | None = None,
    ) -> PreparedAdapterInput:
        if not isinstance(request, VirtualCellRequestV2):
            raise TypeError("request must be VirtualCellRequestV2")
        try:
            observed_request = request
            _reject_undeclared_model_fields(request, "request")
            request = VirtualCellRequestV2.model_validate(request.model_dump(mode="python", serialize_as_any=True))
            _reject_model_type_drift(observed_request, request, "request")
        except (TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid request") from exc
        outputs = request.task.requested_outputs or (request.output_modality.name,)
        if (
            request.task.task_type != self.input_contract.task
            or tuple(outputs) != (self.input_contract.output,)
            or request.output_modality.name != self.input_contract.output
        ):
            raise AdapterContractError("request task/output does not match the adapter")
        if (
            request.perturbation.dose_value is not None
            or request.perturbation.dose_unit is not None
            or request.perturbation.timepoint is not None
            or request.baseline_context is not None
        ):
            raise AdapterContractError("reference adapter does not silently discard dose, time, or baseline")
        if unit != self.input_contract.unit:
            raise AdapterContractError("prepared input unit does not match the adapter contract")
        normalized_values = None
        shape = None
        if values is not None:
            normalized_values, shape = _tensor(values)
            if not _shape_matches(shape, self.input_contract.shape):
                raise AdapterContractError("prepared values shape does not match the adapter input contract")
        feature_fingerprint = _alignment_binding(shape, feature_contract, alignment_report)
        if self.input_contract.pack_data_required and normalized_values is None:
            raise AdapterContractError("adapter requires explicit Pack data values")
        if self.input_contract.alignment_required and feature_fingerprint is None:
            raise AdapterContractError("adapter requires a feature contract and alignment report")
        request_fingerprint = _fingerprint(request.to_dict())
        pack_fingerprint = _bound_fingerprint(pack, explicit_key="fingerprint")
        compatibility_fingerprint = _bound_fingerprint(compatibility_report)
        model_input = {
            "request_id": request.request_id,
            "targets": tuple(request.perturbation.targets),
            "perturbation_kind": request.perturbation.kind,
            "request_fingerprint": request_fingerprint,
            "pack_fingerprint": pack_fingerprint,
            "compatibility_fingerprint": compatibility_fingerprint,
            "adapter_fingerprint": self.fingerprint(),
            "input_contract_fingerprint": self.input_contract.fingerprint(),
        }
        return PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=request_fingerprint,
            pack_fingerprint=pack_fingerprint,
            compatibility_fingerprint=compatibility_fingerprint,
            model_input=model_input,
            values=normalized_values,
            shape=shape,
            unit=unit,
            feature_contract=feature_contract,
            feature_contract_fingerprint=feature_fingerprint,
            alignment_report=alignment_report,
        )

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        if not isinstance(prepared, PreparedAdapterInput):
            raise TypeError("prepared must be PreparedAdapterInput")
        if prepared.adapter_fingerprint != self.fingerprint():
            raise AdapterContractError("prepared adapter fingerprint drift")
        if prepared.input_contract_fingerprint != self.input_contract.fingerprint():
            raise AdapterContractError("prepared input contract fingerprint drift")
        if (prepared.task, prepared.output) != (
            self.output_contract.task,
            self.output_contract.output,
        ):
            raise AdapterContractError("prepared task/output drift")
        if not isinstance(raw_output, dict):
            raise AdapterContractError("wrapper output must be a JSON object")
        allowed = {
            "prediction",
            "uncertainty",
            "ood",
            "abstain",
            "abstain_reasons",
            "provenance",
            "evidence",
            "policy",
        }
        unknown = set(raw_output).difference(allowed)
        if unknown:
            raise AdapterContractError(f"unknown wrapper output fields: {sorted(unknown)}")
        abstain = raw_output.get("abstain", False)
        if not isinstance(abstain, bool):
            raise AdapterContractError("abstain must be a boolean")
        reasons = raw_output.get("abstain_reasons", [])
        if not isinstance(reasons, (list, tuple)):
            raise AdapterContractError("abstain_reasons must be an array")
        reasons = tuple(_strict_text(item, "abstain_reasons") for item in reasons)

        prediction = raw_output.get("prediction")
        values = None
        shape = None
        metadata: dict[str, Any] = {}
        unit = self.output_contract.unit
        if prediction is not None:
            if not isinstance(prediction, dict):
                raise AdapterContractError("prediction must be an object or null")
            prediction_allowed = {
                "delta",
                "unit",
                "baseline",
                "feature_ids_sha256",
                "n_features",
                "value_type",
                "unseen_train_targets",
            }
            prediction_unknown = set(prediction).difference(prediction_allowed)
            if prediction_unknown:
                raise AdapterContractError(f"unknown prediction fields: {sorted(prediction_unknown)}")
            if prediction.get("unit") != unit and "unit" in prediction:
                raise AdapterContractError("prediction unit does not match the output contract")
            if "delta" not in prediction:
                raise AdapterContractError("prediction is missing delta values")
            values, shape = _tensor(prediction["delta"])
            if not _shape_matches(shape, self.output_contract.shape):
                raise AdapterContractError("prediction shape does not match the output contract")
            metadata = {key: deepcopy(value) for key, value in prediction.items() if key not in {"delta", "unit"}}
            _json_value(metadata, "$.prediction_metadata")

        uncertainty_raw = raw_output.get("uncertainty")
        uncertainty = None
        if uncertainty_raw is not None:
            if not isinstance(uncertainty_raw, dict):
                raise AdapterContractError("uncertainty must be an object")
            uncertainty_allowed = {"available", "method", "calibrated", "value", "sigma", "reason"}
            uncertainty_unknown = set(uncertainty_raw).difference(uncertainty_allowed)
            if uncertainty_unknown:
                raise AdapterContractError(f"unknown uncertainty fields: {sorted(uncertainty_unknown)}")
            try:
                uncertainty = AdapterUncertainty(
                    available=uncertainty_raw.get("available", True),
                    method=uncertainty_raw.get("method"),
                    calibrated=uncertainty_raw.get("calibrated", False),
                    value=uncertainty_raw.get("value"),
                    sigma=uncertainty_raw.get("sigma"),
                    reason=uncertainty_raw.get("reason"),
                )
            except ValidationError as exc:
                raise AdapterContractError(f"invalid uncertainty: {exc}") from exc
        if self.output_contract.uncertainty_required and uncertainty is None:
            raise AdapterContractError("output contract requires uncertainty")

        ood_raw = raw_output.get("ood")
        ood = None
        if ood_raw is not None:
            if not isinstance(ood_raw, dict):
                raise AdapterContractError("ood must be an object")
            ood_unknown = set(ood_raw).difference({"detected", "dimensions", "reason"})
            if ood_unknown:
                raise AdapterContractError(f"unknown ood fields: {sorted(ood_unknown)}")
            try:
                ood = AdapterOOD(
                    detected=ood_raw.get("detected"),
                    dimensions=ood_raw.get("dimensions", []),
                    reason=ood_raw.get("reason"),
                )
            except ValidationError as exc:
                raise AdapterContractError(f"invalid OOD status: {exc}") from exc
        if self.output_contract.ood_required and ood is None:
            raise AdapterContractError("output contract requires OOD status")
        if ood is not None and ood.detected and not abstain:
            raise AdapterContractError("OOD output must abstain")
        if abstain and not self.output_contract.abstain_allowed:
            raise AdapterContractError("output contract does not allow abstention")
        if abstain and values is not None:
            raise AdapterContractError("abstain output must not contain values")
        if not abstain and values is None:
            raise AdapterContractError("non-abstain output requires prediction values")
        if abstain and not reasons:
            raise AdapterContractError("abstain output requires reasons")

        input_fingerprint = prepared.fingerprint()
        provenance = AdapterExecutionProvenance(
            schema_version="vc.adapter-execution-provenance.v1",
            adapter_fingerprint=self.fingerprint(),
            input_fingerprints=(input_fingerprint,),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            output_contract_fingerprint=self.output_contract.fingerprint(),
            request_fingerprints=(prepared.request_fingerprint,),
            pack_fingerprints=(() if prepared.pack_fingerprint is None else (prepared.pack_fingerprint,)),
            compatibility_fingerprints=(
                () if prepared.compatibility_fingerprint is None else (prepared.compatibility_fingerprint,)
            ),
        )
        envelope = AdapterOutputEnvelope(
            schema_version="vc.adapter-output-envelope.v1",
            task=self.output_contract.task,
            output=self.output_contract.output,
            shape=None if abstain else shape,
            unit=unit,
            values=None if abstain else values,
            uncertainty=uncertainty,
            ood=ood,
            abstain=abstain,
            abstain_reasons=reasons,
            projection_metadata={} if abstain else metadata,
            provenance=provenance,
        )
        return self.validate_prepared_envelope(prepared, envelope)

    def aggregate(self, envelopes: tuple[AdapterOutputEnvelope, ...]) -> AdapterOutputEnvelope:
        if not envelopes:
            raise AdapterContractError("cannot aggregate zero adapter outputs")
        rows = []
        normalized = []
        for raw_envelope in envelopes:
            try:
                envelope = self.validate_envelope(raw_envelope)
            except (AdapterContractError, TypeError, ValueError) as exc:
                raise AdapterContractError("adapter outputs are not aggregation-compatible") from exc
            if (
                envelope.provenance.adapter_fingerprint != self.fingerprint()
                or envelope.provenance.input_contract_fingerprint != self.input_contract.fingerprint()
                or envelope.provenance.output_contract_fingerprint != self.output_contract.fingerprint()
                or envelope.task != self.output_contract.task
                or envelope.output != self.output_contract.output
                or envelope.unit != self.output_contract.unit
                or envelope.abstain
                or envelope.values is None
                or envelope.shape is None
            ):
                raise AdapterContractError("adapter outputs are not aggregation-compatible")
            values, actual_shape = _tensor(envelope.values)
            if actual_shape != envelope.shape or not _shape_matches(actual_shape, self.output_contract.shape):
                raise AdapterContractError("adapter output shape does not match its values")
            rows.append(tuple(values))
            normalized.append(envelope)
        envelopes = tuple(normalized)
        shapes = {envelope.shape for envelope in envelopes}
        if len(shapes) != 1:
            raise AdapterContractError("adapter output shapes differ")
        values = tuple(sum(row[index] for row in rows) / len(rows) for index in range(len(rows[0])))
        metadata = envelopes[0].projection_metadata
        if any(envelope.projection_metadata != metadata for envelope in envelopes[1:]):
            metadata = {}
        first = envelopes[0]
        provenance = AdapterExecutionProvenance(
            schema_version="vc.adapter-execution-provenance.v1",
            adapter_fingerprint=self.fingerprint(),
            input_fingerprints=tuple(
                dict.fromkeys(item for envelope in envelopes for item in envelope.provenance.input_fingerprints)
            ),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            output_contract_fingerprint=self.output_contract.fingerprint(),
            request_fingerprints=tuple(
                dict.fromkeys(item for envelope in envelopes for item in envelope.provenance.request_fingerprints)
            ),
            pack_fingerprints=tuple(
                dict.fromkeys(item for envelope in envelopes for item in envelope.provenance.pack_fingerprints)
            ),
            compatibility_fingerprints=tuple(
                dict.fromkeys(item for envelope in envelopes for item in envelope.provenance.compatibility_fingerprints)
            ),
        )
        return AdapterOutputEnvelope(
            schema_version="vc.adapter-output-envelope.v1",
            task=first.task,
            output=first.output,
            shape=first.shape,
            unit=first.unit,
            values=values,
            uncertainty=AdapterUncertainty(
                available=False,
                method="ensemble_mean",
                calibrated=False,
                reason="reference adapter does not infer ensemble uncertainty",
            ),
            ood=AdapterOOD(detected=False, dimensions=(), reason=None),
            abstain=False,
            abstain_reasons=(),
            projection_metadata=metadata,
            provenance=provenance,
        )

    def project_output(self, envelope: AdapterOutputEnvelope) -> dict[str, Any]:
        try:
            envelope = self.validate_envelope(envelope)
        except (AdapterContractError, TypeError, ValueError) as exc:
            raise AdapterContractError("adapter output is not projection-compatible") from exc
        if (
            envelope.provenance.adapter_fingerprint != self.fingerprint()
            or envelope.provenance.input_contract_fingerprint != self.input_contract.fingerprint()
            or envelope.provenance.output_contract_fingerprint != self.output_contract.fingerprint()
            or envelope.task != self.output_contract.task
            or envelope.output != self.output_contract.output
            or envelope.unit != self.output_contract.unit
        ):
            raise AdapterContractError("adapter output is not projection-compatible")
        if envelope.abstain or envelope.values is None or envelope.shape is None:
            raise AdapterContractError("cannot project an abstaining delta output")
        if "delta" in envelope.projection_metadata:
            raise AdapterContractError("projection metadata cannot replace validated delta values")
        values, shape = _tensor(envelope.values)
        if shape != envelope.shape or not _shape_matches(shape, self.output_contract.shape):
            raise AdapterContractError("adapter output shape does not match its values")
        return {
            **deepcopy(envelope.projection_metadata),
            "delta": _canonical_value(values),
        }


def run_adapter_conformance(
    adapter: VirtualCellModelAdapter,
    prepared: PreparedAdapterInput,
    raw_output: dict[str, Any],
) -> AdapterConformanceReport:
    if not isinstance(adapter, VirtualCellModelAdapter):
        raise TypeError("adapter must implement VirtualCellModelAdapter")
    if not isinstance(prepared, PreparedAdapterInput):
        raise TypeError("prepared must be PreparedAdapterInput")
    prepared = adapter.validate_prepared_input(prepared)
    first = adapter.validate_prepared_envelope(
        prepared,
        adapter.adapt_output(prepared, deepcopy(raw_output)),
    )
    second = adapter.validate_prepared_envelope(
        prepared,
        adapter.adapt_output(prepared, deepcopy(raw_output)),
    )
    deterministic = first.to_dict() == second.to_dict() and first.fingerprint() == second.fingerprint()
    if not first.abstain:
        first_projection = adapter.validate_projection(adapter.project_prepared_output(prepared, first))
        second_projection = adapter.validate_projection(adapter.project_prepared_output(prepared, second))
        if first_projection != second_projection:
            deterministic = False
    if not deterministic:
        raise AdapterContractError("adapter output is not deterministic")
    return AdapterConformanceReport(
        schema_version="vc.adapter-conformance-report.v1",
        adapter_fingerprint=adapter.fingerprint(),
        input_fingerprint=prepared.fingerprint(),
        output_fingerprint=first.fingerprint(),
        deterministic=True,
    )


DEFAULT_ADAPTER_REGISTRY = AdapterRegistry([DeltaExpressionReferenceAdapter()])
