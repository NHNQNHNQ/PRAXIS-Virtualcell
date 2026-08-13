#!/usr/bin/env python3
"""Offline, deterministic P30A release-candidate metadata helpers.

This module intentionally does not download, publish, sign, push, tag, or deploy.
It validates the checked-in capability classification, materializes already
cached hash-locked wheels, emits an out-of-tree local RC evidence bundle, and
compares two OCI layouts by their manifest/config/layer identities.
"""

from __future__ import annotations

import argparse
import email
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tomllib
import urllib.parse
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

_SHA256 = re.compile(r"[0-9a-f]{64}")
_OCI_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9_.-]*")
_SAFE_WHEEL_PART = re.compile(r"[A-Za-z0-9_.]+")
_CAPABILITY_CLASSES = ("production", "preview", "experimental", "unsupported")
_AUDITED_WORK_UNITS = (
    "P12",
    "P13",
    "P14E",
    "P14R",
    "P14B",
    "P15E",
    "P15R",
    "P15B",
    "P16E",
    "P16R",
    "P16B",
    "P17",
    "P18",
    "P19",
    "P20",
    "P21A",
    "P21B",
    "P21C",
    "P22",
    "P23A",
    "P23B",
    "P24",
    "P25E",
    "P25R",
    "P25_POLICY",
    "P26E",
    "P26R",
    "P27A-E",
    "P27A-R",
    "P27B",
    "P27C",
    "P28E",
    "P28_REAL",
    "P29E",
    "P29_REAL",
)
_CAPABILITY_KEYS = {
    "capability_id",
    "work_units",
    "capability_kind",
    "default_enabled",
    "prediction_allowed",
    "engineering_status",
    "science_status",
    "policy_status",
    "completion_shas",
    "evidence_fingerprints",
    "policy_fingerprints",
    "reason_code",
}
_TEST_GATES = (
    "core",
    "legacy",
    "frontend",
    "wheel",
    "container",
    "ruff",
    "pip_check",
    "packaging",
)
_PACKAGED_DATA_ASSETS = ("bacteria", "human", "mouse", "yeast")
_WHEELHOUSE_PROFILES = ("linux_arm64_cp313", "macos_arm64_cp313")


class ReleaseContractError(ValueError):
    """Stable fail-closed error for local RC inputs."""


@dataclass(frozen=True)
class LockedComponent:
    name: str
    version: str
    hashes: tuple[str, ...]


@dataclass(frozen=True)
class WheelRecord:
    name: str
    version: str
    sha256: str
    size: int
    tags: tuple[str, ...]
    build: str | None
    filename: str
    license_expression: str | None
    license_classifiers: tuple[str, ...]
    cache_path: Path


@dataclass(frozen=True)
class OciIdentity:
    index_digest: str
    manifest_digest: str
    config_digest: str
    layer_digests: tuple[str, ...]
    architecture: str
    operating_system: str
    labels: tuple[tuple[str, str], ...]


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> Any:
    raise ReleaseContractError(f"non-finite JSON number is forbidden: {value}")


