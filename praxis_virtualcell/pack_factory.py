"""Controlled, contract-only authoring and registration for uploaded Packs.

The factory never infers biological truth, transforms matrices, trains models, or
creates scientific evidence or product policy.  It binds an existing P7
quarantine receipt to an operator-authored v0.2/v0.3 Pack candidate, requires an
explicit metadata review, emits a complete deterministic validation report, and
only then accepts a separate named operator registration decision.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.data_packs.errors import VirtualCellPackError
from praxis_virtualcell.data_packs.manifest import PackManifest, load_manifest
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.data_packs.validator import resolve_asset_path

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_SECONDS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_STORE_MARKER_NAME = ".factory-store.json"
_STORE_MARKER_BYTES = b'{"schema_version":"vc.pack-factory-store.v1"}\n'
REQUIRED_REVIEW_TOPICS = (
    "taxon",
    "assembly",
    "cell_identity",
    "modality",
    "feature_namespace",
    "value_semantics",
    "condition",
    "control",
    "unit",
    "split",
    "leakage_group",
    "feature_mapping",
)
_VALIDATION_CHECKS = (
    "explicit_metadata_review",
    "receipt_bytes_immutable",
    "candidate_tree_immutable",
    "modern_pack_schema",
    "source_payload_binding",
    "taxon_review_binding",
    "metadata_manifest_binding",
    "strict_pack_registry_validation",
    "metadata_unit_binding",
    "feature_mapping_binding",
    "declared_files_only",
    "no_forbidden_transformations",
)


class PackFactoryError(ValueError):
    """A controlled Pack Factory contract or transition failed closed."""


def _canonical_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", serialize_as_any=True)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PackFactoryError("value is not canonical JSON") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _sha256(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _canonical_relative_path(value: Any, field: str) -> str:
    value = _text(value, field)
    relative = PurePosixPath(value)
    if (
        "\\" in value
        or relative.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or not relative.parts
        or any(part in (".", "..") for part in relative.parts)
        or str(relative) != value
    ):
        raise ValueError(f"{field} must be a canonical relative POSIX path")
    return value


def _utc_seconds(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _UTC_SECONDS.fullmatch(value):
        raise ValueError(f"{field} must be canonical UTC seconds ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        raise ValueError(f"{field} must be canonical UTC seconds ending in Z")
    return value


def _duplicate_key_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PackFactoryError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _json_object_bytes(payload: bytes, field: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_duplicate_key_object)
    except (UnicodeDecodeError, json.JSONDecodeError, PackFactoryError) as exc:
        raise PackFactoryError(f"invalid {field} JSON") from exc
    if type(value) is not dict:
        raise PackFactoryError(f"{field} must contain a JSON object")
    return value


def _reject_undeclared_fields(value: Any, path: str) -> None:
    if isinstance(value, BaseModel):
        declared = type(value).model_fields
        unexpected = set(value.__dict__).difference(declared)
        pydantic_extra = getattr(value, "__pydantic_extra__", None)
        if pydantic_extra:
            unexpected.update(pydantic_extra)
        if unexpected:
            raise ValueError(f"{path} contains undeclared fields: {sorted(unexpected)}")
        for name in declared:
            _reject_undeclared_fields(getattr(value, name), f"{path}.{name}")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_undeclared_fields(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_undeclared_fields(item, f"{path}[{index}]")


def _same_model_shape(value: Any, normalized: Any, path: str) -> None:
    if isinstance(normalized, BaseModel):
        if type(value) is not type(normalized):
            raise TypeError(f"{path} has non-canonical model type")
        for name in type(normalized).model_fields:
            _same_model_shape(getattr(value, name), getattr(normalized, name), f"{path}.{name}")
    elif isinstance(normalized, tuple):
        if type(value) is not tuple or len(value) != len(normalized):
            raise TypeError(f"{path} has non-canonical array type")
        for index, (item, expected) in enumerate(zip(value, normalized, strict=True)):
            _same_model_shape(item, expected, f"{path}[{index}]")
    elif type(value) is not type(normalized) or value != normalized:
        raise TypeError(f"{path} has non-canonical value type")


_ContractT = TypeVar("_ContractT", bound="_FactoryContract")


def _revalidate(value: Any, expected: type[_ContractT], field: str) -> _ContractT:
    if type(value) is not expected:
        raise PackFactoryError(f"{field} must be exact {expected.__name__}")
    try:
        _reject_undeclared_fields(value, field)
        normalized = expected.model_validate(value.model_dump(mode="python", serialize_as_any=True))
        _same_model_shape(value, normalized, field)
        return normalized
    except (AttributeError, TypeError, ValidationError, ValueError) as exc:
        raise PackFactoryError(f"invalid {field}") from exc


class _FactoryContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls: type[_ContractT], value: dict[str, Any]) -> _ContractT:
        if type(value) is not dict:
            raise PackFactoryError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise PackFactoryError(f"invalid {cls.__name__}: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        _reject_undeclared_fields(self, type(self).__name__)
        return self.model_dump(mode="json", serialize_as_any=True)

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


class UploadReceiptV1(_FactoryContract):
    schema_version: Literal["vc.upload-receipt.v1"]
    upload_id: str
    status: Literal["quarantined"]
    species: Literal["human", "mouse", "yeast", "bacteria"]
    filename: str
    size_bytes: int
    sha256: str
    declared_content_type: str | None
    created_at: str

    @field_validator("upload_id", mode="before")
    @classmethod
    def _valid_upload_id(cls, value):
        value = _text(value, "upload_id")
        try:
            parsed = uuid.UUID(value)
        except ValueError as exc:
            raise ValueError("upload_id must be a canonical UUID") from exc
        if parsed.version != 4 or str(parsed) != value:
            raise ValueError("upload_id must be a canonical UUIDv4")
        return value

    @field_validator("filename", mode="before")
    @classmethod
    def _valid_filename(cls, value):
        value = _text(value, "filename")
        if PurePosixPath(value).name != value or PureWindowsPath(value).name != value:
            raise ValueError("filename must be a basename")
        if any(ord(char) < 32 for char in value):
            raise ValueError("filename must not contain control characters")
        return value

    @field_validator("size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        return _positive_int(value, "size_bytes")

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value):
        return _sha256(value, "sha256")

    @field_validator("declared_content_type", mode="before")
    @classmethod
    def _valid_content_type(cls, value):
        return None if value is None else _text(value, "declared_content_type")

    @field_validator("created_at", mode="before")
    @classmethod
    def _valid_created_at(cls, value):
        return _utc_seconds(value, "created_at")


@dataclass(frozen=True)
class QuarantinedUpload:
    receipt: UploadReceiptV1
    directory: Path
    receipt_bytes_sha256: str


def load_quarantined_upload(upload_directory: str | Path) -> QuarantinedUpload:
    """Load and re-hash an exact P7 quarantine receipt without changing bytes."""

    path = Path(upload_directory)
    try:
        if path.is_symlink():
            raise PackFactoryError("upload directory must not be a symlink")
        directory = path.resolve(strict=True)
        if not directory.is_dir():
            raise PackFactoryError("upload directory must be a directory")
        entries = {item.name for item in directory.iterdir()}
    except OSError as exc:
        raise PackFactoryError("upload directory is unavailable") from exc
    if entries != {"payload", "receipt.json"}:
        raise PackFactoryError("completed upload directory must contain only payload and receipt.json")

    payload_path = directory / "payload"
    receipt_path = directory / "receipt.json"
    for candidate, label in ((payload_path, "payload"), (receipt_path, "receipt")):
        try:
            file_stat = candidate.lstat()
        except OSError as exc:
            raise PackFactoryError(f"upload {label} is unavailable") from exc
        if not stat.S_ISREG(file_stat.st_mode) or candidate.is_symlink():
            raise PackFactoryError(f"upload {label} must be a regular non-symlink file")

    try:
        receipt_bytes = receipt_path.read_bytes()
    except OSError as exc:
        raise PackFactoryError("cannot read upload receipt") from exc
    if not receipt_bytes or len(receipt_bytes) > 64 * 1024:
        raise PackFactoryError("upload receipt has an invalid size")
    receipt = UploadReceiptV1.from_dict(_json_object_bytes(receipt_bytes, "upload receipt"))
    if receipt.upload_id != directory.name:
        raise PackFactoryError("upload receipt id does not match its quarantine directory")
    actual_size = payload_path.stat().st_size
    actual_hash = _hash_file(payload_path)
    if actual_size != receipt.size_bytes or actual_hash != receipt.sha256:
        raise PackFactoryError("upload payload does not match its immutable receipt")
    return QuarantinedUpload(
        receipt=receipt,
        directory=directory,
        receipt_bytes_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
    )


class CandidateFileIdentityV1(_FactoryContract):
    schema_version: Literal["vc.pack-candidate-file.v1"]
    path: str
    size_bytes: int
    sha256: str

    @field_validator("path", mode="before")
    @classmethod
    def _valid_path(cls, value):
        return _canonical_relative_path(value, "candidate file path")

    @field_validator("size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        return _positive_int(value, "candidate file size")

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value):
        return _sha256(value, "candidate file sha256")


class MappingNamespaceV1(_FactoryContract):
    schema_version: Literal["vc.pack-factory-mapping-namespace.v1"]
    name: str
    version: str

    @field_validator("name", "version", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)


class FeatureMappingEntryV1(_FactoryContract):
    schema_version: Literal["vc.pack-factory-feature-map-entry.v1"]
    source: str
    target: str

    @field_validator("source", "target", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)


class FeatureMappingDocumentV1(_FactoryContract):
    schema_version: Literal["vc.pack-factory-feature-mapping.v1"]
    mapping_id: str
    mapping_version: str
    modality_key: str
    source_namespace: MappingNamespaceV1
    target_namespace: MappingNamespaceV1
    source_feature_ids: tuple[str, ...]
    target_feature_ids: tuple[str, ...]
    mappings: tuple[FeatureMappingEntryV1, ...]

    @field_validator("mapping_id", "mapping_version", "modality_key", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("source_feature_ids", "target_feature_ids", mode="before")
    @classmethod
    def _valid_features(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be a non-empty array")
        return tuple(_text(item, info.field_name) for item in value)

    @field_validator("mappings", mode="before")
    @classmethod
    def _valid_mappings(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("mappings must be an array")
        return tuple(value)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(duplicates)


class FeatureMappingSummaryV1(_FactoryContract):
    schema_version: Literal["vc.pack-factory-feature-mapping-summary.v1"]
    modality_key: str
    mapping_id: str
    mapping_version: str
    asset_id: str
    asset_path: str
    asset_sha256: str
    asset_size_bytes: int
    document_fingerprint: str
    source_namespace: MappingNamespaceV1
    target_namespace: MappingNamespaceV1
    source_feature_count: int
    target_feature_count: int
    source_order_fingerprint: str
    target_order_fingerprint: str
    duplicate_source_feature_ids: tuple[str, ...]
    duplicate_target_feature_ids: tuple[str, ...]
    duplicate_mapping_sources: tuple[str, ...]
    duplicate_mapping_targets: tuple[str, ...]
    out_of_domain_mapping_sources: tuple[str, ...]
    out_of_domain_mapping_targets: tuple[str, ...]
    unmapped_source_feature_ids: tuple[str, ...]
    unmapped_target_feature_ids: tuple[str, ...]
    order_preserved: bool
    transformation_policy: Literal["identity_only_no_transform"]

    @field_validator("modality_key", "mapping_id", "mapping_version", "asset_id", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("asset_path", mode="before")
    @classmethod
    def _valid_path(cls, value):
        return _canonical_relative_path(value, "mapping asset path")

    @field_validator(
        "asset_sha256",
        "document_fingerprint",
        "source_order_fingerprint",
        "target_order_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator(
        "asset_size_bytes",
        "source_feature_count",
        "target_feature_count",
        mode="before",
    )
    @classmethod
    def _valid_counts(cls, value, info):
        return _positive_int(value, info.field_name)

    @field_validator(
        "duplicate_source_feature_ids",
        "duplicate_target_feature_ids",
        "duplicate_mapping_sources",
        "duplicate_mapping_targets",
        "out_of_domain_mapping_sources",
        "out_of_domain_mapping_targets",
        "unmapped_source_feature_ids",
        "unmapped_target_feature_ids",
        mode="before",
    )
    @classmethod
    def _valid_issue_ids(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        values = tuple(_text(item, info.field_name) for item in value)
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return values

    @field_validator("order_preserved", mode="before")
    @classmethod
    def _valid_order(cls, value):
        if type(value) is not bool:
            raise ValueError("order_preserved must be an exact boolean")
        return value


def _mapping_summary(
    root: Path,
    manifest: PackManifest,
    asset_id: str,
) -> FeatureMappingSummaryV1:
    assets = {asset.id: asset for asset in manifest.assets}
    try:
        asset = assets[asset_id]
    except KeyError as exc:
        raise PackFactoryError(f"mapping is not a declared Pack asset: {asset_id!r}") from exc
    if asset.media_type != "application/json":
        raise PackFactoryError("factory feature mapping must be an application/json Pack asset")
    path = resolve_asset_path(root, asset.path)
    actual_size = path.stat().st_size
    actual_hash = _hash_file(path)
    if actual_size != asset.size_bytes or actual_hash != asset.sha256:
        raise PackFactoryError("mapping asset does not match its manifest identity")
    document = FeatureMappingDocumentV1.from_dict(_json_object_bytes(path.read_bytes(), "feature mapping"))
    source_duplicates = _duplicates(document.source_feature_ids)
    target_duplicates = _duplicates(document.target_feature_ids)
    mapping_sources = tuple(item.source for item in document.mappings)
    mapping_targets = tuple(item.target for item in document.mappings)
    mapping_source_duplicates = _duplicates(mapping_sources)
    mapping_target_duplicates = _duplicates(mapping_targets)
    source_features = set(document.source_feature_ids)
    target_features = set(document.target_feature_ids)
    out_of_domain_sources = tuple(value for value in dict.fromkeys(mapping_sources) if value not in source_features)
    out_of_domain_targets = tuple(value for value in dict.fromkeys(mapping_targets) if value not in target_features)
    mapping = (
        {}
        if mapping_source_duplicates or mapping_target_duplicates
        else {item.source: item.target for item in document.mappings}
    )
    same_namespace = document.source_namespace == document.target_namespace
    resolved: list[str] = []
    unmapped_source: list[str] = []
    for feature_id in document.source_feature_ids:
        target = mapping.get(feature_id)
        if target is None and same_namespace:
            target = feature_id
        if target is None:
            if feature_id not in unmapped_source:
                unmapped_source.append(feature_id)
            continue
        resolved.append(target)
    target_set = set(resolved)
    unmapped_target = tuple(value for value in document.target_feature_ids if value not in target_set)
    return FeatureMappingSummaryV1(
        schema_version="vc.pack-factory-feature-mapping-summary.v1",
        modality_key=document.modality_key,
        mapping_id=document.mapping_id,
        mapping_version=document.mapping_version,
        asset_id=asset.id,
        asset_path=asset.path,
        asset_sha256=actual_hash,
        asset_size_bytes=actual_size,
        document_fingerprint=document.fingerprint(),
        source_namespace=document.source_namespace,
        target_namespace=document.target_namespace,
        source_feature_count=len(document.source_feature_ids),
        target_feature_count=len(document.target_feature_ids),
        source_order_fingerprint=_fingerprint(list(document.source_feature_ids)),
        target_order_fingerprint=_fingerprint(list(document.target_feature_ids)),
        duplicate_source_feature_ids=source_duplicates,
        duplicate_target_feature_ids=target_duplicates,
        duplicate_mapping_sources=mapping_source_duplicates,
        duplicate_mapping_targets=mapping_target_duplicates,
        out_of_domain_mapping_sources=out_of_domain_sources,
        out_of_domain_mapping_targets=out_of_domain_targets,
        unmapped_source_feature_ids=tuple(unmapped_source),
        unmapped_target_feature_ids=unmapped_target,
        order_preserved=tuple(resolved) == document.target_feature_ids,
        transformation_policy="identity_only_no_transform",
    )


class MetadataClaimV1(_FactoryContract):
    schema_version: Literal["vc.pack-factory-metadata-claim.v1"]
    topic: Literal[
        "taxon",
        "assembly",
        "cell_identity",
        "modality",
        "feature_namespace",
        "value_semantics",
        "condition",
        "control",
        "unit",
        "split",
        "leakage_group",
        "feature_mapping",
    ]
    origin: Literal["operator_declared", "inferred_candidate"]
    value_json: str
    value_fingerprint: str

    @field_validator("value_json", mode="before")
    @classmethod
    def _valid_json(cls, value):
        value = _text(value, "value_json")
        try:
            parsed = json.loads(value, object_pairs_hook=_duplicate_key_object)
        except (json.JSONDecodeError, PackFactoryError) as exc:
            raise ValueError("value_json must be canonical JSON") from exc
        if _canonical_bytes(parsed).decode("utf-8") != value:
            raise ValueError("value_json must use canonical JSON encoding")
        return value

    @field_validator("value_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _sha256(value, "value_fingerprint")

    @model_validator(mode="after")
    def _self_bound(self):
        if hashlib.sha256(self.value_json.encode("utf-8")).hexdigest() != self.value_fingerprint:
            raise ValueError("metadata claim fingerprint does not match value_json")
        return self


def _claim(topic: str, value: Any, origin: str) -> MetadataClaimV1:
    value_json = _canonical_bytes(value).decode("utf-8")
    return MetadataClaimV1(
        schema_version="vc.pack-factory-metadata-claim.v1",
        topic=topic,
        origin=origin,
        value_json=value_json,
        value_fingerprint=hashlib.sha256(value_json.encode("utf-8")).hexdigest(),
    )


class PackCandidateV1(_FactoryContract):
    schema_version: Literal["vc.pack-candidate.v1"]
    receipt_fingerprint: str
    receipt_bytes_sha256: str
    upload_id: str
    source_payload_sha256: str
    source_payload_size_bytes: int
    source_asset_id: str
    source_asset_path: str
    pack_id: str
    pack_version: str
    manifest_schema_version: Literal["vc.pack.v0.2", "vc.pack.v0.3"]
    manifest_fingerprint: str
    candidate_files: tuple[CandidateFileIdentityV1, ...]
    candidate_tree_fingerprint: str
    metadata_claims: tuple[MetadataClaimV1, ...]
    feature_mappings: tuple[FeatureMappingSummaryV1, ...]
    status: Literal["candidate_unvalidated"]
    pack_valid: None
    normalization_performed: Literal[False]
    fill_performed: Literal[False]
    imputation_performed: Literal[False]
    deduplication_performed: Literal[False]
    reordering_performed: Literal[False]
    random_split_performed: Literal[False]
    identifier_conversion_performed: Literal[False]
    training_performed: Literal[False]
    checkpoint_created: Literal[False]
    evidence_created: Literal[False]
    promotion_created: Literal[False]

    @field_validator(
        "receipt_fingerprint",
        "receipt_bytes_sha256",
        "source_payload_sha256",
        "manifest_fingerprint",
        "candidate_tree_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator(
        "upload_id",
        "source_asset_id",
        "pack_id",
        "pack_version",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("source_asset_path", mode="before")
    @classmethod
    def _valid_source_path(cls, value):
        return _canonical_relative_path(value, "source_asset_path")

    @field_validator("source_payload_size_bytes", mode="before")
    @classmethod
    def _valid_source_size(cls, value):
        return _positive_int(value, "source_payload_size_bytes")

    @field_validator("candidate_files", "metadata_claims", "feature_mappings", mode="before")
    @classmethod
    def _valid_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be a non-empty array")
        return tuple(value)

    @model_validator(mode="after")
    def _self_bound(self):
        paths = tuple(item.path for item in self.candidate_files)
        if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise ValueError("candidate files must be unique and sorted by path")
        expected_tree = _fingerprint([item.to_dict() for item in self.candidate_files])
        if expected_tree != self.candidate_tree_fingerprint:
            raise ValueError("candidate tree fingerprint is stale")
        topics = tuple(item.topic for item in self.metadata_claims)
        if topics != REQUIRED_REVIEW_TOPICS:
            raise ValueError("candidate metadata claims must use the complete canonical topic order")
        modality_keys = tuple(item.modality_key for item in self.feature_mappings)
        if len(set(modality_keys)) != len(modality_keys):
            raise ValueError("candidate feature mapping modalities must be unique")
        return self


@dataclass(frozen=True)
class PreparedPackCandidate:
    upload: QuarantinedUpload
    root: Path
    candidate: PackCandidateV1


def _validate_candidate_receipt_binding(
    upload: QuarantinedUpload,
    candidate: PackCandidateV1,
) -> None:
    expected = (
        upload.receipt.fingerprint(),
        upload.receipt_bytes_sha256,
        upload.receipt.upload_id,
        upload.receipt.sha256,
        upload.receipt.size_bytes,
    )
    actual = (
        candidate.receipt_fingerprint,
        candidate.receipt_bytes_sha256,
        candidate.upload_id,
        candidate.source_payload_sha256,
        candidate.source_payload_size_bytes,
    )
    if actual != expected:
        raise PackFactoryError("candidate does not bind the exact supplied upload identity")


def _snapshot_tree(root: Path) -> tuple[CandidateFileIdentityV1, ...]:
    files: list[CandidateFileIdentityV1] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in names:
            child = directory_path / name
            if child.is_symlink() or not stat.S_ISDIR(child.lstat().st_mode):
                raise PackFactoryError("candidate directories must be real directories")
        for filename in filenames:
            path = directory_path / filename
            file_stat = path.lstat()
            if path.is_symlink() or not stat.S_ISREG(file_stat.st_mode):
                raise PackFactoryError("candidate files must be regular non-symlink files")
            relative = path.relative_to(root).as_posix()
            files.append(
                CandidateFileIdentityV1(
                    schema_version="vc.pack-candidate-file.v1",
                    path=relative,
                    size_bytes=file_stat.st_size,
                    sha256=_hash_file(path),
                )
            )
    files.sort(key=lambda item: item.path)
    if not files or files[0].path != "manifest.yaml":
        if not any(item.path == "manifest.yaml" for item in files):
            raise PackFactoryError("candidate must contain manifest.yaml")
    return tuple(files)


def _modality_keys(manifest: PackManifest) -> tuple[str, ...]:
    if manifest.schema_version == "vc.pack.v0.2":
        return ("primary",)
    assert manifest.multiomics is not None
    return tuple(item.key for item in manifest.multiomics.modalities)


def _primary_data_asset_id(manifest: PackManifest) -> str:
    if manifest.schema_version == "vc.pack.v0.2":
        assert manifest.matrix is not None
        return manifest.matrix.asset
    assert manifest.multiomics is not None
    return manifest.multiomics.asset


def _manifest_claim_values(
    manifest: PackManifest,
    mappings: tuple[FeatureMappingSummaryV1, ...],
    value_semantics: Mapping[str, str],
    units: Mapping[str, tuple[str, ...]],
) -> dict[str, Any]:
    assert manifest.cell_semantics is not None
    assert manifest.conditions is not None
    assert manifest.perturbations is not None
    if manifest.schema_version == "vc.pack.v0.2":
        modality = {"primary": manifest.modality.model_dump(mode="json")}
        namespace = {"primary": manifest.feature_namespace.model_dump(mode="json")}
    else:
        assert manifest.multiomics is not None
        modality = {item.key: item.modality.model_dump(mode="json") for item in manifest.multiomics.modalities}
        namespace = {
            item.key: item.feature_namespace.model_dump(mode="json") for item in manifest.multiomics.modalities
        }
    controls = [item.model_dump(mode="json") for item in manifest.perturbations.values if item.kind == "control"]
    return {
        "taxon": manifest.taxon.model_dump(mode="json"),
        "assembly": manifest.assembly.model_dump(mode="json"),
        "cell_identity": manifest.cell_semantics.model_dump(mode="json"),
        "modality": modality,
        "feature_namespace": namespace,
        "value_semantics": dict(value_semantics),
        "condition": manifest.conditions.model_dump(mode="json"),
        "control": controls,
        "unit": {key: list(value) for key, value in units.items()},
        "split": manifest.split.model_dump(mode="json"),
        "leakage_group": list(manifest.split.leakage_guard),
        "feature_mapping": [item.to_dict() for item in mappings],
    }


def _valid_declared_mapping(
    value: Mapping[str, Any],
    *,
    keys: tuple[str, ...],
    field: str,
) -> dict[str, Any]:
    if type(value) is not dict or tuple(value) != keys:
        raise PackFactoryError(f"{field} keys must equal the ordered modality keys: {list(keys)}")
    result = {}
    for key, item in value.items():
        result[key] = _text(item, f"{field}.{key}")
    return result


def _valid_units(value: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    if type(value) is not dict or tuple(value) != ("dose_units", "time_units"):
        raise PackFactoryError("units must contain ordered dose_units and time_units")
    result: dict[str, tuple[str, ...]] = {}
    for key, items in value.items():
        if not isinstance(items, (list, tuple)) or not items:
            raise PackFactoryError(f"units.{key} must be a non-empty array")
        values = tuple(_text(item, f"units.{key}") for item in items)
        if len(set(values)) != len(values) or values != tuple(sorted(values)):
            raise PackFactoryError(f"units.{key} must be unique and canonically sorted")
        result[key] = values
    return result


def prepare_pack_candidate(
    upload: QuarantinedUpload,
    pack_root: str | Path,
    *,
    source_asset_id: str,
    mapping_asset_ids: Mapping[str, str],
    value_semantics: Mapping[str, str],
    units: Mapping[str, tuple[str, ...] | list[str]],
    claim_origins: Mapping[str, Literal["operator_declared", "inferred_candidate"]],
) -> PreparedPackCandidate:
    """Bind an operator-authored Pack root to an exact immutable upload receipt."""

    if type(upload) is not QuarantinedUpload:
        raise PackFactoryError("upload must be exact QuarantinedUpload")
    verified = load_quarantined_upload(upload.directory)
    if verified != upload:
        raise PackFactoryError("upload receipt or bytes changed before candidate authoring")
    path = Path(pack_root)
    try:
        if path.is_symlink():
            raise PackFactoryError("candidate root must not be a symlink")
        root = path.resolve(strict=True)
    except OSError as exc:
        raise PackFactoryError("candidate root is unavailable") from exc
    if not root.is_dir():
        raise PackFactoryError("candidate root must be a directory")
    manifest = load_manifest(root / "manifest.yaml")
    if manifest.schema_version not in {"vc.pack.v0.2", "vc.pack.v0.3"}:
        raise PackFactoryError("controlled candidates require vc.pack.v0.2 or vc.pack.v0.3")
    modality_keys = _modality_keys(manifest)
    if type(mapping_asset_ids) is not dict or tuple(mapping_asset_ids) != modality_keys:
        raise PackFactoryError("mapping_asset_ids must match ordered candidate modalities")
    mappings = tuple(
        _mapping_summary(root, manifest, _text(mapping_asset_ids[key], "mapping asset id")) for key in modality_keys
    )
    if tuple(item.modality_key for item in mappings) != modality_keys:
        raise PackFactoryError("mapping documents must match ordered candidate modalities")
    semantics = _valid_declared_mapping(
        value_semantics,
        keys=modality_keys,
        field="value_semantics",
    )
    unit_values = _valid_units(units)
    if type(claim_origins) is not dict or tuple(claim_origins) != REQUIRED_REVIEW_TOPICS:
        raise PackFactoryError("claim_origins must explicitly cover every canonical review topic")
    origins = {}
    for topic, origin in claim_origins.items():
        if origin not in {"operator_declared", "inferred_candidate"}:
            raise PackFactoryError(f"invalid claim origin for {topic}")
        origins[topic] = origin

    assets = {asset.id: asset for asset in manifest.assets}
    requested_source_asset_id = _text(source_asset_id, "source_asset_id")
    if requested_source_asset_id != _primary_data_asset_id(manifest):
        raise PackFactoryError("source payload must be the actual matrix or multiomics data asset")
    try:
        source_asset = assets[requested_source_asset_id]
    except KeyError as exc:
        raise PackFactoryError("source payload must name a declared Pack asset") from exc
    source_path = resolve_asset_path(root, source_asset.path)
    if (
        source_asset.size_bytes != verified.receipt.size_bytes
        or source_asset.sha256 != verified.receipt.sha256
        or source_path.stat().st_size != verified.receipt.size_bytes
        or _hash_file(source_path) != verified.receipt.sha256
    ):
        raise PackFactoryError("candidate source asset must preserve exact upload payload bytes")

    files = _snapshot_tree(root)
    claim_values = _manifest_claim_values(manifest, mappings, semantics, unit_values)
    claims = tuple(_claim(topic, claim_values[topic], origins[topic]) for topic in REQUIRED_REVIEW_TOPICS)
    candidate = PackCandidateV1(
        schema_version="vc.pack-candidate.v1",
        receipt_fingerprint=verified.receipt.fingerprint(),
        receipt_bytes_sha256=verified.receipt_bytes_sha256,
        upload_id=verified.receipt.upload_id,
        source_payload_sha256=verified.receipt.sha256,
        source_payload_size_bytes=verified.receipt.size_bytes,
        source_asset_id=source_asset.id,
        source_asset_path=source_asset.path,
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
        manifest_schema_version=manifest.schema_version,
        manifest_fingerprint=manifest.fingerprint(),
        candidate_files=files,
        candidate_tree_fingerprint=_fingerprint([item.to_dict() for item in files]),
        metadata_claims=claims,
        feature_mappings=mappings,
        status="candidate_unvalidated",
        pack_valid=None,
        normalization_performed=False,
        fill_performed=False,
        imputation_performed=False,
        deduplication_performed=False,
        reordering_performed=False,
        random_split_performed=False,
        identifier_conversion_performed=False,
        training_performed=False,
        checkpoint_created=False,
        evidence_created=False,
        promotion_created=False,
    )
    return PreparedPackCandidate(upload=verified, root=root, candidate=candidate)


def bind_pack_candidate(
    upload: QuarantinedUpload,
    pack_root: str | Path,
    candidate: PackCandidateV1,
) -> PreparedPackCandidate:
    """Rebind serialized candidate identity to runtime paths; no validation state is promoted."""

    candidate = _revalidate(candidate, PackCandidateV1, "candidate")
    if type(upload) is not QuarantinedUpload:
        raise PackFactoryError("upload must be exact QuarantinedUpload")
    path = Path(pack_root)
    if path.is_symlink():
        raise PackFactoryError("candidate root must be a real directory")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise PackFactoryError("candidate root must be a real directory")
    verified = load_quarantined_upload(upload.directory)
    if verified != upload:
        raise PackFactoryError("upload receipt or bytes changed before candidate binding")
    _validate_candidate_receipt_binding(verified, candidate)
    return PreparedPackCandidate(upload=verified, root=root, candidate=candidate)


class MetadataConfirmationV1(_FactoryContract):
    schema_version: Literal["vc.pack-factory-metadata-confirmation.v1"]
    topic: Literal[
        "taxon",
        "assembly",
        "cell_identity",
        "modality",
        "feature_namespace",
        "value_semantics",
        "condition",
        "control",
        "unit",
        "split",
        "leakage_group",
        "feature_mapping",
    ]
    claim_fingerprint: str
    status: Literal["confirmed", "rejected"]

    @field_validator("claim_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _sha256(value, "claim_fingerprint")


class PackMetadataReviewV1(_FactoryContract):
    schema_version: Literal["vc.pack-metadata-review.v1"]
    candidate_fingerprint: str
    reviewer_id: str
    reviewer_role: Literal["metadata_reviewer"]
    reviewed_at: str
    decision: Literal["approve_for_strict_validation", "reject"]
    rationale: str
    confirmations: tuple[MetadataConfirmationV1, ...]
    scientific_validation_performed: Literal[False]
    product_policy_created: Literal[False]

    @field_validator("candidate_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _sha256(value, "candidate_fingerprint")

    @field_validator("reviewer_id", "rationale", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _utc_seconds(value, "reviewed_at")

    @field_validator("confirmations", mode="before")
    @classmethod
    def _valid_confirmations(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("confirmations must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _valid_decision(self):
        topics = tuple(item.topic for item in self.confirmations)
        if len(set(topics)) != len(topics):
            raise ValueError("review confirmation topics must be unique")
        if self.decision == "approve_for_strict_validation":
            if topics != REQUIRED_REVIEW_TOPICS:
                raise ValueError("approved metadata review must confirm every topic in canonical order")
            if any(item.status != "confirmed" for item in self.confirmations):
                raise ValueError("approved metadata review cannot contain rejected confirmations")
        return self


def validate_metadata_review(
    prepared: PreparedPackCandidate,
    review: PackMetadataReviewV1,
) -> PackMetadataReviewV1:
    if type(prepared) is not PreparedPackCandidate:
        raise PackFactoryError("prepared must be exact PreparedPackCandidate")
    candidate = _revalidate(prepared.candidate, PackCandidateV1, "candidate")
    review = _revalidate(review, PackMetadataReviewV1, "metadata review")
    if review.candidate_fingerprint != candidate.fingerprint():
        raise PackFactoryError("metadata review does not bind the exact candidate")
    claims = {item.topic: item.fingerprint() for item in candidate.metadata_claims}
    for confirmation in review.confirmations:
        if confirmation.claim_fingerprint != claims[confirmation.topic]:
            raise PackFactoryError(f"metadata confirmation does not bind candidate claim: {confirmation.topic}")
    return review


class PackValidationCheckV1(_FactoryContract):
    schema_version: Literal["vc.pack-validation-check.v1"]
    code: Literal[
        "explicit_metadata_review",
        "receipt_bytes_immutable",
        "candidate_tree_immutable",
        "modern_pack_schema",
        "source_payload_binding",
        "taxon_review_binding",
        "metadata_manifest_binding",
        "strict_pack_registry_validation",
        "metadata_unit_binding",
        "feature_mapping_binding",
        "declared_files_only",
        "no_forbidden_transformations",
    ]
    passed: bool
    detail: str

    @field_validator("passed", mode="before")
    @classmethod
    def _valid_passed(cls, value):
        if type(value) is not bool:
            raise ValueError("validation check passed must be an exact boolean")
        return value

    @field_validator("detail", mode="before")
    @classmethod
    def _valid_detail(cls, value):
        return _text(value, "validation check detail")


class PackValidationReportV1(_FactoryContract):
    schema_version: Literal["vc.pack-validation-report.v1"]
    candidate_fingerprint: str
    review_fingerprint: str
    pack_id: str
    pack_version: str
    candidate_manifest_fingerprint: str
    validated_pack_fingerprint: str | None
    checks: tuple[PackValidationCheckV1, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    pack_valid: bool
    registration_allowed: bool
    passed: bool
    validation_method: Literal["PackRegistry.register+canonical_view+factory_checks"]
    training_performed: Literal[False]
    checkpoint_created: Literal[False]
    evidence_created: Literal[False]
    promotion_created: Literal[False]

    @field_validator(
        "candidate_fingerprint",
        "review_fingerprint",
        "candidate_manifest_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator("validated_pack_fingerprint", mode="before")
    @classmethod
    def _valid_optional_hash(cls, value):
        return None if value is None else _sha256(value, "validated_pack_fingerprint")

    @field_validator("pack_id", "pack_version", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("checks", mode="before")
    @classmethod
    def _valid_checks(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("checks must be a non-empty array")
        return tuple(value)

    @field_validator("warnings", "errors", mode="before")
    @classmethod
    def _valid_messages(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        values = tuple(_text(item, info.field_name) for item in value)
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return values

    @field_validator("pack_valid", "registration_allowed", "passed", mode="before")
    @classmethod
    def _valid_bools(cls, value, info):
        if type(value) is not bool:
            raise ValueError(f"{info.field_name} must be an exact boolean")
        return value

    @model_validator(mode="after")
    def _consistent_report(self):
        codes = tuple(item.code for item in self.checks)
        if codes != _VALIDATION_CHECKS:
            raise ValueError("validation checks must use the complete canonical order")
        failed = tuple(item.code for item in self.checks if not item.passed)
        if self.errors != failed:
            raise ValueError("validation errors must exactly list failed checks")
        strict_passed = next(item.passed for item in self.checks if item.code == "strict_pack_registry_validation")
        if self.pack_valid != strict_passed:
            raise ValueError("pack_valid must equal strict PackRegistry validation")
        if (self.validated_pack_fingerprint is not None) != self.pack_valid:
            raise ValueError("validated Pack fingerprint presence must equal pack_valid")
        expected_pass = not failed and not self.warnings
        if self.passed != expected_pass or self.registration_allowed != expected_pass:
            raise ValueError("report pass and registration state are inconsistent")
        return self


def _check(code: str, passed: bool, detail: str) -> PackValidationCheckV1:
    return PackValidationCheckV1(
        schema_version="vc.pack-validation-check.v1",
        code=code,
        passed=passed,
        detail=detail,
    )


def _redact_error(exc: BaseException, *roots: Path) -> str:
    value = str(exc)
    for root in roots:
        value = value.replace(str(root), "<local-root>")
    value = " ".join(value.split())
    return value[:512] or type(exc).__name__


def _claim_values(candidate: PackCandidateV1) -> dict[str, Any]:
    return {item.topic: json.loads(item.value_json) for item in candidate.metadata_claims}


def _current_view_facts(
    root: Path,
    manifest: PackManifest,
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    if manifest.schema_version == "vc.pack.v0.2":
        from praxis_virtualcell.data_packs.anndata_adapter import load_anndata_view

        with load_anndata_view(root) as view:
            units = {
                "dose_units": tuple(sorted({unit for _value, unit in view.doses})),
                "time_units": tuple(sorted({unit for _value, unit in view.times})),
            }
            features = {"primary": tuple(view.feature_ids)}
        return units, features
    from praxis_virtualcell.data_packs.mudata_adapter import load_mudata_view

    with load_mudata_view(root) as view:
        units = {
            "dose_units": tuple(sorted({unit for _value, unit in view.doses})),
            "time_units": tuple(sorted({unit for _value, unit in view.times})),
        }
        features = {modality.key: tuple(modality.feature_ids) for modality in view.modalities}
    return units, features


def _mapping_is_identity_only(
    summary: FeatureMappingSummaryV1,
    feature_ids: tuple[str, ...],
    namespace_name: str,
    namespace_version: str,
) -> bool:
    issues = (
        summary.duplicate_source_feature_ids,
        summary.duplicate_target_feature_ids,
        summary.duplicate_mapping_sources,
        summary.duplicate_mapping_targets,
        summary.out_of_domain_mapping_sources,
        summary.out_of_domain_mapping_targets,
        summary.unmapped_source_feature_ids,
        summary.unmapped_target_feature_ids,
    )
    expected_order = _fingerprint(list(feature_ids))
    return (
        not any(issues)
        and summary.order_preserved
        and summary.source_feature_count == len(feature_ids)
        and summary.target_feature_count == len(feature_ids)
        and summary.source_order_fingerprint == expected_order
        and summary.target_order_fingerprint == expected_order
        and summary.source_namespace.name == namespace_name
        and summary.source_namespace.version == namespace_version
        and summary.target_namespace == summary.source_namespace
    )


def validate_pack_candidate(
    prepared: PreparedPackCandidate,
    review: PackMetadataReviewV1,
) -> PackValidationReportV1:
    """Return a full deterministic report; invalid candidates never mutate a registry."""

    if type(prepared) is not PreparedPackCandidate:
        raise PackFactoryError("prepared must be exact PreparedPackCandidate")
    candidate = _revalidate(prepared.candidate, PackCandidateV1, "candidate")
    review = _revalidate(review, PackMetadataReviewV1, "metadata review")
    root = prepared.root
    upload_root = prepared.upload.directory
    checks: dict[str, PackValidationCheckV1] = {}

    try:
        validate_metadata_review(prepared, review)
        review_ok = review.decision == "approve_for_strict_validation"
        detail = "all exact candidate claims confirmed" if review_ok else "metadata review rejected"
    except PackFactoryError as exc:
        review_ok = False
        detail = _redact_error(exc, root, upload_root)
    checks["explicit_metadata_review"] = _check("explicit_metadata_review", review_ok, detail)

    try:
        current_upload = load_quarantined_upload(upload_root)
        _validate_candidate_receipt_binding(current_upload, candidate)
        receipt_ok = current_upload == prepared.upload
        detail = (
            "receipt and raw payload identities unchanged" if receipt_ok else "receipt or raw payload identity changed"
        )
    except PackFactoryError as exc:
        current_upload = None
        receipt_ok = False
        detail = _redact_error(exc, root, upload_root)
    checks["receipt_bytes_immutable"] = _check("receipt_bytes_immutable", receipt_ok, detail)

    try:
        files = _snapshot_tree(root)
        tree_ok = (
            files == candidate.candidate_files
            and _fingerprint([item.to_dict() for item in files]) == candidate.candidate_tree_fingerprint
        )
        detail = "candidate file tree unchanged" if tree_ok else "candidate file tree changed"
    except (OSError, PackFactoryError) as exc:
        files = ()
        tree_ok = False
        detail = _redact_error(exc, root, upload_root)
    checks["candidate_tree_immutable"] = _check("candidate_tree_immutable", tree_ok, detail)

    try:
        manifest = load_manifest(root / "manifest.yaml")
        modern_ok = (
            manifest.schema_version in {"vc.pack.v0.2", "vc.pack.v0.3"}
            and manifest.schema_version == candidate.manifest_schema_version
            and manifest.fingerprint() == candidate.manifest_fingerprint
            and manifest.pack_id == candidate.pack_id
            and manifest.pack_version == candidate.pack_version
        )
        detail = "modern candidate manifest identity matched" if modern_ok else "manifest identity changed"
    except (OSError, VirtualCellPackError) as exc:
        manifest = None
        modern_ok = False
        detail = _redact_error(exc, root, upload_root)
    checks["modern_pack_schema"] = _check("modern_pack_schema", modern_ok, detail)

    source_ok = False
    source_detail = "blocked by invalid manifest or receipt"
    if manifest is not None and current_upload is not None:
        try:
            assets = {asset.id: asset for asset in manifest.assets}
            source = assets[candidate.source_asset_id]
            source_path = resolve_asset_path(root, source.path)
            source_ok = (
                candidate.source_asset_id == _primary_data_asset_id(manifest)
                and source.path == candidate.source_asset_path
                and source.sha256 == candidate.source_payload_sha256
                and source.size_bytes == candidate.source_payload_size_bytes
                and source.sha256 == current_upload.receipt.sha256
                and source.size_bytes == current_upload.receipt.size_bytes
                and _hash_file(source_path) == current_upload.receipt.sha256
                and source_path.stat().st_size == current_upload.receipt.size_bytes
            )
            source_detail = (
                "actual Pack data asset preserves exact upload bytes"
                if source_ok
                else "actual Pack data asset does not preserve exact upload bytes"
            )
        except (KeyError, OSError, VirtualCellPackError) as exc:
            source_detail = _redact_error(exc, root, upload_root)
    checks["source_payload_binding"] = _check("source_payload_binding", source_ok, source_detail)

    taxon_ok = False
    taxon_detail = "blocked by invalid manifest or exact metadata review"
    if manifest is not None:
        taxon_claim = next(item for item in candidate.metadata_claims if item.topic == "taxon")
        taxon_confirmation = next(
            (item for item in review.confirmations if item.topic == "taxon"),
            None,
        )
        taxon_ok = (
            json.loads(taxon_claim.value_json) == manifest.taxon.model_dump(mode="json")
            and taxon_confirmation is not None
            and taxon_confirmation.status == "confirmed"
            and taxon_confirmation.claim_fingerprint == taxon_claim.fingerprint()
        )
        taxon_detail = (
            "exact manifest taxon was separately confirmed; receipt species is routing-only"
            if taxon_ok
            else "exact manifest taxon lacks a matching explicit confirmation"
        )
    checks["taxon_review_binding"] = _check(
        "taxon_review_binding",
        taxon_ok,
        taxon_detail,
    )

    current_mappings: tuple[FeatureMappingSummaryV1, ...] = ()
    metadata_ok = False
    metadata_detail = "blocked by invalid manifest"
    if manifest is not None:
        try:
            current_mappings = tuple(
                _mapping_summary(root, manifest, item.asset_id) for item in candidate.feature_mappings
            )
            values = _claim_values(candidate)
            value_semantics = values["value_semantics"]
            unit_values = {key: tuple(value) for key, value in values["unit"].items()}
            expected = _manifest_claim_values(
                manifest,
                current_mappings,
                value_semantics,
                unit_values,
            )
            manifest_topics = tuple(
                topic for topic in REQUIRED_REVIEW_TOPICS if topic not in {"value_semantics", "unit", "feature_mapping"}
            )
            metadata_ok = all(values[topic] == expected[topic] for topic in manifest_topics)
            metadata_detail = (
                "reviewed metadata matches exact manifest declarations"
                if metadata_ok
                else "reviewed metadata does not match exact manifest declarations"
            )
        except (KeyError, TypeError, ValueError, OSError, PackFactoryError, VirtualCellPackError) as exc:
            metadata_detail = _redact_error(exc, root, upload_root)
    checks["metadata_manifest_binding"] = _check("metadata_manifest_binding", metadata_ok, metadata_detail)

    registered = None
    pack_ok = False
    pack_detail = "strict Pack validation failed"
    if manifest is not None:
        try:
            registry = PackRegistry()
            registry.register(root)
            registered = registry.record(manifest.pack_id, manifest.pack_version)
            pack_ok = registered.fingerprint == manifest.fingerprint()
            pack_detail = (
                "PackRegistry full semantic validation passed"
                if pack_ok
                else "PackRegistry returned a different Pack identity"
            )
        except (OSError, VirtualCellPackError) as exc:
            pack_detail = _redact_error(exc, root, upload_root)
    checks["strict_pack_registry_validation"] = _check("strict_pack_registry_validation", pack_ok, pack_detail)

    units_ok = False
    units_detail = "blocked by strict Pack validation"
    mapping_ok = False
    mapping_detail = "blocked by strict Pack validation"
    if pack_ok and manifest is not None:
        try:
            actual_units, actual_features = _current_view_facts(root, manifest)
            values = _claim_values(candidate)
            declared_units = {key: tuple(value) for key, value in values["unit"].items()}
            units_ok = declared_units == actual_units
            units_detail = (
                "reviewed unit declarations match observed canonical values"
                if units_ok
                else "reviewed unit declarations do not match observed canonical values"
            )
            namespace_by_key = (
                {
                    "primary": (
                        manifest.feature_namespace.name,
                        manifest.feature_namespace.version,
                    )
                }
                if manifest.schema_version == "vc.pack.v0.2"
                else {
                    item.key: (
                        item.feature_namespace.name,
                        item.feature_namespace.version,
                    )
                    for item in manifest.multiomics.modalities
                }
            )
            mapping_ok = (
                current_mappings == candidate.feature_mappings
                and tuple(item.modality_key for item in current_mappings) == tuple(actual_features)
                and all(
                    _mapping_is_identity_only(
                        summary,
                        actual_features[summary.modality_key],
                        *namespace_by_key[summary.modality_key],
                    )
                    for summary in current_mappings
                )
            )
            mapping_detail = (
                "feature mapping is exact identity-only with preserved order"
                if mapping_ok
                else "feature mapping has drift, ambiguity, unmapped ids, duplicates, or transforms"
            )
        except (KeyError, TypeError, ValueError, OSError, PackFactoryError, VirtualCellPackError) as exc:
            units_ok = False
            mapping_ok = False
            units_detail = _redact_error(exc, root, upload_root)
            mapping_detail = units_detail
    checks["metadata_unit_binding"] = _check("metadata_unit_binding", units_ok, units_detail)
    checks["feature_mapping_binding"] = _check("feature_mapping_binding", mapping_ok, mapping_detail)

    declared_ok = False
    declared_detail = "blocked by invalid manifest"
    if manifest is not None and files:
        expected_paths = {"manifest.yaml", *(asset.path for asset in manifest.assets)}
        actual_paths = {item.path for item in files}
        declared_ok = actual_paths == expected_paths
        declared_detail = (
            "candidate contains only manifest-declared files"
            if declared_ok
            else "candidate contains missing or undeclared files"
        )
    checks["declared_files_only"] = _check("declared_files_only", declared_ok, declared_detail)

    transform_fields = (
        candidate.normalization_performed,
        candidate.fill_performed,
        candidate.imputation_performed,
        candidate.deduplication_performed,
        candidate.reordering_performed,
        candidate.random_split_performed,
        candidate.identifier_conversion_performed,
    )
    transform_ok = not any(transform_fields) and mapping_ok
    checks["no_forbidden_transformations"] = _check(
        "no_forbidden_transformations",
        transform_ok,
        (
            "no normalization, fill, imputation, deduplication, reorder, random split, or conversion"
            if transform_ok
            else "candidate requires or records a forbidden transformation"
        ),
    )

    ordered_checks = tuple(checks[code] for code in _VALIDATION_CHECKS)
    errors = tuple(item.code for item in ordered_checks if not item.passed)
    passed = not errors
    return PackValidationReportV1(
        schema_version="vc.pack-validation-report.v1",
        candidate_fingerprint=candidate.fingerprint(),
        review_fingerprint=review.fingerprint(),
        pack_id=candidate.pack_id,
        pack_version=candidate.pack_version,
        candidate_manifest_fingerprint=candidate.manifest_fingerprint,
        validated_pack_fingerprint=(registered.fingerprint if pack_ok else None),
        checks=ordered_checks,
        warnings=(),
        errors=errors,
        pack_valid=pack_ok,
        registration_allowed=passed,
        passed=passed,
        validation_method="PackRegistry.register+canonical_view+factory_checks",
        training_performed=False,
        checkpoint_created=False,
        evidence_created=False,
        promotion_created=False,
    )


class PackOperatorDecisionV1(_FactoryContract):
    schema_version: Literal["vc.pack-operator-decision.v1"]
    candidate_fingerprint: str
    review_fingerprint: str
    validation_report_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    operator_id: str
    operator_role: Literal["pack_registration_operator"]
    decided_at: str
    decision: Literal["approve_register", "reject"]
    reason: str
    decision_scope: Literal["pack_registration_only"]
    scientific_evidence_decision: Literal[False]
    product_promotion_decision: Literal[False]

    @field_validator(
        "candidate_fingerprint",
        "review_fingerprint",
        "validation_report_fingerprint",
        "pack_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator("pack_id", "pack_version", "operator_id", "reason", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("decided_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _utc_seconds(value, "decided_at")


def validate_operator_decision(
    candidate: PackCandidateV1,
    review: PackMetadataReviewV1,
    report: PackValidationReportV1,
    decision: PackOperatorDecisionV1,
) -> PackOperatorDecisionV1:
    candidate = _revalidate(candidate, PackCandidateV1, "candidate")
    review = _revalidate(review, PackMetadataReviewV1, "metadata review")
    report = _revalidate(report, PackValidationReportV1, "validation report")
    decision = _revalidate(decision, PackOperatorDecisionV1, "operator decision")
    expected = (
        candidate.fingerprint(),
        review.fingerprint(),
        report.fingerprint(),
        candidate.pack_id,
        candidate.pack_version,
        report.validated_pack_fingerprint,
    )
    actual = (
        decision.candidate_fingerprint,
        decision.review_fingerprint,
        decision.validation_report_fingerprint,
        decision.pack_id,
        decision.pack_version,
        decision.pack_fingerprint,
    )
    if actual != expected:
        raise PackFactoryError("operator decision does not bind the exact candidate/review/report")
    if decision.decision == "approve_register" and not report.registration_allowed:
        raise PackFactoryError("operator cannot approve an invalid validation report")
    return decision


class FactoryRegisteredPackV1(_FactoryContract):
    schema_version: Literal["vc.factory-registered-pack.v1"]
    receipt_fingerprint: str
    candidate_fingerprint: str
    metadata_review_fingerprint: str
    validation_report_fingerprint: str
    operator_decision_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    operator_id: str
    registered_at: str
    registration_method: Literal["controlled_pack_factory_v1"]
    factory_registered: Literal[True]
    cataloged: Literal[True]
    pack_valid: Literal[True]
    model_compatible: None
    environment_compatible: None
    adapter_compatible: None
    executable: Literal[False]
    training_performed: Literal[False]
    checkpoint_created: Literal[False]
    model_card_created: Literal[False]
    benchmark_performed: Literal[False]
    evidence_created: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator(
        "receipt_fingerprint",
        "candidate_fingerprint",
        "metadata_review_fingerprint",
        "validation_report_fingerprint",
        "operator_decision_fingerprint",
        "pack_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator("pack_id", "pack_version", "operator_id", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("registered_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _utc_seconds(value, "registered_at")


def _registration_artifact(
    candidate: PackCandidateV1,
    review: PackMetadataReviewV1,
    report: PackValidationReportV1,
    decision: PackOperatorDecisionV1,
) -> FactoryRegisteredPackV1:
    return FactoryRegisteredPackV1(
        schema_version="vc.factory-registered-pack.v1",
        receipt_fingerprint=candidate.receipt_fingerprint,
        candidate_fingerprint=candidate.fingerprint(),
        metadata_review_fingerprint=review.fingerprint(),
        validation_report_fingerprint=report.fingerprint(),
        operator_decision_fingerprint=decision.fingerprint(),
        pack_id=candidate.pack_id,
        pack_version=candidate.pack_version,
        pack_fingerprint=candidate.manifest_fingerprint,
        operator_id=decision.operator_id,
        registered_at=decision.decided_at,
        registration_method="controlled_pack_factory_v1",
        factory_registered=True,
        cataloged=True,
        pack_valid=True,
        model_compatible=None,
        environment_compatible=None,
        adapter_compatible=None,
        executable=False,
        training_performed=False,
        checkpoint_created=False,
        model_card_created=False,
        benchmark_performed=False,
        evidence_created=False,
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )


def register_pack_candidate(
    prepared: PreparedPackCandidate,
    review: PackMetadataReviewV1,
    report: PackValidationReportV1,
    decision: PackOperatorDecisionV1,
    *,
    index,
    store,
) -> FactoryRegisteredPackV1:
    """Commit a verified chain to one explicit store and index."""

    from praxis_virtualcell.pack_product import PackIndex

    if type(prepared) is not PreparedPackCandidate:
        raise PackFactoryError("prepared must be exact PreparedPackCandidate")
    if type(index) is not PackIndex:
        raise PackFactoryError("index must be an explicitly injected exact PackIndex")
    if type(store) is not PackFactoryStore:
        raise PackFactoryError("store must be an explicitly injected exact PackFactoryStore")
    if (
        not index.explicit_index_path
        or not index.path.is_absolute()
        or index.path.parent.is_symlink()
        or index.path.parent.resolve(strict=True) != index.path.parent
    ):
        raise PackFactoryError(
            "controlled registration requires an explicit absolute index in an existing canonical directory"
        )
    candidate = _revalidate(prepared.candidate, PackCandidateV1, "candidate")
    verified_upload = load_quarantined_upload(prepared.upload.directory)
    if verified_upload != prepared.upload:
        raise PackFactoryError("upload identity changed before registration")
    _validate_candidate_receipt_binding(verified_upload, candidate)
    review = validate_metadata_review(prepared, review)
    report = _revalidate(report, PackValidationReportV1, "validation report")
    current_report = validate_pack_candidate(prepared, review)
    if current_report.fingerprint() != report.fingerprint():
        raise PackFactoryError("candidate or validation identity changed before registration")
    decision = validate_operator_decision(candidate, review, report, decision)
    if decision.decision != "approve_register":
        raise PackFactoryError("operator decision did not approve registration")
    registration = _registration_artifact(candidate, review, report, decision)
    store.record_upload(verified_upload)
    store.record_candidate(prepared)
    store.record(review)
    store.record_validation(prepared, review, report)
    store.record(decision)
    try:
        record = index._register_validated_path(
            prepared.root,
            expected_pack_id=candidate.pack_id,
            expected_pack_version=candidate.pack_version,
            expected_pack_fingerprint=candidate.manifest_fingerprint,
            factory_registration_fingerprint=registration.fingerprint(),
            factory_store_root=str(store.root),
        )
    except (OSError, ValueError) as exc:
        raise PackFactoryError("controlled Pack index registration failed") from exc
    if (
        record.get("pack_id") != candidate.pack_id
        or record.get("pack_version") != candidate.pack_version
        or record.get("pack_fingerprint") != candidate.manifest_fingerprint
        or record.get("pack_valid") is not True
    ):
        raise PackFactoryError("Pack index returned a different or invalid Pack identity")
    store.record_registration(
        prepared,
        review,
        report,
        decision,
        registration,
        index=index,
    )
    committed = index.get_record(candidate.pack_id, candidate.pack_version)
    if committed.get("pack_fingerprint") != candidate.manifest_fingerprint or committed.get("pack_valid") is not True:
        raise PackFactoryError("factory registration commit is not consumable")
    return registration


class PackSupersessionV1(_FactoryContract):
    schema_version: Literal["vc.pack-supersession.v1"]
    superseded_registration_fingerprint: str
    replacement_registration_fingerprint: str
    pack_id: str
    superseded_pack_version: str
    replacement_pack_version: str
    operator_id: str
    decided_at: str
    reason: str
    effect: Literal["append_only_projection_no_history_rewrite"]
    product_promotion_decision: Literal[False]

    @field_validator(
        "superseded_registration_fingerprint",
        "replacement_registration_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator(
        "pack_id",
        "superseded_pack_version",
        "replacement_pack_version",
        "operator_id",
        "reason",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("decided_at", mode="before")
    @classmethod
    def _valid_time(cls, value):
        return _utc_seconds(value, "decided_at")

    @model_validator(mode="after")
    def _different_versions(self):
        if self.superseded_registration_fingerprint == self.replacement_registration_fingerprint:
            raise ValueError("a registration cannot supersede itself")
        if self.superseded_pack_version == self.replacement_pack_version:
            raise ValueError("supersession requires a new Pack version")
        return self


def declare_pack_supersession(
    superseded: FactoryRegisteredPackV1,
    replacement: FactoryRegisteredPackV1,
    *,
    operator_id: str,
    decided_at: str,
    reason: str,
) -> PackSupersessionV1:
    superseded = _revalidate(superseded, FactoryRegisteredPackV1, "superseded registration")
    replacement = _revalidate(replacement, FactoryRegisteredPackV1, "replacement registration")
    if superseded.pack_id != replacement.pack_id:
        raise PackFactoryError("supersession must remain within one Pack id")
    return PackSupersessionV1(
        schema_version="vc.pack-supersession.v1",
        superseded_registration_fingerprint=superseded.fingerprint(),
        replacement_registration_fingerprint=replacement.fingerprint(),
        pack_id=superseded.pack_id,
        superseded_pack_version=superseded.pack_version,
        replacement_pack_version=replacement.pack_version,
        operator_id=operator_id,
        decided_at=decided_at,
        reason=reason,
        effect="append_only_projection_no_history_rewrite",
        product_promotion_decision=False,
    )


_STORE_KINDS: dict[type[_FactoryContract], str] = {
    UploadReceiptV1: "receipts",
    PackCandidateV1: "candidates",
    PackMetadataReviewV1: "reviews",
    PackValidationReportV1: "validations",
    PackOperatorDecisionV1: "decisions",
    FactoryRegisteredPackV1: "registrations",
    PackSupersessionV1: "supersessions",
}
_STORE_MODELS = {kind: model for model, kind in _STORE_KINDS.items()}


class PackFactoryStore:
    """Explicit, local, append-only storage for content-addressed factory records."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path) or not root.is_absolute():
            raise PackFactoryError("factory store root must be an explicit absolute Path")
        if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
            raise PackFactoryError("factory store root must be a canonical real directory")
        marker = root / _STORE_MARKER_NAME
        try:
            if marker.is_symlink() or not stat.S_ISREG(marker.lstat().st_mode):
                raise PackFactoryError("factory store marker must be a regular non-symlink file")
            if marker.read_bytes() != _STORE_MARKER_BYTES:
                raise PackFactoryError("factory store marker is invalid")
        except FileNotFoundError as exc:
            raise PackFactoryError("factory store must be initialized in a write-new directory") from exc
        except OSError as exc:
            raise PackFactoryError("factory store marker is unavailable") from exc
        self.root = root

    @classmethod
    def create(cls, root: str | Path) -> PackFactoryStore:
        path = Path(root)
        if not path.is_absolute():
            raise PackFactoryError("factory store root must be an explicit absolute path")
        parent = path.parent
        if parent.is_symlink() or parent.resolve(strict=True) != parent:
            raise PackFactoryError("factory store parent must be canonical and non-symlink")
        try:
            path.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise PackFactoryError("factory store must be write-new") from exc
        except OSError as exc:
            raise PackFactoryError("cannot create factory store") from exc
        marker = path / _STORE_MARKER_NAME
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(marker, flags, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(_STORE_MARKER_BYTES)
                stream.flush()
                os.fsync(stream.fileno())
            directory_flags = os.O_RDONLY
            if hasattr(os, "O_DIRECTORY"):
                directory_flags |= os.O_DIRECTORY
            directory_descriptor = os.open(path, directory_flags)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError as exc:
            raise PackFactoryError("cannot initialize factory store marker") from exc
        return cls(path.resolve(strict=True))

    @classmethod
    def open(cls, root: str | Path) -> PackFactoryStore:
        path = Path(root)
        if path.is_symlink():
            raise PackFactoryError("factory store root must not be a symlink")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise PackFactoryError("factory store does not exist") from exc
        return cls(resolved)

    def _kind_directory(self, kind: str, *, create: bool) -> Path:
        if kind not in _STORE_MODELS:
            raise PackFactoryError("unknown factory artifact kind")
        path = self.root / kind
        if path.is_symlink():
            raise PackFactoryError("factory artifact directory must not be a symlink")
        if create:
            try:
                path.mkdir(mode=0o700, exist_ok=True)
            except OSError as exc:
                raise PackFactoryError("cannot create factory artifact directory") from exc
        if not path.exists():
            return path
        if not path.is_dir() or path.resolve(strict=True).parent != self.root:
            raise PackFactoryError("factory artifact directory escapes store root")
        return path.resolve(strict=True)

    @staticmethod
    def _model(value: _FactoryContract) -> tuple[type[_FactoryContract], str]:
        model = type(value)
        try:
            kind = _STORE_KINDS[model]
        except KeyError as exc:
            raise PackFactoryError("unsupported factory artifact type") from exc
        return model, kind

    def _path(self, model: type[_FactoryContract], fingerprint: str) -> Path:
        kind = _STORE_KINDS[model]
        return self._kind_directory(kind, create=False) / f"{fingerprint}.json"

    def get(self, model: type[_ContractT], fingerprint: str) -> _ContractT:
        if model not in _STORE_KINDS:
            raise PackFactoryError("unsupported factory artifact type")
        fingerprint = _sha256(fingerprint, "artifact fingerprint")
        path = self._path(model, fingerprint)
        try:
            if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
                raise PackFactoryError("factory artifact must be a regular non-symlink file")
            payload = path.read_bytes()
        except FileNotFoundError as exc:
            raise PackFactoryError("factory artifact does not exist") from exc
        except OSError as exc:
            raise PackFactoryError("cannot read factory artifact") from exc
        value = model.from_dict(_json_object_bytes(payload, "factory artifact"))
        if value.fingerprint() != fingerprint:
            raise PackFactoryError("factory artifact filename and content fingerprint disagree")
        canonical = _canonical_bytes(value.to_dict()) + b"\n"
        if payload != canonical:
            raise PackFactoryError("factory artifact bytes are not canonical")
        return value

    def list(self, model: type[_ContractT]) -> tuple[_ContractT, ...]:
        if model not in _STORE_KINDS:
            raise PackFactoryError("unsupported factory artifact type")
        directory = self._kind_directory(_STORE_KINDS[model], create=False)
        if not directory.exists():
            return ()
        values = []
        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            if path.name.startswith(".") or path.suffix != ".json":
                raise PackFactoryError("factory artifact directory contains an unexpected file")
            values.append(self.get(model, path.stem))
        return tuple(values)

    def _require_dependencies(self, value: _FactoryContract) -> None:
        if type(value) is PackCandidateV1:
            receipt = self.get(UploadReceiptV1, value.receipt_fingerprint)
            if (
                value.upload_id != receipt.upload_id
                or value.source_payload_sha256 != receipt.sha256
                or value.source_payload_size_bytes != receipt.size_bytes
            ):
                raise PackFactoryError("stored candidate does not bind its receipt content")
            return
        if type(value) is PackMetadataReviewV1:
            candidate = self.get(PackCandidateV1, value.candidate_fingerprint)
            claims = {item.topic: item.fingerprint() for item in candidate.metadata_claims}
            if any(item.claim_fingerprint != claims[item.topic] for item in value.confirmations):
                raise PackFactoryError("stored review does not bind exact candidate claims")
            return
        if type(value) is PackValidationReportV1:
            candidate = self.get(PackCandidateV1, value.candidate_fingerprint)
            review = self.get(PackMetadataReviewV1, value.review_fingerprint)
            if (
                review.candidate_fingerprint != candidate.fingerprint()
                or value.candidate_fingerprint != candidate.fingerprint()
                or value.review_fingerprint != review.fingerprint()
                or value.pack_id != candidate.pack_id
                or value.pack_version != candidate.pack_version
                or value.candidate_manifest_fingerprint != candidate.manifest_fingerprint
                or (
                    value.validated_pack_fingerprint is not None
                    and value.validated_pack_fingerprint != candidate.manifest_fingerprint
                )
            ):
                raise PackFactoryError("stored validation report has a mixed artifact chain")
            return
        if type(value) is PackOperatorDecisionV1:
            candidate = self.get(PackCandidateV1, value.candidate_fingerprint)
            review = self.get(PackMetadataReviewV1, value.review_fingerprint)
            report = self.get(
                PackValidationReportV1,
                value.validation_report_fingerprint,
            )
            validate_operator_decision(candidate, review, report, value)
            return
        if type(value) is FactoryRegisteredPackV1:
            receipt = self.get(UploadReceiptV1, value.receipt_fingerprint)
            candidate = self.get(PackCandidateV1, value.candidate_fingerprint)
            review = self.get(
                PackMetadataReviewV1,
                value.metadata_review_fingerprint,
            )
            report = self.get(
                PackValidationReportV1,
                value.validation_report_fingerprint,
            )
            decision = self.get(
                PackOperatorDecisionV1,
                value.operator_decision_fingerprint,
            )
            validate_operator_decision(candidate, review, report, decision)
            if (
                decision.decision != "approve_register"
                or not report.registration_allowed
                or candidate.receipt_fingerprint != receipt.fingerprint()
                or value.receipt_fingerprint != receipt.fingerprint()
                or value.candidate_fingerprint != candidate.fingerprint()
                or value.metadata_review_fingerprint != review.fingerprint()
                or value.validation_report_fingerprint != report.fingerprint()
                or value.operator_decision_fingerprint != decision.fingerprint()
                or value.pack_id != candidate.pack_id
                or value.pack_version != candidate.pack_version
                or value.pack_fingerprint != candidate.manifest_fingerprint
                or value.operator_id != decision.operator_id
                or value.registered_at != decision.decided_at
            ):
                raise PackFactoryError("stored registration has a mixed or unapproved chain")
            return
        if type(value) is PackSupersessionV1:
            superseded = self.get(
                FactoryRegisteredPackV1,
                value.superseded_registration_fingerprint,
            )
            replacement = self.get(
                FactoryRegisteredPackV1,
                value.replacement_registration_fingerprint,
            )
            if (
                superseded.pack_id != replacement.pack_id
                or value.pack_id != superseded.pack_id
                or value.superseded_pack_version != superseded.pack_version
                or value.replacement_pack_version != replacement.pack_version
            ):
                raise PackFactoryError("stored supersession does not bind exact registrations")

    def record(self, value: _ContractT) -> str:
        """Append declared lifecycle inputs; derived truth uses verified methods."""

        if type(value) in {
            UploadReceiptV1,
            PackCandidateV1,
            PackValidationReportV1,
            FactoryRegisteredPackV1,
        }:
            raise PackFactoryError(
                "receipt, candidate, validation and registration artifacts require runtime verification"
            )
        return self._append_verified(value)

    def record_upload(self, upload: QuarantinedUpload) -> str:
        """Persist only a receipt reverified against its immutable local payload."""

        if type(upload) is not QuarantinedUpload:
            raise PackFactoryError("upload must be exact QuarantinedUpload")
        verified = load_quarantined_upload(upload.directory)
        if verified != upload:
            raise PackFactoryError("upload identity changed before store append")
        return self._append_verified(verified.receipt)

    def record_candidate(self, prepared: PreparedPackCandidate) -> str:
        """Persist only a candidate reproduced from current receipt and Pack bytes."""

        if type(prepared) is not PreparedPackCandidate:
            raise PackFactoryError("prepared must be exact PreparedPackCandidate")
        candidate = _revalidate(prepared.candidate, PackCandidateV1, "candidate")
        values = _claim_values(candidate)
        rebuilt = prepare_pack_candidate(
            prepared.upload,
            prepared.root,
            source_asset_id=candidate.source_asset_id,
            mapping_asset_ids={item.modality_key: item.asset_id for item in candidate.feature_mappings},
            value_semantics={
                item.modality_key: values["value_semantics"][item.modality_key] for item in candidate.feature_mappings
            },
            units={key: values["unit"][key] for key in ("dose_units", "time_units")},
            claim_origins={item.topic: item.origin for item in candidate.metadata_claims},
        )
        if rebuilt.candidate.fingerprint() != candidate.fingerprint():
            raise PackFactoryError("candidate is not reproducible from current local bytes")
        return self._append_verified(candidate)

    def record_validation(
        self,
        prepared: PreparedPackCandidate,
        review: PackMetadataReviewV1,
        report: PackValidationReportV1,
    ) -> str:
        """Persist only a report reproduced from current immutable local bytes."""

        if type(prepared) is not PreparedPackCandidate:
            raise PackFactoryError("prepared must be exact PreparedPackCandidate")
        review = validate_metadata_review(prepared, review)
        report = _revalidate(report, PackValidationReportV1, "validation report")
        current = validate_pack_candidate(prepared, review)
        if current.fingerprint() != report.fingerprint():
            raise PackFactoryError("validation report is not reproducible from current bytes")
        return self._append_verified(report)

    def record_registration(
        self,
        prepared: PreparedPackCandidate,
        review: PackMetadataReviewV1,
        report: PackValidationReportV1,
        decision: PackOperatorDecisionV1,
        registration: FactoryRegisteredPackV1,
        *,
        index,
    ) -> str:
        """Persist registration truth only after matching durable index provenance."""

        from praxis_virtualcell.pack_product import PackIndex

        if type(prepared) is not PreparedPackCandidate:
            raise PackFactoryError("prepared must be exact PreparedPackCandidate")
        if type(index) is not PackIndex:
            raise PackFactoryError("index must be exact PackIndex")
        candidate = _revalidate(prepared.candidate, PackCandidateV1, "candidate")
        review = validate_metadata_review(prepared, review)
        report = _revalidate(report, PackValidationReportV1, "validation report")
        if validate_pack_candidate(prepared, review).fingerprint() != report.fingerprint():
            raise PackFactoryError("registration report is not reproducible from current bytes")
        decision = validate_operator_decision(candidate, review, report, decision)
        registration = _revalidate(
            registration,
            FactoryRegisteredPackV1,
            "factory registration",
        )
        expected = _registration_artifact(candidate, review, report, decision)
        if registration.fingerprint() != expected.fingerprint():
            raise PackFactoryError("registration artifact does not bind the verified chain")
        if index.factory_registration_fingerprint(
            candidate.pack_id,
            candidate.pack_version,
        ) != registration.fingerprint() or index.factory_store_root(
            candidate.pack_id,
            candidate.pack_version,
        ) != str(self.root):
            raise PackFactoryError("Pack index does not bind the factory registration")
        return self._append_verified(registration)

    def verify_registration(
        self,
        fingerprint: str,
    ) -> FactoryRegisteredPackV1:
        """Revalidate one committed registration and its complete stored chain."""

        registration = self.get(FactoryRegisteredPackV1, fingerprint)
        self._require_dependencies(registration)
        return registration

    def _append_verified(self, value: _ContractT) -> str:
        model, kind = self._model(value)
        value = _revalidate(value, model, "factory artifact")
        fingerprint = value.fingerprint()
        payload = _canonical_bytes(value.to_dict()) + b"\n"
        lock_path = self.root / ".factory.lock"
        if lock_path.is_symlink():
            raise PackFactoryError("factory store lock must not be a symlink")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise PackFactoryError("factory store lock is unavailable") from exc
        with os.fdopen(descriptor, "a+b") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                self._require_dependencies(value)
                if type(value) is PackSupersessionV1:
                    existing = self.list(PackSupersessionV1)
                    if any(
                        item.superseded_registration_fingerprint == value.superseded_registration_fingerprint
                        and item.fingerprint() != fingerprint
                        for item in existing
                    ):
                        raise PackFactoryError("registration already has a different supersession")
                    edges = {
                        item.superseded_registration_fingerprint: item.replacement_registration_fingerprint
                        for item in (*existing, value)
                    }
                    current = value.replacement_registration_fingerprint
                    seen = {value.superseded_registration_fingerprint}
                    while current in edges:
                        if current in seen:
                            raise PackFactoryError("supersession would create a cycle")
                        seen.add(current)
                        current = edges[current]
                directory = self._kind_directory(kind, create=True)
                target = directory / f"{fingerprint}.json"
                if target.exists():
                    if target.is_symlink() or target.read_bytes() != payload:
                        raise PackFactoryError("factory artifact identity conflicts with stored bytes")
                    return fingerprint
                descriptor, temporary = tempfile.mkstemp(
                    prefix=f".factory-{fingerprint}.",
                    suffix=".tmp",
                    dir=self.root,
                )
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, 0o600)
                    os.replace(temporary, target)
                    directory_flags = os.O_RDONLY
                    if hasattr(os, "O_DIRECTORY"):
                        directory_flags |= os.O_DIRECTORY
                    directory_descriptor = os.open(directory, directory_flags)
                    try:
                        os.fsync(directory_descriptor)
                    finally:
                        os.close(directory_descriptor)
                finally:
                    try:
                        Path(temporary).unlink()
                    except FileNotFoundError:
                        pass
                return fingerprint
            except OSError as exc:
                raise PackFactoryError("cannot append factory artifact") from exc
            finally:
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass


