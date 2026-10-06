"""Strict, explicit feature alignment for model input contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError, field_validator, model_validator

from praxis_virtualcell.data_packs.anndata_adapter import _FEATURE_IDS
from praxis_virtualcell.data_packs.errors import (
    FeatureAlignmentError,
    OmicsDependencyError,
    VirtualCellPackError,
)
from praxis_virtualcell.data_packs.manifest import load_manifest
from praxis_virtualcell.data_packs.mudata_adapter import CanonicalModalityView
from praxis_virtualcell.data_packs.schema import FeatureNamespaceSpec, SchemaObject
from praxis_virtualcell.data_packs.validator import resolve_asset_path

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        qualifier = "" if allow_empty else " non-empty"
        raise ValueError(f"{field} must be a{qualifier} JSON array")
    values = tuple(_text(item, field) for item in value)
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return values


class FillRule(SchemaObject):
    feature_id: str
    value: float

    @field_validator("feature_id", mode="before")
    @classmethod
    def _valid_feature_id(cls, value):
        return _text(value, "fill.feature_id")

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("fill.value must be a finite number")
        try:
            value = float(value)
        except OverflowError as exc:
            raise ValueError("fill.value must be a finite number") from exc
        if not math.isfinite(value):
            raise ValueError("fill.value must be a finite number")
        return value


class MappingAssetRef(SchemaObject):
    asset_id: str
    path: str
    version: str
    sha256: str

    @field_validator("asset_id", "path", "version", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "mapping asset field")

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value):
        value = _text(value, "mapping_asset.sha256")
        if not _SHA256.fullmatch(value):
            raise ValueError(
                "mapping_asset.sha256 must be 64 lowercase hexadecimal characters"
            )
        return value


class ModelFeatureContract(SchemaObject):
    schema_version: Literal["vc.model-feature-contract.v1"]
    model_id: str
    model_version: str
    taxonomy_id: str
    assembly_accession: str
    modality: str
    feature_namespace: FeatureNamespaceSpec
    feature_id_format: Literal[
        "ensembl_gene",
        "ncbi_gene_curie",
        "uniprot_protein",
    ]
    feature_ids: tuple[str, ...]
    reorder: bool = False
    drop: tuple[str, ...] = ()
    fill: tuple[FillRule, ...] = ()
    mapping_asset: MappingAssetRef | None = None

    @field_validator(
        "model_id",
        "model_version",
        "taxonomy_id",
        "assembly_accession",
        "modality",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "model feature contract field")

    @field_validator("feature_ids", mode="before")
    @classmethod
    def _valid_features(cls, value):
        return _string_tuple(value, "feature_ids", allow_empty=False)

    @field_validator("drop", mode="before")
    @classmethod
    def _valid_drop(cls, value):
        return _string_tuple(value, "drop", allow_empty=True)

    @field_validator("fill", mode="before")
    @classmethod
    def _valid_fill(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("fill must be a JSON array")
        return value

    @field_validator("reorder", mode="before")
    @classmethod
    def _valid_reorder(cls, value):
        if not isinstance(value, bool):
            raise ValueError("reorder must be a boolean")
        return value

    @model_validator(mode="after")
    def _valid_operations(self):
        filled = [value.feature_id for value in self.fill]
        if len(set(filled)) != len(filled):
            raise ValueError("fill feature ids must be unique")
        unknown = set(filled).difference(self.feature_ids)
        if unknown:
            raise ValueError(f"fill feature ids are not model features: {sorted(unknown)}")
        pattern = _FEATURE_IDS[self.feature_id_format]
        for label, values in (
            ("feature_ids", self.feature_ids),
            ("drop", self.drop),
            ("fill", filled),
        ):
            invalid = [value for value in values if not pattern.fullmatch(value)]
            if invalid:
                raise ValueError(
                    f"non-canonical {label} for {self.feature_id_format}: {invalid}"
                )
        return self

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ModelFeatureContract:
        if not isinstance(value, dict):
            raise FeatureAlignmentError("ModelFeatureContract must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise FeatureAlignmentError(
                f"invalid ModelFeatureContract: {exc}"
            ) from exc

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


class _AliasRule(SchemaObject):
    source: str
    target: str

    @field_validator("source", "target", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "alias field")


class _AggregateRule(SchemaObject):
    sources: tuple[str, ...]
    target: str
    reducer: Literal["sum", "mean"]

    @field_validator("sources", mode="before")
    @classmethod
    def _valid_sources(cls, value):
        values = _string_tuple(value, "aggregate.sources", allow_empty=False)
        if len(values) < 2:
            raise ValueError("aggregate.sources must contain at least two features")
        return values

    @field_validator("target", mode="before")
    @classmethod
    def _valid_target(cls, value):
        return _text(value, "aggregate.target")


class _MappingDocument(SchemaObject):
    schema_version: Literal["vc.feature-mapping.v1"]
    mapping_id: str
    mapping_version: str
    aliases: tuple[_AliasRule, ...] = ()
    aggregates: tuple[_AggregateRule, ...] = ()

    @field_validator("mapping_id", "mapping_version", mode="before")
    @classmethod
    def _valid_identity(cls, value):
        return _text(value, "mapping identity")

    @field_validator("aliases", "aggregates", mode="before")
    @classmethod
    def _valid_arrays(cls, value):
        if not isinstance(value, list):
            raise ValueError("mapping rules must be JSON arrays")
        return value

    @model_validator(mode="after")
    def _unique_rules(self):
        alias_sources = [value.source for value in self.aliases]
        aggregate_sources = [
            source for value in self.aggregates for source in value.sources
        ]
        if len(set(alias_sources)) != len(alias_sources):
            raise ValueError("alias sources must be unique")
        if len(set(aggregate_sources)) != len(aggregate_sources):
            raise ValueError("aggregate sources must be unique")
        if set(alias_sources).intersection(aggregate_sources):
            raise ValueError("alias and aggregate sources must not overlap")
        targets = [
            *(value.target for value in self.aliases),
            *(value.target for value in self.aggregates),
        ]
        if len(set(targets)) != len(targets):
            raise ValueError("mapping targets must be unique")
        if not self.aliases and not self.aggregates:
            raise ValueError("mapping asset must declare alias or aggregate rules")
        return self


@dataclass(frozen=True)
class AlignmentStep:
    operation: Literal["alias", "aggregate", "drop", "fill", "reorder"]
    source_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    reducer: str | None = None
    value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "operation": self.operation,
            "source_ids": list(self.source_ids),
            "target_ids": list(self.target_ids),
        }
        if self.reducer is not None:
            value["reducer"] = self.reducer
        if self.value is not None:
            value["value"] = self.value
        return value


@dataclass(frozen=True)
class AlignmentReport:
    schema_version: Literal["vc.alignment-report.v1"]
    contract_fingerprint: str
    source_feature_ids: tuple[str, ...]
    target_feature_ids: tuple[str, ...]
    source_shape: tuple[int, int]
    target_shape: tuple[int, int]
    steps: tuple[AlignmentStep, ...]
    mapping_asset: MappingAssetRef | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_fingerprint": self.contract_fingerprint,
            "source_feature_ids": list(self.source_feature_ids),
            "target_feature_ids": list(self.target_feature_ids),
            "source_shape": list(self.source_shape),
            "target_shape": list(self.target_shape),
            "steps": [value.to_dict() for value in self.steps],
            "mapping_asset": (
                None
                if self.mapping_asset is None
                else self.mapping_asset.model_dump(mode="json")
            ),
        }

    @property
    def provenance(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(frozen=True)
class AlignedFeatureMatrix:
    feature_ids: tuple[str, ...]
    matrix: Any
    report: AlignmentReport


def _json_object(path: Path) -> dict[str, Any]:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise FeatureAlignmentError(
                    f"duplicate key in mapping asset: {key!r}"
                )
            value[key] = item
        return value

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise FeatureAlignmentError(f"cannot read mapping asset: {exc}") from exc
    if not isinstance(value, dict):
        raise FeatureAlignmentError("mapping asset must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _omics_modules():
    try:
        import numpy as np
        from scipy import sparse
    except ImportError as exc:
        raise OmicsDependencyError(
            "feature alignment requires the 'omics' extra"
        ) from exc
    return np, sparse


def _load_mapping(
    reference: MappingAssetRef,
    root: str | Path | None,
) -> _MappingDocument:
    if root is None:
        raise FeatureAlignmentError("mapping_root is required for a mapping asset")
    try:
        pack_root = Path(root).resolve(strict=True)
        manifest_path = resolve_asset_path(pack_root, "manifest.yaml")
        manifest = load_manifest(manifest_path)
        path = resolve_asset_path(pack_root, reference.path)
    except (OSError, VirtualCellPackError) as exc:
        raise FeatureAlignmentError(f"invalid mapping asset path: {exc}") from exc
    declared = next(
        (asset for asset in manifest.assets if asset.id == reference.asset_id),
        None,
    )
    if declared is None:
        raise FeatureAlignmentError(
            f"mapping must be a declared Pack asset: {reference.asset_id!r}"
        )
    if (
        declared.path != reference.path
        or declared.sha256 != reference.sha256
        or declared.media_type != "application/json"
    ):
        raise FeatureAlignmentError(
            "mapping reference does not match its declared Pack asset"
        )
    actual_hash = _sha256(path)
    if actual_hash != reference.sha256:
        raise FeatureAlignmentError(
            f"mapping asset hash mismatch: expected {reference.sha256}, got {actual_hash}"
        )
    if path.stat().st_size != declared.size_bytes:
        raise FeatureAlignmentError("mapping asset size does not match its Pack manifest")
    try:
        mapping = _MappingDocument.model_validate(_json_object(path))
    except ValidationError as exc:
        raise FeatureAlignmentError(f"invalid mapping asset: {exc}") from exc
    if mapping.mapping_id != reference.asset_id:
        raise FeatureAlignmentError("mapping asset id does not match its reference")
    if mapping.mapping_version != reference.version:
        raise FeatureAlignmentError("mapping asset version does not match its reference")
    return mapping


def _materialize(matrix):
    np, sparse = _omics_modules()
    if sparse.issparse(matrix):
        return matrix
    if hasattr(matrix, "to_memory"):
        return matrix.to_memory()
    try:
        value = matrix[...]
    except (TypeError, AttributeError):
        value = matrix
    return value if sparse.issparse(value) else np.asarray(value)


def _aggregate_column(matrix, positions: list[int], reducer: str):
    np, sparse = _omics_modules()
    selected = matrix[:, positions]
    if sparse.issparse(selected):
        column = sparse.csr_matrix(np.asarray(selected.sum(axis=1)))
        if reducer == "mean":
            column = column / len(positions)
        return column
    values = np.asarray(selected)
    result = values.sum(axis=1) if reducer == "sum" else values.mean(axis=1)
    return result.reshape(-1, 1)


def _fill_column(matrix, rows: int, value: float):
    np, sparse = _omics_modules()
    values = np.full((rows, 1), value)
    return sparse.csr_matrix(values) if sparse.issparse(matrix) else values


def _combine_columns(matrix, columns: list[Any]):
    np, sparse = _omics_modules()
    if sparse.issparse(matrix):
        output_format = "csc" if matrix.format == "csc" else "csr"
        return sparse.hstack(columns, format=output_format)
    return np.hstack(columns)


def align_features(
    modality: CanonicalModalityView,
    contract: ModelFeatureContract,
    *,
    mapping_root: str | Path | None = None,
) -> AlignedFeatureMatrix:
    """Align one modality only through operations explicitly declared by a contract."""
    if not isinstance(contract, ModelFeatureContract):
        raise FeatureAlignmentError("contract must be a ModelFeatureContract")
    if modality.taxonomy_id != contract.taxonomy_id:
        raise FeatureAlignmentError(
            "taxonomy mismatch; automatic ortholog conversion is forbidden"
        )
    if modality.assembly_accession != contract.assembly_accession:
        raise FeatureAlignmentError("assembly mismatch")
    if modality.key != contract.modality:
        raise FeatureAlignmentError("modality mismatch")
    if (
        modality.feature_namespace_name != contract.feature_namespace.name
        or modality.feature_namespace_version != contract.feature_namespace.version
        or modality.feature_id_format != contract.feature_id_format
    ):
        raise FeatureAlignmentError(
            "feature namespace mismatch; automatic alias fallback is forbidden"
        )

    mapping = (
        None
        if contract.mapping_asset is None
        else _load_mapping(contract.mapping_asset, mapping_root)
    )
    if mapping is not None:
        mapping_ids = [
            *(value for rule in mapping.aliases for value in (rule.source, rule.target)),
            *(
                value
                for rule in mapping.aggregates
                for value in (*rule.sources, rule.target)
            ),
        ]
        pattern = _FEATURE_IDS[contract.feature_id_format]
        invalid = [value for value in mapping_ids if not pattern.fullmatch(value)]
        if invalid:
            raise FeatureAlignmentError(
                "non-canonical mapping feature ids for "
                f"{contract.feature_id_format}: {invalid}"
            )
    aliases = {} if mapping is None else {value.source: value for value in mapping.aliases}
    aggregate_by_source = {}
    if mapping is not None:
        for rule in mapping.aggregates:
            for source in rule.sources:
                aggregate_by_source[source] = rule

    source_ids = modality.feature_ids
    source_positions = {value: index for index, value in enumerate(source_ids)}
    unknown_drop = set(contract.drop).difference(source_ids)
    if unknown_drop:
        raise FeatureAlignmentError(
            f"drop contains unknown source features: {sorted(unknown_drop)}"
        )
    mapped_sources = set(aliases).union(aggregate_by_source)
    overlapping_drop = set(contract.drop).intersection(mapped_sources)
    if overlapping_drop:
        raise FeatureAlignmentError(
            f"drop cannot overlap alias or aggregate sources: {sorted(overlapping_drop)}"
        )
    unknown_mapping = mapped_sources.difference(source_ids)
    if unknown_mapping:
        raise FeatureAlignmentError(
            f"mapping contains unknown source features: {sorted(unknown_mapping)}"
        )

    matrix = _materialize(modality.matrix)
    entries: list[tuple[str, Any]] = []
    completed_aggregates: set[str] = set()
    for index, source in enumerate(source_ids):
        if source in contract.drop:
            continue
        aggregate = aggregate_by_source.get(source)
        if aggregate is not None:
            if aggregate.target in completed_aggregates:
                continue
            positions = [source_positions[value] for value in aggregate.sources]
            entries.append(
                (
                    aggregate.target,
                    _aggregate_column(matrix, positions, aggregate.reducer),
                )
            )
            completed_aggregates.add(aggregate.target)
            continue
        alias = aliases.get(source)
        target = source if alias is None else alias.target
        entries.append((target, matrix[:, [index]]))

    produced_ids = [value[0] for value in entries]
    if len(set(produced_ids)) != len(produced_ids):
        raise FeatureAlignmentError(
            "duplicate aligned features require an explicit aggregate rule"
        )
    for fill in contract.fill:
        if fill.feature_id in produced_ids:
            raise FeatureAlignmentError(
                f"fill target already exists in source alignment: {fill.feature_id!r}"
            )
        entries.append(
            (
                fill.feature_id,
                _fill_column(matrix, matrix.shape[0], fill.value),
            )
        )
        produced_ids.append(fill.feature_id)

    target_ids = contract.feature_ids
    extras = set(produced_ids).difference(target_ids)
    missing = set(target_ids).difference(produced_ids)
    if extras and missing:
        raise FeatureAlignmentError(
            "feature mismatch requires an explicit alias or aggregate mapping"
        )
    if extras:
        raise FeatureAlignmentError(
            f"source features require explicit drop or aggregate: {sorted(extras)}"
        )
    if missing:
        raise FeatureAlignmentError(
            f"model features require explicit fill or mapping: {sorted(missing)}"
        )

    steps: list[AlignmentStep] = []
    if mapping is not None:
        steps.extend(
            AlignmentStep(
                operation="alias",
                source_ids=(value.source,),
                target_ids=(value.target,),
            )
            for value in mapping.aliases
        )
        steps.extend(
            AlignmentStep(
                operation="aggregate",
                source_ids=value.sources,
                target_ids=(value.target,),
                reducer=value.reducer,
            )
            for value in mapping.aggregates
        )
    if contract.drop:
        steps.append(AlignmentStep(operation="drop", source_ids=contract.drop))
    steps.extend(
        AlignmentStep(
            operation="fill",
            target_ids=(value.feature_id,),
            value=value.value,
        )
        for value in contract.fill
    )

    current_ids = tuple(value[0] for value in entries)
    if current_ids != target_ids:
        if not contract.reorder:
            raise FeatureAlignmentError(
                "feature order differs; reorder must be explicitly enabled"
            )
        by_id = {feature_id: column for feature_id, column in entries}
        entries = [(feature_id, by_id[feature_id]) for feature_id in target_ids]
        steps.append(
            AlignmentStep(
                operation="reorder",
                source_ids=current_ids,
                target_ids=target_ids,
            )
        )

    output = _combine_columns(matrix, [value[1] for value in entries])
    report = AlignmentReport(
        schema_version="vc.alignment-report.v1",
        contract_fingerprint=contract.fingerprint(),
        source_feature_ids=source_ids,
        target_feature_ids=target_ids,
        source_shape=tuple(matrix.shape),
        target_shape=tuple(output.shape),
        steps=tuple(steps),
        mapping_asset=contract.mapping_asset,
    )
    return AlignedFeatureMatrix(
        feature_ids=target_ids,
        matrix=output,
        report=report,
    )
