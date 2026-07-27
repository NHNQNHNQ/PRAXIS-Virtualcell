"""Field-level schema objects for versioned VirtualCellPack manifests."""

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


class FeatureSemanticsSpec(SchemaObject):
    id_source: Literal["var_names"]
    id_format: Literal["ensembl_gene", "ncbi_gene_curie", "uniprot_protein"]
    symbol_field: str | None = None

    @field_validator("symbol_field", mode="before")
    @classmethod
    def _valid_symbol_field(cls, value):
        return _optional_text(value, "feature_semantics.symbol_field")


class LocalTermSpec(SchemaObject):
    id: str
    role: Literal["identity", "state", "context"]
    label: str
    definition: str

    @field_validator("id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        value = _text(value, "local_terms.id")
        if not _CURIE.fullmatch(value):
            raise ValueError("local_terms.id must be a CURIE")
        if value.split(":", 1)[0] in {"CL", "UBERON", "cellosaurus"}:
            raise ValueError("standard ontology CURIEs must not be redefined as local terms")
        return value

    @field_validator("label", "definition", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "local term field")


class CellSemanticsSpec(SchemaObject):
    identity: str
    state: tuple[str, ...]
    context: tuple[str, ...]
    local_terms: tuple[LocalTermSpec, ...] = ()

    @field_validator("identity", mode="before")
    @classmethod
    def _valid_identity(cls, value):
        return _text(value, "cell_semantics.identity")

    @field_validator("state", "context", mode="before")
    @classmethod
    def _valid_fields(cls, value):
        return _string_array(value, "cell semantic fields")

    @field_validator("local_terms", mode="before")
    @classmethod
    def _valid_local_terms(cls, value):
        if not isinstance(value, list):
            raise ValueError("cell_semantics.local_terms must be a JSON array")
        return value

    @model_validator(mode="after")
    def _unique_semantics(self):
        fields = (self.identity, *self.state, *self.context)
        if len(set(fields)) != len(fields):
            raise ValueError("identity, state, and context fields must be distinct")
        ids = [term.id for term in self.local_terms]
        if len(set(ids)) != len(ids):
            raise ValueError("cell_semantics.local_terms ids must be unique")
        return self


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


class MultiOmicsModalitySpec(SchemaObject):
    key: str
    modality: ModalitySpec
    feature_namespace: FeatureNamespaceSpec
    feature_semantics: FeatureSemanticsSpec
    shape: tuple[int, int]

    @field_validator("key", mode="before")
    @classmethod
    def _valid_key(cls, value):
        return _text(value, "multiomics.modalities.key")

    @field_validator("shape", mode="before")
    @classmethod
    def _valid_shape(cls, value):
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item <= 0
                for item in value
            )
        ):
            raise ValueError(
                "multiomics modality shape must be "
                "[positive observations, positive features]"
            )
        return tuple(value)


class MultiOmicsSpec(SchemaObject):
    asset: str
    observation_pairing: Literal["paired", "partially_paired"]
    modalities: tuple[MultiOmicsModalitySpec, ...]

    @field_validator("asset", mode="before")
    @classmethod
    def _valid_asset(cls, value):
        return _text(value, "multiomics.asset")

    @field_validator("modalities", mode="before")
    @classmethod
    def _valid_modalities(cls, value):
        if not isinstance(value, list) or len(value) < 2:
            raise ValueError("multiomics.modalities must contain at least two modalities")
        return value

    @model_validator(mode="after")
    def _unique_modalities(self):
        keys = [value.key for value in self.modalities]
        if len(set(keys)) != len(keys):
            raise ValueError("multiomics modality keys must be unique")
        return self


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


class QuantityFieldsSpec(SchemaObject):
    value_field: str
    unit_field: str

    @field_validator("value_field", "unit_field", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "quantity field")

    @model_validator(mode="after")
    def _distinct_fields(self):
        if self.value_field == self.unit_field:
            raise ValueError("quantity value and unit fields must be distinct")
        return self


class ConditionsSpec(SchemaObject):
    field: str
    values: tuple[str, ...]
    matched_control_field: str
    dose: QuantityFieldsSpec
    time: QuantityFieldsSpec

    @field_validator("field", "matched_control_field", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "conditions field")

    @field_validator("values", mode="before")
    @classmethod
    def _valid_values(cls, value):
        return _string_array(value, "conditions.values")

    @model_validator(mode="after")
    def _distinct_fields(self):
        fields = {
            self.field,
            self.matched_control_field,
            self.dose.value_field,
            self.dose.unit_field,
            self.time.value_field,
            self.time.unit_field,
        }
        if len(fields) != 6:
            raise ValueError("condition, control, dose, and time fields must be distinct")
        if len(set(self.values)) != len(self.values):
            raise ValueError("condition ids must be unique")
        return self


class PerturbationRecordSpec(SchemaObject):
    id: str
    kind: Literal["control", "genetic", "chemical", "environmental"]
    targets: tuple[str, ...]

    @field_validator("id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "perturbations.values.id")

    @field_validator("targets", mode="before")
    @classmethod
    def _valid_targets(cls, value):
        if not isinstance(value, list):
            raise ValueError("perturbation targets must be a JSON array")
        return tuple(_text(item, "perturbation target") for item in value)

    @model_validator(mode="after")
    def _valid_target_semantics(self):
        if len(set(self.targets)) != len(self.targets):
            raise ValueError("perturbation targets must not contain duplicates")
        if self.kind == "control" and self.targets:
            raise ValueError("control perturbations must not declare targets")
        if self.kind != "control" and not self.targets:
            raise ValueError("non-control perturbations must declare targets")
        return self


class PerturbationsSpec(SchemaObject):
    field: str
    target_modality: str | None = None
    values: tuple[PerturbationRecordSpec, ...]

    @field_validator("field", "target_modality", mode="before")
    @classmethod
    def _valid_field(cls, value):
        return _optional_text(value, "perturbations field")

    @field_validator("values", mode="before")
    @classmethod
    def _valid_values(cls, value):
        if not isinstance(value, list) or not value:
            raise ValueError("perturbations.values must be a non-empty JSON array")
        return value

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [value.id for value in self.values]
        if len(set(ids)) != len(ids):
            raise ValueError("perturbation ids must be unique")
        return self


class SplitSpec(SchemaObject):
    field: str
    strategy: Literal["predefined"]
    values: tuple[str, ...]
    name: str | None = None
    leakage_guard: tuple[str, ...] = ()

    @field_validator("field", "name", mode="before")
    @classmethod
    def _valid_field(cls, value):
        return _optional_text(value, "split field")

    @field_validator("values", mode="before")
    @classmethod
    def _valid_values(cls, value):
        return _string_array(value, "split.values")

    @field_validator("leakage_guard", mode="before")
    @classmethod
    def _valid_leakage_guard(cls, value):
        if not isinstance(value, list):
            raise ValueError("split.leakage_guard must be a JSON array")
        return tuple(_text(item, "split.leakage_guard") for item in value)

    @model_validator(mode="after")
    def _unique_values(self):
        if len(set(self.values)) != len(self.values):
            raise ValueError("split.values must not contain duplicates")
        if len(set(self.leakage_guard)) != len(self.leakage_guard):
            raise ValueError("split.leakage_guard must not contain duplicates")
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