def _load_json(path: Path) -> Any:
    if not path.is_file() or path.is_symlink():
        raise ReleaseContractError(f"input must be a regular file: {path.name}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseContractError(f"invalid JSON input: {path.name}") from error


def _git_commit_is_ancestor(repo: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, "HEAD"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _head_blob_bytes(repo: Path, relative: str) -> bytes:
    """Read one safe, tracked HEAD blob without consulting the worktree."""
    relative_path = PurePosixPath(relative)
    if (
        not relative_path.parts
        or relative_path.is_absolute()
        or relative_path.as_posix() != relative
        or any(part in {".", ".."} or ":" in part or part.startswith("._") for part in relative_path.parts)
    ):
        raise ReleaseContractError(f"release input path is unsafe: {relative}")
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{relative}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseContractError(f"release input is not a tracked exact HEAD file: {relative}")
    return result.stdout


def _object(value: Any, context: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ReleaseContractError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> list[Any]:
    if type(value) is not list:
        raise ReleaseContractError(f"{context} must be an array")
    return value


def _text(value: Any, context: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ReleaseContractError(f"{context} must be a non-empty trimmed string")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ReleaseContractError(f"{context} has invalid format")
    return value


def _boolean(value: Any, context: str) -> bool:
    if type(value) is not bool:
        raise ReleaseContractError(f"{context} must be a boolean")
    return value


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ReleaseContractError(f"{context} must be an integer >= {minimum}")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise ReleaseContractError(f"{context} fields differ; missing={missing}, extra={extra}")


def _unique_texts(
    value: Any,
    context: str,
    *,
    pattern: re.Pattern[str] | None = None,
) -> tuple[str, ...]:
    items = tuple(
        _text(item, f"{context}[{index}]", pattern=pattern) for index, item in enumerate(_array(value, context))
    )
    if len(set(items)) != len(items):
        raise ReleaseContractError(f"{context} contains duplicates")
    return items


def validate_capability_classification(
    document: Any,
    *,
    expected_version: str | None = None,
    repo_root: Path | None = None,
    bind_source_reports_to_head: bool = False,
) -> dict[str, Any]:
    root = _object(document, "capability classification")
    _exact_keys(
        root,
        {
            "schema_version",
            "product_version",
            "baseline_sha",
            "authoritative_for_execution",
            "release_class_semantics",
            "scope_catalog",
            "source_reports",
            "audited_work_units",
            "science_qualified_badge",
            "classes",
        },
        "capability classification",
    )
    if _text(root["schema_version"], "schema_version") != "praxis.release-capability-classification.v1":
        raise ReleaseContractError("unsupported capability classification schema")
    product_version = _text(root["product_version"], "product_version")
    if expected_version is not None and product_version != expected_version:
        raise ReleaseContractError("capability classification product version mismatch")
    _text(root["baseline_sha"], "baseline_sha", pattern=_GIT_SHA)
    if _boolean(root["authoritative_for_execution"], "authoritative_for_execution"):
        raise ReleaseContractError("release classification cannot be authoritative for execution")
    if (
        _text(root["release_class_semantics"], "release_class_semantics")
        != "software_release_exposure_only_not_scientific_validation_or_production_promoted_policy"
    ):
        raise ReleaseContractError("release class semantics are ambiguous")
    audited = _unique_texts(root["audited_work_units"], "audited_work_units")
    if audited != _AUDITED_WORK_UNITS:
        raise ReleaseContractError("audited_work_units does not exactly cover the P12-P29 ledger")

    badge = _object(root["science_qualified_badge"], "science_qualified_badge")
    _exact_keys(
        badge,
        {
            "eligible",
            "required_real_species_count",
            "current_real_species_count",
            "required_promoted_community_capability",
            "current_promoted_community_capability",
            "evidence_fingerprints",
            "policy_fingerprints",
            "reason_code",
        },
        "science_qualified_badge",
    )
    eligible = _boolean(badge["eligible"], "science_qualified_badge.eligible")
    required_species = _integer(
        badge["required_real_species_count"],
        "science_qualified_badge.required_real_species_count",
        minimum=1,
    )
    current_species = _integer(
        badge["current_real_species_count"],
        "science_qualified_badge.current_real_species_count",
    )
    requires_community = _boolean(
        badge["required_promoted_community_capability"],
        "science_qualified_badge.required_promoted_community_capability",
    )
    has_community = _boolean(
        badge["current_promoted_community_capability"],
        "science_qualified_badge.current_promoted_community_capability",
    )
    badge_evidence = _unique_texts(
        badge["evidence_fingerprints"],
        "science_qualified_badge.evidence_fingerprints",
        pattern=_SHA256,
    )
    badge_policy = _unique_texts(
        badge["policy_fingerprints"],
        "science_qualified_badge.policy_fingerprints",
        pattern=_SHA256,
    )
    badge_reason = _text(
        badge["reason_code"],
        "science_qualified_badge.reason_code",
        pattern=_SAFE_ID,
    )
    if (
        eligible
        or required_species != 3
        or current_species != 0
        or requires_community is not True
        or has_community
        or badge_evidence
        or badge_policy
        or badge_reason != "science_qualification_requirements_not_met"
    ):
        raise ReleaseContractError("P30A science-qualified badge must preserve the audited negative state")

    classes = _object(root["classes"], "classes")
    _exact_keys(classes, set(_CAPABILITY_CLASSES), "classes")
    observed_work_units: list[str] = []
    observed_ids: set[str] = set()
    completed_work_units: set[str] = set()
    for release_class in _CAPABILITY_CLASSES:
        records = _array(classes[release_class], f"classes.{release_class}")
        ids_in_class: list[str] = []
        for index, raw_record in enumerate(records):
            context = f"classes.{release_class}[{index}]"
            record = _object(raw_record, context)
            _exact_keys(record, _CAPABILITY_KEYS, context)
            capability_id = _text(record["capability_id"], f"{context}.capability_id", pattern=_SAFE_ID)
            if capability_id in observed_ids:
                raise ReleaseContractError(f"duplicate capability_id: {capability_id}")
            observed_ids.add(capability_id)
            ids_in_class.append(capability_id)
            work_units = _unique_texts(record["work_units"], f"{context}.work_units")
            if not work_units:
                raise ReleaseContractError(f"{context}.work_units must not be empty")
            observed_work_units.extend(work_units)
            _text(
                record["capability_kind"],
                f"{context}.capability_kind",
                pattern=_SAFE_ID,
            )
            default_enabled = _boolean(record["default_enabled"], f"{context}.default_enabled")
            prediction_allowed = _boolean(record["prediction_allowed"], f"{context}.prediction_allowed")
            engineering_status = _text(
                record["engineering_status"],
                f"{context}.engineering_status",
                pattern=_SAFE_ID,
            )
            _text(record["science_status"], f"{context}.science_status", pattern=_SAFE_ID)
            _text(record["policy_status"], f"{context}.policy_status", pattern=_SAFE_ID)
            completion_shas = _unique_texts(
                record["completion_shas"],
                f"{context}.completion_shas",
                pattern=_GIT_SHA,
            )
            evidence = _unique_texts(
                record["evidence_fingerprints"],
                f"{context}.evidence_fingerprints",
                pattern=_SHA256,
            )
            policy = _unique_texts(
                record["policy_fingerprints"],
                f"{context}.policy_fingerprints",
                pattern=_SHA256,
            )
            _text(record["reason_code"], f"{context}.reason_code", pattern=_SAFE_ID)

            if release_class != "production" and (default_enabled or prediction_allowed):
                raise ReleaseContractError(f"{context} must remain disabled and non-predictive")
            if release_class == "unsupported" and completion_shas:
                raise ReleaseContractError(f"{context} cannot cite a completion SHA")
            if release_class != "unsupported" and not completion_shas:
                raise ReleaseContractError(f"{context} requires an engineering completion SHA")
            if completion_shas:
                completed_work_units.update(work_units)
            if prediction_allowed:
                raise ReleaseContractError(f"{context} classification cannot grant execution authority")
            if evidence or policy:
                raise ReleaseContractError(f"{context} cannot carry evidence/policy fingerprints without authority")
            if engineering_status.startswith("complete") and release_class == "unsupported":
                raise ReleaseContractError(f"{context} cannot mark unsupported work complete")
        if ids_in_class != sorted(ids_in_class):
            raise ReleaseContractError(f"classes.{release_class} must be sorted by capability_id")

    scope_catalog = _object(root["scope_catalog"], "scope_catalog")
    if list(scope_catalog) != sorted(scope_catalog):
        raise ReleaseContractError("scope_catalog must be sorted by capability_id")
    if set(scope_catalog) != observed_ids:
        missing = sorted(observed_ids - set(scope_catalog))
        extra = sorted(set(scope_catalog) - observed_ids)
        raise ReleaseContractError(f"scope_catalog differs; missing={missing}, extra={extra}")
    for capability_id, raw_scope in scope_catalog.items():
        scope = _object(raw_scope, f"scope_catalog.{capability_id}")
        _exact_keys(scope, {"scope_ref", "scope_fingerprint"}, f"scope_catalog.{capability_id}")
        scope_ref = _text(scope["scope_ref"], f"scope_catalog.{capability_id}.scope_ref")
        if not scope_ref.startswith("praxis-capability://"):
            raise ReleaseContractError(f"scope_catalog.{capability_id}.scope_ref is not canonical")
        scope_fingerprint = _text(
            scope["scope_fingerprint"],
            f"scope_catalog.{capability_id}.scope_fingerprint",
            pattern=_SHA256,
        )
        if scope_fingerprint != _sha256_bytes(scope_ref.encode("utf-8")):
            raise ReleaseContractError(f"scope_catalog.{capability_id}.scope_fingerprint is stale")

    source_reports = _object(root["source_reports"], "source_reports")
    if set(source_reports) != completed_work_units:
        missing = sorted(completed_work_units - set(source_reports))
        extra = sorted(set(source_reports) - completed_work_units)
        raise ReleaseContractError(f"source_reports differs; missing={missing}, extra={extra}")
    if bind_source_reports_to_head and repo_root is None:
        raise ReleaseContractError("exact HEAD binding requires a repository root")
    resolved_repo = repo_root.resolve() if repo_root is not None else None
    for work_unit, raw_source in source_reports.items():
        source = _object(raw_source, f"source_reports.{work_unit}")
        _exact_keys(
            source,
            {"path", "sha256", "conformance_fingerprints"},
            f"source_reports.{work_unit}",
        )
        relative_text = _text(source["path"], f"source_reports.{work_unit}.path")
        relative_path = PurePosixPath(relative_text)
        if relative_path.is_absolute() or ".." in relative_path.parts or relative_path.name.startswith("._"):
            raise ReleaseContractError(f"source_reports.{work_unit}.path is unsafe")
        source_sha = _text(
            source["sha256"],
            f"source_reports.{work_unit}.sha256",
            pattern=_SHA256,
        )
        _unique_texts(
            source["conformance_fingerprints"],
            f"source_reports.{work_unit}.conformance_fingerprints",
            pattern=_SHA256,
        )
        if resolved_repo is not None:
            source_path = resolved_repo.joinpath(*relative_path.parts)
            if not source_path.is_file() or source_path.is_symlink() or _sha256_file(source_path) != source_sha:
                raise ReleaseContractError(f"source_reports.{work_unit} bytes differ from the audited report")
            if bind_source_reports_to_head:
                head_bytes = _head_blob_bytes(resolved_repo, relative_text)
                if source_path.read_bytes() != head_bytes:
                    raise ReleaseContractError(f"source_reports.{work_unit} differs from exact HEAD")
                if _sha256_bytes(head_bytes) != source_sha:
                    raise ReleaseContractError(f"source_reports.{work_unit} HEAD bytes differ from the audited report")

    if tuple(observed_work_units) == _AUDITED_WORK_UNITS:
        return root
    if len(observed_work_units) != len(set(observed_work_units)):
        raise ReleaseContractError("work units are classified more than once")
    if set(observed_work_units) != set(_AUDITED_WORK_UNITS):
        missing = sorted(set(_AUDITED_WORK_UNITS) - set(observed_work_units))
        extra = sorted(set(observed_work_units) - set(_AUDITED_WORK_UNITS))
        raise ReleaseContractError(f"work-unit classification differs; missing={missing}, extra={extra}")
    return root


def _normalize_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_hash_lock(path: Path) -> tuple[LockedComponent, ...]:
    if not path.is_file() or path.is_symlink():
        raise ReleaseContractError(f"lock must be a regular file: {path.name}")
    components: list[LockedComponent] = []
    current_name: str | None = None
    current_version: str | None = None
    current_hashes: list[str] = []

    def finish() -> None:
        nonlocal current_name, current_version, current_hashes
        if current_name is None or current_version is None:
            return
        if not current_hashes:
            raise ReleaseContractError(f"lock entry lacks hashes: {current_name}")
        components.append(LockedComponent(current_name, current_version, tuple(sorted(set(current_hashes)))))
        current_name = None
        current_version = None
        current_hashes = []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReleaseContractError(f"lock is unreadable: {path.name}") from error
    if not any("autogenerated by pip-compile with Python 3.13" in line for line in lines):
        raise ReleaseContractError(f"lock lacks the Python 3.13 generation marker: {path.name}")
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^ ;\\]+) \\$", line)
        if match:
            finish()
            current_name = _normalize_distribution(match.group(1))
            current_version = match.group(2)
            continue
        hash_match = re.search(r"--hash=sha256:([0-9a-f]{64})(?: \\)?$", line)
        if hash_match:
            if current_name is None:
                raise ReleaseContractError(f"orphan hash in lock: {path.name}")
            current_hashes.append(hash_match.group(1))
            continue
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not line.startswith(" "):
            raise ReleaseContractError(f"non-exact requirement in lock: {path.name}")
    finish()
    if not components:
        raise ReleaseContractError(f"lock has no components: {path.name}")
    names = [component.name for component in components]
    if len(names) != len(set(names)):
        raise ReleaseContractError(f"lock contains duplicate distributions: {path.name}")
    return tuple(components)


def _wheel_filename(name: str, version: str, tags: tuple[str, ...], build: str | None) -> str:
    parsed: set[tuple[str, str, str]] = set()
    for tag in tags:
        parts = tag.split("-")
        if len(parts) != 3 or any(_SAFE_WHEEL_PART.fullmatch(part) is None for part in parts):
            raise ReleaseContractError("wheel contains an invalid compatibility tag")
        parsed.add((parts[0], parts[1], parts[2]))
    if not parsed:
        raise ReleaseContractError("wheel contains no compatibility tag")
    python_tags = sorted({item[0] for item in parsed})
    abi_tags = sorted({item[1] for item in parsed})
    platform_tags = sorted({item[2] for item in parsed})
    product = {
        (python_tag, abi_tag, platform_tag)
        for python_tag in python_tags
        for abi_tag in abi_tags
        for platform_tag in platform_tags
    }
    if product == parsed:
        tag_text = "-".join((".".join(python_tags), ".".join(abi_tags), ".".join(platform_tags)))
    else:
        tag_text = "-".join(sorted(parsed)[0])
    distribution = _normalize_distribution(name).replace("-", "_")
    wheel_version = version.replace("-", "_")
    build_text = ""
    if build is not None:
        if _SAFE_WHEEL_PART.fullmatch(build) is None:
            raise ReleaseContractError("wheel contains an invalid build tag")
        build_text = f"-{build}"
    return f"{distribution}-{wheel_version}{build_text}-{tag_text}.whl"


def _wheel_dist_info_directory(name: str, version: str) -> str:
    distribution = _normalize_distribution(name).replace("-", "_")
    return f"{distribution}-{version.replace('-', '_')}.dist-info"


def _top_level_dist_info_member(name: str, leaf: str) -> bool:
    path = PurePosixPath(name)
    return len(path.parts) == 2 and path.parts[0].endswith(".dist-info") and path.parts[1] == leaf


def _wheel_metadata_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_regular_file_bytes(path: Path, context: str) -> bytes:
    """Read one regular file through a no-follow descriptor."""

    if not hasattr(os, "O_NOFOLLOW"):
        raise ReleaseContractError(f"{context} secure open is unsupported")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise ReleaseContractError(f"{context} is unreadable: {path.name}") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ReleaseContractError(f"{context} must be a regular non-symlink file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError as error:
        raise ReleaseContractError(f"{context} is unreadable: {path.name}") from error
    finally:
        os.close(descriptor)


def _read_wheel(path: Path, sha256: str, *, data: bytes | None = None) -> WheelRecord | None:
    if data is None:
        try:
            data = path.read_bytes()
        except OSError:
            return None
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            wheel_names = [name for name in names if _top_level_dist_info_member(name, "WHEEL")]
            metadata_names = [name for name in names if _top_level_dist_info_member(name, "METADATA")]
            if len(wheel_names) != 1 or len(metadata_names) != 1:
                return None
            if PurePosixPath(wheel_names[0]).parent != PurePosixPath(metadata_names[0]).parent:
                return None
            wheel_metadata = email.message_from_bytes(archive.read(wheel_names[0]))
            package_metadata = email.message_from_bytes(archive.read(metadata_names[0]))
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    name = _wheel_metadata_text(package_metadata.get("Name"))
    version = _wheel_metadata_text(package_metadata.get("Version"))
    if not name or not version:
        return None
    expected_dist_info = _wheel_dist_info_directory(name, version)
    top_level_dist_info = {
        PurePosixPath(member_name).parts[0]
        for member_name in names
        if len(PurePosixPath(member_name).parts) >= 2 and PurePosixPath(member_name).parts[0].endswith(".dist-info")
    }
    if PurePosixPath(wheel_names[0]).parent.name != expected_dist_info or top_level_dist_info != {expected_dist_info}:
        return None
    tags = tuple(
        sorted(
            tag for raw_tag in wheel_metadata.get_all("Tag", []) if (tag := _wheel_metadata_text(raw_tag)) is not None
        )
    )
    build = _wheel_metadata_text(wheel_metadata.get("Build"))
    license_expression = _wheel_metadata_text(
        package_metadata.get("License-Expression") or package_metadata.get("License")
    )
    classifiers = tuple(
        sorted(
            classifier.removeprefix("License :: ").strip()
            for raw_classifier in package_metadata.get_all("Classifier", [])
            if (classifier := _wheel_metadata_text(raw_classifier)) is not None and classifier.startswith("License :: ")
        )
    )
    return WheelRecord(
        name=_normalize_distribution(name),
        version=version,
        sha256=sha256,
        size=len(data),
        tags=tags,
        build=build,
        filename=_wheel_filename(name, version, tags, build),
        license_expression=license_expression,
        license_classifiers=classifiers,
        cache_path=path,
    )


def _tags_support_profile(tags: tuple[str, ...], target_profile: str) -> bool:
    if target_profile not in _WHEELHOUSE_PROFILES:
        raise ReleaseContractError("unsupported wheelhouse target profile")
    for tag in tags:
        parts = tag.split("-")
        if len(parts) != 3 or any(_SAFE_WHEEL_PART.fullmatch(part) is None for part in parts):
            raise ReleaseContractError("wheel contains an invalid compatibility tag")
        python_tag, abi_tag, platform_tag = parts
        if python_tag == "py3" and abi_tag == "none" and platform_tag == "any":
            return True
        if (python_tag, abi_tag) == ("py3", "none"):
            pass
        elif abi_tag == "abi3":
            match = re.fullmatch(r"cp3(\d+)", python_tag)
            if match is None or not 2 <= int(match.group(1)) <= 13:
                continue
        elif (python_tag, abi_tag) != ("cp313", "cp313"):
            continue
        if target_profile == "macos_arm64_cp313":
            if platform_tag.startswith("macosx_") and platform_tag.endswith(("_arm64", "_universal2")):
                return True
        elif (
            platform_tag == "linux_aarch64"
            or platform_tag.startswith("manylinux")
            and platform_tag.endswith("_aarch64")
        ):
            return True
    return False


def _wheel_supports_profile(wheel: WheelRecord, target_profile: str) -> bool:
    return _tags_support_profile(wheel.tags, target_profile)


def _new_directory(path: Path) -> Path:
    if path.exists():
        if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
            raise ReleaseContractError(f"output directory must be absent or empty: {path.name}")
    else:
        path.mkdir(parents=True)
    return path.resolve()


def materialize_wheelhouse(
    *,
    lock_paths: tuple[Path, ...],
    cache_root: Path,
    output_dir: Path,
    source_date_epoch: int,
    target_profile: str,
) -> dict[str, Any]:
    if not lock_paths:
        raise ReleaseContractError("at least one lock is required")
    if target_profile not in _WHEELHOUSE_PROFILES:
        raise ReleaseContractError("unsupported wheelhouse target profile")
    cache_root = cache_root.resolve()
    if not cache_root.is_dir():
        raise ReleaseContractError("pip cache root is unavailable")
    output = _new_directory(output_dir)
    locks: list[dict[str, Any]] = []
    expected: dict[tuple[str, str], set[str]] = {}
    allowed_hashes: dict[str, tuple[str, str]] = {}
    for lock_path in lock_paths:
        components = parse_hash_lock(lock_path)
        locks.append(
            {
                "name": lock_path.name,
                "sha256": _sha256_file(lock_path),
                "component_count": len(components),
            }
        )
        for component in components:
            key = (component.name, component.version)
            existing = expected.setdefault(key, set())
            existing.update(component.hashes)
            for digest in component.hashes:
                previous = allowed_hashes.setdefault(digest, key)
                if previous != key:
                    raise ReleaseContractError("one lock hash maps to multiple distributions")

    found: dict[tuple[str, str], dict[str, WheelRecord]] = {key: {} for key in expected}
    for cache_path in sorted(cache_root.rglob("*.body")):
        if cache_path.is_symlink() or not cache_path.is_file():
            continue
        digest = _sha256_file(cache_path)
        expected_key = allowed_hashes.get(digest)
        if expected_key is None:
            continue
        wheel = _read_wheel(cache_path, digest)
        if wheel is None:
            continue
        if (wheel.name, wheel.version) != expected_key:
            raise ReleaseContractError("cached wheel identity differs from its locked hash owner")
        if not _wheel_supports_profile(wheel, target_profile):
            continue
        found[expected_key][digest] = wheel

    missing = [f"{name}=={version}" for (name, version), wheels in sorted(found.items()) if not wheels]
    if missing:
        raise ReleaseContractError(f"offline wheel cache is incomplete: {missing}")

    components_document: list[dict[str, Any]] = []
    emitted_filenames: dict[str, str] = {}
    for (name, version), wheels_by_hash in sorted(found.items()):
        wheel_documents: list[dict[str, Any]] = []
        license_values: set[tuple[str | None, tuple[str, ...]]] = set()
        for digest, wheel in sorted(wheels_by_hash.items()):
            previous_hash = emitted_filenames.setdefault(wheel.filename, digest)
            if previous_hash != digest:
                raise ReleaseContractError("distinct cached wheels resolve to the same filename")
            destination = output / wheel.filename
            if not destination.exists():
                shutil.copyfile(wheel.cache_path, destination)
                os.chmod(destination, 0o644)
                os.utime(destination, (source_date_epoch, source_date_epoch))
            if _sha256_file(destination) != digest:
                raise ReleaseContractError("materialized wheel hash changed")
            license_values.add((wheel.license_expression, wheel.license_classifiers))
            wheel_documents.append(
                {
                    "filename": wheel.filename,
                    "sha256": digest,
                    "size": wheel.size,
                    "tags": list(wheel.tags),
                }
            )
        if len(license_values) != 1:
            raise ReleaseContractError(f"wheel license metadata differs by platform: {name}")
        license_expression, license_classifiers = next(iter(license_values))
        components_document.append(
            {
                "name": name,
                "version": version,
                "license_expression": license_expression,
                "license_classifiers": list(license_classifiers),
                "wheels": wheel_documents,
            }
        )

    manifest = {
        "schema_version": "praxis.offline-wheelhouse.v1",
        "python_implementation": "CPython",
        "python_minor": "3.13",
        "target_profile": target_profile,
        "source_date_epoch": source_date_epoch,
        "locks": sorted(locks, key=lambda item: item["name"]),
        "components": components_document,
    }
    manifest_path = output / "wheelhouse-manifest.json"
    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    os.chmod(manifest_path, 0o644)
    os.utime(manifest_path, (source_date_epoch, source_date_epoch))
    os.utime(output, (source_date_epoch, source_date_epoch))
    return manifest


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseContractError(f"git command failed: {' '.join(arguments)}")
    return result.stdout.strip()


def _require_clean_committed_repo(repo: Path) -> tuple[str, str, int]:
    repo = repo.resolve()
    if _git(repo, "rev-parse", "--show-toplevel") != str(repo):
        raise ReleaseContractError("repository root mismatch")
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=normal")
    if status:
        raise ReleaseContractError("release metadata requires a clean committed worktree")
    source_sha = _text(_git(repo, "rev-parse", "HEAD"), "source_sha", pattern=_GIT_SHA)
    source_tree = _text(_git(repo, "rev-parse", "HEAD^{tree}"), "source_tree", pattern=_GIT_SHA)
    epoch_text = _git(repo, "show", "-s", "--format=%ct", "HEAD")
    if not epoch_text.isdigit():
        raise ReleaseContractError("commit epoch is invalid")
    return source_sha, source_tree, int(epoch_text)


def _require_exact_head_file(repo: Path, path: Path, relative: str) -> Path:
    expected = repo / relative
    if path.is_symlink() or path.resolve() != expected.resolve() or not expected.is_file() or expected.is_symlink():
        raise ReleaseContractError(f"release input must be exact HEAD path: {relative}")
    if _head_blob_bytes(repo, relative) != expected.read_bytes():
        raise ReleaseContractError(f"release input differs from exact HEAD: {relative}")
    return expected


def _load_wheelhouse_manifest(path: Path, locks: tuple[Path, ...]) -> dict[str, Any]:
    manifest = _object(_load_json(path), "wheelhouse manifest")
    _exact_keys(
        manifest,
        {
            "schema_version",
            "python_implementation",
            "python_minor",
            "target_profile",
            "source_date_epoch",
            "locks",
            "components",
        },
        "wheelhouse manifest",
    )
    if manifest["schema_version"] != "praxis.offline-wheelhouse.v1":
        raise ReleaseContractError("unsupported wheelhouse manifest schema")
    if manifest["python_implementation"] != "CPython" or manifest["python_minor"] != "3.13":
        raise ReleaseContractError("wheelhouse interpreter identity mismatch")
    target_profile = manifest["target_profile"]
    if target_profile not in _WHEELHOUSE_PROFILES:
        raise ReleaseContractError("wheelhouse target profile is invalid")
    _integer(manifest["source_date_epoch"], "wheelhouse source_date_epoch", minimum=315532800)
    observed_locks = _array(manifest["locks"], "wheelhouse locks")
    expected_locks = sorted(
        (
            {
                "name": path.name,
                "sha256": _sha256_file(path),
                "component_count": len(parse_hash_lock(path)),
            }
            for path in locks
        ),
        key=lambda item: item["name"],
    )
    if observed_locks != expected_locks:
        raise ReleaseContractError("wheelhouse lock identity mismatch")
    allowed_hashes: dict[tuple[str, str], set[str]] = {}
    hash_owners: dict[str, tuple[str, str]] = {}
    for lock in locks:
        for component in parse_hash_lock(lock):
            key = (component.name, component.version)
            component_hashes = allowed_hashes.setdefault(key, set())
            component_hashes.update(component.hashes)
            for digest in component.hashes:
                owner = hash_owners.setdefault(digest, key)
                if owner != key:
                    raise ReleaseContractError("one lock hash maps to multiple distributions")
    components = _array(manifest["components"], "wheelhouse components")
    observed_keys: list[tuple[str, str]] = []
    for index, raw in enumerate(components):
        component = _object(raw, f"wheelhouse components[{index}]")
        _exact_keys(
            component,
            {"name", "version", "license_expression", "license_classifiers", "wheels"},
            f"wheelhouse components[{index}]",
        )
        name = _text(component["name"], "wheelhouse component name")
        version = _text(component["version"], "wheelhouse component version")
        observed_keys.append((name, version))
        if component["license_expression"] is not None:
            _text(component["license_expression"], "wheelhouse license_expression")
        _unique_texts(component["license_classifiers"], "wheelhouse license_classifiers")
        wheels = _array(component["wheels"], "wheelhouse wheels")
        if not wheels:
            raise ReleaseContractError("wheelhouse component has no wheels")
        for wheel_index, raw_wheel in enumerate(wheels):
            wheel = _object(raw_wheel, f"wheelhouse wheel[{wheel_index}]")
            _exact_keys(wheel, {"filename", "sha256", "size", "tags"}, "wheelhouse wheel")
            filename = _text(wheel["filename"], "wheelhouse wheel filename")
            filename_path = PurePosixPath(filename)
            if (
                filename_path.is_absolute()
                or len(filename_path.parts) != 1
                or filename_path.name != filename
                or "\\" in filename
            ):
                raise ReleaseContractError("wheelhouse wheel filename is unsafe")
            digest = _text(wheel["sha256"], "wheelhouse wheel sha256", pattern=_SHA256)
            if digest not in allowed_hashes.get((name, version), set()):
                raise ReleaseContractError("wheelhouse wheel hash is not a locked hash for its component")
            size = _integer(wheel["size"], "wheelhouse wheel size", minimum=1)
            tags = _unique_texts(wheel["tags"], "wheelhouse wheel tags")
            if not _tags_support_profile(tags, target_profile):
                raise ReleaseContractError("wheelhouse contains a wheel incompatible with target profile")
            wheel_path = path.parent / filename
            wheel_bytes = _read_regular_file_bytes(wheel_path, "wheelhouse wheel")
            if len(wheel_bytes) != size:
                raise ReleaseContractError("wheelhouse wheel size differs from manifest")
            if _sha256_bytes(wheel_bytes) != digest:
                raise ReleaseContractError("wheelhouse wheel hash differs from manifest")
            physical_wheel = _read_wheel(wheel_path, digest, data=wheel_bytes)
            if physical_wheel is None:
                raise ReleaseContractError("wheelhouse wheel metadata is invalid")
            if (
                physical_wheel.filename != filename
                or physical_wheel.name != name
                or physical_wheel.version != version
                or physical_wheel.tags != tags
            ):
                raise ReleaseContractError("wheelhouse wheel metadata differs from manifest")
    if observed_keys != sorted(observed_keys) or len(observed_keys) != len(set(observed_keys)):
        raise ReleaseContractError("wheelhouse components must be sorted and unique")
    expected_keys = sorted(
        {(component.name, component.version) for lock in locks for component in parse_hash_lock(lock)}
    )
    if observed_keys != expected_keys:
        raise ReleaseContractError("wheelhouse component closure differs from locks")
    return manifest


def _packaged_data_components(repo: Path, product_version: str) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for organism in _PACKAGED_DATA_ASSETS:
        relative_root = Path("praxis_virtualcell") / "example_packs" / organism
        manifest_relative = (relative_root / "manifest.yaml").as_posix()
        payload_relative = (relative_root / "tiny.h5ad").as_posix()
        manifest_path = _require_exact_head_file(repo, repo / manifest_relative, manifest_relative)
        payload_path = _require_exact_head_file(repo, repo / payload_relative, payload_relative)
        try:
            manifest_text = manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ReleaseContractError(f"packaged data manifest is unreadable: {organism}") from error
        if re.search(r"(?m)^license:\n  id: CC0-1\.0$", manifest_text) is None:
            raise ReleaseContractError(f"packaged data asset lacks exact CC0-1.0 license: {organism}")
        components.append(
            {
                "ecosystem": "data",
                "name": f"praxis-example-pack-{organism}",
                "version": product_version,
                "purl": f"pkg:generic/praxis-example-pack-{organism}@{product_version}",
                "scope": "bundled-synthetic-conformance-data",
                "license": "CC0-1.0",
                "license_source": str(relative_root / "manifest.yaml"),
                "manifest_sha256": _sha256_file(manifest_path),
                "payload_sha256": _sha256_file(payload_path),
            }
        )
    return components


def _npm_components(path: Path, expected_version: str) -> list[dict[str, Any]]:
    root = _object(_load_json(path), "npm lock")
    if root.get("lockfileVersion") != 3:
        raise ReleaseContractError("npm lockfileVersion must be 3")
    packages = _object(root.get("packages"), "npm packages")
    root_package = _object(packages.get(""), "npm root package")
    if root.get("version") != expected_version or root_package.get("version") != expected_version:
        raise ReleaseContractError("npm product version differs from Python product version")
    components: dict[tuple[str, str], dict[str, Any]] = {}
    for package_path, raw_package in sorted(packages.items()):
        if package_path == "":
            continue
        package = _object(raw_package, f"npm package {package_path}")
        name = package.get("name")
        if name is None:
            marker = "node_modules/"
            if marker not in package_path:
                raise ReleaseContractError("npm package path lacks node_modules identity")
            name = package_path.rsplit(marker, 1)[1]
        name = _text(name, "npm package name")
        version = _text(package.get("version"), "npm package version")
        license_expression = _text(package.get("license"), "npm package license")
        integrity = _text(package.get("integrity"), "npm package integrity")
        if not re.fullmatch(r"sha(?:256|384|512)-[A-Za-z0-9+/=]+", integrity):
            raise ReleaseContractError("npm package integrity has invalid format")
        key = (name, version)
        candidate = {
            "ecosystem": "npm",
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{urllib.parse.quote(name, safe='/')}@{version}",
            "scope": "development" if package.get("dev") is True else "required",
            "license": license_expression,
            "license_source": "package-lock.json",
            "integrity": integrity,
        }
        existing = components.setdefault(key, candidate)
        if existing != candidate:
            raise ReleaseContractError(f"npm duplicate identity has conflicting metadata: {name}@{version}")
    if not components:
        raise ReleaseContractError("npm lock contains no dependencies")
    return [components[key] for key in sorted(components)]


def _python_components(wheelhouse: dict[str, Any]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for raw in wheelhouse["components"]:
        component = _object(raw, "wheelhouse component")
        license_expression = component["license_expression"]
        classifiers = tuple(component["license_classifiers"])
        if license_expression:
            license_value = license_expression
            license_source = "wheel METADATA License-Expression/License"
        elif classifiers:
            license_value = " | ".join(classifiers)
            license_source = "wheel METADATA License classifiers"
        else:
            license_value = "NOASSERTION"
            license_source = "unavailable"
        wheel_hashes = sorted(wheel["sha256"] for wheel in component["wheels"])
        components.append(
            {
                "ecosystem": "pypi",
                "name": component["name"],
                "version": component["version"],
                "purl": f"pkg:pypi/{component['name']}@{component['version']}",
                "scope": "required",
                "license": license_value,
                "license_source": license_source,
                "locked_wheel_sha256": wheel_hashes,
            }
        )
    return components


def _load_test_evidence(path: Path, source_sha: str) -> dict[str, Any]:
    evidence = _object(_load_json(path), "test evidence")
    _exact_keys(evidence, {"schema_version", "source_sha", "gates"}, "test evidence")
    if evidence["schema_version"] != "praxis.release-test-evidence.v1":
        raise ReleaseContractError("unsupported test evidence schema")
    if evidence["source_sha"] != source_sha:
        raise ReleaseContractError("test evidence source SHA mismatch")
    gates = _object(evidence["gates"], "test evidence gates")
    _exact_keys(gates, set(_TEST_GATES), "test evidence gates")
    for name in _TEST_GATES:
        gate = _object(gates[name], f"test evidence gate {name}")
        _exact_keys(gate, {"status", "command", "summary"}, f"test evidence gate {name}")
        if gate["status"] not in {"passed", "failed", "blocked_external", "not_run"}:
            raise ReleaseContractError(f"test evidence gate {name} has invalid status")
        _text(gate["command"], f"test evidence gate {name} command")
        _text(gate["summary"], f"test evidence gate {name} summary")
    return evidence


def _copy_regular_file(source: Path, destination: Path, epoch: int) -> dict[str, Any]:
    if not source.is_file() or source.is_symlink():
        raise ReleaseContractError(f"artifact must be a regular file: {source.name}")
    shutil.copyfile(source, destination)
    os.chmod(destination, 0o644)
    os.utime(destination, (epoch, epoch))
    return {
        "filename": destination.name,
        "size": destination.stat().st_size,
        "sha256": _sha256_file(destination),
    }


def _inspect_release_artifact(
    path: Path,
    product_version: str,
    *,
    repo: Path | None = None,
    source_sha: str | None = None,
) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ReleaseContractError(f"artifact must be a regular file: {path.name}")
    if source_sha is not None:
        _text(source_sha, "source_sha", pattern=_GIT_SHA)
    sha256 = _sha256_file(path)
    if path.name.endswith(".whl"):
        wheel = _read_wheel(path, sha256)
        if (
            wheel is None
            or wheel.name != "praxis-virtualcell"
            or wheel.version != product_version
            or wheel.filename != path.name
        ):
            raise ReleaseContractError("release wheel identity differs from product version")
        return {"kind": "wheel", "wheel_tags": list(wheel.tags)}
    if path.name == f"praxis-virtualcell-{product_version}.tar.gz":
        prefix = f"praxis-virtualcell-{product_version}/"
        try:
            with tarfile.open(path, mode="r:gz") as archive:
                members = archive.getmembers()
                if not members:
                    raise ReleaseContractError("source archive is empty")
                members_by_name: dict[str, tarfile.TarInfo] = {}
                for member in members:
                    member_path = PurePosixPath(member.name)
                    if (
                        member_path.is_absolute()
                        or ".." in member_path.parts
                        or not (member.isfile() or member.isdir())
                        or member.issym()
                        or member.islnk()
                        or member.name.startswith("._")
                        or "/._" in member.name
                        or not member.name.startswith(prefix)
                        or member.name in members_by_name
                    ):
                        raise ReleaseContractError("source archive contains an unsafe or unexpected member")
                    members_by_name[member.name] = member
                pyproject_name = prefix + "pyproject.toml"
                pyproject_member = members_by_name.get(pyproject_name)
                if pyproject_member is None or not pyproject_member.isfile():
                    raise ReleaseContractError("source archive lacks pyproject.toml")
                stream = archive.extractfile(pyproject_member)
                if stream is None:
                    raise ReleaseContractError("source archive pyproject.toml is unreadable")
                pyproject_bytes = stream.read()
                archived_project = tomllib.loads(pyproject_bytes.decode("utf-8"))
                if repo is not None:
                    for relative in ("pyproject.toml", "praxis_virtualcell/__init__.py"):
                        member = members_by_name.get(prefix + relative)
                        if member is None or not member.isfile():
                            raise ReleaseContractError(f"source archive lacks exact HEAD member: {relative}")
                        member_stream = archive.extractfile(member)
                        if member_stream is None or member_stream.read() != _head_blob_bytes(repo, relative):
                            raise ReleaseContractError(f"source archive member differs from exact HEAD: {relative}")
        except (OSError, UnicodeError, tarfile.TarError, tomllib.TOMLDecodeError) as error:
            raise ReleaseContractError("invalid source archive") from error
        if archived_project.get("project", {}).get("version") != product_version:
            raise ReleaseContractError("source archive product version differs from release")
        return {"kind": "source_archive"}
    if path.name.endswith(".oci.tar"):
        identity = read_oci_identity(path)
        if source_sha is not None:
            labels = dict(identity.labels)
            if (
                identity.architecture != "arm64"
                or identity.operating_system != "linux"
                or labels.get("org.opencontainers.image.revision") != source_sha
                or labels.get("org.opencontainers.image.version") != product_version
            ):
                raise ReleaseContractError("OCI artifact does not carry the exact source/version identity")
        return {
            "kind": "oci",
            "manifest_digest": identity.manifest_digest,
            "config_digest": identity.config_digest,
            "layer_digests": list(identity.layer_digests),
        }
    raise ReleaseContractError(f"unsupported release artifact: {path.name}")


def compare_wheels(first: Path, second: Path, *, source_sha: str) -> dict[str, Any]:
    _text(source_sha, "source_sha", pattern=_GIT_SHA)
    if first.name != second.name:
        raise ReleaseContractError("reproducible wheel filenames differ")
    if any(not path.is_file() or path.is_symlink() for path in (first, second)):
        raise ReleaseContractError("wheel comparison inputs must be regular files")
    first_sha = _sha256_file(first)
    second_sha = _sha256_file(second)
    first_wheel = _read_wheel(first, first_sha)
    second_wheel = _read_wheel(second, second_sha)
    if (
        first_wheel is None
        or second_wheel is None
        or first_wheel.name != "praxis-virtualcell"
        or first_wheel.filename != first.name
        or second_wheel.filename != second.name
        or (first_wheel.name, first_wheel.version) != (second_wheel.name, second_wheel.version)
    ):
        raise ReleaseContractError("wheel comparison input identity differs")
    return {
        "schema_version": "praxis.wheel-reproducibility.v1",
        "source_sha": source_sha,
        "filename": first.name,
        "product_version": first_wheel.version,
        "first": {"size": first.stat().st_size, "sha256": first_sha},
        "second": {"size": second.stat().st_size, "sha256": second_sha},
        "identical": first_sha == second_sha,
    }


def emit_release_metadata(
    *,
    repo: Path,
    capabilities_path: Path,
    lock_paths: tuple[Path, ...],
    npm_lock_path: Path,
    wheelhouse_manifest_path: Path,
    artifact_paths: tuple[Path, ...],
    output_dir: Path,
    test_evidence_path: Path | None,
    wheel_comparison_path: Path | None,
    oci_comparison_path: Path | None,
    vulnerability_report_path: Path | None,
) -> dict[str, Any]:
    repo = repo.resolve()
    source_sha, source_tree, source_epoch = _require_clean_committed_repo(repo)
    _require_exact_head_file(repo, repo / "pyproject.toml", "pyproject.toml")
    canonical_capabilities = _require_exact_head_file(
        repo,
        capabilities_path,
        "release/p30a/capability-classification.json",
    )
    expected_locks = {
        "requirements/build-py313.lock",
        "requirements/runtime-py313.lock",
    }
    observed_locks: dict[str, Path] = {}
    for lock_path in lock_paths:
        try:
            relative = lock_path.resolve().relative_to(repo).as_posix()
        except ValueError as error:
            raise ReleaseContractError("Python lock is outside the exact source tree") from error
        observed_locks[relative] = _require_exact_head_file(repo, lock_path, relative)
    if set(observed_locks) != expected_locks or len(lock_paths) != 2:
        raise ReleaseContractError("release requires the exact build and runtime locks")
    canonical_locks = tuple(observed_locks[name] for name in sorted(expected_locks))
    canonical_npm_lock = _require_exact_head_file(
        repo,
        npm_lock_path,
        "praxis_vc_react/package-lock.json",
    )
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    product_version = _text(pyproject["project"]["version"], "product version")
    capabilities = validate_capability_classification(
        _load_json(canonical_capabilities),
        expected_version=product_version,
        repo_root=repo,
        bind_source_reports_to_head=True,
    )
    capability_commits = {capabilities["baseline_sha"]}
    for records in capabilities["classes"].values():
        for record in records:
            capability_commits.update(record["completion_shas"])
    if any(not _git_commit_is_ancestor(repo, sha) for sha in capability_commits):
        raise ReleaseContractError("capability classification cites a commit outside exact HEAD history")
    wheelhouse = _load_wheelhouse_manifest(wheelhouse_manifest_path, canonical_locks)
    if wheelhouse["source_date_epoch"] != source_epoch:
        raise ReleaseContractError("wheelhouse source_date_epoch differs from exact source commit")
    output = _new_directory(output_dir)

    basenames = [path.name for path in artifact_paths]
    if not artifact_paths or len(basenames) != len(set(basenames)):
        raise ReleaseContractError("artifacts must be non-empty with unique basenames")
    artifacts: list[dict[str, Any]] = []
    for path in sorted(artifact_paths, key=lambda item: item.name):
        artifact_identity = _inspect_release_artifact(
            path,
            product_version,
            repo=repo,
            source_sha=source_sha,
        )
        artifact = _copy_regular_file(path, output / path.name, source_epoch)
        artifact.update(artifact_identity)
        artifacts.append(artifact)
    capability_copy = _copy_regular_file(
        capabilities_path,
        output / "capability-classification.json",
        source_epoch,
    )
    wheelhouse_copy = _copy_regular_file(
        wheelhouse_manifest_path,
        output / "wheelhouse-manifest.json",
        source_epoch,
    )

    test_evidence: dict[str, Any] | None = None
    if test_evidence_path is not None:
        test_evidence = _load_test_evidence(test_evidence_path, source_sha)
        _copy_regular_file(test_evidence_path, output / "test-evidence.json", source_epoch)

    wheel_comparison: dict[str, Any] | None = None
    if wheel_comparison_path is not None:
        wheel_comparison = _object(_load_json(wheel_comparison_path), "wheel comparison")
        _exact_keys(
            wheel_comparison,
            {
                "schema_version",
                "source_sha",
                "filename",
                "product_version",
                "first",
                "second",
                "identical",
            },
            "wheel comparison",
        )
        wheel_filename = _text(wheel_comparison["filename"], "wheel comparison filename")
        wheel_product_version = _text(wheel_comparison["product_version"], "wheel comparison product version")
        if (
            wheel_comparison["schema_version"] != "praxis.wheel-reproducibility.v1"
            or wheel_comparison["source_sha"] != source_sha
            or wheel_product_version != product_version
            or wheel_comparison["identical"] is not True
        ):
            raise ReleaseContractError("wheel comparison does not prove the exact source/version")
        wheel_artifacts = [artifact for artifact in artifacts if artifact["kind"] == "wheel"]
        if len(wheel_artifacts) != 1:
            raise ReleaseContractError("wheel comparison requires exactly one release wheel artifact")
        for side in ("first", "second"):
            identity = _object(wheel_comparison[side], f"wheel comparison {side}")
            _exact_keys(identity, {"size", "sha256"}, f"wheel comparison {side}")
            _integer(identity["size"], f"wheel comparison {side} size", minimum=1)
            _text(
                identity["sha256"],
                f"wheel comparison {side} sha256",
                pattern=_SHA256,
            )
            if identity["size"] != wheel_artifacts[0]["size"] or identity["sha256"] != wheel_artifacts[0]["sha256"]:
                raise ReleaseContractError("wheel comparison differs from release wheel artifact")
        if wheel_filename != wheel_artifacts[0]["filename"]:
            raise ReleaseContractError("wheel comparison filename differs from release artifact")
        _copy_regular_file(
            wheel_comparison_path,
            output / "wheel-reproducibility.json",
            source_epoch,
        )

    oci_comparison: dict[str, Any] | None = None
    if oci_comparison_path is not None:
        oci_comparison = _object(_load_json(oci_comparison_path), "OCI comparison")
        _exact_keys(
            oci_comparison,
            {
                "schema_version",
                "source_sha",
                "comparison_policy",
                "first",
                "second",
                "tar_bytes_required_identical",
                "provenance_attestations_in_layout",
                "identical",
            },
            "OCI comparison",
        )
        if (
            oci_comparison["schema_version"] != "praxis.oci-reproducibility.v1"
            or oci_comparison["source_sha"] != source_sha
            or oci_comparison["comparison_policy"] != "manifest_config_and_ordered_layers_exact"
            or oci_comparison["tar_bytes_required_identical"] is not False
            or oci_comparison["provenance_attestations_in_layout"] is not False
            or oci_comparison["identical"] is not True
        ):
            raise ReleaseContractError("OCI comparison does not prove the exact source SHA")
        compared_identities: list[dict[str, Any]] = []
        for side in ("first", "second"):
            identity = _object(oci_comparison[side], f"OCI comparison {side}")
            _exact_keys(
                identity,
                {"archive_sha256", "index_digest", "manifest_digest", "config_digest", "layer_digests"},
                f"OCI comparison {side}",
            )
            _text(identity["archive_sha256"], f"OCI comparison {side} archive SHA", pattern=_SHA256)
            for field in ("index_digest", "manifest_digest", "config_digest"):
                _text(identity[field], f"OCI comparison {side} {field}", pattern=_OCI_SHA256)
            _unique_texts(identity["layer_digests"], f"OCI comparison {side} layer digests", pattern=_OCI_SHA256)
            compared_identities.append(identity)
        oci_artifacts = [artifact for artifact in artifacts if artifact["kind"] == "oci"]
        if len(oci_artifacts) != 1:
            raise ReleaseContractError("OCI comparison requires exactly one release OCI artifact")
        release_oci = oci_artifacts[0]
        if not any(
            identity["archive_sha256"] == release_oci["sha256"]
            and identity["manifest_digest"] == release_oci["manifest_digest"]
            and identity["config_digest"] == release_oci["config_digest"]
            and identity["layer_digests"] == release_oci["layer_digests"]
            for identity in compared_identities
        ):
            raise ReleaseContractError("OCI comparison does not exactly include the release OCI artifact")
        _copy_regular_file(oci_comparison_path, output / "oci-reproducibility.json", source_epoch)

    vulnerability_audit: dict[str, Any] | None = None
    if vulnerability_report_path is not None:
        vulnerability_audit = _object(_load_json(vulnerability_report_path), "vulnerability report")
        _exact_keys(
            vulnerability_audit,
            {
                "schema_version",
                "database",
                "database_sha256",
                "database_as_of",
                "findings",
                "status",
            },
            "vulnerability report",
        )
        if vulnerability_audit["schema_version"] != "praxis.vulnerability-audit.v1":
            raise ReleaseContractError("unsupported vulnerability report schema")
        _text(vulnerability_audit["database"], "vulnerability database")
        _text(
            vulnerability_audit["database_sha256"],
            "vulnerability database SHA",
            pattern=_SHA256,
        )
        _text(vulnerability_audit["database_as_of"], "vulnerability database date")
        _array(vulnerability_audit["findings"], "vulnerability findings")
        if vulnerability_audit["status"] not in {"passed", "failed"}:
            raise ReleaseContractError("vulnerability report status is invalid")
        _copy_regular_file(vulnerability_report_path, output / "vulnerability-audit.json", source_epoch)

    python_components = _python_components(wheelhouse)
    npm_components = _npm_components(canonical_npm_lock, product_version)
    project_component = {
        "ecosystem": "project",
        "name": "praxis-virtualcell",
        "version": product_version,
        "purl": f"pkg:pypi/praxis-virtualcell@{product_version}",
        "scope": "required",
        "license": "MIT",
        "license_source": "pyproject.toml and LICENSE",
    }
    data_components = _packaged_data_components(repo, product_version)
    license_components = [
        project_component,
        *python_components,
        *npm_components,
        *data_components,
    ]
    license_complete = all(component["license"] != "NOASSERTION" for component in license_components)
    license_inventory = {
        "schema_version": "praxis.license-inventory.v1",
        "source_sha": source_sha,
        "product_version": product_version,
        "complete": license_complete,
        "component_count": len(license_components),
        "components": license_components,
    }

    bom_components: list[dict[str, Any]] = []
    for component in license_components:
        bom_component: dict[str, Any] = {
            "type": "application" if component["ecosystem"] == "project" else "library",
            "bom-ref": component["purl"],
            "name": component["name"],
            "version": component["version"],
            "purl": component["purl"],
            "licenses": [{"license": {"name": component["license"]}}],
            "properties": [
                {"name": "praxis:ecosystem", "value": component["ecosystem"]},
                {"name": "praxis:scope", "value": component["scope"]},
                {"name": "praxis:license-source", "value": component["license_source"]},
            ],
        }
        if "integrity" in component:
            bom_component["properties"].append({"name": "praxis:npm-integrity", "value": component["integrity"]})
        if "locked_wheel_sha256" in component:
            bom_component["properties"].append(
                {
                    "name": "praxis:locked-wheel-sha256",
                    "value": ",".join(component["locked_wheel_sha256"]),
                }
            )
        for identity_name in ("manifest_sha256", "payload_sha256"):
            if identity_name in component:
                bom_component["properties"].append(
                    {
                        "name": f"praxis:{identity_name.replace('_', '-')}",
                        "value": component[identity_name],
                    }
                )
        bom_components.append(bom_component)
    serial_material = (
        source_sha
        + _sha256_bytes(_canonical_json_bytes(capabilities))
        + "".join(artifact["sha256"] for artifact in artifacts)
    )
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, serial_material)}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": project_component["purl"],
                "name": project_component["name"],
                "version": product_version,
                "purl": project_component["purl"],
            },
            "properties": [
                {"name": "praxis:source-sha", "value": source_sha},
                {"name": "praxis:source-tree", "value": source_tree},
                {"name": "praxis:science-qualified-badge", "value": "false"},
            ],
        },
        "components": bom_components,
    }

    vulnerability_status = "not_run_no_offline_database"
    if vulnerability_audit is not None:
        vulnerability_status = vulnerability_audit["status"]
    dependency_audit_status = (
        "failed"
        if not license_complete or vulnerability_status == "failed"
        else "passed"
        if vulnerability_status == "passed"
        else "incomplete"
    )
    dependency_audit = {
        "schema_version": "praxis.dependency-audit.v1",
        "source_sha": source_sha,
        "product_version": product_version,
        "status": dependency_audit_status,
        "python_lock_integrity": "passed",
        "python_wheelhouse_coverage": "passed",
        "npm_lock_integrity": "passed",
        "license_inventory": "passed" if license_complete else "failed",
        "vulnerability_scan": vulnerability_status,
        "vulnerability_database_sha256": (
            vulnerability_audit["database_sha256"] if vulnerability_audit is not None else None
        ),
        "known_limitation": (
            None
            if vulnerability_audit is not None
            else "No dated offline vulnerability database was supplied; lock integrity is not a vulnerability scan."
        ),
    }

    subjects = [{"name": artifact["filename"], "digest": {"sha256": artifact["sha256"]}} for artifact in artifacts]
    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://github.com/NHNQNHNQ/PRAXIS-Virtualcell/p30a-local-rc/v1",
                "externalParameters": {
                    "sourceSha": source_sha,
                    "sourceTree": source_tree,
                    "sourceDateEpoch": source_epoch,
                    "productVersion": product_version,
                },
                "internalParameters": {
                    "capabilityClassificationSha256": capability_copy["sha256"],
                    "wheelhouseManifestSha256": wheelhouse_copy["sha256"],
                    "networkUsedByMetadataGenerator": False,
                },
                "resolvedDependencies": [
                    {
                        "uri": f"git+local://PRAXIS-VirtualCell@{source_sha}",
                        "digest": {"gitTree": source_tree},
                    }
                ],
            },
            "runDetails": {
                "builder": {"id": "local://praxis-virtualcell/p30a-release-candidate"},
                "metadata": {"invocationId": _sha256_bytes(serial_material.encode())},
                "byproducts": [
                    {
                        "name": "signature-status",
                        "content": "unsigned-candidate-only; no signer or issuer attestation",
                    }
                ],
            },
        },
    }

    tests_complete = test_evidence is not None and all(
        test_evidence["gates"][name]["status"] == "passed" for name in _TEST_GATES
    )
    artifact_kinds = [artifact["kind"] for artifact in artifacts]
    artifact_set_complete = sorted(artifact_kinds) == ["oci", "source_archive", "wheel"]
    unverified_supplied_claims_complete = bool(
        tests_complete
        and wheel_comparison is not None
        and oci_comparison is not None
        and artifact_set_complete
        and dependency_audit_status == "passed"
    )
    # This command validates supplied bytes but does not execute or attest builds/tests.
    # A separate, dedicated finalizer must establish those facts before any RC can pass.
    software_rc_gates_passed = False
    release_manifest = {
        "schema_version": "praxis.local-release-candidate.v1",
        "status": ("LOCAL_RC_UNPUBLISHED" if software_rc_gates_passed else "LOCAL_RC_INCOMPLETE"),
        "product_version": product_version,
        "source_sha": source_sha,
        "source_tree": source_tree,
        "source_date_epoch": source_epoch,
        "capability_classification": capability_copy,
        "wheelhouse_manifest": wheelhouse_copy,
        "artifacts": artifacts,
        "metadata_files": [
            "sbom.cdx.json",
            "license-inventory.json",
            "dependency-audit.json",
            "provenance-candidate.unsigned.json",
            "SHA256SUMS",
        ],
        "test_evidence_supplied": test_evidence is not None,
        "wheel_reproducibility_supplied": wheel_comparison is not None,
        "oci_reproducibility_supplied": oci_comparison is not None,
        "vulnerability_database_supplied": vulnerability_audit is not None,
        "license_inventory_complete": license_complete,
        "dependency_audit_status": dependency_audit_status,
        "artifact_set_complete": artifact_set_complete,
        "unverified_supplied_claims_complete": unverified_supplied_claims_complete,
        "software_rc_gate_reason": "metadata_generator_cannot_attest_supplied_build_or_test_evidence",
        "software_rc_gates_passed": software_rc_gates_passed,
        "science_qualified_badge": False,
        "published": False,
        "signed": False,
        "tag_created": False,
        "deployed": False,
    }

    generated = {
        "sbom.cdx.json": sbom,
        "license-inventory.json": license_inventory,
        "dependency-audit.json": dependency_audit,
        "provenance-candidate.unsigned.json": provenance,
        "release-manifest.json": release_manifest,
    }
    for filename, document in generated.items():
        path = output / filename
        path.write_bytes(_canonical_json_bytes(document))
        os.chmod(path, 0o644)
        os.utime(path, (source_epoch, source_epoch))

    sums: list[str] = []
    for path in sorted(output.iterdir(), key=lambda item: item.name):
        if path.name == "SHA256SUMS":
            continue
        if not path.is_file() or path.is_symlink():
            raise ReleaseContractError("release bundle contains a non-regular entry")
        sums.append(f"{_sha256_file(path)}  {path.name}")
    sums_path = output / "SHA256SUMS"
    sums_path.write_text("\n".join(sums) + "\n", encoding="ascii")
    os.chmod(sums_path, 0o644)
    os.utime(sums_path, (source_epoch, source_epoch))
    os.utime(output, (source_epoch, source_epoch))
    return release_manifest


