"""Field-level schema objects for VirtualCellPack v0.1."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
_TAXON = re.compile(r"^NCBITaxon:[0-9]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else _text(value, field)


def _string_array(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty JSON array")
    return tuple(_text(item, field) for item in value)


class SchemaObject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaxonSpec(SchemaObject):
    ontology_id: str
    scientific_name: str

    @field_validator("ontology_id", mode="before")
    @classmethod
    def _valid_taxon(cls, value):
        value = _text(value, "taxon.ontology_id")
        if not _TAXON.fullmatch(value):
            raise ValueError("taxon.ontology_id must use NCBITaxon:<digits>")
        return value

    @field_validator("scientific_name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _text(value, "taxon.scientific_name")


class AssemblySpec(SchemaObject):
    name: str
    accession: str

    @field_validator("name", "accession", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "assembly field")


class IdentitySpec(SchemaObject):
    observation_key: str
    feature_key: str

    @field_validator("observation_key", "feature_key", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "identity field")


class ModalitySpec(SchemaObject):
    name: str
    ontology_id: str

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _text(value, "modality.name")

    @field_validator("ontology_id", mode="before")
    @classmethod
    def _valid_ontology(cls, value):
        value = _text(value, "modality.ontology_id")
        if not _CURIE.fullmatch(value):
            raise ValueError("modality.ontology_id must be a CURIE")
        return value


class FeatureNamespaceSpec(SchemaObject):
    name: str
    version: str

    @field_validator("name", "version", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "feature_namespace field")


class AssetSpec(SchemaObject):
    id: str
    path: str
    media_type: str
    sha256: str
    size_bytes: int

    @field_validator("id", "path", "media_type", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "asset field")

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value):
        value = _text(value, "asset.sha256")
        if not _SHA256.fullmatch(value):
            raise ValueError("asset.sha256 must be exactly 64 lowercase hexadecimal characters")
        return value

    @field_validator("size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("asset.size_bytes must be a non-negative integer")
        return value


class MatrixSpec(SchemaObject):
    asset: str
    location: Literal["X"]
    shape: tuple[int, int]

    @field_validator("asset", mode="before")
    @classmethod
    def _valid_asset(cls, value):
        return _text(value, "matrix.asset")

    @field_validator("shape", mode="before")
    @classmethod
    def _valid_shape(cls, value):
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value)
        ):
            raise ValueError("matrix.shape must be [positive observations, positive features]")
        return tuple(value)


class ConditionSpec(SchemaObject):
    field: str
    values: tuple[str, ...]
    control: str

    @field_validator("field", "control", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "condition field")

    @field_validator("values", mode="before")
    @classmethod
    def _valid_values(cls, value):
        return _string_array(value, "condition.values")

    @model_validator(mode="after")
    def _valid_control(self):
        if len(set(self.values)) != len(self.values):
            raise ValueError("condition.values must not contain duplicates")
        if self.control not in self.values:
            raise ValueError("condition.control must appear in condition.values")
        return self


class SplitSpec(SchemaObject):
    field: str
    strategy: Literal["predefined"]
    values: tuple[str, ...]

    @field_validator("field", mode="before")
    @classmethod
    def _valid_field(cls, value):
        return _text(value, "split.field")

    @field_validator("values", mode="before")
    @classmethod
    def _valid_values(cls, value):
        return _string_array(value, "split.values")

    @model_validator(mode="after")
    def _unique_values(self):
        if len(set(self.values)) != len(self.values):
            raise ValueError("split.values must not contain duplicates")
        return self


class ProvenanceSpec(SchemaObject):
    source: str
    created_by: str
    citation: str

    @field_validator("source", "created_by", "citation", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "provenance field")


class LicenseSpec(SchemaObject):
    id: str
    name: str
    url: str | None = None

    @field_validator("id", "name", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "license field")

    @field_validator("url", mode="before")
    @classmethod
    def _valid_url(cls, value):
        return _optional_text(value, "license.url")