def _operator_identity_fingerprint(operator_id: str) -> str:
    return _fingerprint({"kind": "local_operator_identity", "id": operator_id})


def _receipt_catalog_item(
    receipt: UploadReceiptV1,
    candidates: list[PackCandidateV1],
    reports_by_candidate: dict[str, list[PackValidationReportV1]],
    registration_candidates: set[str],
) -> dict[str, Any]:
    candidate_fingerprints = {value.fingerprint() for value in candidates}
    reports = [report for fingerprint in candidate_fingerprints for report in reports_by_candidate.get(fingerprint, [])]
    return {
        "schema_version": receipt.schema_version,
        "receipt_fingerprint": receipt.fingerprint(),
        "upload_id": receipt.upload_id,
        "status": receipt.status,
        "species": receipt.species,
        "filename": receipt.filename,
        "size_bytes": receipt.size_bytes,
        "sha256": receipt.sha256,
        "pack_valid": (True if any(item.pack_valid for item in reports) else False if reports else None),
        "factory_registered": bool(candidate_fingerprints & registration_candidates),
        "model_compatible": None,
        "executable": False,
    }


def _empty_catalog() -> dict[str, Any]:
    return {
        "schema_version": "vc.pack-factory-catalog.v1",
        "configured": False,
        "receipts": [],
        "candidates": [],
        "reviews": [],
        "validations": [],
        "decisions": [],
        "registrations": [],
        "supersessions": [],
        "review_count": 0,
        "validation_count": 0,
        "operator_decision_count": 0,
        "registration_count": 0,
        "supersession_count": 0,
        "write_api_enabled": False,
    }


