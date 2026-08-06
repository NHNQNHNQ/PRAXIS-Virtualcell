"""Versioned VirtualCellPack manifest parsing and canonical fingerprinting."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError, field_validator, model_validator
from yaml.constructor import ConstructorError

from praxis_virtualcell.data_packs.errors import PackManifestError
from praxis_virtualcell.data_packs.schema import (
    AssemblySpec,
    AssetSpec,
    CellSemanticsSpec,
    ConditionSpec,
    ConditionsSpec,
    FeatureNamespaceSpec,
    FeatureSemanticsSpec,
    IdentitySpec,
    LicenseSpec,
    MatrixSpec,
    ModalitySpec,
    MultiOmicsSpec,
    PerturbationsSpec,
    ProvenanceSpec,
    SchemaObject,
    SplitSpec,
    TaxonSpec,
)

_ASSEMBLY_ACCESSION = re.compile(r"^(?:GCA|GCF)_[0-9]{9}\.[0-9]+$")


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"unhashable mapping key: {key!r}",
                    key_node.start_mark,
                ) from exc
            if key in mapping:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


class PackManifest(SchemaObject):
    schema_version: Literal["vc.pack.v0.1", "vc.pack.v0.2", "vc.pack.v0.3"]
    pack_id: str
    pack_version: str
    taxon: TaxonSpec
    assembly: AssemblySpec
    identity: IdentitySpec
    modality: ModalitySpec | None = None
    feature_namespace: FeatureNamespaceSpec | None = None
    assets: tuple[AssetSpec, ...]
    matrix: MatrixSpec | None = None
    multiomics: MultiOmicsSpec | None = None
    condition: ConditionSpec | None = None
    feature_semantics: FeatureSemanticsSpec | None = None
    cell_semantics: CellSemanticsSpec | None = None
    conditions: ConditionsSpec | None = None
    perturbations: PerturbationsSpec | None = None
    split: SplitSpec
    provenance: ProvenanceSpec
    license: LicenseSpec

    @model_validator(mode="before")
    @classmethod
    def _reject_ambiguous_version_fields(cls, value):
        if not isinstance(value, dict):
            return value
        if "matrix" in value and value["matrix"] is None:
            raise ValueError("matrix must be omitted or an object")
        for field in ("modality", "feature_namespace", "multiomics"):
            if field in value and value[field] is None:
                raise ValueError(f"{field} must be omitted or an object")
        version = value.get("schema_version")
        semantic_fields = (
            "feature_semantics",
            "cell_semantics",
            "conditions",
            "perturbations",
        )
        if version == "vc.pack.v0.1":
            split = value.get("split")
            has_v02_split_fields = isinstance(split, dict) and any(
                field in split for field in ("name", "leakage_guard")
            )
            if (
                any(field in value for field in semantic_fields)
                or "multiomics" in value
                or has_v02_split_fields
            ):
                raise ValueError(
                    "vc.pack.v0.1 must not declare vc.pack.v0.2 semantic fields "
                    "or vc.pack.v0.3 multiomics"
                )
        if version == "vc.pack.v0.2":
            if "multiomics" in value:
                raise ValueError("vc.pack.v0.2 must not declare multiomics")
            if "condition" in value:
                raise ValueError(
                    "vc.pack.v0.2 must not declare the legacy condition field"
                )
            perturbations = value.get("perturbations")
            if isinstance(perturbations, dict) and "target_modality" in perturbations:
                raise ValueError(
                    "vc.pack.v0.2 perturbations must not declare target_modality"
                )
            null_fields = [
                field
                for field in semantic_fields
                if field in value and value[field] is None
            ]
            if null_fields:
                raise ValueError(
                    f"vc.pack.v0.2 semantic fields must be objects: {null_fields}"
                )
        if version == "vc.pack.v0.3":
            forbidden = [
                field
                for field in (
                    "condition",
                    "matrix",
                    "modality",
                    "feature_namespace",
                    "feature_semantics",
                )
                if field in value
            ]
            if forbidden:
                raise ValueError(
                    f"vc.pack.v0.3 must not declare single-modality fields: {forbidden}"
                )
            required = (
                "multiomics",
                "cell_semantics",
                "conditions",
                "perturbations",
            )
            missing = [field for field in required if field not in value]
            if missing:
                raise ValueError(f"vc.pack.v0.3 requires fields: {missing}")
        return value

    @field_validator("pack_id", "pack_version", mode="before")
    @classmethod
    def _valid_identity(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("pack identity fields must be non-empty strings")
        return value

    @field_validator("assets", mode="before")
    @classmethod
    def _valid_assets(cls, value):
        if not isinstance(value, list) or not value:
            raise ValueError("assets must be a non-empty JSON array")
        return value

    @model_validator(mode="after")
    def _validate_contract(self):
        ids = [asset.id for asset in self.assets]
        paths = [asset.path for asset in self.assets]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate asset ids are not allowed")
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate asset paths are not allowed")
        if self.matrix is not None and self.matrix.asset not in ids:
            raise ValueError(f"matrix.asset does not name a declared asset: {self.matrix.asset!r}")
        if self.multiomics is not None and self.multiomics.asset not in ids:
            raise ValueError(
                "multiomics.asset does not name a declared asset: "
                f"{self.multiomics.asset!r}"
            )
        p4 = (
            self.feature_semantics,
            self.cell_semantics,
            self.conditions,
            self.perturbations,
        )
        if self.schema_version == "vc.pack.v0.1":
            if (
                self.condition is None
                or self.modality is None
                or self.feature_namespace is None
            ):
                raise ValueError(
                    "vc.pack.v0.1 requires modality, feature_namespace, and condition"
                )
            if (
                any(value is not None for value in p4)
                or self.multiomics is not None
                or self.split.name
                or self.split.leakage_guard
            ):
                raise ValueError(
                    "vc.pack.v0.1 must not declare vc.pack.v0.2 semantic fields "
                    "or vc.pack.v0.3 multiomics"
                )
            return self
        if self.condition is not None:
            raise ValueError(
                f"{self.schema_version} uses conditions and must not declare legacy condition"
            )
        if any(value is None for value in (self.cell_semantics, self.conditions, self.perturbations)):
            raise ValueError(
                f"{self.schema_version} requires cell_semantics, conditions, and perturbations"
            )
        if not _ASSEMBLY_ACCESSION.fullmatch(self.assembly.accession):
            raise ValueError(
                "assembly.accession must be a versioned GCA_ or GCF_ accession"
            )
        if self.split.name is None:
            raise ValueError("vc.pack.v0.2 requires split.name")
        if not self.split.leakage_guard:
            raise ValueError(
                f"{self.schema_version} requires a non-empty split.leakage_guard"
            )
        if self.schema_version == "vc.pack.v0.2":
            if (
                self.matrix is None
                or self.modality is None
                or self.feature_namespace is None
                or self.feature_semantics is None
            ):
                raise ValueError(
                    "vc.pack.v0.2 requires modality, feature_namespace, matrix, "
                    "and feature_semantics"
                )
            if self.multiomics is not None:
                raise ValueError("vc.pack.v0.2 must not declare multiomics")
            if self.identity.feature_key != "var_names":
                raise ValueError("vc.pack.v0.2 identity.feature_key must be var_names")
            expected_namespace = {
                "ensembl_gene": "EnsemblGene",
                "ncbi_gene_curie": "NCBIGene",
            }.get(self.feature_semantics.id_format)
            if (
                expected_namespace is None
                or self.feature_namespace.name != expected_namespace
            ):
                raise ValueError(
                    "feature_namespace.name does not match feature_semantics.id_format"
                )
            if self.perturbations.target_modality is not None:
                raise ValueError(
                    "vc.pack.v0.2 perturbations must not declare target_modality"
                )
            return self
        if (
            self.multiomics is None
            or self.matrix is not None
            or self.modality is not None
            or self.feature_namespace is not None
            or self.feature_semantics is not None
        ):
            raise ValueError(
                "vc.pack.v0.3 requires multiomics and forbids single-modality mappings"
            )
        if (
            self.identity.observation_key != "obs_names"
            or self.identity.feature_key != "var_names"
        ):
            raise ValueError(
                "vc.pack.v0.3 identity keys must be obs_names and var_names"
            )
        expected_namespaces = {
            "ensembl_gene": "EnsemblGene",
            "ncbi_gene_curie": "NCBIGene",
            "uniprot_protein": "UniProtKB",
        }
        for modality in self.multiomics.modalities:
            if (
                modality.feature_namespace.name
                != expected_namespaces[modality.feature_semantics.id_format]
            ):
                raise ValueError(
                    "multiomics feature_namespace.name does not match "
                    "feature_semantics.id_format"
                )
        keys = {value.key for value in self.multiomics.modalities}
        if self.perturbations.target_modality not in keys:
            raise ValueError(
                "perturbations.target_modality must name a declared modality"
            )
        return self

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PackManifest:
        if not isinstance(value, dict):
            raise PackManifestError("Pack manifest must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise PackManifestError(f"invalid Pack manifest: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        value = self.model_dump(mode="json")
        for field in (
            "modality",
            "feature_namespace",
            "matrix",
            "multiomics",
            "condition",
            "feature_semantics",
            "cell_semantics",
            "conditions",
            "perturbations",
        ):
            if value[field] is None:
                value.pop(field)
        if self.schema_version == "vc.pack.v0.1":
            value["split"].pop("name")
            value["split"].pop("leakage_guard")
        if self.schema_version == "vc.pack.v0.2":
            value["perturbations"].pop("target_modality")
        return value

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


def load_manifest_bytes(payload: bytes) -> PackManifest:
    """Parse one manifest from already-authenticated bytes."""

    if type(payload) is not bytes:
        raise PackManifestError("Pack manifest payload must be bytes")
    try:
        value = yaml.load(payload.decode("utf-8"), Loader=_UniqueKeyLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PackManifestError(f"cannot parse Pack manifest: {exc}") from exc
    return PackManifest.from_dict(value)


def load_manifest(path: str | Path) -> PackManifest:
    manifest_path = Path(path)
    try:
        payload = manifest_path.read_bytes()
    except OSError as exc:
        raise PackManifestError(f"cannot read Pack manifest {manifest_path}: {exc}") from exc
    try:
        return load_manifest_bytes(payload)
    except PackManifestError as exc:
        raise PackManifestError(f"cannot read Pack manifest {manifest_path}: {exc}") from exc
