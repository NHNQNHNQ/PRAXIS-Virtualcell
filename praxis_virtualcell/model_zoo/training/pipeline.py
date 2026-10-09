"""Strict, contract-only Phase 20 training pipeline.

The pipeline consumes only a live, fully committed Phase 19 factory
registration.  It audits split metadata before reading any training labels,
runs one fixed stdlib worker in an isolated subprocess, and publishes only a
data-only candidate bundle through a write-new staging directory.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.data_packs.feature_alignment import AlignmentReport, ModelFeatureContract
from praxis_virtualcell.data_packs.manifest import PackManifest, load_manifest_bytes
from praxis_virtualcell.pack_factory import (
    CandidateFileIdentityV1,
    FactoryRegisteredPackV1,
    PackCandidateV1,
    PackFactoryStore,
)
from praxis_virtualcell.pack_product import PackIndex

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_TRAINER_ID = "builtin.tiny-json-summary.v1"
TRAINER_REVISION = "p20.tiny-json-summary.v1"
_WORKER_NAME = "tiny_worker.py"
_MAX_JOB_BYTES = 2 * 1024 * 1024
_MAX_SPLIT_BYTES = 2 * 1024 * 1024
_MAX_TRUSTED_SOURCE_BYTES = 2 * 1024 * 1024
_ABS_MAX_INPUT_BYTES = 4 * 1024 * 1024
_ABS_MAX_SAMPLES = 1024
_ABS_MAX_FEATURES = 4096
_ABS_MAX_LABELS = 256
_ABS_MAX_CHECKPOINT_BYTES = 4 * 1024 * 1024
_ABS_MAX_TIMEOUT_SECONDS = 60.0
_OUTPUT_FILE_NAMES = (
    "checkpoint.json",
    "checkpoint-manifest.json",
    "training-result.json",
    "candidate-model.json",
)
_TRAINING_SOURCE_PATHS = (
    "data_packs/anndata_adapter.py",
    "data_packs/errors.py",
    "data_packs/feature_alignment.py",
    "data_packs/manifest.py",
    "data_packs/mudata_adapter.py",
    "data_packs/registry.py",
    "data_packs/schema.py",
    "data_packs/validator.py",
    "model_zoo/training/pipeline.py",
    "model_zoo/training/tiny_worker.py",
    "pack_factory.py",
    "pack_product.py",
)


class TrainingPipelineError(ValueError):
    """A Phase 20 contract, identity, or safe-execution gate failed closed."""


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
    except (RecursionError, TypeError, ValueError) as exc:
        raise TrainingPipelineError("value is not canonical JSON") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_descriptor(
    descriptor: int,
    *,
    max_bytes: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > max_bytes:
        raise TrainingPipelineError("file has an invalid size or type")
    if expected_size is not None and before.st_size != expected_size:
        raise TrainingPipelineError("file size changed")
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    after = os.fstat(descriptor)
    if len(payload) != before.st_size or (before.st_dev, before.st_ino, before.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise TrainingPipelineError("file changed while it was read")
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise TrainingPipelineError("file bytes changed")
    return payload


def _read_regular_path(path: Path, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
        try:
            return _read_descriptor(descriptor, max_bytes=max_bytes)
        finally:
            os.close(descriptor)
    except TrainingPipelineError:
        raise
    except OSError as exc:
        raise TrainingPipelineError("file is unavailable") from exc


def _read_root_relative_file(
    root: Path,
    relative: str,
    *,
    max_bytes: int,
    expected_size: int,
    expected_sha256: str,
) -> bytes:
    relative_path = PurePosixPath(relative)
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or any(part in {"", ".", ".."} for part in relative_path.parts)
    ):
        raise TrainingPipelineError("file path must be canonical and relative")
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    file_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        file_flags |= os.O_NOFOLLOW
    descriptors: list[int] = []
    try:
        descriptors.append(os.open(root, directory_flags))
        for part in relative_path.parts[:-1]:
            descriptors.append(os.open(part, directory_flags, dir_fd=descriptors[-1]))
        descriptor = os.open(relative_path.parts[-1], file_flags, dir_fd=descriptors[-1])
        try:
            return _read_descriptor(
                descriptor,
                max_bytes=max_bytes,
                expected_size=expected_size,
                expected_sha256=expected_sha256,
            )
        finally:
            os.close(descriptor)
    except TrainingPipelineError:
        raise
    except OSError as exc:
        raise TrainingPipelineError("Pack file is unavailable") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_directory_file(
    directory_descriptor: int,
    relative: str,
    *,
    max_bytes: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> bytes:
    if PurePosixPath(relative).parts != (relative,):
        raise TrainingPipelineError("staged artifact name must be a basename")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(relative, flags, dir_fd=directory_descriptor)
        try:
            return _read_descriptor(
                descriptor,
                max_bytes=max_bytes,
                expected_size=expected_size,
                expected_sha256=expected_sha256,
            )
        finally:
            os.close(descriptor)
    except TrainingPipelineError:
        raise
    except OSError as exc:
        raise TrainingPipelineError("staged artifact is unavailable") from exc


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(f"{field} must be non-empty canonical text")
    return value


def _identifier(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _sha256(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be lowercase SHA-256")
    return value


def _positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _finite_number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not finite:
        raise ValueError(f"{field} must be a finite number")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        raise ValueError(f"{field} must be a JSON array")
    items = tuple(_identifier(item, field) for item in value)
    if len(set(items)) != len(items):
        raise ValueError(f"{field} must not contain duplicates")
    return items


def _duplicate_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise TrainingPipelineError("duplicate JSON key")
        value[key] = item
    return value


def _json_object(payload: bytes, field: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_duplicate_object)
    except (RecursionError, UnicodeDecodeError, ValueError) as exc:
        raise TrainingPipelineError(f"invalid {field} JSON") from exc
    if type(value) is not dict:
        raise TrainingPipelineError(f"{field} must contain a JSON object")
    return value


def _canonical_json_text(value: Any, field: str) -> str:
    value = _text(value, field)
    try:
        parsed = json.loads(value, object_pairs_hook=_duplicate_object)
    except (RecursionError, ValueError) as exc:
        raise ValueError(f"{field} must be canonical JSON") from exc
    if _canonical_bytes(parsed).decode("utf-8") != value:
        raise ValueError(f"{field} must use canonical JSON encoding")
    return value


def _reject_undeclared_fields(value: Any, path: str) -> None:
    if isinstance(value, BaseModel):
        declared = type(value).model_fields
        unexpected = set(value.__dict__).difference(declared)
        extra = getattr(value, "__pydantic_extra__", None)
        if extra:
            unexpected.update(extra)
        if unexpected:
            raise ValueError(f"{path} contains undeclared fields")
        for name in declared:
            _reject_undeclared_fields(getattr(value, name), f"{path}.{name}")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_undeclared_fields(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_undeclared_fields(item, f"{path}[{index}]")


def _same_shape(value: Any, normalized: Any, path: str) -> None:
    if isinstance(normalized, BaseModel):
        if type(value) is not type(normalized):
            raise TypeError(f"{path} has a non-canonical model type")
        for name in type(normalized).model_fields:
            _same_shape(getattr(value, name), getattr(normalized, name), f"{path}.{name}")
    elif isinstance(normalized, tuple):
        if type(value) is not tuple or len(value) != len(normalized):
            raise TypeError(f"{path} has a non-canonical array type")
        for index, (item, expected) in enumerate(zip(value, normalized, strict=True)):
            _same_shape(item, expected, f"{path}[{index}]")
    elif type(value) is not type(normalized) or value != normalized:
        raise TypeError(f"{path} has a non-canonical value")


_ContractT = TypeVar("_ContractT", bound="_TrainingContract")


def _revalidate(value: Any, expected: type[_ContractT], field: str) -> _ContractT:
    if type(value) is not expected:
        raise TrainingPipelineError(f"{field} must be exact {expected.__name__}")
    try:
        _reject_undeclared_fields(value, field)
        normalized = expected.model_validate(value.model_dump(mode="python", serialize_as_any=True))
        _same_shape(value, normalized, field)
        return normalized
    except (AttributeError, TypeError, ValidationError, ValueError) as exc:
        raise TrainingPipelineError(f"invalid {field}") from exc


class _TrainingContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls: type[_ContractT], value: dict[str, Any]) -> _ContractT:
        if type(value) is not dict:
            raise TrainingPipelineError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except (RecursionError, TypeError, ValidationError, ValueError) as exc:
            raise TrainingPipelineError(f"invalid {cls.__name__}") from exc

    def to_dict(self) -> dict[str, Any]:
        _reject_undeclared_fields(self, type(self).__name__)
        return self.model_dump(mode="json", serialize_as_any=True)

    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())


class TrainingEnvironmentV1(_TrainingContract):
    schema_version: Literal["vc.training-environment.v1"]
    environment_id: str
    python_version: str
    implementation: str
    platform_system: str
    machine: str
    declared_dependency_lock_sha256: str
    installed_distributions_sha256: str
    cpu_threads: Literal[1]
    network_access_requested: Literal[False]
    gpu_access_requested: Literal[False]

    @field_validator(
        "environment_id",
        "python_version",
        "implementation",
        "platform_system",
        "machine",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("declared_dependency_lock_sha256", "installed_distributions_sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value, info):
        return _sha256(value, info.field_name)


class TrainingResourceLimitsV1(_TrainingContract):
    schema_version: Literal["vc.training-resource-limits.v1"]
    max_input_bytes: int
    max_samples: int
    max_features: int
    max_labels: int
    max_checkpoint_bytes: int
    timeout_seconds: float
    cpu_threads: Literal[1]
    network_allowed: Literal[False]
    gpu_allowed: Literal[False]

    @field_validator(
        "max_input_bytes",
        "max_samples",
        "max_features",
        "max_labels",
        "max_checkpoint_bytes",
        mode="before",
    )
    @classmethod
    def _valid_positive(cls, value, info):
        return _positive_int(value, info.field_name)

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def _valid_timeout(cls, value):
        value = _finite_number(value, "timeout_seconds")
        if value <= 0 or value > _ABS_MAX_TIMEOUT_SECONDS:
            raise ValueError(f"timeout_seconds must be in (0, {_ABS_MAX_TIMEOUT_SECONDS:g}]")
        return float(value)

    @model_validator(mode="after")
    def _tiny_hard_ceilings(self):
        ceilings = {
            "max_input_bytes": _ABS_MAX_INPUT_BYTES,
            "max_samples": _ABS_MAX_SAMPLES,
            "max_features": _ABS_MAX_FEATURES,
            "max_labels": _ABS_MAX_LABELS,
            "max_checkpoint_bytes": _ABS_MAX_CHECKPOINT_BYTES,
        }
        if any(getattr(self, field) > ceiling for field, ceiling in ceilings.items()):
            raise ValueError("resource limit exceeds the fixed P20 tiny ceiling")
        return self


class TrainingHyperparameterV1(_TrainingContract):
    schema_version: Literal["vc.training-hyperparameter.v1"]
    name: str
    value_type: Literal["integer", "number", "boolean"]
    value: int | float | bool

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _identifier(value, "hyperparameter.name")

    @model_validator(mode="after")
    def _typed_value(self):
        expected = {
            "integer": type(self.value) is int,
            "number": type(self.value) is float and math.isfinite(self.value),
            "boolean": type(self.value) is bool,
        }[self.value_type]
        if not expected:
            raise ValueError("hyperparameter value does not match value_type")
        return self


class TrainingAssetBindingV1(_TrainingContract):
    schema_version: Literal["vc.training-asset-binding.v1"]
    asset_id: str
    media_type: str
    size_bytes: int
    sha256: str

    @field_validator("asset_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _identifier(value, "asset_id")

    @field_validator("media_type", mode="before")
    @classmethod
    def _valid_media(cls, value):
        return _text(value, "media_type")

    @field_validator("size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        return _positive_int(value, "size_bytes")

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value):
        return _sha256(value, "sha256")


class TrainingSplitV1(_TrainingContract):
    schema_version: Literal["vc.training-split.v1"]
    split_asset: TrainingAssetBindingV1
    split_name: str
    split_field: str
    partitions: tuple[str, ...]
    leakage_guard: tuple[str, ...]
    train_sample_ids: tuple[str, ...]
    train_feature_asset_ids: tuple[str, ...]
    train_label_asset_ids: tuple[str, ...]
    validation_label_asset_ids: tuple[str, ...]
    test_label_asset_ids: tuple[str, ...]
    external_label_asset_ids: tuple[str, ...]
    random_split_performed: Literal[False]
    test_external_read: Literal[False]

    @field_validator("split_name", "split_field", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator(
        "partitions",
        "leakage_guard",
        "train_sample_ids",
        "train_feature_asset_ids",
        "train_label_asset_ids",
        "validation_label_asset_ids",
        "test_label_asset_ids",
        "external_label_asset_ids",
        mode="before",
    )
    @classmethod
    def _valid_arrays(cls, value, info):
        allow_empty = info.field_name in {
            "validation_label_asset_ids",
            "test_label_asset_ids",
            "external_label_asset_ids",
        }
        return _string_tuple(value, info.field_name, allow_empty=allow_empty)

    @model_validator(mode="after")
    def _training_assets_are_partitioned(self):
        forbidden = set(self.test_label_asset_ids).union(self.external_label_asset_ids)
        if forbidden.intersection(self.train_label_asset_ids):
            raise ValueError("test/external label assets cannot be training assets")
        if "train" not in self.partitions:
            raise ValueError("training split must include train")
        return self


class LeakageOverlapV1(_TrainingContract):
    schema_version: Literal["vc.training-leakage-overlap.v1"]
    group_field: str
    group_value_sha256: str
    partitions: tuple[str, ...]

    @field_validator("group_field", mode="before")
    @classmethod
    def _valid_field(cls, value):
        return _identifier(value, "group_field")

    @field_validator("group_value_sha256", mode="before")
    @classmethod
    def _valid_hash(cls, value):
        return _sha256(value, "group_value_sha256")

    @field_validator("partitions", mode="before")
    @classmethod
    def _valid_partitions(cls, value):
        return _string_tuple(value, "partitions")


class TrainingLeakageAuditV1(_TrainingContract):
    schema_version: Literal["vc.training-leakage-audit.v1"]
    split_fingerprint: str
    checked_group_fields: tuple[str, ...]
    checked_partitions: tuple[str, ...]
    overlaps: tuple[LeakageOverlapV1, ...]
    metadata_only: Literal[True]
    performed_before_label_read: Literal[True]
    source_observation_binding_performed: Literal[False]
    scientific_validation_performed: Literal[False]
    passed: bool

    @field_validator("split_fingerprint", mode="before")
    @classmethod
    def _valid_fp(cls, value):
        return _sha256(value, "split_fingerprint")

    @field_validator("checked_group_fields", "checked_partitions", mode="before")
    @classmethod
    def _valid_arrays(cls, value, info):
        return _string_tuple(value, info.field_name)

    @field_validator("overlaps", mode="before")
    @classmethod
    def _valid_overlaps(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("overlaps must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _truthful_result(self):
        if self.passed != (not self.overlaps):
            raise ValueError("leakage audit result contradicts overlaps")
        return self


class TrainingJobV1(_TrainingContract):
    schema_version: Literal["vc.training-job.v1"]
    factory_registration_fingerprint: str
    pack_candidate_fingerprint: str
    pack_candidate_tree_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    feature_mapping_fingerprints: tuple[str, ...]
    feature_contract_json: str
    feature_contract_fingerprint: str
    alignment_report_json: str
    alignment_report_fingerprint: str
    split: TrainingSplitV1
    leakage_audit: TrainingLeakageAuditV1
    train_feature_assets: tuple[TrainingAssetBindingV1, ...]
    train_label_assets: tuple[TrainingAssetBindingV1, ...]
    trainer_id: Literal["builtin.tiny-json-summary.v1"]
    trainer_revision: str
    trainer_source_sha256: str
    code_sha256: str
    environment: TrainingEnvironmentV1
    seed: int
    hyperparameters: tuple[TrainingHyperparameterV1, ...]
    resource_limits: TrainingResourceLimitsV1
    model_id: str
    model_version: str
    contract_only: Literal[True]
    deterministic: Literal[True]
    uploaded_code_executed: Literal[False]
    network_access_requested: Literal[False]
    gpu_access_requested: Literal[False]
    test_external_read: Literal[False]
    benchmark_performed: Literal[False]
    evidence_created: Literal[False]
    promotion_created: Literal[False]

    @field_validator(
        "factory_registration_fingerprint",
        "pack_candidate_fingerprint",
        "pack_candidate_tree_fingerprint",
        "pack_fingerprint",
        "feature_contract_fingerprint",
        "alignment_report_fingerprint",
        "trainer_source_sha256",
        "code_sha256",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator(
        "pack_id",
        "pack_version",
        "trainer_revision",
        "model_id",
        "model_version",
        mode="before",
    )
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator("feature_mapping_fingerprints", mode="before")
    @classmethod
    def _valid_mapping_fps(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("feature_mapping_fingerprints must be non-empty")
        result = tuple(_sha256(item, "feature_mapping_fingerprints") for item in value)
        if len(set(result)) != len(result):
            raise ValueError("feature mapping fingerprints must be unique")
        return result

    @field_validator("feature_contract_json", "alignment_report_json", mode="before")
    @classmethod
    def _valid_json(cls, value, info):
        return _canonical_json_text(value, info.field_name)

    @field_validator("seed", mode="before")
    @classmethod
    def _valid_seed(cls, value):
        return _nonnegative_int(value, "seed")

    @field_validator("train_feature_assets", "train_label_assets", mode="before")
    @classmethod
    def _valid_assets(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be non-empty")
        return tuple(value)

    @field_validator("hyperparameters", mode="before")
    @classmethod
    def _valid_hyperparameters(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("hyperparameters must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _self_bound(self):
        if hashlib.sha256(self.feature_contract_json.encode()).hexdigest() != self.feature_contract_fingerprint:
            raise ValueError("feature contract fingerprint is stale")
        if hashlib.sha256(self.alignment_report_json.encode()).hexdigest() != self.alignment_report_fingerprint:
            raise ValueError("alignment report fingerprint is stale")
        names = tuple(item.name for item in self.hyperparameters)
        if names != tuple(sorted(names)) or len(set(names)) != len(names):
            raise ValueError("hyperparameters must be unique and sorted")
        feature_ids = tuple(item.asset_id for item in self.train_feature_assets)
        label_ids = tuple(item.asset_id for item in self.train_label_assets)
        if feature_ids != self.split.train_feature_asset_ids or label_ids != self.split.train_label_asset_ids:
            raise ValueError("training assets do not match frozen split allowlist")
        if not self.leakage_audit.passed or self.leakage_audit.split_fingerprint != self.split.fingerprint():
            raise ValueError("job requires a passing audit of its exact split")
        return self


class CandidateCheckpointV1(_TrainingContract):
    schema_version: Literal["vc.candidate-checkpoint.v1"]
    training_job_fingerprint: str
    factory_registration_fingerprint: str
    pack_fingerprint: str
    trainer_revision: str
    trainer_source_sha256: str
    environment_fingerprint: str
    state_path: Literal["checkpoint.json"]
    state_media_type: Literal["application/vnd.praxis-vc.tiny-checkpoint+json"]
    state_size_bytes: int
    state_sha256: str
    safe_load_policy: Literal["data_only"]
    executable_code: Literal[False]
    contract_only: Literal[True]
    real_candidate_training_performed: Literal[False]

    @field_validator(
        "training_job_fingerprint",
        "factory_registration_fingerprint",
        "pack_fingerprint",
        "trainer_source_sha256",
        "environment_fingerprint",
        "state_sha256",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator("trainer_revision", mode="before")
    @classmethod
    def _valid_revision(cls, value):
        return _identifier(value, "trainer_revision")

    @field_validator("state_size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        return _positive_int(value, "state_size_bytes")


class TrainingMetricV1(_TrainingContract):
    schema_version: Literal["vc.training-metric.v1"]
    name: Literal["contract_sample_count", "contract_feature_count", "contract_label_count"]
    value: int
    scope: Literal["contract_only_tiny_dry_run"]
    scientific_metric: Literal[False]
    evidence_eligible: Literal[False]

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        return _positive_int(value, "metric.value")


class TrainingResourceObservationV1(_TrainingContract):
    schema_version: Literal["vc.training-resource-observation.v1"]
    input_bytes: int
    sample_count: int
    feature_count: int
    label_count: int
    checkpoint_bytes: int
    worker_processes: Literal[1]
    cpu_threads: Literal[1]
    network_access_requested: Literal[False]
    gpu_access_requested: Literal[False]

    @field_validator(
        "input_bytes",
        "sample_count",
        "feature_count",
        "label_count",
        "checkpoint_bytes",
        mode="before",
    )
    @classmethod
    def _valid_positive(cls, value, info):
        return _positive_int(value, info.field_name)


class TrainingResultV1(_TrainingContract):
    schema_version: Literal["vc.training-result.v1"]
    training_job_fingerprint: str
    status: Literal["succeeded_contract_only"]
    checkpoint_fingerprint: str
    checkpoint_state_sha256: str
    checkpoint_state_size_bytes: int
    log_sha256: str
    resources: TrainingResourceObservationV1
    metrics: tuple[TrainingMetricV1, ...]
    deterministic_replay: Literal[True]
    contract_only: Literal[True]
    real_candidate_training_performed: Literal[False]
    test_external_read: Literal[False]
    benchmark_performed: Literal[False]
    evidence_created: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator(
        "training_job_fingerprint",
        "checkpoint_fingerprint",
        "checkpoint_state_sha256",
        "log_sha256",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator("checkpoint_state_size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        return _positive_int(value, "checkpoint_state_size_bytes")

    @field_validator("metrics", mode="before")
    @classmethod
    def _valid_metrics(cls, value):
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ValueError("metrics must contain the three contract-only counters")
        return tuple(value)

    @model_validator(mode="after")
    def _metrics_match_resources(self):
        expected = (
            ("contract_sample_count", self.resources.sample_count),
            ("contract_feature_count", self.resources.feature_count),
            ("contract_label_count", self.resources.label_count),
        )
        actual = tuple((metric.name, metric.value) for metric in self.metrics)
        if actual != expected or self.checkpoint_state_size_bytes != self.resources.checkpoint_bytes:
            raise ValueError("result metrics/resources are not exactly cross-bound")
        return self


class CandidateModelArtifactV1(_TrainingContract):
    schema_version: Literal["vc.candidate-model-artifact.v1"]
    model_id: str
    model_version: str
    model_identity_fingerprint: str
    training_job_fingerprint: str
    training_result_fingerprint: str
    checkpoint_fingerprint: str
    factory_registration_fingerprint: str
    pack_fingerprint: str
    trainer_revision: str
    trainer_source_sha256: str
    environment_fingerprint: str
    artifact_path: Literal["checkpoint.json"]
    artifact_size_bytes: int
    artifact_sha256: str
    media_type: Literal["application/vnd.praxis-vc.tiny-checkpoint+json"]
    safe_load_policy: Literal["data_only"]
    status: Literal["candidate"]
    cataloged: Literal[True]
    executable: Literal[False]
    production_registry_written: Literal[False]
    benchmark_performed: Literal[False]
    evidence_created: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator("model_id", "model_version", "trainer_revision", mode="before")
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator(
        "model_identity_fingerprint",
        "training_job_fingerprint",
        "training_result_fingerprint",
        "checkpoint_fingerprint",
        "factory_registration_fingerprint",
        "pack_fingerprint",
        "trainer_source_sha256",
        "environment_fingerprint",
        "artifact_sha256",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)

    @field_validator("artifact_size_bytes", mode="before")
    @classmethod
    def _valid_size(cls, value):
        return _positive_int(value, "artifact_size_bytes")


class CandidateModelCardV1(_TrainingContract):
    schema_version: Literal["vc.candidate-model-card.v1"]
    model_id: str
    model_version: str
    model_identity_fingerprint: str
    artifact_fingerprint: str
    training_job_fingerprint: str
    training_result_fingerprint: str
    checkpoint_fingerprint: str
    factory_registration_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    feature_contract_fingerprint: str
    alignment_report_fingerprint: str
    split_fingerprint: str
    leakage_audit_fingerprint: str
    trainer_revision: str
    trainer_source_sha256: str
    environment_fingerprint: str
    metrics_scope: Literal["contract_only_tiny_dry_run"]
    status: Literal["candidate"]
    cataloged: Literal[True]
    executable: Literal[False]
    production_registry_written: Literal[False]
    benchmark_performed: Literal[False]
    evidence_created: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator(
        "model_id",
        "model_version",
        "pack_id",
        "pack_version",
        "trainer_revision",
        mode="before",
    )
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator(
        "model_identity_fingerprint",
        "artifact_fingerprint",
        "training_job_fingerprint",
        "training_result_fingerprint",
        "checkpoint_fingerprint",
        "factory_registration_fingerprint",
        "pack_fingerprint",
        "feature_contract_fingerprint",
        "alignment_report_fingerprint",
        "split_fingerprint",
        "leakage_audit_fingerprint",
        "trainer_source_sha256",
        "environment_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)


class TrainingCandidateModelV1(_TrainingContract):
    schema_version: Literal["vc.training-candidate-model.v1"]
    model_id: str
    model_version: str
    model_identity_fingerprint: str
    training_job_fingerprint: str
    training_result_fingerprint: str
    checkpoint_fingerprint: str
    artifact_fingerprint: str
    model_card_fingerprint: str
    factory_registration_fingerprint: str
    pack_fingerprint: str
    trainer_revision: str
    trainer_source_sha256: str
    environment_fingerprint: str
    status: Literal["candidate_cataloged_contract_only"]
    candidate_cataloged: Literal[True]
    executable: Literal[False]
    production_registry_written: Literal[False]
    benchmark_performed: Literal[False]
    evidence_created: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]

    @field_validator("model_id", "model_version", "trainer_revision", mode="before")
    @classmethod
    def _valid_ids(cls, value, info):
        return _identifier(value, info.field_name)

    @field_validator(
        "model_identity_fingerprint",
        "training_job_fingerprint",
        "training_result_fingerprint",
        "checkpoint_fingerprint",
        "artifact_fingerprint",
        "model_card_fingerprint",
        "factory_registration_fingerprint",
        "pack_fingerprint",
        "trainer_source_sha256",
        "environment_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_hashes(cls, value, info):
        return _sha256(value, info.field_name)


@dataclass(frozen=True)
class _ResolvedFactoryPack:
    registration: FactoryRegisteredPackV1
    candidate: PackCandidateV1
    manifest: PackManifest
    root: Path


@dataclass(frozen=True)
class TrainingRunBundle:
    job: TrainingJobV1
    checkpoint: CandidateCheckpointV1
    result: TrainingResultV1
    artifact: CandidateModelArtifactV1
    model_card: CandidateModelCardV1
    candidate_model: TrainingCandidateModelV1

    def to_dict(self) -> dict[str, Any]:
        _validate_bundle(self)
        return {
            "schema_version": "vc.training-run-bundle.v1",
            "job": self.job.to_dict(),
            "checkpoint": self.checkpoint.to_dict(),
            "result": self.result.to_dict(),
            "artifact": self.artifact.to_dict(),
            "model_card": self.model_card.to_dict(),
            "candidate_model": self.candidate_model.to_dict(),
        }


def trainer_source_sha256() -> str:
    """Return the exact fixed worker source identity used by this runtime."""

    payload = _read_regular_path(
        Path(__file__).with_name(_WORKER_NAME),
        max_bytes=_MAX_TRUSTED_SOURCE_BYTES,
    )
    return hashlib.sha256(payload).hexdigest()


def _installed_distributions_sha256() -> str:
    distributions = []
    for distribution in importlib.metadata.distributions():
        try:
            name = distribution.metadata.get("Name")
            version = distribution.version
        except (OSError, UnicodeError, ValueError):
            path = getattr(distribution, "_path", None)
            distributions.append(("unreadable-dist-info", "" if path is None else Path(path).name))
            continue
        if name:
            distributions.append((name.casefold().replace("_", "-"), version))
    return _fingerprint(sorted(set(distributions)))


def capture_training_environment(*, dependency_lock_sha256: str) -> TrainingEnvironmentV1:
    """Capture only deterministic, allowlisted runtime facts; never environment variables."""

    return TrainingEnvironmentV1(
        schema_version="vc.training-environment.v1",
        environment_id="local-stdlib-cpu",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        implementation=platform.python_implementation().lower(),
        platform_system=platform.system().lower(),
        machine=platform.machine().lower(),
        declared_dependency_lock_sha256=_sha256(
            dependency_lock_sha256,
            "dependency_lock_sha256",
        ),
        installed_distributions_sha256=_installed_distributions_sha256(),
        cpu_threads=1,
        network_access_requested=False,
        gpu_access_requested=False,
    )


def training_code_sha256() -> str:
    """Bind the curated security-critical P20 source set without Git state."""

    package_root = Path(__file__).parents[2]
    identities = []
    for relative in _TRAINING_SOURCE_PATHS:
        payload = _read_regular_path(
            package_root / PurePosixPath(relative),
            max_bytes=_MAX_TRUSTED_SOURCE_BYTES,
        )
        identities.append(
            {
                "path": relative,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return _fingerprint(identities)


def _read_candidate_file(
    root: Path,
    identity: CandidateFileIdentityV1,
    *,
    max_bytes: int,
) -> bytes:
    return _read_root_relative_file(
        root,
        identity.path,
        max_bytes=max_bytes,
        expected_size=identity.size_bytes,
        expected_sha256=identity.sha256,
    )


def _resolve_factory_pack(
    index: PackIndex,
    pack_id: str,
    pack_version: str,
    registration_fingerprint: str,
) -> _ResolvedFactoryPack:
    if type(index) is not PackIndex:
        raise TrainingPipelineError("index must be exact PackIndex")
    if not index.explicit_index_path or not index.path.is_absolute():
        raise TrainingPipelineError("training requires an explicit absolute Pack index")
    try:
        if (
            index.path.is_symlink()
            or index.path.parent.is_symlink()
            or not index.path.parent.is_dir()
            or index.path.parent.resolve(strict=True) != index.path.parent
        ):
            raise TrainingPipelineError("Pack index path must be canonical and non-symlink")
        expected_fingerprint = _sha256(registration_fingerprint, "registration_fingerprint")
        provenance = index.factory_provenance(pack_id, pack_version)
        indexed_fingerprint = provenance["factory_registration_fingerprint"]
        store_root = provenance["factory_store_root"]
        if indexed_fingerprint != expected_fingerprint:
            raise TrainingPipelineError("training job registration does not match Pack index")
        store = PackFactoryStore.open(Path(store_root))
        registration = store.verify_registration(expected_fingerprint)
        candidate = store.get(PackCandidateV1, registration.candidate_fingerprint)
        root = Path(provenance["root"])
        if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
            raise TrainingPipelineError("factory Pack root must be canonical and non-symlink")
        manifest_identity = next(
            (item for item in candidate.candidate_files if item.path == "manifest.yaml"),
            None,
        )
        if manifest_identity is None:
            raise TrainingPipelineError("factory candidate has no manifest identity")
        manifest_payload = _read_candidate_file(
            root,
            manifest_identity,
            max_bytes=2 * 1024 * 1024,
        )
        manifest = load_manifest_bytes(manifest_payload)
    except TrainingPipelineError:
        raise
    except (OSError, ValueError) as exc:
        raise TrainingPipelineError("factory-registered Pack verification failed") from exc
    if (
        provenance["pack_id"] != pack_id
        or provenance["pack_version"] != pack_version
        or provenance["pack_fingerprint"] != registration.pack_fingerprint
        or manifest.pack_id != pack_id
        or manifest.pack_version != pack_version
        or manifest.fingerprint() != registration.pack_fingerprint
        or registration.pack_id != candidate.pack_id
        or registration.pack_version != candidate.pack_version
        or registration.pack_fingerprint != candidate.manifest_fingerprint
        or candidate.candidate_tree_fingerprint != _fingerprint([item.to_dict() for item in candidate.candidate_files])
    ):
        raise TrainingPipelineError("factory registration/candidate/current Pack chain is mixed")
    return _ResolvedFactoryPack(
        registration=registration,
        candidate=candidate,
        manifest=manifest,
        root=root,
    )


def _asset_by_id(resolved: _ResolvedFactoryPack, asset_id: str):
    asset_id = _identifier(asset_id, "asset_id")
    matches = [asset for asset in resolved.manifest.assets if asset.id == asset_id]
    if len(matches) != 1:
        raise TrainingPipelineError("training asset must be uniquely declared by the registered Pack")
    return matches[0]


def _asset_binding(resolved: _ResolvedFactoryPack, asset_id: str) -> TrainingAssetBindingV1:
    asset = _asset_by_id(resolved, asset_id)
    if asset.media_type != "application/json" or asset.size_bytes <= 0:
        raise TrainingPipelineError("training assets must be non-empty application/json")
    return TrainingAssetBindingV1(
        schema_version="vc.training-asset-binding.v1",
        asset_id=asset.id,
        media_type=asset.media_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
    )


def _read_bound_asset(
    resolved: _ResolvedFactoryPack,
    binding: TrainingAssetBindingV1,
    *,
    max_bytes: int,
) -> bytes:
    binding = _revalidate(binding, TrainingAssetBindingV1, "asset binding")
    asset = _asset_by_id(resolved, binding.asset_id)
    expected = (binding.media_type, binding.size_bytes, binding.sha256)
    if (asset.media_type, asset.size_bytes, asset.sha256) != expected:
        raise TrainingPipelineError("training asset binding drifted from Pack manifest")
    return _read_root_relative_file(
        resolved.root,
        asset.path,
        max_bytes=max_bytes,
        expected_size=binding.size_bytes,
        expected_sha256=binding.sha256,
    )


def _strict_identifier_array(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not list or (not value and not allow_empty):
        raise TrainingPipelineError(f"{field} must be an array")
    try:
        values = tuple(_identifier(item, field) for item in value)
    except ValueError as exc:
        raise TrainingPipelineError(f"invalid {field}") from exc
    if len(set(values)) != len(values):
        raise TrainingPipelineError(f"{field} must not contain duplicates")
    return values


def _strict_text_array(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not list or (not value and not allow_empty):
        raise TrainingPipelineError(f"{field} must be an array")
    try:
        values = tuple(_text(item, field) for item in value)
    except ValueError as exc:
        raise TrainingPipelineError(f"invalid {field}") from exc
    if len(set(values)) != len(values):
        raise TrainingPipelineError(f"{field} must not contain duplicates")
    return values


def _split_and_audit(
    resolved: _ResolvedFactoryPack,
    split_asset_id: str,
    train_feature_asset_ids: tuple[str, ...],
    train_label_asset_ids: tuple[str, ...],
) -> tuple[TrainingSplitV1, TrainingLeakageAuditV1]:
    split_binding = _asset_binding(resolved, split_asset_id)
    payload = _read_bound_asset(resolved, split_binding, max_bytes=_MAX_SPLIT_BYTES)
    value = _json_object(payload, "training split metadata")
    if payload != _canonical_bytes(value):
        raise TrainingPipelineError("training split metadata bytes must be canonical JSON")
    if (
        set(value)
        != {
            "schema_version",
            "split_name",
            "split_field",
            "leakage_guard",
            "rows",
            "label_assets",
        }
        or value["schema_version"] != "vc.training-split-asset.v1"
    ):
        raise TrainingPipelineError("invalid training split metadata contract")
    manifest_split = resolved.manifest.split
    split_name = _identifier(value["split_name"], "split_name")
    split_field = _identifier(value["split_field"], "split_field")
    leakage_guard = _strict_identifier_array(value["leakage_guard"], "leakage_guard")
    if (
        split_name != manifest_split.name
        or split_field != manifest_split.field
        or leakage_guard != manifest_split.leakage_guard
    ):
        raise TrainingPipelineError("training split metadata does not match Pack manifest")
    partitions = tuple(manifest_split.values)
    if "train" not in partitions:
        raise TrainingPipelineError("registered Pack has no frozen train partition")

    rows = value["rows"]
    if type(rows) is not list or not rows:
        raise TrainingPipelineError("training split rows must be non-empty")
    sample_ids: list[str] = []
    train_sample_ids: list[str] = []
    seen_partitions: set[str] = set()
    group_partitions: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        if type(row) is not dict or set(row) != {"sample_id", "partition", "leakage_groups"}:
            raise TrainingPipelineError("invalid training split row")
        sample_id = _identifier(row["sample_id"], "sample_id")
        partition = _identifier(row["partition"], "partition")
        groups = row["leakage_groups"]
        if sample_id in sample_ids or partition not in partitions:
            raise TrainingPipelineError("training split row identity is invalid")
        if type(groups) is not dict or set(groups) != set(leakage_guard):
            raise TrainingPipelineError("training split leakage groups are incomplete or reordered")
        sample_ids.append(sample_id)
        seen_partitions.add(partition)
        if partition == "train":
            train_sample_ids.append(sample_id)
        for field in leakage_guard:
            group_value = groups[field]
            if field == "target_ids":
                group_values = _strict_text_array(
                    group_value,
                    f"leakage_groups.{field}",
                    allow_empty=True,
                )
            else:
                group_values = (_text(group_value, f"leakage_groups.{field}"),)
            for canonical_group in group_values:
                group_partitions.setdefault((field, canonical_group), set()).add(partition)
    if not train_sample_ids:
        raise TrainingPipelineError("training split has no train samples")
    if seen_partitions != set(partitions):
        raise TrainingPipelineError("training split metadata does not cover every declared partition")

    label_assets = value["label_assets"]
    if type(label_assets) is not dict or set(label_assets) != {"train", "validation", "test", "external"}:
        raise TrainingPipelineError("training split label asset map is invalid")
    declared_labels = {
        key: _strict_identifier_array(label_assets[key], f"label_assets.{key}", allow_empty=True)
        for key in ("train", "validation", "test", "external")
    }
    label_id_sequence = tuple(
        asset_id for key in ("train", "validation", "test", "external") for asset_id in declared_labels[key]
    )
    if len(set(label_id_sequence)) != len(label_id_sequence):
        raise TrainingPipelineError("partition label asset allowlists must be pairwise disjoint")
    feature_ids = tuple(_identifier(item, "train_feature_asset_ids") for item in train_feature_asset_ids)
    label_ids = tuple(_identifier(item, "train_label_asset_ids") for item in train_label_asset_ids)
    if (
        not feature_ids
        or not label_ids
        or len(set(feature_ids)) != len(feature_ids)
        or len(set(label_ids)) != len(label_ids)
    ):
        raise TrainingPipelineError("training feature/label allowlists must be non-empty and unique")
    if label_ids != declared_labels["train"]:
        raise TrainingPipelineError("training labels do not match split train allowlist")
    all_label_ids = set(label_id_sequence)
    if set(feature_ids).intersection(all_label_ids) or split_asset_id in set(feature_ids).union(all_label_ids):
        raise TrainingPipelineError("split, feature and partition label assets must be disjoint")
    all_asset_ids = set(feature_ids).union(all_label_ids, {split_asset_id})
    for asset_id in all_asset_ids:
        _asset_by_id(resolved, asset_id)

    split = TrainingSplitV1(
        schema_version="vc.training-split.v1",
        split_asset=split_binding,
        split_name=split_name,
        split_field=split_field,
        partitions=partitions,
        leakage_guard=leakage_guard,
        train_sample_ids=tuple(train_sample_ids),
        train_feature_asset_ids=feature_ids,
        train_label_asset_ids=label_ids,
        validation_label_asset_ids=declared_labels["validation"],
        test_label_asset_ids=declared_labels["test"],
        external_label_asset_ids=declared_labels["external"],
        random_split_performed=False,
        test_external_read=False,
    )
    overlaps = []
    for (field, group_value), seen_partitions in sorted(group_partitions.items()):
        if len(seen_partitions) > 1:
            overlaps.append(
                LeakageOverlapV1(
                    schema_version="vc.training-leakage-overlap.v1",
                    group_field=field,
                    group_value_sha256=hashlib.sha256(group_value.encode()).hexdigest(),
                    partitions=tuple(sorted(seen_partitions)),
                )
            )
    audit = TrainingLeakageAuditV1(
        schema_version="vc.training-leakage-audit.v1",
        split_fingerprint=split.fingerprint(),
        checked_group_fields=leakage_guard,
        checked_partitions=partitions,
        overlaps=tuple(overlaps),
        metadata_only=True,
        performed_before_label_read=True,
        source_observation_binding_performed=False,
        scientific_validation_performed=False,
        passed=not overlaps,
    )
    if not audit.passed:
        raise TrainingPipelineError("training split leakage audit failed")
    return split, audit


def _feature_documents(
    feature_contract: ModelFeatureContract,
    alignment_report: AlignmentReport,
) -> tuple[str, str, str, str]:
    if type(feature_contract) is not ModelFeatureContract or type(alignment_report) is not AlignmentReport:
        raise TrainingPipelineError("feature contract and alignment report must use exact canonical types")
    try:
        feature_value = feature_contract.model_dump(mode="json")
        reparsed = ModelFeatureContract.from_dict(feature_value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise TrainingPipelineError("invalid model feature contract") from exc
    if reparsed != feature_contract or alignment_report.contract_fingerprint != feature_contract.fingerprint():
        raise TrainingPipelineError("alignment report does not bind the exact feature contract")
    if (
        feature_contract.reorder
        or feature_contract.drop
        or feature_contract.fill
        or feature_contract.mapping_asset is not None
    ):
        raise TrainingPipelineError("P20 tiny runner forbids feature transformations")
    feature_json = _canonical_bytes(feature_value).decode("utf-8")
    alignment_value = alignment_report.to_dict()
    _verify_alignment_value(alignment_value, feature_contract)
    alignment_json = _canonical_bytes(alignment_value).decode("utf-8")
    return (
        feature_json,
        hashlib.sha256(feature_json.encode()).hexdigest(),
        alignment_json,
        hashlib.sha256(alignment_json.encode()).hexdigest(),
    )


def _verify_alignment_value(alignment: dict[str, Any], contract: ModelFeatureContract) -> None:
    if set(alignment) != {
        "schema_version",
        "contract_fingerprint",
        "source_feature_ids",
        "target_feature_ids",
        "source_shape",
        "target_shape",
        "steps",
        "mapping_asset",
    }:
        raise TrainingPipelineError("training alignment report has invalid fields")
    expected_features = list(contract.feature_ids)
    if (
        alignment["schema_version"] != "vc.alignment-report.v1"
        or alignment["contract_fingerprint"] != contract.fingerprint()
        or alignment["source_feature_ids"] != expected_features
        or alignment["target_feature_ids"] != expected_features
        or alignment["steps"] != []
        or alignment["mapping_asset"] is not None
    ):
        raise TrainingPipelineError("P20 tiny runner requires exact identity-only alignment")
    for field in ("source_shape", "target_shape"):
        shape = alignment[field]
        if type(shape) is not list or len(shape) != 2 or any(type(item) is not int or item <= 0 for item in shape):
            raise TrainingPipelineError("training alignment shape is invalid")
    if alignment["source_shape"] != alignment["target_shape"]:
        raise TrainingPipelineError("P20 tiny runner cannot transform alignment shape")


def _verify_pack_feature_binding(
    resolved: _ResolvedFactoryPack,
    contract: ModelFeatureContract,
) -> None:
    manifest = resolved.manifest
    if manifest.schema_version == "vc.pack.v0.2":
        if manifest.modality is None or manifest.feature_namespace is None or manifest.feature_semantics is None:
            raise TrainingPipelineError("registered Pack primary feature declarations are incomplete")
        modality_key = "primary"
        expected_modality = manifest.modality.name
        namespace = manifest.feature_namespace
        id_format = manifest.feature_semantics.id_format
    else:
        if manifest.multiomics is None:
            raise TrainingPipelineError("registered multi-omics Pack declarations are incomplete")
        matches = [item for item in manifest.multiomics.modalities if item.key == contract.modality]
        if len(matches) != 1:
            raise TrainingPipelineError("feature contract modality does not identify one Pack modality")
        modality = matches[0]
        modality_key = modality.key
        expected_modality = modality.key
        namespace = modality.feature_namespace
        id_format = modality.feature_semantics.id_format
    summaries = [item for item in resolved.candidate.feature_mappings if item.modality_key == modality_key]
    if len(summaries) != 1:
        raise TrainingPipelineError("registered Pack has no unique applicable feature mapping")
    summary = summaries[0]
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
    expected_order = _fingerprint(list(contract.feature_ids))
    if (
        contract.modality != expected_modality
        or contract.feature_namespace.name != namespace.name
        or contract.feature_namespace.version != namespace.version
        or contract.feature_id_format != id_format
        or summary.source_namespace.name != contract.feature_namespace.name
        or summary.source_namespace.version != contract.feature_namespace.version
        or summary.target_namespace != summary.source_namespace
        or summary.source_feature_count != len(contract.feature_ids)
        or summary.target_feature_count != len(contract.feature_ids)
        or summary.source_order_fingerprint != expected_order
        or summary.target_order_fingerprint != expected_order
        or any(issues)
        or not summary.order_preserved
    ):
        raise TrainingPipelineError("feature contract does not match the exact P19 identity mapping")


def _hyperparameters(value: Any) -> tuple[TrainingHyperparameterV1, ...]:
    if type(value) is not dict:
        raise TrainingPipelineError("hyperparameters must be a JSON object")
    items = []
    for name in sorted(value):
        try:
            name = _identifier(name, "hyperparameter name")
        except ValueError as exc:
            raise TrainingPipelineError("hyperparameter names must be canonical identifiers") from exc
        item = value[name]
        if type(item) is bool:
            value_type = "boolean"
        elif type(item) is int:
            value_type = "integer"
        elif type(item) is float and math.isfinite(item):
            value_type = "number"
        else:
            raise TrainingPipelineError("hyperparameters accept only finite typed scalars")
        items.append(
            TrainingHyperparameterV1(
                schema_version="vc.training-hyperparameter.v1",
                name=name,
                value_type=value_type,
                value=item,
            )
        )
    return tuple(items)


def _verify_allowlisted_asset_bytes(
    resolved: _ResolvedFactoryPack,
    bindings: tuple[TrainingAssetBindingV1, ...],
    *,
    max_bytes: int,
) -> None:
    consumed = 0
    for binding in bindings:
        remaining = max_bytes - consumed
        if remaining <= 0:
            raise TrainingPipelineError("allowlisted training assets exceed the input byte limit")
        consumed += len(_read_bound_asset(resolved, binding, max_bytes=remaining))


def bind_training_job(
    *,
    index: PackIndex,
    pack_id: str,
    pack_version: str,
    registration_fingerprint: str,
    feature_contract: ModelFeatureContract,
    alignment_report: AlignmentReport,
    split_asset_id: str,
    train_feature_asset_ids: tuple[str, ...],
    train_label_asset_ids: tuple[str, ...],
    trainer_revision: str,
    trainer_source_sha256: str,
    code_sha256: str,
    environment: TrainingEnvironmentV1,
    seed: int,
    hyperparameters: dict[str, int | float | bool],
    resource_limits: TrainingResourceLimitsV1,
    model_id: str,
    model_version: str,
) -> TrainingJobV1:
    """Freeze one deterministic job from a live exact P19 registration."""

    pack_id = _identifier(pack_id, "pack_id")
    pack_version = _identifier(pack_version, "pack_version")
    resolved = _resolve_factory_pack(index, pack_id, pack_version, registration_fingerprint)
    environment = _revalidate(environment, TrainingEnvironmentV1, "training environment")
    resource_limits = _revalidate(resource_limits, TrainingResourceLimitsV1, "resource limits")
    current_environment = capture_training_environment(
        dependency_lock_sha256=environment.declared_dependency_lock_sha256,
    )
    if environment != current_environment:
        raise TrainingPipelineError("training environment does not match this runtime")
    if environment.cpu_threads != resource_limits.cpu_threads:
        raise TrainingPipelineError("environment and resource CPU limits disagree")
    if trainer_revision != TRAINER_REVISION or trainer_source_sha256 != globals()["trainer_source_sha256"]():
        raise TrainingPipelineError("training job must bind the fixed trusted trainer")
    if code_sha256 != training_code_sha256():
        raise TrainingPipelineError("training job code identity does not match this runtime")
    split, audit = _split_and_audit(
        resolved,
        split_asset_id,
        tuple(train_feature_asset_ids),
        tuple(train_label_asset_ids),
    )
    feature_json, feature_fp, alignment_json, alignment_fp = _feature_documents(
        feature_contract,
        alignment_report,
    )
    expected_shape = (len(split.train_sample_ids), len(feature_contract.feature_ids))
    if alignment_report.source_shape != expected_shape or alignment_report.target_shape != expected_shape:
        raise TrainingPipelineError("feature alignment shape does not match the frozen split/contract")
    if feature_contract.model_id != model_id or feature_contract.model_version != model_version:
        raise TrainingPipelineError("feature contract model identity does not match training job")
    manifest = resolved.manifest
    if (
        feature_contract.taxonomy_id != manifest.taxon.ontology_id
        or feature_contract.assembly_accession != manifest.assembly.accession
    ):
        raise TrainingPipelineError("feature contract taxon/assembly does not match registered Pack")
    _verify_pack_feature_binding(resolved, feature_contract)
    mapping_fingerprints = tuple(item.document_fingerprint for item in resolved.candidate.feature_mappings)
    feature_assets = tuple(_asset_binding(resolved, item) for item in split.train_feature_asset_ids)
    label_assets = tuple(_asset_binding(resolved, item) for item in split.train_label_asset_ids)
    _verify_allowlisted_asset_bytes(
        resolved,
        feature_assets + label_assets,
        max_bytes=resource_limits.max_input_bytes,
    )
    job = TrainingJobV1(
        schema_version="vc.training-job.v1",
        factory_registration_fingerprint=resolved.registration.fingerprint(),
        pack_candidate_fingerprint=resolved.candidate.fingerprint(),
        pack_candidate_tree_fingerprint=resolved.candidate.candidate_tree_fingerprint,
        pack_id=pack_id,
        pack_version=pack_version,
        pack_fingerprint=resolved.registration.pack_fingerprint,
        feature_mapping_fingerprints=mapping_fingerprints,
        feature_contract_json=feature_json,
        feature_contract_fingerprint=feature_fp,
        alignment_report_json=alignment_json,
        alignment_report_fingerprint=alignment_fp,
        split=split,
        leakage_audit=audit,
        train_feature_assets=feature_assets,
        train_label_assets=label_assets,
        trainer_id=_TRAINER_ID,
        trainer_revision=TRAINER_REVISION,
        trainer_source_sha256=trainer_source_sha256,
        code_sha256=code_sha256,
        environment=environment,
        seed=_nonnegative_int(seed, "seed"),
        hyperparameters=_hyperparameters(hyperparameters),
        resource_limits=resource_limits,
        model_id=_identifier(model_id, "model_id"),
        model_version=_identifier(model_version, "model_version"),
        contract_only=True,
        deterministic=True,
        uploaded_code_executed=False,
        network_access_requested=False,
        gpu_access_requested=False,
        test_external_read=False,
        benchmark_performed=False,
        evidence_created=False,
        promotion_created=False,
    )
    _verify_feature_documents(job)
    return job


def load_training_job(path: str | Path) -> TrainingJobV1:
    """Load an exact canonical job file without accepting duplicate keys or symlinks."""

    candidate = Path(path)
    payload = _read_regular_path(candidate, max_bytes=_MAX_JOB_BYTES)
    value = _json_object(payload, "training job")
    job = TrainingJobV1.from_dict(value)
    if payload != _canonical_bytes(job.to_dict()) + b"\n":
        raise TrainingPipelineError("training job file bytes are not canonical")
    return job


def _verify_feature_documents(job: TrainingJobV1) -> ModelFeatureContract:
    feature_value = _json_object(job.feature_contract_json.encode(), "feature contract")
    try:
        contract = ModelFeatureContract.from_dict(feature_value)
    except (TypeError, ValueError) as exc:
        raise TrainingPipelineError("training job feature contract is invalid") from exc
    if contract.fingerprint() != job.feature_contract_fingerprint:
        raise TrainingPipelineError("training job feature contract identity drifted")
    if contract.model_id != job.model_id or contract.model_version != job.model_version:
        raise TrainingPipelineError("training job and feature contract model identities differ")
    if contract.reorder or contract.drop or contract.fill or contract.mapping_asset is not None:
        raise TrainingPipelineError("P20 tiny runner forbids feature transformations")
    alignment = _json_object(job.alignment_report_json.encode(), "alignment report")
    _verify_alignment_value(alignment, contract)
    expected_shape = [len(job.split.train_sample_ids), len(contract.feature_ids)]
    if alignment["source_shape"] != expected_shape or alignment["target_shape"] != expected_shape:
        raise TrainingPipelineError("training job alignment shape drifted from split/contract")
    if hashlib.sha256(job.alignment_report_json.encode()).hexdigest() != job.alignment_report_fingerprint:
        raise TrainingPipelineError("training alignment report identity drifted")
    return contract


def _verify_job_bindings(job: TrainingJobV1, index: PackIndex) -> _ResolvedFactoryPack:
    job = _revalidate(job, TrainingJobV1, "training job")
    resolved = _resolve_factory_pack(
        index,
        job.pack_id,
        job.pack_version,
        job.factory_registration_fingerprint,
    )
    expected = (
        resolved.registration.fingerprint(),
        resolved.candidate.fingerprint(),
        resolved.candidate.candidate_tree_fingerprint,
        resolved.registration.pack_fingerprint,
        tuple(item.document_fingerprint for item in resolved.candidate.feature_mappings),
    )
    actual = (
        job.factory_registration_fingerprint,
        job.pack_candidate_fingerprint,
        job.pack_candidate_tree_fingerprint,
        job.pack_fingerprint,
        job.feature_mapping_fingerprints,
    )
    if actual != expected:
        raise TrainingPipelineError("training job does not bind the current exact factory chain")
    if (
        job.trainer_id != _TRAINER_ID
        or job.trainer_revision != TRAINER_REVISION
        or job.trainer_source_sha256 != trainer_source_sha256()
        or job.code_sha256 != training_code_sha256()
    ):
        raise TrainingPipelineError("training job trusted code identity does not match runtime")
    current_environment = capture_training_environment(
        dependency_lock_sha256=job.environment.declared_dependency_lock_sha256,
    )
    if job.environment != current_environment:
        raise TrainingPipelineError("training job environment does not match this runtime")
    contract = _verify_feature_documents(job)
    if (
        contract.model_id != job.model_id
        or contract.model_version != job.model_version
        or contract.taxonomy_id != resolved.manifest.taxon.ontology_id
        or contract.assembly_accession != resolved.manifest.assembly.accession
    ):
        raise TrainingPipelineError("training job feature semantics drifted from Pack/model identity")
    _verify_pack_feature_binding(resolved, contract)
    split, audit = _split_and_audit(
        resolved,
        job.split.split_asset.asset_id,
        job.split.train_feature_asset_ids,
        job.split.train_label_asset_ids,
    )
    if split != job.split or audit != job.leakage_audit:
        raise TrainingPipelineError("training split or leakage audit identity drifted")
    if tuple(_asset_binding(resolved, item.asset_id) for item in job.train_feature_assets) != job.train_feature_assets:
        raise TrainingPipelineError("training feature asset binding drifted")
    if tuple(_asset_binding(resolved, item.asset_id) for item in job.train_label_assets) != job.train_label_assets:
        raise TrainingPipelineError("training label asset binding drifted")
    _verify_allowlisted_asset_bytes(
        resolved,
        job.train_feature_assets + job.train_label_assets,
        max_bytes=job.resource_limits.max_input_bytes,
    )
    return resolved


def _number(value: Any, field: str) -> float:
    value = _finite_number(value, field)
    try:
        result = float(value)
    except OverflowError as exc:
        raise TrainingPipelineError(f"{field} must fit a finite float") from exc
    if not math.isfinite(result):
        raise TrainingPipelineError(f"{field} must fit a finite float")
    return result


def _materialize_training_input(
    job: TrainingJobV1,
    resolved: _ResolvedFactoryPack,
) -> tuple[bytes, int, int, int, int]:
    """Read only allowlisted train assets after the leakage gate has passed."""

    limits = job.resource_limits
    total_input_bytes = 0
    feature_rows: dict[str, list[float]] = {}
    ordered_samples: tuple[str, ...] | None = None
    feature_ids: list[str] = []
    for binding in job.train_feature_assets:
        remaining = limits.max_input_bytes - total_input_bytes
        if remaining <= 0:
            raise TrainingPipelineError("training input exceeds byte limit")
        payload = _read_bound_asset(resolved, binding, max_bytes=remaining)
        total_input_bytes += len(payload)
        value = _json_object(payload, "tiny training features")
        if payload != _canonical_bytes(value):
            raise TrainingPipelineError("tiny training feature bytes must be canonical JSON")
        if set(value) != {"schema_version", "feature_ids", "samples"} or value["schema_version"] != (
            "vc.tiny-training-features.v1"
        ):
            raise TrainingPipelineError("invalid tiny training feature contract")
        current_feature_ids = _strict_text_array(value["feature_ids"], "feature_ids")
        if set(feature_ids).intersection(current_feature_ids):
            raise TrainingPipelineError("tiny training feature assets overlap")
        feature_ids.extend(current_feature_ids)
        samples = value["samples"]
        if type(samples) is not list or not samples:
            raise TrainingPipelineError("tiny training feature samples must be non-empty")
        current_samples = []
        for sample in samples:
            if type(sample) is not dict or set(sample) != {"sample_id", "values"}:
                raise TrainingPipelineError("invalid tiny training feature sample")
            sample_id = _identifier(sample["sample_id"], "sample_id")
            values = sample["values"]
            if type(values) is not list or len(values) != len(current_feature_ids):
                raise TrainingPipelineError("tiny training feature width is invalid")
            if sample_id in current_samples:
                raise TrainingPipelineError("tiny training feature sample ids must be unique")
            current_samples.append(sample_id)
            feature_rows.setdefault(sample_id, []).extend(_number(item, "training feature") for item in values)
        if ordered_samples is None:
            ordered_samples = tuple(current_samples)
        elif tuple(current_samples) != ordered_samples:
            raise TrainingPipelineError("tiny training feature assets have different sample order")

    label_rows: dict[str, list[float]] = {}
    label_count = 0
    for binding in job.train_label_assets:
        remaining = limits.max_input_bytes - total_input_bytes
        if remaining <= 0:
            raise TrainingPipelineError("training input exceeds byte limit")
        payload = _read_bound_asset(resolved, binding, max_bytes=remaining)
        total_input_bytes += len(payload)
        value = _json_object(payload, "tiny training labels")
        if payload != _canonical_bytes(value):
            raise TrainingPipelineError("tiny training label bytes must be canonical JSON")
        if set(value) != {"schema_version", "samples"} or value["schema_version"] != "vc.tiny-training-labels.v1":
            raise TrainingPipelineError("invalid tiny training label contract")
        samples = value["samples"]
        if type(samples) is not list or not samples:
            raise TrainingPipelineError("tiny training label samples must be non-empty")
        current_samples = []
        for sample in samples:
            if type(sample) is not dict or set(sample) != {"sample_id", "value"}:
                raise TrainingPipelineError("invalid tiny training label sample")
            sample_id = _identifier(sample["sample_id"], "sample_id")
            if sample_id in current_samples:
                raise TrainingPipelineError("tiny training label sample ids must be unique")
            current_samples.append(sample_id)
            label_rows.setdefault(sample_id, []).append(_number(sample["value"], "training label"))
        if ordered_samples is None or tuple(current_samples) != ordered_samples:
            raise TrainingPipelineError("tiny training labels do not match feature sample order")
        label_count += 1

    if ordered_samples is None:
        raise TrainingPipelineError("training feature samples are missing")
    if ordered_samples != job.split.train_sample_ids:
        raise TrainingPipelineError("materialized samples do not match audited train split")
    contract = _verify_feature_documents(job)
    if tuple(feature_ids) != tuple(contract.feature_ids):
        raise TrainingPipelineError("materialized feature order does not match frozen contract")
    if any(sample_id not in label_rows for sample_id in ordered_samples):
        raise TrainingPipelineError("training labels are incomplete")
    sample_count = len(ordered_samples)
    feature_count = len(feature_ids)
    if sample_count > limits.max_samples or feature_count > limits.max_features or label_count > limits.max_labels:
        raise TrainingPipelineError("materialized training data exceeds resource limits")
    alignment = _json_object(job.alignment_report_json.encode(), "alignment report")
    if alignment["target_shape"] != [sample_count, feature_count]:
        raise TrainingPipelineError("alignment shape does not match materialized training data")
    worker_input = {
        "schema_version": "vc.tiny-trainer-input.v1",
        "job_fingerprint": job.fingerprint(),
        "seed": job.seed,
        "hyperparameters": [item.to_dict() for item in job.hyperparameters],
        "samples": [
            {
                "sample_id": sample_id,
                "features": feature_rows[sample_id],
                "labels": label_rows[sample_id],
            }
            for sample_id in ordered_samples
        ],
    }
    worker_bytes = _canonical_bytes(worker_input)
    if len(worker_bytes) > limits.max_input_bytes:
        raise TrainingPipelineError("isolated worker input exceeds resource limit")
    return worker_bytes, total_input_bytes, sample_count, feature_count, label_count


def _run_fixed_worker(
    payload: bytes,
    *,
    timeout_seconds: float,
    max_checkpoint_bytes: int,
    trainer_source_hash: str,
) -> bytes:
    input_value = _json_object(payload, "fixed worker input")
    samples = input_value.get("samples")
    if type(samples) is not list or not samples:
        raise TrainingPipelineError("fixed worker input has no samples")
    try:
        sample_ids = [sample["sample_id"] for sample in samples]
        expected_feature_count = len(samples[0]["features"])
        expected_label_count = len(samples[0]["labels"])
    except (KeyError, TypeError) as exc:
        raise TrainingPipelineError("fixed worker input shape is invalid") from exc
    expected = {
        "job_fingerprint": input_value.get("job_fingerprint"),
        "seed": input_value.get("seed"),
        "sample_ids_sha256": hashlib.sha256(_canonical_bytes(sample_ids)).hexdigest(),
        "sample_count": len(samples),
        "feature_count": expected_feature_count,
        "label_count": expected_label_count,
    }
    worker_source = _read_regular_path(
        Path(__file__).with_name(_WORKER_NAME),
        max_bytes=_MAX_TRUSTED_SOURCE_BYTES,
    )
    if hashlib.sha256(worker_source).hexdigest() != trainer_source_hash:
        raise TrainingPipelineError("fixed training worker identity changed")
    environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.defpath,
        "PYTHONHASHSEED": "0",
    }
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix="praxis-p20-worker-") as working_directory:
            worker_root = Path(working_directory)
            worker = worker_root / _WORKER_NAME
            stdout_path = worker_root / "checkpoint.out"
            stderr_path = worker_root / "worker.err"
            _write_new_file(worker_root, _WORKER_NAME, worker_source)
            with stdout_path.open("xb") as stdout_stream, stderr_path.open("xb") as stderr_stream:
                process = subprocess.Popen(
                    [sys.executable, "-I", "-S", str(worker)],
                    stdin=subprocess.PIPE,
                    stdout=stdout_stream,
                    stderr=stderr_stream,
                    cwd=working_directory,
                    env=environment,
                    start_new_session=True,
                )
                try:
                    process.communicate(payload, timeout=timeout_seconds)
                except subprocess.TimeoutExpired as exc:
                    process.kill()
                    process.communicate()
                    raise TrainingPipelineError("fixed training worker timed out") from exc
                finally:
                    if process.returncode is None:
                        process.kill()
                        process.communicate()
            if process.returncode != 0:
                raise TrainingPipelineError("fixed training worker rejected input")
            stdout = _read_regular_path(
                stdout_path,
                max_bytes=max_checkpoint_bytes,
            )
    except TrainingPipelineError:
        raise
    except OSError as exc:
        raise TrainingPipelineError("fixed training worker failed") from exc
    value = _json_object(stdout, "candidate checkpoint state")
    if stdout != _canonical_bytes(value) + b"\n":
        raise TrainingPipelineError("fixed worker emitted non-canonical checkpoint bytes")
    if (
        set(value)
        != {
            "schema_version",
            "job_fingerprint",
            "seed",
            "sample_ids_sha256",
            "sample_count",
            "feature_count",
            "label_count",
            "feature_means",
            "label_means",
            "contract_only",
        }
        or value["schema_version"] != "vc.tiny-json-checkpoint.v1"
        or value["contract_only"] is not True
    ):
        raise TrainingPipelineError("fixed worker emitted an invalid checkpoint contract")
    if any(value[field] != expected[field] for field in expected):
        raise TrainingPipelineError("fixed worker checkpoint does not match its exact input")
    if (
        type(value["feature_means"]) is not list
        or len(value["feature_means"]) != expected_feature_count
        or type(value["label_means"]) is not list
        or len(value["label_means"]) != expected_label_count
    ):
        raise TrainingPipelineError("fixed worker checkpoint vector shape is invalid")
    for field in ("feature_means", "label_means"):
        try:
            tuple(_number(item, field) for item in value[field])
        except (TypeError, ValueError) as exc:
            raise TrainingPipelineError("fixed worker checkpoint contains a non-finite value") from exc
    return stdout


def _model_identity(job: TrainingJobV1, checkpoint: CandidateCheckpointV1, result: TrainingResultV1) -> str:
    return _fingerprint(
        {
            "schema_version": "vc.training-model-identity.v1",
            "model_id": job.model_id,
            "model_version": job.model_version,
            "training_job_fingerprint": job.fingerprint(),
            "training_result_fingerprint": result.fingerprint(),
            "checkpoint_fingerprint": checkpoint.fingerprint(),
            "factory_registration_fingerprint": job.factory_registration_fingerprint,
            "pack_fingerprint": job.pack_fingerprint,
            "trainer_revision": job.trainer_revision,
            "trainer_source_sha256": job.trainer_source_sha256,
            "environment_fingerprint": job.environment.fingerprint(),
        }
    )


def _build_bundle(
    job: TrainingJobV1,
    checkpoint_state: bytes,
    *,
    input_bytes: int,
    sample_count: int,
    feature_count: int,
    label_count: int,
) -> TrainingRunBundle:
    state_sha256 = hashlib.sha256(checkpoint_state).hexdigest()
    checkpoint = CandidateCheckpointV1(
        schema_version="vc.candidate-checkpoint.v1",
        training_job_fingerprint=job.fingerprint(),
        factory_registration_fingerprint=job.factory_registration_fingerprint,
        pack_fingerprint=job.pack_fingerprint,
        trainer_revision=job.trainer_revision,
        trainer_source_sha256=job.trainer_source_sha256,
        environment_fingerprint=job.environment.fingerprint(),
        state_path="checkpoint.json",
        state_media_type="application/vnd.praxis-vc.tiny-checkpoint+json",
        state_size_bytes=len(checkpoint_state),
        state_sha256=state_sha256,
        safe_load_policy="data_only",
        executable_code=False,
        contract_only=True,
        real_candidate_training_performed=False,
    )
    resources = TrainingResourceObservationV1(
        schema_version="vc.training-resource-observation.v1",
        input_bytes=input_bytes,
        sample_count=sample_count,
        feature_count=feature_count,
        label_count=label_count,
        checkpoint_bytes=len(checkpoint_state),
        worker_processes=1,
        cpu_threads=1,
        network_access_requested=False,
        gpu_access_requested=False,
    )
    metrics = tuple(
        TrainingMetricV1(
            schema_version="vc.training-metric.v1",
            name=name,
            value=value,
            scope="contract_only_tiny_dry_run",
            scientific_metric=False,
            evidence_eligible=False,
        )
        for name, value in (
            ("contract_sample_count", sample_count),
            ("contract_feature_count", feature_count),
            ("contract_label_count", label_count),
        )
    )
    log_sha256 = _fingerprint(
        [
            "factory_chain_verified",
            "metadata_leakage_audit_passed",
            "train_assets_materialized",
            "fixed_worker_succeeded",
            "prepublish_identity_reverified",
        ]
    )
    result = TrainingResultV1(
        schema_version="vc.training-result.v1",
        training_job_fingerprint=job.fingerprint(),
        status="succeeded_contract_only",
        checkpoint_fingerprint=checkpoint.fingerprint(),
        checkpoint_state_sha256=state_sha256,
        checkpoint_state_size_bytes=len(checkpoint_state),
        log_sha256=log_sha256,
        resources=resources,
        metrics=metrics,
        deterministic_replay=True,
        contract_only=True,
        real_candidate_training_performed=False,
        test_external_read=False,
        benchmark_performed=False,
        evidence_created=False,
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )
    identity = _model_identity(job, checkpoint, result)
    artifact = CandidateModelArtifactV1(
        schema_version="vc.candidate-model-artifact.v1",
        model_id=job.model_id,
        model_version=job.model_version,
        model_identity_fingerprint=identity,
        training_job_fingerprint=job.fingerprint(),
        training_result_fingerprint=result.fingerprint(),
        checkpoint_fingerprint=checkpoint.fingerprint(),
        factory_registration_fingerprint=job.factory_registration_fingerprint,
        pack_fingerprint=job.pack_fingerprint,
        trainer_revision=job.trainer_revision,
        trainer_source_sha256=job.trainer_source_sha256,
        environment_fingerprint=job.environment.fingerprint(),
        artifact_path="checkpoint.json",
        artifact_size_bytes=len(checkpoint_state),
        artifact_sha256=state_sha256,
        media_type="application/vnd.praxis-vc.tiny-checkpoint+json",
        safe_load_policy="data_only",
        status="candidate",
        cataloged=True,
        executable=False,
        production_registry_written=False,
        benchmark_performed=False,
        evidence_created=False,
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )
    card = CandidateModelCardV1(
        schema_version="vc.candidate-model-card.v1",
        model_id=job.model_id,
        model_version=job.model_version,
        model_identity_fingerprint=identity,
        artifact_fingerprint=artifact.fingerprint(),
        training_job_fingerprint=job.fingerprint(),
        training_result_fingerprint=result.fingerprint(),
        checkpoint_fingerprint=checkpoint.fingerprint(),
        factory_registration_fingerprint=job.factory_registration_fingerprint,
        pack_id=job.pack_id,
        pack_version=job.pack_version,
        pack_fingerprint=job.pack_fingerprint,
        feature_contract_fingerprint=job.feature_contract_fingerprint,
        alignment_report_fingerprint=job.alignment_report_fingerprint,
        split_fingerprint=job.split.fingerprint(),
        leakage_audit_fingerprint=job.leakage_audit.fingerprint(),
        trainer_revision=job.trainer_revision,
        trainer_source_sha256=job.trainer_source_sha256,
        environment_fingerprint=job.environment.fingerprint(),
        metrics_scope="contract_only_tiny_dry_run",
        status="candidate",
        cataloged=True,
        executable=False,
        production_registry_written=False,
        benchmark_performed=False,
        evidence_created=False,
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )
    candidate_model = TrainingCandidateModelV1(
        schema_version="vc.training-candidate-model.v1",
        model_id=job.model_id,
        model_version=job.model_version,
        model_identity_fingerprint=identity,
        training_job_fingerprint=job.fingerprint(),
        training_result_fingerprint=result.fingerprint(),
        checkpoint_fingerprint=checkpoint.fingerprint(),
        artifact_fingerprint=artifact.fingerprint(),
        model_card_fingerprint=card.fingerprint(),
        factory_registration_fingerprint=job.factory_registration_fingerprint,
        pack_fingerprint=job.pack_fingerprint,
        trainer_revision=job.trainer_revision,
        trainer_source_sha256=job.trainer_source_sha256,
        environment_fingerprint=job.environment.fingerprint(),
        status="candidate_cataloged_contract_only",
        candidate_cataloged=True,
        executable=False,
        production_registry_written=False,
        benchmark_performed=False,
        evidence_created=False,
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )
    bundle = TrainingRunBundle(
        job=job,
        checkpoint=checkpoint,
        result=result,
        artifact=artifact,
        model_card=card,
        candidate_model=candidate_model,
    )
    _validate_bundle(bundle, checkpoint_state)
    return bundle


def _validate_bundle(bundle: TrainingRunBundle, checkpoint_state: bytes | None = None) -> None:
    if type(bundle) is not TrainingRunBundle:
        raise TrainingPipelineError("training run bundle has an invalid type")
    job = _revalidate(bundle.job, TrainingJobV1, "bundle job")
    checkpoint = _revalidate(bundle.checkpoint, CandidateCheckpointV1, "bundle checkpoint")
    result = _revalidate(bundle.result, TrainingResultV1, "bundle result")
    artifact = _revalidate(bundle.artifact, CandidateModelArtifactV1, "bundle artifact")
    card = _revalidate(bundle.model_card, CandidateModelCardV1, "bundle model card")
    candidate = _revalidate(bundle.candidate_model, TrainingCandidateModelV1, "bundle candidate model")
    job_fingerprint = job.fingerprint()
    result_fingerprint = result.fingerprint()
    checkpoint_fingerprint = checkpoint.fingerprint()
    environment_fingerprint = job.environment.fingerprint()
    checkpoint_provenance = (
        checkpoint.training_job_fingerprint,
        checkpoint.factory_registration_fingerprint,
        checkpoint.pack_fingerprint,
        checkpoint.trainer_revision,
        checkpoint.trainer_source_sha256,
        checkpoint.environment_fingerprint,
    )
    if checkpoint_provenance != (
        job_fingerprint,
        job.factory_registration_fingerprint,
        job.pack_fingerprint,
        job.trainer_revision,
        job.trainer_source_sha256,
        environment_fingerprint,
    ):
        raise TrainingPipelineError("checkpoint is not bound to the exact training job")
    if (
        result.training_job_fingerprint != job_fingerprint
        or result.checkpoint_fingerprint != checkpoint_fingerprint
        or result.checkpoint_state_sha256 != checkpoint.state_sha256
        or result.checkpoint_state_size_bytes != checkpoint.state_size_bytes
        or result.resources.checkpoint_bytes != checkpoint.state_size_bytes
        or result.resources.input_bytes
        != sum(item.size_bytes for item in job.train_feature_assets + job.train_label_assets)
        or result.resources.sample_count != len(job.split.train_sample_ids)
        or result.resources.feature_count != len(_verify_feature_documents(job).feature_ids)
        or result.resources.label_count != len(job.train_label_assets)
        or result.resources.input_bytes > job.resource_limits.max_input_bytes
        or result.resources.sample_count > job.resource_limits.max_samples
        or result.resources.feature_count > job.resource_limits.max_features
        or result.resources.label_count > job.resource_limits.max_labels
        or checkpoint.state_size_bytes > job.resource_limits.max_checkpoint_bytes
        or result.log_sha256
        != _fingerprint(
            [
                "factory_chain_verified",
                "metadata_leakage_audit_passed",
                "train_assets_materialized",
                "fixed_worker_succeeded",
                "prepublish_identity_reverified",
            ]
        )
    ):
        raise TrainingPipelineError("training result/checkpoint/resources are not exactly bound")
    common = (
        job_fingerprint,
        result_fingerprint,
        checkpoint_fingerprint,
        job.factory_registration_fingerprint,
        job.pack_fingerprint,
        job.trainer_revision,
        job.trainer_source_sha256,
        environment_fingerprint,
    )
    if (
        (
            artifact.training_job_fingerprint,
            artifact.training_result_fingerprint,
            artifact.checkpoint_fingerprint,
            artifact.factory_registration_fingerprint,
            artifact.pack_fingerprint,
            artifact.trainer_revision,
            artifact.trainer_source_sha256,
            artifact.environment_fingerprint,
        )
        != common
        or (
            card.training_job_fingerprint,
            card.training_result_fingerprint,
            card.checkpoint_fingerprint,
            card.factory_registration_fingerprint,
            card.pack_fingerprint,
            card.trainer_revision,
            card.trainer_source_sha256,
            card.environment_fingerprint,
        )
        != common
        or (
            candidate.training_job_fingerprint,
            candidate.training_result_fingerprint,
            candidate.checkpoint_fingerprint,
            candidate.factory_registration_fingerprint,
            candidate.pack_fingerprint,
            candidate.trainer_revision,
            candidate.trainer_source_sha256,
            candidate.environment_fingerprint,
        )
        != common
    ):
        raise TrainingPipelineError("candidate model artifacts have mixed provenance")
    identity = _model_identity(job, checkpoint, result)
    if (
        (artifact.model_id, artifact.model_version) != (job.model_id, job.model_version)
        or artifact.model_identity_fingerprint != identity
        or artifact.artifact_size_bytes != checkpoint.state_size_bytes
        or artifact.artifact_sha256 != checkpoint.state_sha256
        or (card.model_id, card.model_version) != (job.model_id, job.model_version)
        or card.model_identity_fingerprint != identity
        or card.pack_id != job.pack_id
        or card.pack_version != job.pack_version
        or card.feature_contract_fingerprint != job.feature_contract_fingerprint
        or card.alignment_report_fingerprint != job.alignment_report_fingerprint
        or card.split_fingerprint != job.split.fingerprint()
        or card.leakage_audit_fingerprint != job.leakage_audit.fingerprint()
        or (candidate.model_id, candidate.model_version) != (job.model_id, job.model_version)
        or candidate.model_identity_fingerprint != identity
        or card.artifact_fingerprint != artifact.fingerprint()
        or candidate.artifact_fingerprint != artifact.fingerprint()
        or candidate.model_card_fingerprint != card.fingerprint()
    ):
        raise TrainingPipelineError("candidate model artifact/card identities are not bidirectionally bound")
    if checkpoint_state is None:
        return
    if type(checkpoint_state) is not bytes:
        raise TrainingPipelineError("checkpoint state must be exact bytes")
    if (
        len(checkpoint_state) != checkpoint.state_size_bytes
        or hashlib.sha256(checkpoint_state).hexdigest() != checkpoint.state_sha256
    ):
        raise TrainingPipelineError("checkpoint bytes do not match the checkpoint manifest")
    state = _json_object(checkpoint_state, "candidate checkpoint state")
    if checkpoint_state != _canonical_bytes(state) + b"\n":
        raise TrainingPipelineError("candidate checkpoint state is not canonical")
    if set(state) != {
        "schema_version",
        "job_fingerprint",
        "seed",
        "sample_ids_sha256",
        "sample_count",
        "feature_count",
        "label_count",
        "feature_means",
        "label_means",
        "contract_only",
    }:
        raise TrainingPipelineError("candidate checkpoint state has invalid fields")
    expected_state = (
        "vc.tiny-json-checkpoint.v1",
        job_fingerprint,
        job.seed,
        hashlib.sha256(_canonical_bytes(list(job.split.train_sample_ids))).hexdigest(),
        result.resources.sample_count,
        result.resources.feature_count,
        result.resources.label_count,
        True,
    )
    actual_state = (
        state["schema_version"],
        state["job_fingerprint"],
        state["seed"],
        state["sample_ids_sha256"],
        state["sample_count"],
        state["feature_count"],
        state["label_count"],
        state["contract_only"],
    )
    if actual_state != expected_state:
        raise TrainingPipelineError("candidate checkpoint state is not bound to the training result")
    for field, count in (
        ("feature_means", result.resources.feature_count),
        ("label_means", result.resources.label_count),
    ):
        values = state[field]
        if type(values) is not list or len(values) != count:
            raise TrainingPipelineError("candidate checkpoint vector shape is invalid")
        try:
            tuple(_number(value, field) for value in values)
        except (TypeError, ValueError) as exc:
            raise TrainingPipelineError("candidate checkpoint vector is not finite") from exc


def _output_target(output_root: str | Path) -> tuple[Path, Path]:
    target = Path(output_root)
    if not target.is_absolute() or target.is_symlink() or target.exists():
        raise TrainingPipelineError("training output root must be an absolute write-new path")
    parent = target.parent
    try:
        if parent.is_symlink() or not parent.is_dir() or parent.resolve(strict=True) != parent:
            raise TrainingPipelineError("training output parent must be canonical and non-symlink")
        if target.resolve(strict=False) != target:
            raise TrainingPipelineError("training output root must be canonical")
    except OSError as exc:
        raise TrainingPipelineError("training output parent is unavailable") from exc
    return target, parent


def _write_new_file(root: Path, relative: str, payload: bytes) -> None:
    path = root / relative
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise TrainingPipelineError("cannot write candidate training artifact") from exc


def _load_staged_bundle(
    directory_descriptor: int,
    job: TrainingJobV1,
) -> tuple[TrainingRunBundle, bytes]:
    checkpoint_state = _read_directory_file(
        directory_descriptor,
        "checkpoint.json",
        max_bytes=job.resource_limits.max_checkpoint_bytes,
    )

    def contract(relative: str, expected: type[_ContractT]) -> _ContractT:
        payload = _read_directory_file(
            directory_descriptor,
            relative,
            max_bytes=_MAX_JOB_BYTES,
        )
        value = _json_object(payload, relative)
        result = expected.from_dict(value)
        if payload != _canonical_bytes(result.to_dict()) + b"\n":
            raise TrainingPipelineError(f"{relative} is not canonical")
        return result

    checkpoint = contract("checkpoint-manifest.json", CandidateCheckpointV1)
    result = contract("training-result.json", TrainingResultV1)
    candidate_payload = _read_directory_file(
        directory_descriptor,
        "candidate-model.json",
        max_bytes=_MAX_JOB_BYTES,
    )
    candidate_value = _json_object(candidate_payload, "candidate-model.json")
    if (
        set(candidate_value) != {"schema_version", "artifact", "model_card", "candidate_model"}
        or candidate_value["schema_version"] != "vc.training-candidate-bundle.v1"
    ):
        raise TrainingPipelineError("candidate-model.json has invalid fields")
    artifact = CandidateModelArtifactV1.from_dict(candidate_value["artifact"])
    card = CandidateModelCardV1.from_dict(candidate_value["model_card"])
    candidate = TrainingCandidateModelV1.from_dict(candidate_value["candidate_model"])
    normalized_candidate = {
        "schema_version": "vc.training-candidate-bundle.v1",
        "artifact": artifact.to_dict(),
        "model_card": card.to_dict(),
        "candidate_model": candidate.to_dict(),
    }
    if candidate_payload != _canonical_bytes(normalized_candidate) + b"\n":
        raise TrainingPipelineError("candidate-model.json is not canonical")
    bundle = TrainingRunBundle(
        job=job,
        checkpoint=checkpoint,
        result=result,
        artifact=artifact,
        model_card=card,
        candidate_model=candidate,
    )
    _validate_bundle(bundle, checkpoint_state)
    return bundle, checkpoint_state


def _atomic_rename_no_replace(
    source: Path,
    target: Path,
    *,
    parent_descriptor: int,
    source_descriptor: int,
    expected_source_identity: tuple[int, int],
) -> None:
    held = os.fstat(source_descriptor)
    try:
        named = os.stat(source.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError as exc:
        raise TrainingPipelineError("verified staging directory is no longer publishable") from exc
    if (
        source.parent != target.parent
        or not stat.S_ISDIR(held.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (held.st_dev, held.st_ino) != expected_source_identity
        or (named.st_dev, named.st_ino) != expected_source_identity
    ):
        raise TrainingPipelineError("verified staging directory identity changed before publish")
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source.name)
    target_bytes = os.fsencode(target.name)
    if sys.platform == "darwin":
        try:
            operation = libc.renameatx_np
        except AttributeError as exc:  # pragma: no cover - unsupported Darwin runtime
            raise TrainingPipelineError("atomic no-replace publish is unavailable") from exc
        operation.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        operation.restype = ctypes.c_int
        result = operation(
            parent_descriptor,
            source_bytes,
            parent_descriptor,
            target_bytes,
            0x00000004,
        )  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        try:
            operation = libc.renameat2
        except AttributeError as exc:  # pragma: no cover - old libc fails closed
            raise TrainingPipelineError("atomic no-replace publish is unavailable") from exc
        operation.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        operation.restype = ctypes.c_int
        result = operation(
            parent_descriptor,
            source_bytes,
            parent_descriptor,
            target_bytes,
            1,
        )  # RENAME_NOREPLACE
    else:  # pragma: no cover - deliberately unsupported rather than overwrite-prone
        raise TrainingPipelineError("atomic no-replace publish is unavailable")
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise TrainingPipelineError("training output root already exists")
    raise TrainingPipelineError("atomic candidate publish failed") from OSError(error, os.strerror(error))


def _remove_owned_staging(staging: Path, identity: tuple[int, int]) -> None:
    try:
        metadata = staging.lstat()
    except FileNotFoundError:
        return
    except OSError:
        return
    if stat.S_ISDIR(metadata.st_mode) and not staging.is_symlink() and (metadata.st_dev, metadata.st_ino) == identity:
        shutil.rmtree(staging, ignore_errors=True)


def _clear_held_staging_files(directory_descriptor: int) -> None:
    for relative in _OUTPUT_FILE_NAMES:
        try:
            os.unlink(relative, dir_fd=directory_descriptor)
        except FileNotFoundError:
            continue
        except OSError:
            continue
    try:
        os.fsync(directory_descriptor)
    except OSError:
        pass


def _publish_bundle(
    bundle: TrainingRunBundle,
    checkpoint_state: bytes,
    *,
    output_root: str | Path,
    index: PackIndex,
) -> TrainingRunBundle:
    _validate_bundle(bundle, checkpoint_state)
    target, parent = _output_target(output_root)
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    try:
        parent_descriptor = os.open(parent, directory_flags)
    except OSError as exc:
        raise TrainingPipelineError("training output parent is unavailable") from exc
    staging: Path | None = None
    staging_descriptor: int | None = None
    staging_identity: tuple[int, int] | None = None
    published = False
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.training-", dir=parent))
        created = staging.lstat()
        staging_identity = (created.st_dev, created.st_ino)
        staging_descriptor = os.open(staging, directory_flags)
        held = os.fstat(staging_descriptor)
        named = os.stat(staging.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(created.st_mode)
            or (held.st_dev, held.st_ino) != staging_identity
            or (named.st_dev, named.st_ino) != staging_identity
        ):
            raise TrainingPipelineError("new staging directory identity is unstable")
        candidate_payload = {
            "schema_version": "vc.training-candidate-bundle.v1",
            "artifact": bundle.artifact.to_dict(),
            "model_card": bundle.model_card.to_dict(),
            "candidate_model": bundle.candidate_model.to_dict(),
        }
        artifacts = {
            "checkpoint.json": checkpoint_state,
            "checkpoint-manifest.json": _canonical_bytes(bundle.checkpoint.to_dict()) + b"\n",
            "training-result.json": _canonical_bytes(bundle.result.to_dict()) + b"\n",
            "candidate-model.json": _canonical_bytes(candidate_payload) + b"\n",
        }
        for relative, payload in artifacts.items():
            _write_new_file(staging, relative, payload)
        file_identities = [
            {
                "path": relative,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for relative, payload in sorted(artifacts.items())
        ]

        def verify_staged_files() -> None:
            if staging_descriptor is None:  # pragma: no cover - construction invariant
                raise TrainingPipelineError("staging directory is unavailable")
            for item in file_identities:
                _read_directory_file(
                    staging_descriptor,
                    item["path"],
                    max_bytes=item["size_bytes"],
                    expected_size=item["size_bytes"],
                    expected_sha256=item["sha256"],
                )

        verify_staged_files()
        loaded_bundle, loaded_checkpoint = _load_staged_bundle(staging_descriptor, bundle.job)
        if loaded_checkpoint != checkpoint_state:
            raise TrainingPipelineError("staged checkpoint bytes changed")
        os.fsync(staging_descriptor)
        os.fsync(parent_descriptor)

        # Revalidate the exact stored P19 chain plus manifest/split/train
        # allowlist, then re-hash the held staging inode before commit.
        _verify_job_bindings(bundle.job, index)
        verify_staged_files()
        _atomic_rename_no_replace(
            staging,
            target,
            parent_descriptor=parent_descriptor,
            source_descriptor=staging_descriptor,
            expected_source_identity=staging_identity,
        )
        published = True
        try:
            os.fsync(parent_descriptor)
        except OSError:
            # Atomic visibility has committed. A durability advisory must
            # never trigger rollback or deletion of the final directory.
            pass
        return loaded_bundle
    finally:
        if staging_descriptor is not None:
            if not published:
                _clear_held_staging_files(staging_descriptor)
            try:
                os.close(staging_descriptor)
            except OSError:
                if not published:
                    pass
        try:
            os.close(parent_descriptor)
        except OSError:
            if not published:
                pass
        if not published and staging is not None and staging_identity is not None:
            _remove_owned_staging(staging, staging_identity)


def _run_training_job(
    job: TrainingJobV1,
    *,
    index: PackIndex,
    output_root: str | Path,
    cancelled: bool = False,
    timeout_seconds: float | None = None,
) -> TrainingRunBundle:
    """Run one synchronous tiny contract proof; never run a real candidate."""

    job = _revalidate(job, TrainingJobV1, "training job")
    if type(cancelled) is not bool:
        raise TrainingPipelineError("cancelled must be a boolean")
    if cancelled:
        raise TrainingPipelineError("training run was cancelled before label access")
    _output_target(output_root)
    resolved = _verify_job_bindings(job, index)
    worker_input, input_bytes, samples, features, labels = _materialize_training_input(job, resolved)
    timeout = job.resource_limits.timeout_seconds
    if timeout_seconds is not None:
        requested = _finite_number(timeout_seconds, "timeout_seconds")
        if requested <= 0:
            raise TrainingPipelineError("timeout_seconds must be positive")
        timeout = min(timeout, float(requested))
    checkpoint_state = _run_fixed_worker(
        worker_input,
        timeout_seconds=timeout,
        max_checkpoint_bytes=job.resource_limits.max_checkpoint_bytes,
        trainer_source_hash=job.trainer_source_sha256,
    )
    bundle = _build_bundle(
        job,
        checkpoint_state,
        input_bytes=input_bytes,
        sample_count=samples,
        feature_count=features,
        label_count=labels,
    )
    return _publish_bundle(bundle, checkpoint_state, output_root=output_root, index=index)


def run_training_job(
    job: TrainingJobV1,
    *,
    index: PackIndex,
    output_root: str | Path,
    cancelled: bool = False,
    timeout_seconds: float | None = None,
) -> TrainingRunBundle:
    """Public fail-closed wrapper that never reflects raw untrusted values."""

    try:
        return _run_training_job(
            job,
            index=index,
            output_root=output_root,
            cancelled=cancelled,
            timeout_seconds=timeout_seconds,
        )
    except TrainingPipelineError:
        raise
    except (OSError, RecursionError, subprocess.SubprocessError, TypeError, ValidationError, ValueError) as exc:
        raise TrainingPipelineError("training job failed closed") from exc