def _safe_tar_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    members: dict[str, tarfile.TarInfo] = {}
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
            raise ReleaseContractError("OCI archive contains an unsafe member")
        if member.name in members:
            raise ReleaseContractError("OCI archive contains duplicate members")
        members[member.name] = member
    return members


def _tar_bytes(archive: tarfile.TarFile, members: dict[str, tarfile.TarInfo], name: str) -> bytes:
    member = members.get(name)
    if member is None or not member.isfile():
        raise ReleaseContractError(f"OCI archive lacks required member: {name}")
    stream = archive.extractfile(member)
    if stream is None:
        raise ReleaseContractError(f"OCI archive member is unreadable: {name}")
    return stream.read()


def _digest_blob(archive: tarfile.TarFile, members: dict[str, tarfile.TarInfo], digest: str) -> bytes:
    _text(digest, "OCI digest")
    algorithm, separator, value = digest.partition(":")
    if separator != ":" or algorithm != "sha256" or _SHA256.fullmatch(value) is None:
        raise ReleaseContractError("OCI digest must be sha256")
    data = _tar_bytes(archive, members, f"blobs/sha256/{value}")
    if _sha256_bytes(data) != value:
        raise ReleaseContractError("OCI blob digest mismatch")
    return data


def read_oci_identity(path: Path) -> OciIdentity:
    if not path.is_file() or path.is_symlink():
        raise ReleaseContractError("OCI layout must be a regular archive")
    try:
        with tarfile.open(path, mode="r:*") as archive:
            members = _safe_tar_members(archive)
            index_bytes = _tar_bytes(archive, members, "index.json")
            index = _object(json.loads(index_bytes), "OCI index")
            if index.get("schemaVersion") != 2:
                raise ReleaseContractError("OCI index schemaVersion must be 2")
            manifests = _array(index.get("manifests"), "OCI manifests")
            if len(manifests) != 1:
                raise ReleaseContractError("OCI layout must contain exactly one image manifest")
            descriptor = _object(manifests[0], "OCI manifest descriptor")
            if descriptor.get("mediaType") not in {
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            }:
                raise ReleaseContractError("OCI descriptor is not an image manifest")
            manifest_digest = _text(descriptor.get("digest"), "OCI manifest digest")
            manifest_bytes = _digest_blob(archive, members, manifest_digest)
            manifest = _object(json.loads(manifest_bytes), "OCI manifest")
            if manifest.get("schemaVersion") != 2:
                raise ReleaseContractError("OCI manifest schemaVersion must be 2")
            config = _object(manifest.get("config"), "OCI config descriptor")
            if config.get("mediaType") not in {
                "application/vnd.oci.image.config.v1+json",
                "application/vnd.docker.container.image.v1+json",
            }:
                raise ReleaseContractError("OCI config descriptor is invalid")
            config_digest = _text(config.get("digest"), "OCI config digest")
            config_bytes = _digest_blob(archive, members, config_digest)
            config_document = _object(
                json.loads(
                    config_bytes,
                    object_pairs_hook=_reject_duplicate_keys,
                    parse_constant=_reject_nonfinite_json,
                ),
                "OCI config",
            )
            architecture = _text(config_document.get("architecture"), "OCI config architecture")
            operating_system = _text(config_document.get("os"), "OCI config operating system")
            config_section = _object(config_document.get("config", {}), "OCI config section")
            raw_labels = _object(config_section.get("Labels", {}), "OCI config labels")
            labels = tuple(
                sorted(
                    (_text(key, "OCI label key"), _text(value, f"OCI label {key}")) for key, value in raw_labels.items()
                )
            )
            layers = _array(manifest.get("layers"), "OCI layers")
            layer_digests: list[str] = []
            for index_number, raw_layer in enumerate(layers):
                layer = _object(raw_layer, f"OCI layer[{index_number}]")
                layer_digest = _text(layer.get("digest"), f"OCI layer[{index_number}] digest")
                _digest_blob(archive, members, layer_digest)
                layer_digests.append(layer_digest)
    except (OSError, tarfile.TarError, json.JSONDecodeError) as error:
        raise ReleaseContractError("invalid OCI archive") from error
    return OciIdentity(
        index_digest=f"sha256:{_sha256_bytes(index_bytes)}",
        manifest_digest=manifest_digest,
        config_digest=config_digest,
        layer_digests=tuple(layer_digests),
        architecture=architecture,
        operating_system=operating_system,
        labels=labels,
    )


