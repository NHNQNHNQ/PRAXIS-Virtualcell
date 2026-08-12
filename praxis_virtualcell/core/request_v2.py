"""Strict, versioned VirtualCell request/domain objects.

This module defines data contracts only.  It does not read datasets, resolve
packs, select models, or run predictions.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.exceptions import InputValidationError

_ONTOLOGY_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
_TAXONOMY_ID = re.compile(r"^NCBITaxon:[0-9]+$")
_CELL_TYPE_ID = re.compile(r"^CL:[0-9]+$")
_TISSUE_ID = re.compile(r"^UBERON:[0-9]+$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_TIMEPOINT = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:s|min|h|d)$")

_UNITS = frozenset(
    {
        "1",
        "dimensionless",
        "probability",
        "percent",
        "M",
        "mM",
        "uM",
        "nM",
        "pM",
        "g/L",
        "mg/L",
        "ug/mL",
        "s",
        "min",
        "h",
        "d",
        "count",
        "CPM",
        "TPM",
        "log2_fold_change",
        "z_score",
    }
)
_PERTURBATION_KINDS = frozenset({"gene", "gene_combination", "drug", "medium", "ligand"})

_LEGACY_SPECIES = {
    "human": ("NCBITaxon:9606", "Homo sapiens"),
    "mouse": ("NCBITaxon:10090", "Mus musculus"),
    "yeast": ("NCBITaxon:4932", "Saccharomyces cerevisiae"),
    "bacteria": ("NCBITaxon:2", "Bacteria"),
}
_LEGACY_SPECIES_BY_TAXON = {taxon: name for name, (taxon, _) in _LEGACY_SPECIES.items()}


def _nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field_name} must be UTF-8 encodable") from exc
    return value


def _optional_nonempty_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, field_name)


def _ontology_id(value: Any, field_name: str, pattern: re.Pattern[str] = _ONTOLOGY_ID) -> str:
    value = _nonempty_string(value, field_name)
    if not pattern.fullmatch(value):
        raise ValueError(f"invalid {field_name}: {value!r}")
    return value


def _unit(value: Any) -> str | None:
    if value is None:
        return None
    value = _nonempty_string(value, "unit")
    if value not in _UNITS:
        raise ValueError(f"unsupported unit: {value!r}")
    return value


def _json_value(value: Any, path: str = "$") -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{path} contains a non-UTF-8 string") from exc
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{path}[{index}]")
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            try:
                key.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError(f"{path} contains a non-UTF-8 key") from exc
            _json_value(item, f"{path}.{key}")
        return value
    raise ValueError(f"{path} contains non-JSON type {type(value).__name__}")


class _FrozenDict(dict):
    @staticmethod
    def _immutable(*args, **kwargs):
        raise TypeError("validated domain JSON is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __deepcopy__(self, memo):
        return self


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return _FrozenDict({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


class _VersionedDomainObject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def model_post_init(self, __context: Any) -> None:
        for name, value in self.__dict__.items():
            if isinstance(value, dict):
                object.__setattr__(self, name, _freeze_json(value))

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise InputValidationError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise InputValidationError(f"invalid {cls.__name__}: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        value = self.model_dump(mode="json")
        _json_value(value)
        return value


class SpeciesRef(_VersionedDomainObject):
    schema_version: Literal["vc.species-ref.v1"]
    taxonomy_id: str
    scientific_name: str
    common_name: str | None = None

    @field_validator("taxonomy_id", mode="before")
    @classmethod
    def _valid_taxonomy_id(cls, value):
        return _ontology_id(value, "taxonomy_id", _TAXONOMY_ID)

    @field_validator("scientific_name", mode="before")
    @classmethod
    def _valid_scientific_name(cls, value):
        return _nonempty_string(value, "scientific_name")

    @field_validator("common_name", mode="before")
    @classmethod
    def _valid_common_name(cls, value):
        return _optional_nonempty_string(value, "common_name")


class CellContext(_VersionedDomainObject):
    schema_version: Literal["vc.cell-context.v1"]
    cell_type_name: str | None = None
    cell_type_id: str | None = None
    tissue_name: str | None = None
    tissue_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cell_type_name", mode="before")
    @classmethod
    def _valid_cell_type_name(cls, value):
        return _optional_nonempty_string(value, "cell_type_name")

    @field_validator("tissue_name", mode="before")
    @classmethod
    def _valid_tissue_name(cls, value):
        return _optional_nonempty_string(value, "tissue_name")

    @field_validator("cell_type_id", mode="before")
    @classmethod
    def _valid_cell_type_id(cls, value):
        return None if value is None else _ontology_id(value, "cell_type_id", _CELL_TYPE_ID)

    @field_validator("tissue_id", mode="before")
    @classmethod
    def _valid_tissue_id(cls, value):
        return None if value is None else _ontology_id(value, "tissue_id", _TISSUE_ID)

    @field_validator("attributes", mode="before")
    @classmethod
    def _valid_attributes(cls, value):
        if not isinstance(value, dict):
            raise ValueError("attributes must be a JSON object")
        return _json_value(value, "$.attributes")


class ModalitySpec(_VersionedDomainObject):
    schema_version: Literal["vc.modality.v1"]
    name: str
    ontology_id: str | None = None
    unit: str | None = None
    feature_namespace: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _nonempty_string(value, "name")

    @field_validator("ontology_id", mode="before")
    @classmethod
    def _valid_ontology_id(cls, value):
        return None if value is None else _ontology_id(value, "ontology_id")

    @field_validator("unit", mode="before")
    @classmethod
    def _valid_unit(cls, value):
        return _unit(value)

    @field_validator("feature_namespace", mode="before")
    @classmethod
    def _valid_feature_namespace(cls, value):
        return _optional_nonempty_string(value, "feature_namespace")


class DatasetRef(_VersionedDomainObject):
    schema_version: Literal["vc.dataset-ref.v1"]
    dataset_id: str
    version: str
    sha256: str
    uri: str | None = None

    @field_validator("dataset_id", "version", mode="before")
    @classmethod
    def _valid_required_strings(cls, value):
        return _nonempty_string(value, "dataset field")

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_sha256(cls, value):
        value = _nonempty_string(value, "sha256")
        if not _SHA256.fullmatch(value):
            raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
        return value

    @field_validator("uri", mode="before")
    @classmethod
    def _valid_uri(cls, value):
        return _optional_nonempty_string(value, "uri")


class PerturbationSpec(_VersionedDomainObject):
    schema_version: Literal["vc.perturbation.v1"]
    kind: str
    targets: tuple[str, ...]
    dose_value: float | None = None
    dose_unit: str | None = None
    timepoint: str | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def _valid_kind(cls, value):
        value = _nonempty_string(value, "kind")
        if value not in _PERTURBATION_KINDS:
            raise ValueError(f"unsupported perturbation kind: {value!r}")
        return value

    @field_validator("targets", mode="before")
    @classmethod
    def _valid_targets(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("targets must be an array of strings")
        return tuple(_nonempty_string(item, "target") for item in value)

    @field_validator("dose_value", mode="before")
    @classmethod
    def _valid_dose_value(cls, value):
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("dose_value must be a finite non-negative number")
        try:
            value = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError("dose_value must be a finite non-negative number") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError("dose_value must be a finite non-negative number")
        return value

    @field_validator("dose_unit", mode="before")
    @classmethod
    def _valid_dose_unit(cls, value):
        return _unit(value)

    @field_validator("timepoint", mode="before")
    @classmethod
    def _valid_timepoint(cls, value):
        if value is None:
            return None
        value = _nonempty_string(value, "timepoint")
        if not _TIMEPOINT.fullmatch(value):
            raise ValueError("timepoint must use s, min, h, or d")
        return value

    @model_validator(mode="after")
    def _complete_perturbation(self):
        if self.kind != "medium" and not self.targets:
            raise ValueError(f"perturbation kind {self.kind!r} requires targets")
        if self.dose_unit is not None and self.dose_value is None:
            raise ValueError("dose_unit requires dose_value")
        return self


class TaskSpec(_VersionedDomainObject):
    schema_version: Literal["vc.task.v1"]
    task_type: str
    requested_outputs: tuple[str, ...] = ()

    @field_validator("task_type", mode="before")
    @classmethod
    def _valid_task_type(cls, value):
        return _nonempty_string(value, "task_type")

    @field_validator("requested_outputs", mode="before")
    @classmethod
    def _valid_requested_outputs(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("requested_outputs must be an array of strings")
        return tuple(_nonempty_string(item, "requested_output") for item in value)


class PackInputSelectorV1(_VersionedDomainObject):
    """One exact record selector for a Pack-owned runtime input reader."""

    schema_version: Literal["vc.pack-input-selector.v1"]
    record_id: str

    @field_validator("record_id", mode="before")
    @classmethod
    def _valid_record_id(cls, value):
        value = _nonempty_string(value, "pack_input.record_id")
        if value.strip() != value:
            raise ValueError("pack_input.record_id must not have surrounding whitespace")
        return value


class VirtualCellRequestV2(_VersionedDomainObject):
    schema_version: Literal["vc.request.v2"]
    request_id: str
    species: SpeciesRef
    cell_context: CellContext
    input_modality: ModalitySpec
    output_modality: ModalitySpec
    perturbation: PerturbationSpec
    task: TaskSpec
    pack_input: PackInputSelectorV1 | None = None
    baseline_context: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id", mode="before")
    @classmethod
    def _valid_request_id(cls, value):
        return _nonempty_string(value, "request_id")

    @field_validator("baseline_context", mode="before")
    @classmethod
    def _valid_baseline_context(cls, value):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("baseline_context must be a JSON object")
        return _json_value(value, "$.baseline_context")

    @field_validator("metadata", "constraints", mode="before")
    @classmethod
    def _valid_json_objects(cls, value):
        if not isinstance(value, dict):
            raise ValueError("metadata and constraints must be JSON objects")
        return _json_value(value)

    def to_dict(self) -> dict[str, Any]:
        """Preserve historic v2 request bytes when no Pack selector is used."""

        value = super().to_dict()
        if self.pack_input is None:
            value.pop("pack_input")
        return value


class ModelInputBundle(_VersionedDomainObject):
    schema_version: Literal["vc.model-input.v1"]
    bundle_id: str
    request: VirtualCellRequestV2
    datasets: tuple[DatasetRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("bundle_id", mode="before")
    @classmethod
    def _valid_bundle_id(cls, value):
        return _nonempty_string(value, "bundle_id")

    @field_validator("datasets", mode="before")
    @classmethod
    def _valid_datasets(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("datasets must be an array")
        return value

    @field_validator("metadata", mode="before")
    @classmethod
    def _valid_metadata(cls, value):
        if not isinstance(value, dict):
            raise ValueError("metadata must be a JSON object")
        return _json_value(value, "$.metadata")


class PredictionBundle(_VersionedDomainObject):
    schema_version: Literal["vc.prediction.v1"]
    prediction_id: str
    request_id: str
    model_id: str
    task: TaskSpec
    output_modality: ModalitySpec
    feature_ids: tuple[str, ...]
    values: tuple[float, ...]
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prediction_id", "request_id", "model_id", mode="before")
    @classmethod
    def _valid_ids(cls, value):
        return _nonempty_string(value, "prediction identity")

    @field_validator("feature_ids", mode="before")
    @classmethod
    def _valid_feature_ids(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("feature_ids must be an array of strings")
        return tuple(_nonempty_string(item, "feature_id") for item in value)

    @field_validator("values", mode="before")
    @classmethod
    def _valid_values(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("values must be an array of finite numbers")
        values = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError("values must contain only finite numbers")
            try:
                item = float(item)
            except (OverflowError, ValueError) as exc:
                raise ValueError("values must contain only finite numbers") from exc
            if not math.isfinite(item):
                raise ValueError("values must contain only finite numbers")
            values.append(item)
        return tuple(values)

    @field_validator("provenance", mode="before")
    @classmethod
    def _valid_provenance(cls, value):
        if not isinstance(value, dict):
            raise ValueError("provenance must be a JSON object")
        return _json_value(value, "$.provenance")

    @model_validator(mode="after")
    def _identified_vector(self):
        if not self.feature_ids or not self.values:
            raise ValueError("prediction vectors require named features and values")
        if len(self.feature_ids) != len(self.values):
            raise ValueError("feature_ids and values must have the same length")
        if len(set(self.feature_ids)) != len(self.feature_ids):
            raise ValueError("feature_ids must be unique")
        return self


def require_v2_request(value: Any) -> VirtualCellRequestV2:
    """Parse only an explicitly declared v2 request; never project legacy input."""
    if not isinstance(value, dict) or value.get("schema_version") != "vc.request.v2":
        raise InputValidationError("vc.request.v2 schema_version is required")
    return VirtualCellRequestV2.from_dict(value)


def legacy_request_to_v2(request) -> VirtualCellRequestV2:
    """Project a supported legacy request into the explicit v2 contract."""
    from praxis_virtualcell.core.request import VirtualCellRequest

    if not isinstance(request, VirtualCellRequest):
        raise InputValidationError("legacy_request_to_v2 requires VirtualCellRequest")
    species_entry = _LEGACY_SPECIES.get(request.species)
    if species_entry is None:
        raise InputValidationError(f"legacy species has no v2 taxonomy mapping: {request.species!r}")
    taxonomy_id, scientific_name = species_entry
    metadata = deepcopy(request.metadata)
    requested_outputs = metadata.get("requested_outputs", [])
    if not isinstance(requested_outputs, list) or not all(
        isinstance(item, str) and item.strip() for item in requested_outputs
    ):
        raise InputValidationError("legacy metadata.requested_outputs must be list[str]")

    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": request.request_id,
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": taxonomy_id,
                "scientific_name": scientific_name,
                "common_name": request.species,
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": request.cell_type,
                "cell_type_id": None,
                "tissue_name": request.tissue,
                "tissue_id": None,
                "attributes": {},
            },
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": request.input_modality,
                "ontology_id": None,
                "unit": None,
                "feature_namespace": None,
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": request.output_modality,
                "ontology_id": None,
                "unit": None,
                "feature_namespace": None,
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": request.perturbation_type,
                "targets": list(request.perturbation_targets),
                "dose_value": request.perturbation_dose,
                "dose_unit": None,
                "timepoint": request.perturbation_time,
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": request.task_type,
                "requested_outputs": requested_outputs,
            },
            "baseline_context": deepcopy(request.baseline_context),
            "metadata": metadata,
            "constraints": deepcopy(request.constraints),
        }
    )


def v2_request_to_legacy(request: VirtualCellRequestV2):
    """Project v2 to legacy only when no v2-only meaning would be discarded."""
    from praxis_virtualcell.core.request import VirtualCellRequest

    if not isinstance(request, VirtualCellRequestV2):
        raise InputValidationError("v2_request_to_legacy requires VirtualCellRequestV2")
    species = _LEGACY_SPECIES_BY_TAXON.get(request.species.taxonomy_id)
    if species is None:
        raise InputValidationError(f"v2 taxonomy has no legacy mapping: {request.species.taxonomy_id!r}")
    _, expected_scientific_name = _LEGACY_SPECIES[species]
    if request.species.scientific_name != expected_scientific_name or request.species.common_name not in (
        None,
        species,
    ):
        raise InputValidationError("v2 species identity cannot be represented by the legacy request")
    if (
        request.cell_context.cell_type_id is not None
        or request.cell_context.tissue_id is not None
        or request.cell_context.attributes
        or request.input_modality.ontology_id is not None
        or request.input_modality.unit is not None
        or request.input_modality.feature_namespace is not None
        or request.output_modality.ontology_id is not None
        or request.output_modality.unit is not None
        or request.output_modality.feature_namespace is not None
        or request.perturbation.dose_unit is not None
        or request.pack_input is not None
    ):
        raise InputValidationError("v2-only context cannot be silently discarded by the legacy adapter")

    serialized = request.to_dict()
    metadata = serialized["metadata"]
    requested_outputs = list(request.task.requested_outputs)
    existing_outputs = metadata.get("requested_outputs")
    if existing_outputs is not None and existing_outputs != requested_outputs:
        raise InputValidationError("task.requested_outputs conflicts with metadata.requested_outputs")
    if requested_outputs or existing_outputs is not None:
        metadata["requested_outputs"] = requested_outputs

    return VirtualCellRequest.from_dict(
        {
            "request_id": request.request_id,
            "species": species,
            "perturbation_type": request.perturbation.kind,
            "perturbation_targets": list(request.perturbation.targets),
            "input_modality": request.input_modality.name,
            "output_modality": request.output_modality.name,
            "task_type": request.task.task_type,
            "cell_type": request.cell_context.cell_type_name,
            "tissue": request.cell_context.tissue_name,
            "perturbation_dose": request.perturbation.dose_value,
            "perturbation_time": request.perturbation.timepoint,
            "baseline_context": serialized["baseline_context"],
            "metadata": metadata,
            "constraints": serialized["constraints"],
        }
    )