def factory_catalog_payload(
    store: PackFactoryStore | None = None,
) -> dict[str, Any]:
    """Return a root-free read-only lifecycle projection; never create a store."""

    if store is None:
        configured = os.environ.get("PRAXIS_VC_PACK_FACTORY_STORE")
        if not configured:
            return _empty_catalog()
        store = PackFactoryStore.open(Path(configured))
    if type(store) is not PackFactoryStore:
        raise PackFactoryError("store must be exact PackFactoryStore")

    receipts = store.list(UploadReceiptV1)
    candidates = store.list(PackCandidateV1)
    reviews = store.list(PackMetadataReviewV1)
    reports = store.list(PackValidationReportV1)
    decisions = store.list(PackOperatorDecisionV1)
    registrations = tuple(
        store.verify_registration(value.fingerprint()) for value in store.list(FactoryRegisteredPackV1)
    )
    supersessions = store.list(PackSupersessionV1)
    review_by_candidate: dict[str, list[PackMetadataReviewV1]] = {}
    for value in reviews:
        review_by_candidate.setdefault(value.candidate_fingerprint, []).append(value)
    report_by_candidate: dict[str, list[PackValidationReportV1]] = {}
    for value in reports:
        report_by_candidate.setdefault(value.candidate_fingerprint, []).append(value)
    registration_by_candidate = {value.candidate_fingerprint: value for value in registrations}
    registration_candidates = set(registration_by_candidate)
    candidate_by_receipt: dict[str, list[PackCandidateV1]] = {}
    for value in candidates:
        candidate_by_receipt.setdefault(value.receipt_fingerprint, []).append(value)
    superseded_by = {
        value.superseded_registration_fingerprint: value.replacement_registration_fingerprint for value in supersessions
    }

    return {
        "schema_version": "vc.pack-factory-catalog.v1",
        "configured": True,
        "receipts": [
            _receipt_catalog_item(
                value,
                candidate_by_receipt.get(value.fingerprint(), []),
                report_by_candidate,
                registration_candidates,
            )
            for value in receipts
        ],
        "candidates": [
            {
                "schema_version": value.schema_version,
                "candidate_fingerprint": value.fingerprint(),
                "receipt_fingerprint": value.receipt_fingerprint,
                "pack_id": value.pack_id,
                "pack_version": value.pack_version,
                "manifest_fingerprint": value.manifest_fingerprint,
                "status": value.status,
                "reviewed": any(
                    item.decision == "approve_for_strict_validation"
                    for item in review_by_candidate.get(value.fingerprint(), [])
                ),
                "validation_passed": any(item.passed for item in report_by_candidate.get(value.fingerprint(), [])),
                "factory_registered": value.fingerprint() in registration_by_candidate,
                "pack_valid": next(
                    (item.pack_valid for item in report_by_candidate.get(value.fingerprint(), []) if item.passed),
                    None,
                ),
                "model_compatible": None,
                "executable": False,
                "scientifically_validated": False,
                "production_promoted": False,
            }
            for value in candidates
        ],
        "reviews": [
            {
                "schema_version": value.schema_version,
                "review_fingerprint": value.fingerprint(),
                "candidate_fingerprint": value.candidate_fingerprint,
                "reviewer_identity_fingerprint": _operator_identity_fingerprint(value.reviewer_id),
                "reviewed_at": value.reviewed_at,
                "decision": value.decision,
                "confirmations": [
                    {
                        "topic": item.topic,
                        "claim_fingerprint": item.claim_fingerprint,
                        "status": item.status,
                    }
                    for item in value.confirmations
                ],
                "scientific_validation_performed": False,
                "product_policy_created": False,
            }
            for value in reviews
        ],
        "validations": [
            {
                "schema_version": value.schema_version,
                "validation_report_fingerprint": value.fingerprint(),
                "candidate_fingerprint": value.candidate_fingerprint,
                "review_fingerprint": value.review_fingerprint,
                "pack_id": value.pack_id,
                "pack_version": value.pack_version,
                "candidate_manifest_fingerprint": value.candidate_manifest_fingerprint,
                "validated_pack_fingerprint": value.validated_pack_fingerprint,
                "checks": [{"code": item.code, "passed": item.passed} for item in value.checks],
                "warnings": list(value.warnings),
                "errors": list(value.errors),
                "pack_valid": value.pack_valid,
                "registration_allowed": value.registration_allowed,
                "passed": value.passed,
                "training_performed": False,
                "checkpoint_created": False,
                "evidence_created": False,
                "promotion_created": False,
            }
            for value in reports
        ],
        "decisions": [
            {
                "schema_version": value.schema_version,
                "operator_decision_fingerprint": value.fingerprint(),
                "candidate_fingerprint": value.candidate_fingerprint,
                "review_fingerprint": value.review_fingerprint,
                "validation_report_fingerprint": value.validation_report_fingerprint,
                "pack_id": value.pack_id,
                "pack_version": value.pack_version,
                "pack_fingerprint": value.pack_fingerprint,
                "operator_identity_fingerprint": _operator_identity_fingerprint(value.operator_id),
                "decided_at": value.decided_at,
                "decision": value.decision,
                "decision_scope": value.decision_scope,
                "scientific_evidence_decision": False,
                "product_promotion_decision": False,
            }
            for value in decisions
        ],
        "registrations": [
            {
                "schema_version": value.schema_version,
                "registration_fingerprint": value.fingerprint(),
                "receipt_fingerprint": value.receipt_fingerprint,
                "candidate_fingerprint": value.candidate_fingerprint,
                "metadata_review_fingerprint": value.metadata_review_fingerprint,
                "validation_report_fingerprint": value.validation_report_fingerprint,
                "operator_decision_fingerprint": value.operator_decision_fingerprint,
                "pack_id": value.pack_id,
                "pack_version": value.pack_version,
                "pack_fingerprint": value.pack_fingerprint,
                "operator_identity_fingerprint": _operator_identity_fingerprint(value.operator_id),
                "registered_at": value.registered_at,
                "registration_method": value.registration_method,
                "factory_registered": True,
                "cataloged": True,
                "pack_valid": True,
                "model_compatible": None,
                "environment_compatible": None,
                "adapter_compatible": None,
                "executable": False,
                "training_performed": False,
                "checkpoint_created": False,
                "model_card_created": False,
                "benchmark_performed": False,
                "evidence_created": False,
                "scientifically_validated": False,
                "promotion_eligible": False,
                "production_promoted": False,
                "superseded_by": superseded_by.get(value.fingerprint()),
            }
            for value in registrations
        ],
        "supersessions": [
            {
                "schema_version": value.schema_version,
                "supersession_fingerprint": value.fingerprint(),
                "superseded_registration_fingerprint": value.superseded_registration_fingerprint,
                "replacement_registration_fingerprint": value.replacement_registration_fingerprint,
                "pack_id": value.pack_id,
                "superseded_pack_version": value.superseded_pack_version,
                "replacement_pack_version": value.replacement_pack_version,
                "operator_identity_fingerprint": _operator_identity_fingerprint(value.operator_id),
                "decided_at": value.decided_at,
                "effect": value.effect,
                "product_promotion_decision": False,
            }
            for value in supersessions
        ],
        "review_count": len(reviews),
        "validation_count": len(reports),
        "operator_decision_count": len(decisions),
        "registration_count": len(registrations),
        "supersession_count": len(supersessions),
        "write_api_enabled": False,
    }


def load_factory_contract(
    path: str | Path,
    model: type[_ContractT],
) -> _ContractT:
    """Load one strict, duplicate-key-safe factory artifact from an explicit file."""

    if model not in _STORE_KINDS:
        raise PackFactoryError("unsupported factory artifact type")
    artifact_path = Path(path)
    try:
        if artifact_path.is_symlink():
            raise PackFactoryError("factory artifact file must not be a symlink")
        resolved = artifact_path.resolve(strict=True)
        file_stat = resolved.lstat()
        if not stat.S_ISREG(file_stat.st_mode):
            raise PackFactoryError("factory artifact must be a regular file")
        if file_stat.st_size <= 0 or file_stat.st_size > 16 * 1024 * 1024:
            raise PackFactoryError("factory artifact file has an invalid size")
        payload = resolved.read_bytes()
    except OSError as exc:
        raise PackFactoryError("factory artifact file is unavailable") from exc
    return model.from_dict(_json_object_bytes(payload, "factory artifact"))