def compare_oci_layouts(first: Path, second: Path, *, source_sha: str) -> dict[str, Any]:
    _text(source_sha, "source_sha", pattern=_GIT_SHA)
    first_identity = read_oci_identity(first)
    second_identity = read_oci_identity(second)
    identical = (
        first_identity.manifest_digest == second_identity.manifest_digest
        and first_identity.config_digest == second_identity.config_digest
        and first_identity.layer_digests == second_identity.layer_digests
    )
    return {
        "schema_version": "praxis.oci-reproducibility.v1",
        "source_sha": source_sha,
        "comparison_policy": "manifest_config_and_ordered_layers_exact",
        "first": {
            "archive_sha256": _sha256_file(first),
            "index_digest": first_identity.index_digest,
            "manifest_digest": first_identity.manifest_digest,
            "config_digest": first_identity.config_digest,
            "layer_digests": list(first_identity.layer_digests),
        },
        "second": {
            "archive_sha256": _sha256_file(second),
            "index_digest": second_identity.index_digest,
            "manifest_digest": second_identity.manifest_digest,
            "config_digest": second_identity.config_digest,
            "layer_digests": list(second_identity.layer_digests),
        },
        "tar_bytes_required_identical": False,
        "provenance_attestations_in_layout": False,
        "identical": identical,
    }


