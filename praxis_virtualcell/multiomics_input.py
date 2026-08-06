"""Strict, no-fabrication joint multi-omics model-input contracts.

P18 compiles an already validated ``vc.pack.v0.3`` view into a typed,
content-addressed bundle.  It does not create an execution plan, prepare a
wrapper, run a model, normalize values, or fill missing observations.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import (
    TypeAdapter,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, _json_value
from praxis_virtualcell.data_packs.anndata_adapter import _DOSE_UNITS, _TIME_UNITS
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignmentReport,
    ModelFeatureContract,
    _omics_modules,
    align_features,
)
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.mudata_adapter import (
    CanonicalModalityView,
    CanonicalMuDataView,
    _manifest_semantics,
)
from praxis_virtualcell.data_packs.registry import RegisteredPack
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _Contract,
    _fingerprint,
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
    _strict_fingerprint,
    _strict_text,
)
from praxis_virtualcell.model_zoo.registry_v2 import AdapterIdentity

_ALIGNMENT_REPORT = TypeAdapter(AlignmentReport)


class MultiOmicsInputError(ValueError):
    """A joint input contract, view, or identity failed closed."""


def _texts(value: Any, field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        raise ValueError(f"{field} must be a JSON array")
    return tuple(_strict_text(item, field) for item in value)


def _strings(value: Any, field: str, *, allow_empty: bool) -> tuple[str, ...]:
    values = _texts(value, field, allow_empty=allow_empty)
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return values


def _text_rows(
    value: Any,
    field: str,
    *,
    allow_empty_rows: bool,
) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{field} must be a non-empty JSON array")
    return tuple(_texts(item, field, allow_empty=allow_empty_rows) for item in value)


def _quantities(value: Any, field: str) -> tuple[tuple[float, str], ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{field} must be a non-empty JSON array")
    result = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(f"{field} entries must contain value and unit")
        number, unit = item
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            or number < 0
        ):
            raise ValueError(f"{field} values must be finite non-negative numbers")
        result.append((float(number), _strict_text(unit, field)))
    return tuple(result)


def _shape(value: Any, field: str, *, optional: bool) -> tuple[int, int] | None:
    if value is None and optional:
        return None
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value)
    ):
        raise ValueError(f"{field} must contain two positive integers")
    return tuple(value)


def _feature_contract(value: Any) -> ModelFeatureContract:
    observed = value
    if isinstance(value, Mapping):
        raw = dict(value)
    elif type(value) is ModelFeatureContract:
        _reject_undeclared_model_fields(value, "feature_contract")
        raw = value.model_dump(mode="json")
    else:
        raise ValueError("feature_contract must be an exact ModelFeatureContract")
    try:
        normalized = ModelFeatureContract.from_dict(raw)
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    _reject_model_type_drift(observed, normalized, "feature_contract")
    return normalized


def _pack_manifest(value: Any) -> PackManifest:
    observed = value
    if isinstance(value, Mapping):
        raw = dict(value)
        _json_value(raw, "$.pack_manifest")
    elif type(value) is PackManifest:
        _reject_undeclared_model_fields(value, "pack_manifest")
        raw = value.to_dict()
    else:
        raise ValueError("pack_manifest must be an exact PackManifest")
    try:
        normalized = PackManifest.from_dict(raw)
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    _reject_model_type_drift(observed, normalized, "pack_manifest")
    return normalized


def _adapter_identity(value: Any) -> AdapterIdentity:
    observed = value
    if isinstance(value, Mapping):
        raw = dict(value)
        _json_value(raw, "$.adapter_identity")
    elif type(value) is AdapterIdentity:
        _reject_undeclared_model_fields(value, "adapter_identity")
        raw = value.to_dict()
    else:
        raise ValueError("adapter_identity must be an exact AdapterIdentity")
    try:
        normalized = AdapterIdentity.from_dict(raw)
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    _reject_model_type_drift(observed, normalized, "adapter_identity")
    return normalized


def _request(value: Any) -> VirtualCellRequestV2:
    observed = value
    if isinstance(value, Mapping):
        raw = dict(value)
    elif type(value) is VirtualCellRequestV2:
        _reject_undeclared_model_fields(value, "request")
        raw = value.to_dict()
    else:
        raise ValueError("request must be an exact VirtualCellRequestV2")
    try:
        normalized = VirtualCellRequestV2.from_dict(raw)
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    _reject_model_type_drift(observed, normalized, "request")
    return normalized


def _alignment_report(value: Any) -> AlignmentReport | None:
    if value is None:
        return None
    observed = value
    if isinstance(value, AlignmentReport):
        if type(value) is not AlignmentReport:
            raise ValueError("alignment_report must have the canonical dataclass type")
        _reject_undeclared_model_fields(value, "alignment_report")
        raw = value.to_dict()
    elif isinstance(value, Mapping):
        raw = dict(value)
        _json_value(raw, "$.alignment_report")
    else:
        raise ValueError("alignment_report must be an AlignmentReport or JSON object")
    try:
        normalized = _ALIGNMENT_REPORT.validate_python(raw)
    except ValidationError as exc:
        raise ValueError(f"invalid alignment_report: {exc}") from exc
    if _fingerprint(raw) != _fingerprint(normalized.to_dict()):
        raise ValueError("alignment_report must be exact canonical JSON")
    if isinstance(observed, AlignmentReport):
        _reject_model_type_drift(observed, normalized, "alignment_report")
    return normalized


class _P18Contract(_Contract):
    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise MultiOmicsInputError(f"{cls.__name__} must be a JSON object")
        try:
            _json_value(value)
            return cls.model_validate(value)
        except (ValidationError, ValueError, TypeError) as exc:
            raise MultiOmicsInputError(f"invalid {cls.__name__}: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        if type(self) not in _P18_CANONICAL_TYPES:
            raise MultiOmicsInputError("P18 contract must have an exact canonical type")
        raw = _Contract.to_dict(self)
        try:
            normalized = type(self).model_validate(raw)
        except (ValidationError, ValueError, TypeError) as exc:
            raise MultiOmicsInputError(f"invalid constructed {type(self).__name__}: {exc}") from exc
        canonical = _Contract.to_dict(normalized)
        try:
            _reject_model_type_drift(self, normalized, type(self).__name__)
        except (ValueError, TypeError) as exc:
            raise MultiOmicsInputError(f"invalid constructed {type(self).__name__}: {exc}") from exc
        if _fingerprint(raw) != _fingerprint(canonical):
            raise MultiOmicsInputError("P18 contract is not canonically serializable")
        return canonical


class MultiOmicsModalitySlotV1(_P18Contract):
    schema_version: Literal["vc.multiomics-modality-slot.v1"]
    key: str
    required: bool
    modality_name: str
    modality_ontology_id: str
    representation: Literal["matrix:X"]
    feature_contract: ModelFeatureContract
    feature_contract_fingerprint: str

    @field_validator("key", "modality_name", "modality_ontology_id", mode="before")
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("required", mode="before")
    @classmethod
    def _required(cls, value):
        if not isinstance(value, bool):
            raise ValueError("required must be a boolean")
        return value

    @field_validator("feature_contract", mode="before")
    @classmethod
    def _contract(cls, value):
        return _feature_contract(value)

    @field_validator("feature_contract_fingerprint", mode="before")
    @classmethod
    def _contract_fingerprint(cls, value):
        return _strict_fingerprint(value, "feature_contract_fingerprint")

    @model_validator(mode="after")
    def _bound_feature_contract(self):
        if self.feature_contract_fingerprint != self.feature_contract.fingerprint():
            raise ValueError("feature_contract_fingerprint mismatch")
        if self.feature_contract.modality != self.key:
            raise ValueError("feature contract modality must equal the slot key")
        if self.feature_contract.fill:
            raise ValueError("P18 forbids feature fill and imputation")
        return self


def _slot(value: Any) -> MultiOmicsModalitySlotV1:
    if isinstance(value, Mapping):
        return MultiOmicsModalitySlotV1.from_dict(dict(value))
    if type(value) is not MultiOmicsModalitySlotV1:
        raise ValueError("slot must have the canonical MultiOmicsModalitySlotV1 type")
    _reject_undeclared_model_fields(value, "slot")
    normalized = MultiOmicsModalitySlotV1.from_dict(value.to_dict())
    _reject_model_type_drift(value, normalized, "slot")
    return normalized


class MultiOmicsInputContractV1(_P18Contract):
    schema_version: Literal["vc.multiomics-input-contract.v1"]
    model_name: str
    model_version: str
    model_fingerprint: str
    taxonomy_id: str
    assembly_accession: str
    task: str
    outputs: tuple[str, ...]
    target_modality_key: str
    join_policy: Literal["required_inner", "global"]
    missingness_policy: Literal["reject", "explicit_mask"]
    normalization: Literal["none"]
    slots: tuple[MultiOmicsModalitySlotV1, ...]

    @field_validator(
        "model_name",
        "model_version",
        "taxonomy_id",
        "assembly_accession",
        "task",
        "target_modality_key",
        mode="before",
    )
    @classmethod
    def _text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("model_fingerprint", mode="before")
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("outputs", mode="before")
    @classmethod
    def _outputs(cls, value):
        return _strings(value, "outputs", allow_empty=False)

    @field_validator("slots", mode="before")
    @classmethod
    def _slots(cls, value):
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            raise ValueError("slots must contain at least two ordered modalities")
        return tuple(_slot(item) for item in value)

    @model_validator(mode="after")
    def _joint_contract(self):
        keys = tuple(slot.key for slot in self.slots)
        modality_identities = tuple((slot.modality_name, slot.modality_ontology_id) for slot in self.slots)
        if len(set(keys)) != len(keys):
            raise ValueError("slot keys must be unique")
        if len(set(modality_identities)) != len(modality_identities):
            raise ValueError("slot modality identities must be unique")
        target = next(
            (slot for slot in self.slots if slot.key == self.target_modality_key),
            None,
        )
        if target is None or not target.required:
            raise ValueError("target modality must be an explicitly required slot")
        if (self.join_policy, self.missingness_policy) not in {
            ("required_inner", "reject"),
            ("global", "explicit_mask"),
        }:
            raise ValueError("join and missingness policy combination is not supported")
        for slot in self.slots:
            feature = slot.feature_contract
            if feature.model_id != self.model_name or feature.model_version != self.model_version:
                raise ValueError("slot feature contract model identity mismatch")
            if feature.taxonomy_id != self.taxonomy_id:
                raise ValueError("slot feature contract taxonomy mismatch")
            if feature.assembly_accession != self.assembly_accession:
                raise ValueError("slot feature contract assembly mismatch")
        return self


def _input_contract(value: Any) -> MultiOmicsInputContractV1:
    if isinstance(value, Mapping):
        return MultiOmicsInputContractV1.from_dict(dict(value))
    if type(value) is not MultiOmicsInputContractV1:
        raise ValueError("input_contract must have the canonical type")
    _reject_undeclared_model_fields(value, "input_contract")
    normalized = MultiOmicsInputContractV1.from_dict(value.to_dict())
    _reject_model_type_drift(value, normalized, "input_contract")
    return normalized


def _validate_alignment_steps(
    report: AlignmentReport,
    feature: ModelFeatureContract,
) -> None:
    order = {"alias": 0, "aggregate": 1, "drop": 2, "reorder": 3}
    previous = -1
    mapped_sources: list[str] = []
    mapped_targets: list[str] = []
    mapped_operations: dict[str, tuple[str, str]] = {}
    drop_steps = []
    reorder_steps = []
    source_features = set(report.source_feature_ids)
    target_features = set(report.target_feature_ids)
    for step in report.steps:
        if step.operation == "fill":
            raise ValueError("P18 alignment report must not contain fill")
        position = order[step.operation]
        if position < previous:
            raise ValueError("alignment steps are not in canonical operation order")
        previous = position
        if step.operation == "alias":
            if (
                len(step.source_ids) != 1
                or len(step.target_ids) != 1
                or step.reducer is not None
                or step.value is not None
            ):
                raise ValueError("alias alignment step is not canonical")
            mapped_sources.extend(step.source_ids)
            mapped_targets.extend(step.target_ids)
            mapped_operations[step.source_ids[0]] = (
                "alias",
                step.target_ids[0],
            )
        elif step.operation == "aggregate":
            if (
                len(step.source_ids) < 2
                or len(step.target_ids) != 1
                or step.reducer not in {"sum", "mean"}
                or step.value is not None
            ):
                raise ValueError("aggregate alignment step is not canonical")
            mapped_sources.extend(step.source_ids)
            mapped_targets.extend(step.target_ids)
            for source in step.source_ids:
                mapped_operations[source] = (
                    "aggregate",
                    step.target_ids[0],
                )
        elif step.operation == "drop":
            if not step.source_ids or step.target_ids or step.reducer is not None or step.value is not None:
                raise ValueError("drop alignment step is not canonical")
            drop_steps.append(step)
        elif step.operation == "reorder":
            if not step.source_ids or not step.target_ids or step.reducer is not None or step.value is not None:
                raise ValueError("reorder alignment step is not canonical")
            reorder_steps.append(step)

    if report.mapping_asset != feature.mapping_asset:
        raise ValueError("alignment report mapping asset differs from feature contract")
    if feature.mapping_asset is None and (mapped_sources or mapped_targets):
        raise ValueError("mapping steps require an explicit mapping asset")
    if feature.mapping_asset is not None and not mapped_sources:
        raise ValueError("mapping asset requires explicit mapping steps")
    if len(set(mapped_sources)) != len(mapped_sources):
        raise ValueError("mapping source features must be unique")
    if len(set(mapped_targets)) != len(mapped_targets):
        raise ValueError("mapping target features must be unique")
    if not set(mapped_sources).issubset(source_features):
        raise ValueError("mapping steps contain unknown source features")
    if not set(mapped_targets).issubset(target_features):
        raise ValueError("mapping steps contain unknown target features")
    if not set(feature.drop).issubset(source_features):
        raise ValueError("drop step contains unknown source features")
    if set(feature.drop).intersection(mapped_sources):
        raise ValueError("drop and mapping steps overlap")
    if feature.drop:
        if len(drop_steps) != 1 or drop_steps[0].source_ids != feature.drop:
            raise ValueError("drop step differs from feature contract")
    elif drop_steps:
        raise ValueError("drop step is not declared by the feature contract")
    if len(reorder_steps) > 1 or (reorder_steps and not feature.reorder):
        raise ValueError("reorder step is not declared by the feature contract")
    if reorder_steps:
        step = reorder_steps[0]
        if (
            step.target_ids != report.target_feature_ids
            or len(set(step.source_ids)) != len(step.source_ids)
            or set(step.source_ids) != target_features
        ):
            raise ValueError("reorder step does not prove an exact feature permutation")

    produced = []
    completed_aggregates = set()
    dropped = set(feature.drop)
    for source in report.source_feature_ids:
        if source in dropped:
            continue
        operation = mapped_operations.get(source)
        if operation is None:
            produced.append(source)
        elif operation[0] == "alias":
            produced.append(operation[1])
        elif operation[1] not in completed_aggregates:
            produced.append(operation[1])
            completed_aggregates.add(operation[1])
    if reorder_steps:
        if reorder_steps[0].source_ids != tuple(produced):
            raise ValueError("reorder source identity differs from preceding alignment")
        produced = list(reorder_steps[0].target_ids)
    if tuple(produced) != report.target_feature_ids:
        raise ValueError("alignment steps do not derive the target feature identity")


def _checked_matrix(matrix: Any):
    np, sparse = _omics_modules()
    if sparse.issparse(matrix):
        if matrix.format not in {"csr", "csc"}:
            raise MultiOmicsInputError("runtime matrix must be dense, CSR, or CSC")
        if not matrix.has_canonical_format:
            raise MultiOmicsInputError("sparse runtime matrix must have sorted, duplicate-free indices")
        value = matrix
        data = matrix.data
    else:
        value = np.asarray(matrix)
        data = value
    if value.ndim != 2 or any(dimension <= 0 for dimension in value.shape):
        raise MultiOmicsInputError("runtime matrix must be a non-empty two-dimensional tensor")
    if value.dtype.kind not in "biufc":
        raise MultiOmicsInputError("runtime matrix dtype must be deterministic numeric data")
    if not np.isfinite(data).all():
        raise MultiOmicsInputError("runtime matrix must not contain non-finite values")
    return value


@dataclass(frozen=True)
class _MatrixSnapshot:
    storage: Literal["dense", "csr", "csc"]
    shape: tuple[int, int]
    data_dtype: str
    data: bytes
    indices_dtype: str | None = None
    indices: bytes | None = None
    indptr_dtype: str | None = None
    indptr: bytes | None = None

    @classmethod
    def from_matrix(cls, matrix: Any):
        np, sparse = _omics_modules()
        matrix = _checked_matrix(matrix)
        if not sparse.issparse(matrix):
            values = np.ascontiguousarray(matrix)
            return cls(
                storage="dense",
                shape=tuple(values.shape),
                data_dtype=values.dtype.str,
                data=values.tobytes(order="C"),
            )
        data = np.ascontiguousarray(matrix.data)
        indices = np.ascontiguousarray(matrix.indices)
        indptr = np.ascontiguousarray(matrix.indptr)
        return cls(
            storage=matrix.format,
            shape=tuple(matrix.shape),
            data_dtype=data.dtype.str,
            data=data.tobytes(order="C"),
            indices_dtype=indices.dtype.str,
            indices=indices.tobytes(order="C"),
            indptr_dtype=indptr.dtype.str,
            indptr=indptr.tobytes(order="C"),
        )

    def materialize(self):
        np, sparse = _omics_modules()
        data = np.frombuffer(self.data, dtype=np.dtype(self.data_dtype))
        if self.storage == "dense":
            return data.reshape(self.shape)
        indices = np.frombuffer(
            self.indices,
            dtype=np.dtype(self.indices_dtype),
        )
        indptr = np.frombuffer(
            self.indptr,
            dtype=np.dtype(self.indptr_dtype),
        )
        matrix_type = sparse.csr_matrix if self.storage == "csr" else sparse.csc_matrix
        matrix = matrix_type((data, indices, indptr), shape=self.shape, copy=False)
        matrix.data = data
        matrix.indices = indices
        matrix.indptr = indptr
        return matrix


def _hash_array(digest, value, *, dtype=None) -> None:
    np, _ = _omics_modules()
    canonical = np.ascontiguousarray(
        value,
        dtype=dtype or value.dtype.newbyteorder("<"),
    )
    payload = memoryview(canonical).cast("B")
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def _matrix_fingerprint(matrix: Any) -> str:
    np, sparse = _omics_modules()
    matrix = _checked_matrix(matrix)
    storage = matrix.format if sparse.issparse(matrix) else "dense"
    metadata = {
        "schema_version": "vc.multiomics-matrix.v1",
        "storage": storage,
        "dtype": matrix.dtype.newbyteorder("<").str,
        "shape": list(matrix.shape),
    }
    digest = hashlib.sha256()
    digest.update(b"vc.multiomics-matrix.v1\0")
    digest.update(bytes.fromhex(_fingerprint(metadata)))
    if sparse.issparse(matrix):
        _hash_array(digest, matrix.data)
        _hash_array(digest, matrix.indices, dtype=np.dtype("<i8"))
        _hash_array(digest, matrix.indptr, dtype=np.dtype("<i8"))
    else:
        _hash_array(digest, matrix)
    return digest.hexdigest()


class MultiOmicsLayerInputV1(_P18Contract):
    schema_version: Literal["vc.multiomics-layer-input.v1"]
    slot: MultiOmicsModalitySlotV1
    present: bool
    source_observation_ids: tuple[str, ...]
    input_observation_ids: tuple[str, ...]
    observation_mask: tuple[bool, ...]
    alignment_report: AlignmentReport | None
    alignment_report_fingerprint: str | None
    matrix_fingerprint: str | None
    source_matrix_format: Literal["dense", "csr", "csc"] | None
    source_shape: tuple[int, int] | None
    aligned_shape: tuple[int, int] | None
    input_shape: tuple[int, int] | None

    @field_validator("slot", mode="before")
    @classmethod
    def _slot(cls, value):
        return _slot(value)

    @field_validator("present", mode="before")
    @classmethod
    def _present(cls, value):
        if not isinstance(value, bool):
            raise ValueError("present must be a boolean")
        return value

    @field_validator("source_observation_ids", "input_observation_ids", mode="before")
    @classmethod
    def _observations(cls, value, info):
        return _strings(value, info.field_name, allow_empty=True)

    @field_validator("observation_mask", mode="before")
    @classmethod
    def _mask(cls, value):
        if not isinstance(value, (list, tuple)) or any(not isinstance(item, bool) for item in value):
            raise ValueError("observation_mask must be a boolean array")
        return tuple(value)

    @field_validator("alignment_report", mode="before")
    @classmethod
    def _report(cls, value):
        return _alignment_report(value)

    @field_serializer("alignment_report")
    def _serialize_report(self, value: AlignmentReport | None):
        return None if value is None else value.to_dict()

    @field_validator(
        "alignment_report_fingerprint",
        "matrix_fingerprint",
        mode="before",
    )
    @classmethod
    def _optional_fingerprint(cls, value, info):
        return None if value is None else _strict_fingerprint(value, info.field_name)

    @field_validator("source_shape", "aligned_shape", "input_shape", mode="before")
    @classmethod
    def _shapes(cls, value, info):
        return _shape(value, info.field_name, optional=True)

    @model_validator(mode="after")
    def _layer_binding(self):
        report = self.alignment_report
        shapes = (self.source_shape, self.aligned_shape, self.input_shape)
        if not self.present:
            if (
                self.source_observation_ids
                or self.input_observation_ids
                or report is not None
                or self.alignment_report_fingerprint is not None
                or self.matrix_fingerprint is not None
                or self.source_matrix_format is not None
                or any(value is not None for value in shapes)
            ):
                raise ValueError("absent optional layer must not contain observations or data identity")
            return self
        if self.slot.required is False and not self.source_observation_ids:
            raise ValueError("present optional layer requires real observations")
        if not self.source_observation_ids or not self.input_observation_ids:
            raise ValueError("present layer requires real source and input observations")
        if (
            report is None
            or self.alignment_report_fingerprint is None
            or self.matrix_fingerprint is None
            or self.source_matrix_format is None
        ):
            raise ValueError("present layer requires an independent alignment report")
        if any(value is None for value in shapes):
            raise ValueError("present layer requires source/aligned/input shapes")
        if self.alignment_report_fingerprint != _fingerprint(report.to_dict()):
            raise ValueError("alignment_report_fingerprint mismatch")
        if report.schema_version != "vc.alignment-report.v1":
            raise ValueError("unsupported alignment report schema")
        if report.contract_fingerprint != self.slot.feature_contract_fingerprint:
            raise ValueError("alignment report feature contract mismatch")
        if report.target_feature_ids != self.slot.feature_contract.feature_ids:
            raise ValueError("alignment report target features mismatch")
        _validate_alignment_steps(report, self.slot.feature_contract)
        if tuple(report.source_shape) != self.source_shape:
            raise ValueError("alignment report source shape mismatch")
        if tuple(report.target_shape) != self.aligned_shape:
            raise ValueError("alignment report target shape mismatch")
        if self.source_shape[0] != len(self.source_observation_ids):
            raise ValueError("source observations do not match source matrix rows")
        if self.input_shape[0] != len(self.input_observation_ids):
            raise ValueError("input observations do not match input matrix rows")
        if self.aligned_shape[0] != self.source_shape[0]:
            raise ValueError("feature alignment must not change observation rows")
        try:
            source_features = _strings(
                report.source_feature_ids,
                "alignment source features",
                allow_empty=False,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        target_width = len(report.target_feature_ids)
        if self.source_shape[1] != len(source_features):
            raise ValueError("source feature identities do not match source width")
        if self.aligned_shape[1] != target_width:
            raise ValueError("target feature identities do not match aligned width")
        if self.input_shape[1] != target_width:
            raise ValueError("input feature width differs from aligned feature width")
        return self


def _layer(value: Any) -> MultiOmicsLayerInputV1:
    if isinstance(value, Mapping):
        return MultiOmicsLayerInputV1.from_dict(dict(value))
    if type(value) is not MultiOmicsLayerInputV1:
        raise ValueError("layer must have the canonical MultiOmicsLayerInputV1 type")
    _reject_undeclared_model_fields(value, "layer")
    normalized = MultiOmicsLayerInputV1.from_dict(value.to_dict())
    _reject_model_type_drift(value, normalized, "layer")
    return normalized


def _join_fingerprint(
    policy: str,
    global_ids: tuple[str, ...],
    joined_ids: tuple[str, ...],
    layers: tuple[MultiOmicsLayerInputV1, ...],
) -> str:
    return _fingerprint(
        {
            "schema_version": "vc.multiomics-observation-join.v1",
            "policy": policy,
            "global_observation_ids": list(global_ids),
            "joined_observation_ids": list(joined_ids),
            "layers": [
                {
                    "key": layer.slot.key,
                    "present": layer.present,
                    "source_observation_ids": list(layer.source_observation_ids),
                    "input_observation_ids": list(layer.input_observation_ids),
                }
                for layer in layers
            ],
        }
    )


def _missingness_fingerprint(
    policy: str,
    join_fingerprint: str,
    layers: tuple[MultiOmicsLayerInputV1, ...],
) -> str:
    return _fingerprint(
        {
            "schema_version": "vc.multiomics-missingness.v1",
            "policy": policy,
            "join_fingerprint": join_fingerprint,
            "layers": [
                {
                    "key": layer.slot.key,
                    "present": layer.present,
                    "observation_mask": list(layer.observation_mask),
                }
                for layer in layers
            ],
        }
    )


class MultiOmicsObservationSemanticsV1(_P18Contract):
    schema_version: Literal["vc.multiomics-observation-semantics.v1"]
    conditions: tuple[str, ...]
    splits: tuple[str, ...]
    cell_identity_ids: tuple[str, ...]
    cell_state_ids: tuple[tuple[str, ...], ...]
    cell_context_ids: tuple[tuple[str, ...], ...]
    perturbation_ids: tuple[str, ...]
    perturbation_kinds: tuple[str, ...]
    perturbation_targets: tuple[tuple[str, ...], ...]
    matched_control_ids: tuple[str, ...]
    doses: tuple[tuple[float, str], ...]
    times: tuple[tuple[float, str], ...]
    split_name: str

    @field_validator(
        "conditions",
        "splits",
        "cell_identity_ids",
        "perturbation_ids",
        "perturbation_kinds",
        "matched_control_ids",
        mode="before",
    )
    @classmethod
    def _flat_text(cls, value, info):
        return _texts(value, info.field_name, allow_empty=False)

    @field_validator("cell_state_ids", "cell_context_ids", mode="before")
    @classmethod
    def _cell_semantics(cls, value, info):
        return _text_rows(value, info.field_name, allow_empty_rows=False)

    @field_validator("perturbation_targets", mode="before")
    @classmethod
    def _targets(cls, value):
        return _text_rows(
            value,
            "perturbation_targets",
            allow_empty_rows=True,
        )

    @field_validator("doses", "times", mode="before")
    @classmethod
    def _quantity(cls, value, info):
        return _quantities(value, info.field_name)

    @field_validator("split_name", mode="before")
    @classmethod
    def _split_name(cls, value):
        return _strict_text(value, "split_name")

    @model_validator(mode="after")
    def _same_observation_cardinality(self):
        lengths = {
            len(getattr(self, field))
            for field in (
                "conditions",
                "splits",
                "cell_identity_ids",
                "cell_state_ids",
                "cell_context_ids",
                "perturbation_ids",
                "perturbation_kinds",
                "perturbation_targets",
                "matched_control_ids",
                "doses",
                "times",
            )
        }
        if len(lengths) != 1:
            raise ValueError("observation semantic columns must have equal lengths")
        return self


def _observation_semantics(value: Any) -> MultiOmicsObservationSemanticsV1:
    if isinstance(value, Mapping):
        return MultiOmicsObservationSemanticsV1.from_dict(dict(value))
    if type(value) is not MultiOmicsObservationSemanticsV1:
        raise ValueError("observation_semantics must have the canonical type")
    _reject_undeclared_model_fields(value, "observation_semantics")
    normalized = MultiOmicsObservationSemanticsV1.from_dict(value.to_dict())
    _reject_model_type_drift(value, normalized, "observation_semantics")
    return normalized


def _view_semantics(view: CanonicalMuDataView) -> MultiOmicsObservationSemanticsV1:
    try:
        return MultiOmicsObservationSemanticsV1(
            schema_version="vc.multiomics-observation-semantics.v1",
            conditions=view.conditions,
            splits=view.splits,
            cell_identity_ids=view.cell_identity_ids,
            cell_state_ids=view.cell_state_ids,
            cell_context_ids=view.cell_context_ids,
            perturbation_ids=view.perturbation_ids,
            perturbation_kinds=view.perturbation_kinds,
            perturbation_targets=view.perturbation_targets,
            matched_control_ids=view.matched_control_ids,
            doses=view.doses,
            times=view.times,
            split_name=view.split_name,
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise MultiOmicsInputError("view observation semantics are invalid") from exc


def _validate_view_semantics(
    semantics: MultiOmicsObservationSemanticsV1,
    manifest: PackManifest,
) -> None:
    if semantics.split_name != manifest.split.name or not set(semantics.splits).issubset(manifest.split.values):
        raise MultiOmicsInputError("view split identity differs from its Pack")
    conditions = manifest.conditions
    if not set(semantics.conditions).issubset(conditions.values) or not set(semantics.matched_control_ids).issubset(
        conditions.values
    ):
        raise MultiOmicsInputError("view contains undeclared condition identities")
    perturbation_by_id = {item.id: item for item in manifest.perturbations.values}
    for perturbation_id, kind, targets in zip(
        semantics.perturbation_ids,
        semantics.perturbation_kinds,
        semantics.perturbation_targets,
        strict=True,
    ):
        declared = perturbation_by_id.get(perturbation_id)
        if declared is None or (declared.kind, declared.targets) != (kind, targets):
            raise MultiOmicsInputError("view perturbation semantics differ from its Pack")
    if any(unit not in _DOSE_UNITS for _, unit in semantics.doses):
        raise MultiOmicsInputError("view contains unsupported dose units")
    if any(unit not in _TIME_UNITS for _, unit in semantics.times):
        raise MultiOmicsInputError("view contains unsupported time units")

    condition_rows: dict[str, int] = {}
    condition_signatures: dict[str, tuple[Any, ...]] = {}
    for index, condition_id in enumerate(semantics.conditions):
        signature = (
            semantics.perturbation_ids[index],
            semantics.matched_control_ids[index],
            semantics.cell_identity_ids[index],
            semantics.cell_state_ids[index],
            semantics.cell_context_ids[index],
            semantics.doses[index],
            semantics.times[index],
            semantics.splits[index],
        )
        previous = condition_signatures.setdefault(condition_id, signature)
        if previous != signature:
            raise MultiOmicsInputError("view condition has inconsistent semantic definitions")
        condition_rows.setdefault(condition_id, index)

    for condition_id, index in condition_rows.items():
        control_id = semantics.matched_control_ids[index]
        perturbation = perturbation_by_id[semantics.perturbation_ids[index]]
        if perturbation.kind == "control":
            if control_id != condition_id:
                raise MultiOmicsInputError("control conditions must match themselves")
            continue
        control_index = condition_rows.get(control_id)
        if control_index is None:
            continue
        control_perturbation = perturbation_by_id[semantics.perturbation_ids[control_index]]
        if control_perturbation.kind != "control":
            raise MultiOmicsInputError("matched condition does not use a control perturbation")
        control_context = (
            semantics.cell_identity_ids[control_index],
            semantics.cell_state_ids[control_index],
            semantics.cell_context_ids[control_index],
            semantics.times[control_index],
            semantics.splits[control_index],
        )
        condition_context = (
            semantics.cell_identity_ids[index],
            semantics.cell_state_ids[index],
            semantics.cell_context_ids[index],
            semantics.times[index],
            semantics.splits[index],
        )
        if control_context != condition_context:
            raise MultiOmicsInputError("condition does not match its control context")

    if "target_ids" in manifest.split.leakage_guard:
        partition_by_target: dict[str, str] = {}
        for targets, partition in zip(
            semantics.perturbation_targets,
            semantics.splits,
            strict=True,
        ):
            for target in targets:
                previous = partition_by_target.setdefault(target, partition)
                if previous != partition:
                    raise MultiOmicsInputError("view contains target split leakage")


def _view_identity_fingerprint(
    pack_fingerprint: str,
    global_ids: tuple[str, ...],
    layers: tuple[MultiOmicsLayerInputV1, ...],
    semantics_fingerprint: str,
) -> str:
    return _fingerprint(
        {
            "schema_version": "vc.multiomics-view-identity.v1",
            "pack_fingerprint": pack_fingerprint,
            "observation_semantics_fingerprint": semantics_fingerprint,
            "global_observation_ids": list(global_ids),
            "modalities": [
                {
                    "key": layer.slot.key,
                    "present": layer.present,
                    "modality_name": layer.slot.modality_name,
                    "modality_ontology_id": layer.slot.modality_ontology_id,
                    "feature_namespace": layer.slot.feature_contract.feature_namespace.model_dump(mode="json"),
                    "feature_id_format": layer.slot.feature_contract.feature_id_format,
                    "source_observation_ids": list(layer.source_observation_ids),
                    "source_feature_ids": (
                        [] if layer.alignment_report is None else list(layer.alignment_report.source_feature_ids)
                    ),
                    "source_shape": (None if layer.source_shape is None else list(layer.source_shape)),
                    "source_matrix_format": layer.source_matrix_format,
                }
                for layer in layers
            ],
        }
    )


class MultiOmicsModelInputV1(_P18Contract):
    schema_version: Literal["vc.multiomics-model-input.v1"]
    request: VirtualCellRequestV2
    request_fingerprint: str
    pack_manifest: PackManifest
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    observation_semantics: MultiOmicsObservationSemanticsV1
    observation_semantics_fingerprint: str
    view_identity_fingerprint: str
    input_contract: MultiOmicsInputContractV1
    input_contract_fingerprint: str
    adapter_identity: AdapterIdentity
    adapter_fingerprint: str
    broker_agent: Literal["ModelBrokerAgent"]
    broker_resolution: Literal["identity_only_not_registry_evaluated"]
    global_observation_ids: tuple[str, ...]
    joined_observation_ids: tuple[str, ...]
    join_fingerprint: str
    missingness_fingerprint: str
    layers: tuple[MultiOmicsLayerInputV1, ...]
    executable: Literal[False]
    execution_performed: Literal[False]
    execution_step_created: Literal[False]
    abstain: Literal[True]
    abstain_reason: Literal["contract_only_execution_not_authorized"]

    @field_validator("request", mode="before")
    @classmethod
    def _request(cls, value):
        return _request(value)

    @field_validator("request_fingerprint", mode="before")
    @classmethod
    def _request_fingerprint(cls, value):
        return _strict_fingerprint(value, "request_fingerprint")

    @field_validator("pack_manifest", mode="before")
    @classmethod
    def _manifest(cls, value):
        return _pack_manifest(value)

    @field_serializer("pack_manifest")
    def _serialize_manifest(self, value: PackManifest):
        return value.to_dict()

    @field_validator("pack_id", "pack_version", mode="before")
    @classmethod
    def _pack_text(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator(
        "pack_fingerprint",
        "observation_semantics_fingerprint",
        "view_identity_fingerprint",
        "input_contract_fingerprint",
        "adapter_fingerprint",
        "join_fingerprint",
        "missingness_fingerprint",
        mode="before",
    )
    @classmethod
    def _identity_fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("observation_semantics", mode="before")
    @classmethod
    def _semantics(cls, value):
        return _observation_semantics(value)

    @field_validator("input_contract", mode="before")
    @classmethod
    def _contract(cls, value):
        return _input_contract(value)

    @field_validator("adapter_identity", mode="before")
    @classmethod
    def _adapter(cls, value):
        return _adapter_identity(value)

    @field_serializer("adapter_identity")
    def _serialize_adapter(self, value: AdapterIdentity):
        return value.to_dict()

    @field_validator("global_observation_ids", "joined_observation_ids", mode="before")
    @classmethod
    def _observation_ids(cls, value, info):
        return _strings(value, info.field_name, allow_empty=False)

    @field_validator("layers", mode="before")
    @classmethod
    def _layers(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("layers must be a non-empty ordered array")
        return tuple(_layer(item) for item in value)

    @model_validator(mode="after")
    def _self_bound(self):
        contract = self.input_contract
        manifest = self.pack_manifest
        if self.request_fingerprint != _fingerprint(self.request.to_dict()):
            raise ValueError("request_fingerprint mismatch")
        if (
            manifest.schema_version != "vc.pack.v0.3"
            or manifest.multiomics is None
            or self.pack_id != manifest.pack_id
            or self.pack_version != manifest.pack_version
            or self.pack_fingerprint != manifest.fingerprint()
        ):
            raise ValueError("Pack identity differs from its embedded manifest")
        if self.input_contract_fingerprint != contract.fingerprint():
            raise ValueError("input_contract_fingerprint mismatch")
        if self.observation_semantics_fingerprint != self.observation_semantics.fingerprint() or len(
            self.observation_semantics.conditions
        ) != len(self.global_observation_ids):
            raise ValueError("observation semantics identity mismatch")
        _validate_view_semantics(self.observation_semantics, manifest)
        adapter = self.adapter_identity
        _validate_adapter(adapter, contract)
        if self.adapter_fingerprint != adapter.fingerprint():
            raise ValueError("adapter identity does not own the joint input contract")
        if (
            contract.taxonomy_id != manifest.taxon.ontology_id
            or contract.assembly_accession != manifest.assembly.accession
            or manifest.perturbations.target_modality != contract.target_modality_key
        ):
            raise ValueError("input contract biological scope differs from Pack")
        _validate_request(self.request, manifest, contract)
        if tuple(layer.slot for layer in self.layers) != contract.slots:
            raise ValueError("layer order or slot identity differs from input contract")
        if len(self.layers) != len(contract.slots):
            raise ValueError("every contract slot requires one typed layer")
        present = tuple(layer for layer in self.layers if layer.present)
        if len(present) < 2:
            raise ValueError("joint model input requires at least two present modalities")
        if any(slot.required and not layer.present for slot, layer in zip(contract.slots, self.layers, strict=True)):
            raise ValueError("required modality is absent")
        target = next(layer for layer in self.layers if layer.slot.key == contract.target_modality_key)
        if not target.present:
            raise ValueError("target modality is absent")
        _validate_request_target_alignment(self.request, target)

        manifest_slots = {item.key: item for item in manifest.multiomics.modalities}
        for layer in present:
            spec = manifest_slots.get(layer.slot.key)
            feature = layer.slot.feature_contract
            if spec is None or (
                spec.modality.name != layer.slot.modality_name
                or spec.modality.ontology_id != layer.slot.modality_ontology_id
                or spec.feature_namespace.name != feature.feature_namespace.name
                or spec.feature_namespace.version != feature.feature_namespace.version
                or spec.feature_semantics.id_format != feature.feature_id_format
                or spec.shape[1] != layer.source_shape[1]
            ):
                raise ValueError("present layer identity differs from Pack modality")
            mapping = feature.mapping_asset
            if mapping is not None:
                asset = next(
                    (item for item in manifest.assets if item.id == mapping.asset_id),
                    None,
                )
                if asset is None or (
                    asset.path != mapping.path
                    or asset.sha256 != mapping.sha256
                    or asset.media_type != "application/json"
                ):
                    raise ValueError("feature mapping identity differs from a Pack JSON asset")

        expected_view_identity = _view_identity_fingerprint(
            self.pack_fingerprint,
            self.global_observation_ids,
            self.layers,
            self.observation_semantics_fingerprint,
        )
        if self.view_identity_fingerprint != expected_view_identity:
            raise ValueError("view_identity_fingerprint mismatch")

        global_set = set(self.global_observation_ids)
        for layer in self.layers:
            source_set = set(layer.source_observation_ids)
            if not source_set.issubset(global_set):
                raise ValueError("layer contains observations outside the global view")
            expected_order = tuple(value for value in self.global_observation_ids if value in source_set)
            if expected_order != layer.source_observation_ids:
                raise ValueError("layer observation order is ambiguous")
            if len(layer.observation_mask) != len(self.joined_observation_ids):
                raise ValueError("observation mask length differs from joined observations")

        memberships = [set(layer.source_observation_ids) for layer in present]
        if contract.join_policy == "required_inner":
            joined_set = set.intersection(*memberships)
        else:
            joined_set = set.union(*memberships)
        expected_joined = tuple(value for value in self.global_observation_ids if value in joined_set)
        if not expected_joined or expected_joined != self.joined_observation_ids:
            raise ValueError("joined observations do not match the declared join policy")

        for layer in self.layers:
            source_set = set(layer.source_observation_ids)
            expected_mask = tuple(layer.present and value in source_set for value in self.joined_observation_ids)
            if layer.observation_mask != expected_mask:
                raise ValueError("observation mask does not match real membership")
            expected_input = (
                self.joined_observation_ids
                if layer.present and contract.join_policy == "required_inner"
                else layer.source_observation_ids
            )
            if not layer.present:
                expected_input = ()
            if layer.input_observation_ids != expected_input:
                raise ValueError("layer input observations do not match join policy")

        expected_join = _join_fingerprint(
            contract.join_policy,
            self.global_observation_ids,
            self.joined_observation_ids,
            self.layers,
        )
        if self.join_fingerprint != expected_join:
            raise ValueError("join_fingerprint mismatch")
        expected_missingness = _missingness_fingerprint(
            contract.missingness_policy,
            expected_join,
            self.layers,
        )
        if self.missingness_fingerprint != expected_missingness:
            raise ValueError("missingness_fingerprint mismatch")
        return self


_P18_CANONICAL_TYPES = (
    MultiOmicsModalitySlotV1,
    MultiOmicsInputContractV1,
    MultiOmicsLayerInputV1,
    MultiOmicsObservationSemanticsV1,
    MultiOmicsModelInputV1,
)


@dataclass(frozen=True, init=False)
class PreparedMultiOmicsModelInput:
    """Defensive runtime snapshots paired with a root-free identity."""

    model_input: MultiOmicsModelInputV1
    _matrices: tuple[tuple[str, _MatrixSnapshot], ...] = field(
        repr=False,
        compare=False,
    )

    def __init__(
        self,
        model_input: MultiOmicsModelInputV1,
        matrices: tuple[tuple[str, Any], ...],
    ) -> None:
        if type(model_input) is not MultiOmicsModelInputV1:
            raise MultiOmicsInputError("model_input must have the exact canonical type")
        try:
            model_input.to_dict()
        except (ValueError, TypeError) as exc:
            raise MultiOmicsInputError("model_input is not canonical") from exc
        if type(matrices) is not tuple or any(type(item) is not tuple or len(item) != 2 for item in matrices):
            raise MultiOmicsInputError("runtime matrices must be canonical keyed pairs")
        present = tuple(layer for layer in model_input.layers if layer.present)
        keys = tuple(layer.slot.key for layer in present)
        if tuple(key for key, _ in matrices) != keys:
            raise MultiOmicsInputError("runtime matrix order differs from present slots")
        snapshots = []
        for layer, (key, matrix) in zip(present, matrices, strict=True):
            try:
                snapshot = _MatrixSnapshot.from_matrix(matrix)
                materialized = snapshot.materialize()
            except (ValueError, TypeError) as exc:
                raise MultiOmicsInputError("runtime matrix is not canonical") from exc
            if tuple(materialized.shape) != layer.input_shape:
                raise MultiOmicsInputError("runtime matrix shape differs from its identity")
            if snapshot.storage != layer.source_matrix_format:
                raise MultiOmicsInputError("runtime matrix storage differs from its identity")
            if _matrix_fingerprint(materialized) != layer.matrix_fingerprint:
                raise MultiOmicsInputError("runtime matrix differs from its content identity")
            snapshots.append((key, snapshot))
        object.__setattr__(self, "model_input", model_input)
        object.__setattr__(self, "_matrices", tuple(snapshots))

    @property
    def matrices(self) -> tuple[tuple[str, Any], ...]:
        return tuple((key, snapshot.materialize()) for key, snapshot in self._matrices)

    @property
    def alignment_reports(self) -> tuple[tuple[str, AlignmentReport], ...]:
        return tuple((layer.slot.key, layer.alignment_report) for layer in self.model_input.layers if layer.present)


def _exact_pack(pack: RegisteredPack) -> PackManifest:
    if type(pack) is not RegisteredPack:
        raise MultiOmicsInputError("pack must be an exact RegisteredPack")
    _reject_undeclared_model_fields(pack, "pack")
    try:
        manifest = _pack_manifest(pack.manifest)
    except Exception as exc:
        raise MultiOmicsInputError(f"invalid Pack manifest: {exc}") from exc
    try:
        fingerprint = _strict_fingerprint(pack.fingerprint, "pack_fingerprint")
    except ValueError as exc:
        raise MultiOmicsInputError(str(exc)) from exc
    if fingerprint != manifest.fingerprint():
        raise MultiOmicsInputError("RegisteredPack fingerprint mismatch")
    if manifest.schema_version != "vc.pack.v0.3" or manifest.multiomics is None:
        raise MultiOmicsInputError("joint input requires an exact vc.pack.v0.3 Pack")
    return manifest


def _view_modalities(
    view: CanonicalMuDataView,
    manifest: PackManifest,
) -> tuple[
    dict[str, CanonicalModalityView],
    MultiOmicsObservationSemanticsV1,
]:
    if type(view) is not CanonicalMuDataView:
        raise MultiOmicsInputError("view must be an exact CanonicalMuDataView")
    _reject_undeclared_model_fields(view, "view")
    try:
        view_manifest = _pack_manifest(view.manifest)
    except (ValueError, TypeError) as exc:
        raise MultiOmicsInputError("view manifest must have the canonical type") from exc
    if view_manifest.fingerprint() != manifest.fingerprint():
        raise MultiOmicsInputError("view and RegisteredPack manifest identities differ")
    if not view.is_backed:
        raise MultiOmicsInputError("multi-omics view must remain backed")
    if view.manifest_semantics != _manifest_semantics(manifest):
        raise MultiOmicsInputError("view manifest semantics are not canonical")
    if view.observation_pairing != manifest.multiomics.observation_pairing:
        raise MultiOmicsInputError("view observation pairing differs from its Pack")
    observation_semantics = _view_semantics(view)
    _validate_view_semantics(observation_semantics, manifest)

    try:
        global_ids = _strings(view.observation_ids, "global observations", allow_empty=False)
    except ValueError as exc:
        raise MultiOmicsInputError(str(exc)) from exc
    expected_keys = tuple(item.key for item in manifest.multiomics.modalities)
    if tuple(item.key for item in view.modalities) != expected_keys:
        raise MultiOmicsInputError("view modality order differs from its Pack")
    if any(type(item) is not CanonicalModalityView for item in view.modalities):
        raise MultiOmicsInputError("view modalities must have canonical types")

    by_key: dict[str, CanonicalModalityView] = {}
    memberships: list[set[str]] = []
    global_set = set(global_ids)
    for spec, modality in zip(
        manifest.multiomics.modalities,
        view.modalities,
        strict=True,
    ):
        try:
            observations = _strings(
                modality.observation_ids,
                f"{modality.key} observations",
                allow_empty=False,
            )
            features = _strings(
                modality.feature_ids,
                f"{modality.key} features",
                allow_empty=False,
            )
        except ValueError as exc:
            raise MultiOmicsInputError(str(exc)) from exc
        if not modality.is_backed:
            raise MultiOmicsInputError("every multi-omics modality must remain backed")
        try:
            storage = getattr(modality.matrix, "format", None)
        except Exception as exc:
            raise MultiOmicsInputError("cannot inspect modality matrix storage") from exc
        if storage is None:
            actual_format = "dense"
        elif storage in {"csr", "csc"}:
            actual_format = storage
        else:
            raise MultiOmicsInputError("modality matrix storage format is unsupported")
        if actual_format != modality.matrix_format:
            raise MultiOmicsInputError("modality matrix storage differs from its declared identity")
        observation_set = set(observations)
        if not observation_set.issubset(global_set):
            raise MultiOmicsInputError("modality observations are outside the global view")
        if observations != tuple(value for value in global_ids if value in observation_set):
            raise MultiOmicsInputError("modality observation order is ambiguous")
        if modality.shape[0] != len(observations) or modality.shape[1] != len(features):
            raise MultiOmicsInputError("modality shape differs from its identities")
        if modality.shape[1] != spec.shape[1]:
            raise MultiOmicsInputError("modality feature width differs from its Pack")
        if modality.feature_symbols is not None and len(modality.feature_symbols) != len(features):
            raise MultiOmicsInputError("feature symbol count differs from feature identities")
        if (
            modality.taxonomy_id != manifest.taxon.ontology_id
            or modality.assembly_accession != manifest.assembly.accession
            or modality.modality_name != spec.modality.name
            or modality.modality_ontology_id != spec.modality.ontology_id
            or modality.feature_namespace_name != spec.feature_namespace.name
            or modality.feature_namespace_version != spec.feature_namespace.version
            or modality.feature_id_format != spec.feature_semantics.id_format
            or modality.matrix_location != "X"
        ):
            raise MultiOmicsInputError("modality metadata differs from its Pack")
        by_key[modality.key] = modality
        memberships.append(observation_set)

    union = set.union(*memberships)
    if union != global_set:
        raise MultiOmicsInputError("global observations must equal the modality union")
    shared = tuple(value for value in global_ids if all(value in membership for membership in memberships))
    if view.shared_observation_ids != shared:
        raise MultiOmicsInputError("shared observations do not match real membership")
    if view.observation_pairing == "paired" and any(
        modality.observation_ids != global_ids for modality in view.modalities
    ):
        raise MultiOmicsInputError("paired modalities must contain every global observation")
    if len(observation_semantics.conditions) != len(global_ids):
        raise MultiOmicsInputError("view observation semantics differ from global observations")
    return by_key, observation_semantics


def _validate_request(
    request: VirtualCellRequestV2,
    manifest: PackManifest,
    contract: MultiOmicsInputContractV1,
) -> None:
    if (
        request.species.taxonomy_id != manifest.taxon.ontology_id
        or request.species.scientific_name != manifest.taxon.scientific_name
        or contract.taxonomy_id != manifest.taxon.ontology_id
        or contract.assembly_accession != manifest.assembly.accession
    ):
        raise MultiOmicsInputError("request, contract, and Pack biological scope differ")
    if request.task.task_type != contract.task:
        raise MultiOmicsInputError("request task differs from joint input contract")
    outputs = request.task.requested_outputs or (request.output_modality.name,)
    if outputs != contract.outputs or request.output_modality.name != contract.outputs[0]:
        raise MultiOmicsInputError("request outputs differ from joint input contract")
    target = next(slot for slot in contract.slots if slot.key == contract.target_modality_key)
    if (
        request.input_modality.name != target.modality_name
        or request.input_modality.ontology_id != target.modality_ontology_id
        or request.input_modality.feature_namespace != target.feature_contract.feature_namespace.name
    ):
        raise MultiOmicsInputError("request primary input differs from explicit target modality")
    if manifest.perturbations.target_modality != contract.target_modality_key:
        raise MultiOmicsInputError("target modality differs from Pack perturbation semantics")
    if request.perturbation.kind not in {"gene", "gene_combination"}:
        raise MultiOmicsInputError("P18 requires an explicit gene-target modality policy")
    if (request.perturbation.kind == "gene") != (len(request.perturbation.targets) == 1):
        raise MultiOmicsInputError("gene requests require one target; gene combinations require multiple targets")
    if (request.perturbation.dose_value is None) != (request.perturbation.dose_unit is None):
        raise MultiOmicsInputError("request dose requires both a value and canonical unit")
    if request.perturbation.dose_unit is not None and request.perturbation.dose_unit not in _DOSE_UNITS:
        raise MultiOmicsInputError("request contains an unsupported dose unit")
    declared_perturbations = {(item.kind, item.targets) for item in manifest.perturbations.values if item.targets}
    if ("genetic", request.perturbation.targets) not in declared_perturbations:
        raise MultiOmicsInputError("perturbation is not an exact Pack declaration")


def _validate_request_target_alignment(
    request: VirtualCellRequestV2,
    target: MultiOmicsLayerInputV1,
) -> None:
    report = target.alignment_report
    if report is None:  # pragma: no cover - present layer validation rejects this
        raise MultiOmicsInputError("target modality lacks an alignment report")
    mapped: dict[str, str] = {}
    aggregated: set[str] = set()
    dropped: set[str] = set()
    for step in report.steps:
        if step.operation == "alias":
            mapped.update((source, step.target_ids[0]) for source in step.source_ids)
        elif step.operation == "aggregate":
            aggregated.update(step.source_ids)
        elif step.operation == "drop":
            dropped.update(step.source_ids)
    aligned_targets = []
    source_features = set(report.source_feature_ids)
    model_features = set(report.target_feature_ids)
    for source in request.perturbation.targets:
        if source not in source_features or source in dropped:
            raise MultiOmicsInputError("Pack perturbation target is absent from the target modality input")
        if source in aggregated:
            raise MultiOmicsInputError("aggregate alignment cannot prove an exact perturbation target identity")
        aligned = mapped.get(source, source)
        if aligned not in model_features:
            raise MultiOmicsInputError("Pack perturbation target has no explicit model feature identity")
        aligned_targets.append(aligned)
    if len(set(aligned_targets)) != len(aligned_targets):
        raise MultiOmicsInputError("distinct perturbation targets collapse to one model feature")


def _validate_adapter(
    adapter: AdapterIdentity,
    contract: MultiOmicsInputContractV1,
) -> None:
    if (
        adapter.legacy_incomplete
        or adapter.input_contract_fingerprint != contract.fingerprint()
        or adapter.task != contract.task
        or adapter.outputs != contract.outputs
    ):
        raise MultiOmicsInputError("adapter identity does not own this exact joint input contract")


def _take_rows(matrix: Any, source_ids: tuple[str, ...], target_ids: tuple[str, ...]):
    positions = {value: index for index, value in enumerate(source_ids)}
    try:
        return matrix[[positions[value] for value in target_ids], :]
    except (KeyError, IndexError, TypeError) as exc:
        raise MultiOmicsInputError("cannot select exact shared observation rows") from exc


def compile_multiomics_model_input(
    request: VirtualCellRequestV2,
    pack: RegisteredPack,
    view: CanonicalMuDataView,
    contract: MultiOmicsInputContractV1,
    adapter_identity: AdapterIdentity,
) -> PreparedMultiOmicsModelInput:
    """Compile a joint input without creating an execution step or fabricating rows."""
    try:
        request = _request(request)
        contract = _input_contract(contract)
        adapter_identity = _adapter_identity(adapter_identity)
    except (ValueError, TypeError) as exc:
        raise MultiOmicsInputError(str(exc)) from exc
    manifest = _exact_pack(pack)
    modalities, observation_semantics = _view_modalities(view, manifest)
    _validate_request(request, manifest, contract)
    _validate_adapter(adapter_identity, contract)

    aligned: list[tuple[MultiOmicsModalitySlotV1, CanonicalModalityView, Any]] = []
    absent: set[str] = set()
    for slot in contract.slots:
        modality = modalities.get(slot.key)
        if modality is None:
            if slot.required:
                raise MultiOmicsInputError(f"required modality is absent: {slot.key}")
            absent.add(slot.key)
            continue
        feature = slot.feature_contract
        if (
            modality.modality_name != slot.modality_name
            or modality.modality_ontology_id != slot.modality_ontology_id
            or modality.taxonomy_id != contract.taxonomy_id
            or modality.assembly_accession != contract.assembly_accession
            or modality.feature_namespace_name != feature.feature_namespace.name
            or modality.feature_namespace_version != feature.feature_namespace.version
            or modality.feature_id_format != feature.feature_id_format
        ):
            raise MultiOmicsInputError(f"modality contract mismatch: {slot.key}")
        try:
            result = align_features(modality, feature, mapping_root=pack.root)
        except Exception as exc:
            raise MultiOmicsInputError(f"feature alignment failed for {slot.key}: {exc}") from exc
        if any(step.operation == "fill" for step in result.report.steps):
            raise MultiOmicsInputError("P18 forbids fill alignment steps")
        aligned.append((slot, modality, result))

    if len(aligned) < 2:
        raise MultiOmicsInputError("joint model input requires at least two present modalities")
    if contract.target_modality_key in absent:
        raise MultiOmicsInputError("target modality is absent")

    global_ids = tuple(view.observation_ids)
    memberships = [set(modality.observation_ids) for _, modality, _ in aligned]
    if contract.join_policy == "required_inner":
        joined_set = set.intersection(*memberships)
    else:
        joined_set = set.union(*memberships)
    joined_ids = tuple(value for value in global_ids if value in joined_set)
    if not joined_ids:
        raise MultiOmicsInputError("observation join is empty")

    by_key = {slot.key: (modality, result) for slot, modality, result in aligned}
    layers: list[MultiOmicsLayerInputV1] = []
    matrices: list[tuple[str, Any]] = []
    for slot in contract.slots:
        bound = by_key.get(slot.key)
        if bound is None:
            layers.append(
                MultiOmicsLayerInputV1(
                    schema_version="vc.multiomics-layer-input.v1",
                    slot=slot,
                    present=False,
                    source_observation_ids=(),
                    input_observation_ids=(),
                    observation_mask=tuple(False for _ in joined_ids),
                    alignment_report=None,
                    alignment_report_fingerprint=None,
                    matrix_fingerprint=None,
                    source_matrix_format=None,
                    source_shape=None,
                    aligned_shape=None,
                    input_shape=None,
                )
            )
            continue
        modality, result = bound
        source_ids = tuple(modality.observation_ids)
        if contract.join_policy == "required_inner":
            input_ids = joined_ids
            matrix = _take_rows(result.matrix, source_ids, input_ids)
        else:
            input_ids = source_ids
            matrix = result.matrix
        source_set = set(source_ids)
        mask = tuple(value in source_set for value in joined_ids)
        layer = MultiOmicsLayerInputV1(
            schema_version="vc.multiomics-layer-input.v1",
            slot=slot,
            present=True,
            source_observation_ids=source_ids,
            input_observation_ids=input_ids,
            observation_mask=mask,
            alignment_report=result.report,
            alignment_report_fingerprint=_fingerprint(result.report.to_dict()),
            matrix_fingerprint=_matrix_fingerprint(matrix),
            source_matrix_format=modality.matrix_format,
            source_shape=tuple(result.report.source_shape),
            aligned_shape=tuple(result.report.target_shape),
            input_shape=tuple(matrix.shape),
        )
        layers.append(layer)
        matrices.append((slot.key, matrix))

    layer_tuple = tuple(layers)
    join_fingerprint = _join_fingerprint(
        contract.join_policy,
        global_ids,
        joined_ids,
        layer_tuple,
    )
    missingness_fingerprint = _missingness_fingerprint(
        contract.missingness_policy,
        join_fingerprint,
        layer_tuple,
    )
    view_identity_fingerprint = _view_identity_fingerprint(
        pack.fingerprint,
        global_ids,
        layer_tuple,
        observation_semantics.fingerprint(),
    )
    try:
        model_input = MultiOmicsModelInputV1(
            schema_version="vc.multiomics-model-input.v1",
            request=request,
            request_fingerprint=_fingerprint(request.to_dict()),
            pack_manifest=manifest,
            pack_id=manifest.pack_id,
            pack_version=manifest.pack_version,
            pack_fingerprint=pack.fingerprint,
            observation_semantics=observation_semantics,
            observation_semantics_fingerprint=observation_semantics.fingerprint(),
            view_identity_fingerprint=view_identity_fingerprint,
            input_contract=contract,
            input_contract_fingerprint=contract.fingerprint(),
            adapter_identity=adapter_identity,
            adapter_fingerprint=adapter_identity.fingerprint(),
            broker_agent="ModelBrokerAgent",
            broker_resolution="identity_only_not_registry_evaluated",
            global_observation_ids=global_ids,
            joined_observation_ids=joined_ids,
            join_fingerprint=join_fingerprint,
            missingness_fingerprint=missingness_fingerprint,
            layers=layer_tuple,
            executable=False,
            execution_performed=False,
            execution_step_created=False,
            abstain=True,
            abstain_reason="contract_only_execution_not_authorized",
        )
    except (ValidationError, ValueError, TypeError) as exc:
        raise MultiOmicsInputError(f"compiled model input is invalid: {exc}") from exc
    return PreparedMultiOmicsModelInput(
        model_input=model_input,
        matrices=tuple(matrices),
    )
