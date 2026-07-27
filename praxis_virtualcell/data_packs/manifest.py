"""VirtualCellPack v0.1 manifest parsing and canonical fingerprinting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError, field_validator, model_validator
from yaml.constructor import ConstructorError

from praxis_virtualcell.data_packs.errors import PackManifestError
from praxis_virtualcell.data_packs.schema import (
    AssemblySpec,
    AssetSpec,
    ConditionSpec,
    FeatureNamespaceSpec,
    IdentitySpec,
    LicenseSpec,
    ModalitySpec,
    ProvenanceSpec,
    SchemaObject,
    SplitSpec,
    TaxonSpec,
)


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
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
    schema_version: Literal["vc.pack.v0.1"]
    pack_id: str
    pack_version: str
    taxon: TaxonSpec
    assembly: AssemblySpec
    identity: IdentitySpec
    modality: ModalitySpec
    feature_namespace: FeatureNamespaceSpec
    assets: tuple[AssetSpec, ...]
    condition: ConditionSpec
    split: SplitSpec
    provenance: ProvenanceSpec
    license: LicenseSpec

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
    def _unique_assets(self):
        ids = [asset.id for asset in self.assets]
        paths = [asset.path for asset in self.assets]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate asset ids are not allowed")
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate asset paths are not allowed")
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
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


def load_manifest(path: str | Path) -> PackManifest:
    manifest_path = Path(path)
    try:
        value = yaml.load(manifest_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise PackManifestError(f"cannot read Pack manifest {manifest_path}: {exc}") from exc
    return PackManifest.from_dict(value)