def _write_new_json(path: Path, document: Any) -> None:
    if path.exists() or path.is_symlink():
        raise ReleaseContractError(f"refusing to overwrite output: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(document))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-capabilities")
    validate.add_argument("path", type=Path)
    validate.add_argument("--expected-version")
    validate.add_argument("--repo", type=Path)

    wheelhouse = subparsers.add_parser("materialize-wheelhouse")
    wheelhouse.add_argument("--lock", type=Path, action="append", required=True)
    wheelhouse.add_argument("--cache-root", type=Path, required=True)
    wheelhouse.add_argument("--output", type=Path, required=True)
    wheelhouse.add_argument("--source-date-epoch", type=int, required=True)
    wheelhouse.add_argument("--target-profile", choices=_WHEELHOUSE_PROFILES, required=True)

    metadata = subparsers.add_parser("emit-metadata")
    metadata.add_argument("--repo", type=Path, required=True)
    metadata.add_argument("--capabilities", type=Path, required=True)
    metadata.add_argument("--python-lock", type=Path, action="append", required=True)
    metadata.add_argument("--npm-lock", type=Path, required=True)
    metadata.add_argument("--wheelhouse-manifest", type=Path, required=True)
    metadata.add_argument("--artifact", type=Path, action="append", required=True)
    metadata.add_argument("--output", type=Path, required=True)
    metadata.add_argument("--test-evidence", type=Path)
    metadata.add_argument("--wheel-comparison", type=Path)
    metadata.add_argument("--oci-comparison", type=Path)
    metadata.add_argument("--vulnerability-report", type=Path)

    compare_wheel = subparsers.add_parser("compare-wheel")
    compare_wheel.add_argument("first", type=Path)
    compare_wheel.add_argument("second", type=Path)
    compare_wheel.add_argument("--source-sha", required=True)
    compare_wheel.add_argument("--output", type=Path, required=True)

    compare = subparsers.add_parser("compare-oci")
    compare.add_argument("first", type=Path)
    compare.add_argument("second", type=Path)
    compare.add_argument("--source-sha", required=True)
    compare.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "validate-capabilities":
            document = validate_capability_classification(
                _load_json(arguments.path),
                expected_version=arguments.expected_version,
                repo_root=arguments.repo,
            )
            print(_sha256_bytes(_canonical_json_bytes(document)))
            return 0
        if arguments.command == "materialize-wheelhouse":
            manifest = materialize_wheelhouse(
                lock_paths=tuple(arguments.lock),
                cache_root=arguments.cache_root,
                output_dir=arguments.output,
                source_date_epoch=arguments.source_date_epoch,
                target_profile=arguments.target_profile,
            )
            print(_sha256_bytes(_canonical_json_bytes(manifest)))
            return 0
        if arguments.command == "emit-metadata":
            manifest = emit_release_metadata(
                repo=arguments.repo,
                capabilities_path=arguments.capabilities,
                lock_paths=tuple(arguments.python_lock),
                npm_lock_path=arguments.npm_lock,
                wheelhouse_manifest_path=arguments.wheelhouse_manifest,
                artifact_paths=tuple(arguments.artifact),
                output_dir=arguments.output,
                test_evidence_path=arguments.test_evidence,
                wheel_comparison_path=arguments.wheel_comparison,
                oci_comparison_path=arguments.oci_comparison,
                vulnerability_report_path=arguments.vulnerability_report,
            )
            print(_sha256_bytes(_canonical_json_bytes(manifest)))
            return 0
        if arguments.command == "compare-wheel":
            report = compare_wheels(
                arguments.first,
                arguments.second,
                source_sha=arguments.source_sha,
            )
            _write_new_json(arguments.output, report)
            print("identical" if report["identical"] else "different")
            return 0 if report["identical"] else 1
        if arguments.command == "compare-oci":
            report = compare_oci_layouts(arguments.first, arguments.second, source_sha=arguments.source_sha)
            _write_new_json(arguments.output, report)
            print("identical" if report["identical"] else "different")
            return 0 if report["identical"] else 1
    except ReleaseContractError as error:
        print(f"release_contract_error: {error}", file=sys.stderr)
        return 2
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
