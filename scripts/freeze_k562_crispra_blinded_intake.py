#!/usr/bin/env python3
"""Freeze a value-free, path-free K562 CRISPRa custodian intake manifest."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_ROOT = Path(__file__).parents[1]
_CONTRACT = _ROOT / "data/golden/norman_2019/k562_crispra_blinded_intake_contract.json"
_CONTRACT_SIZE_BYTES = 3434
_CONTRACT_SHA256 = "a2c3c2f8205dc7eafbe28370408aad61f65e05628d2ede558d435b62a3f94a40"
_SCOPE_NAME = "scope-manifest.json"
_CUSTODY_NAME = "custody-record.json"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$")
_LICENSE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,127}$")
_UTC_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_STABLE_FIELDS = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
_SOURCE_SCHEMES = {"custodian", "doi", "ena", "geo", "gs", "https", "s3", "sra"}
_NONHIERARCHICAL_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,255}$")
_DOI = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


class BlindedIntakeError(ValueError):
    """A blinded intake identity or filesystem boundary failed closed."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BlindedIntakeError("value is not canonical JSON") from exc


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fingerprint(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BlindedIntakeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json(payload: bytes, label: str, *, canonical: bool = True) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda item: (_ for _ in ()).throw(
                BlindedIntakeError(f"non-finite JSON number in {label}: {item}")
            ),
        )
    except BlindedIntakeError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BlindedIntakeError(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise BlindedIntakeError(f"{label} must contain a JSON object")
    if canonical and payload != _canonical_bytes(value) + b"\n":
        raise BlindedIntakeError(f"{label} bytes are not canonical")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise BlindedIntakeError(f"{label} fields do not match the exact contract")


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise BlindedIntakeError(f"{label} must be non-empty canonical text")
    return value


def _identifier(value: Any, label: str) -> str:
    value = _text(value, label)
    if not _ID.fullmatch(value):
        raise BlindedIntakeError(f"{label} must be a canonical identifier")
    return value


def _hash(value: Any, label: str) -> str:
    value = _text(value, label)
    if not _SHA256.fullmatch(value):
        raise BlindedIntakeError(f"{label} must be a lowercase SHA-256")
    return value


def _media_type(value: Any) -> str:
    value = _text(value, "media_type")
    if not _MEDIA_TYPE.fullmatch(value):
        raise BlindedIntakeError("media_type must be a lowercase path-free media type")
    return value


def _license(value: Any) -> str:
    value = _text(value, "license")
    if not _LICENSE.fullmatch(value):
        raise BlindedIntakeError("license must be a path-free license identifier")
    return value


def _source_locator(value: Any, label: str) -> str:
    value = _text(value, label)
    if "\\" in value or "\x00" in value or value.startswith(("/", "./", "../", "~")):
        raise BlindedIntakeError(f"{label} must not contain a local path")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in _SOURCE_SCHEMES
        or value.partition(":")[0] != parsed.scheme
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise BlindedIntakeError(f"{label} must be an approved path-free source locator")
    if parsed.scheme in {"https", "s3", "gs"}:
        valid = bool(parsed.netloc)
    elif parsed.scheme == "doi":
        valid = not parsed.netloc and _DOI.fullmatch(parsed.path) is not None
    else:
        valid = not parsed.netloc and _NONHIERARCHICAL_SOURCE_ID.fullmatch(parsed.path) is not None
    if not valid:
        raise BlindedIntakeError(f"{label} must be an approved path-free source locator")
    return value


def _timestamp(value: Any, label: str) -> str:
    value = _text(value, label)
    if not _UTC_SECONDS.fullmatch(value):
        raise BlindedIntakeError(f"{label} must be canonical UTC seconds")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BlindedIntakeError(f"{label} is not a valid timestamp") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        raise BlindedIntakeError(f"{label} must be canonical UTC seconds")
    return value


def _safe_basename(value: Any) -> str:
    value = _text(value, "opaque asset filename")
    if value in {_SCOPE_NAME, _CUSTODY_NAME} or "/" in value or "\\" in value or "\x00" in value:
        raise BlindedIntakeError("opaque asset filename must be a safe, non-reserved basename")
    if Path(value).name != value or value in {".", ".."}:
        raise BlindedIntakeError("opaque asset filename must be a safe, non-reserved basename")
    return value


def _stable(info: os.stat_result) -> tuple[Any, ...]:
    return tuple(getattr(info, field) for field in _STABLE_FIELDS)


def _open_regular_at(root_fd: int, name: str) -> tuple[int, os.stat_result]:
    try:
        named_before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    except OSError as exc:
        raise BlindedIntakeError(f"cannot safely inspect intake file: {name}") from exc
    if not stat.S_ISREG(named_before.st_mode) or named_before.st_nlink != 1:
        raise BlindedIntakeError(f"intake file must be regular and single-link: {name}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise BlindedIntakeError("platform lacks O_NOFOLLOW")
    try:
        descriptor = os.open(name, flags | nofollow, dir_fd=root_fd)
    except OSError as exc:
        raise BlindedIntakeError(f"cannot safely open intake file: {name}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or _stable(named_before) != _stable(before):
            raise BlindedIntakeError(f"intake file must be regular and single-link: {name}")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor, before


def _read_small_at(root_fd: int, name: str, *, maximum: int = 1024 * 1024) -> tuple[bytes, dict[str, Any]]:
    descriptor, before = _open_regular_at(root_fd, name)
    try:
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if len(payload) > maximum or len(payload) != before.st_size or _stable(before) != _stable(after):
            raise BlindedIntakeError(f"intake JSON changed or exceeded its byte ceiling: {name}")
        if _stable(after) != _stable(named):
            raise BlindedIntakeError(f"intake JSON identity changed after read: {name}")
        return payload, {"size_bytes": len(payload), "sha256": _sha256(payload)}
    finally:
        os.close(descriptor)


def _hash_opaque_at(root_fd: int, name: str) -> dict[str, Any]:
    descriptor, before = _open_regular_at(root_fd, name)
    digest = hashlib.sha256()
    size = 0
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if size != before.st_size or _stable(before) != _stable(after) or _stable(after) != _stable(named):
            raise BlindedIntakeError(f"opaque asset identity changed while hashing: {name}")
    finally:
        os.close(descriptor)
    return {"size_bytes": size, "sha256": digest.hexdigest()}


def _read_regular_path(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink():
        raise BlindedIntakeError(f"{label} must not be a symlink")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise BlindedIntakeError(f"{label} parent is unavailable") from exc
    if parent != path.parent or parent.is_symlink():
        raise BlindedIntakeError(f"{label} parent must be canonical")
    parent_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        return _read_small_at(parent_fd, path.name)
    finally:
        os.close(parent_fd)


def _load_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    payload, file_identity = _read_regular_path(_CONTRACT, "intake contract")
    if file_identity != {"size_bytes": _CONTRACT_SIZE_BYTES, "sha256": _CONTRACT_SHA256}:
        raise BlindedIntakeError("intake contract raw identity changed")
    contract = _strict_json(payload, "intake contract")
    _exact_fields(
        contract, {"schema_version", "record_role", "identity", "input_contract", "output_contract"}, "contract"
    )
    identity = contract.get("identity")
    if type(identity) is not dict:
        raise BlindedIntakeError("contract identity is invalid")
    _exact_fields(identity, {"payload_sha256", "payload_hash_algorithm"}, "contract identity")
    copy = json.loads(_canonical_bytes(contract))
    copy["identity"]["payload_sha256"] = None
    if not (
        contract["schema_version"] == "praxis.k562-crispra-blinded-intake-contract.v1"
        and contract["record_role"] == "value_free_custodian_intake_contract_not_scientific_evidence"
        and identity["payload_hash_algorithm"]
        == "sha256(canonical_json(contract_with_identity.payload_sha256_set_to_null))"
        and identity["payload_sha256"] == _fingerprint(copy)
    ):
        raise BlindedIntakeError("contract identity changed")
    return contract, file_identity


def _verify_scope(value: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    _exact_fields(
        value,
        {
            "schema_version",
            "record_role",
            "bundle_role",
            "source_id",
            "laboratory_id",
            "dataset_fingerprint",
            "platform_fingerprint",
            "source",
            "license",
            "outcome_values_in_manifest",
            "condition_set_sha256",
            "group_set_sha256",
            "condition_counts",
            "asset_identity_closure",
            "scope",
            "opaque_assets",
        },
        "scope manifest",
    )
    expected = contract["input_contract"]
    if not (
        value["schema_version"] == expected["scope_manifest_schema_version"]
        and value["record_role"] == "outcome_opaque_custodian_scope_declaration"
        and value["bundle_role"] in expected["allowed_bundle_roles"]
        and value["outcome_values_in_manifest"] is False
        and _canonical_bytes(value["scope"]) == _canonical_bytes(expected["required_scope"])
    ):
        raise BlindedIntakeError("scope manifest does not match the exact K562 CRISPRa contract")
    for field in ("source_id", "laboratory_id"):
        _identifier(value[field], field)
    for field in ("dataset_fingerprint", "platform_fingerprint", "condition_set_sha256", "group_set_sha256"):
        _hash(value[field], field)
    _source_locator(value["source"], "source")
    license_id = _license(value["license"])
    condition_counts = value["condition_counts"]
    if type(condition_counts) is not dict:
        raise BlindedIntakeError("condition_counts must be an object")
    _exact_fields(condition_counts, set(expected["condition_count_fields"]), "condition_counts")
    if expected["condition_counts_must_be_positive"] is not True or any(
        type(count) is not int or count <= 0 for count in condition_counts.values()
    ):
        raise BlindedIntakeError("all single, combination, and matched control counts must be positive integers")

    asset_contract = expected["asset_contract"]
    required_roles = set(asset_contract["required_roles"])
    exactly_one_roles = set(asset_contract["exactly_one_roles"])
    role_sha256_fields = asset_contract["role_sha256_fields"]
    if not (
        set(role_sha256_fields) == required_roles
        and exactly_one_roles == required_roles
        and asset_contract["role_sha256_algorithm"] == "declared_asset_sha256"
        and asset_contract["license_sha256_algorithm"] == "sha256(utf8(scope_manifest.license))"
    ):
        raise BlindedIntakeError("asset role contract is not exact")
    assets = value["opaque_assets"]
    if type(assets) is not list or not assets:
        raise BlindedIntakeError("scope manifest must declare opaque assets")
    result = []
    for item in assets:
        if type(item) is not dict:
            raise BlindedIntakeError("opaque asset declaration must be an object")
        _exact_fields(
            item,
            {
                "asset_id",
                "role",
                "filename",
                "source_locator",
                "license",
                "media_type",
                "size_bytes",
                "sha256",
            },
            "opaque asset",
        )
        asset_id = _identifier(item["asset_id"], "asset_id")
        role = _identifier(item["role"], "opaque asset role")
        if role not in required_roles:
            raise BlindedIntakeError("opaque asset role is not allowed")
        filename = _safe_basename(item["filename"])
        source_locator = _source_locator(item["source_locator"], "opaque asset source_locator")
        asset_license = _license(item["license"])
        if asset_license != license_id:
            raise BlindedIntakeError("opaque asset license does not match the scope license")
        media_type = _media_type(item["media_type"])
        if type(item["size_bytes"]) is not int or item["size_bytes"] <= 0:
            raise BlindedIntakeError("opaque asset size_bytes must be positive")
        result.append(
            {
                "asset_id": asset_id,
                "role": role,
                "filename": filename,
                "source_locator": source_locator,
                "license": asset_license,
                "media_type": media_type,
                "size_bytes": item["size_bytes"],
                "sha256": _hash(item["sha256"], "opaque asset sha256"),
            }
        )
    if (
        result != sorted(result, key=lambda item: item["asset_id"])
        or len({item["asset_id"] for item in result}) != len(result)
        or len({item["filename"] for item in result}) != len(result)
    ):
        raise BlindedIntakeError("opaque assets must be uniquely and canonically ordered")
    role_counts = {role: sum(item["role"] == role for item in result) for role in required_roles}
    if set(item["role"] for item in result) != required_roles or any(
        role_counts[role] != 1 for role in exactly_one_roles
    ):
        raise BlindedIntakeError("all seven required opaque asset roles must occur exactly once")

    closure = value["asset_identity_closure"]
    if type(closure) is not dict:
        raise BlindedIntakeError("asset_identity_closure must be an object")
    _exact_fields(closure, {*role_sha256_fields.values(), "license_sha256"}, "asset_identity_closure")
    for field, digest in closure.items():
        _hash(digest, f"asset_identity_closure.{field}")
    by_role = {item["role"]: item for item in result}
    if any(closure[field] != by_role[role]["sha256"] for role, field in role_sha256_fields.items()):
        raise BlindedIntakeError("asset role SHA-256 closure does not match declared assets")
    if closure["license_sha256"] != _sha256(license_id.encode("utf-8")):
        raise BlindedIntakeError("license SHA-256 closure does not match the scope license")
    return result


def _verify_custody(value: dict[str, Any], contract: dict[str, Any], scope_sha256: str) -> dict[str, Any]:
    _exact_fields(
        value,
        {
            "schema_version",
            "record_role",
            "custody_id",
            "custodian_id",
            "authorization_record_sha256",
            "scope_manifest_sha256",
            "events",
        },
        "custody record",
    )
    expected = contract["input_contract"]
    if not (
        value["schema_version"] == expected["custody_record_schema_version"]
        and value["record_role"] == "private_value_free_custody_record_not_scientific_evidence"
        and value["scope_manifest_sha256"] == scope_sha256
    ):
        raise BlindedIntakeError("custody record does not bind the scope manifest")
    _identifier(value["custody_id"], "custody_id")
    _identifier(value["custodian_id"], "custodian_id")
    _hash(value["authorization_record_sha256"], "authorization_record_sha256")
    _hash(value["scope_manifest_sha256"], "scope_manifest_sha256")
    events = value["events"]
    event_order = expected["custody_event_order"]
    if type(events) is not list or len(events) != len(event_order):
        raise BlindedIntakeError("custody record must contain exactly three events")
    timestamps = []
    event_ids = []
    for index, (event, event_type) in enumerate(zip(events, event_order, strict=True), start=1):
        if type(event) is not dict:
            raise BlindedIntakeError("custody event must be an object")
        _exact_fields(
            event,
            {
                "sequence",
                "event_id",
                "event_type",
                "recorded_at",
                "operator_id",
                "outcome_decoded",
                "candidate_team_received_asset_bytes",
                "candidate_outputs_used_for_condition_selection",
            },
            "custody event",
        )
        if not (
            type(event["sequence"]) is int
            and event["sequence"] == index
            and event["event_type"] == event_type
            and event["outcome_decoded"] is False
            and event["candidate_team_received_asset_bytes"] is False
            and event["candidate_outputs_used_for_condition_selection"] is False
        ):
            raise BlindedIntakeError("custody events are out of order or violate the blind boundary")
        event_ids.append(_identifier(event["event_id"], "event_id"))
        _identifier(event["operator_id"], "operator_id")
        timestamps.append(_timestamp(event["recorded_at"], "recorded_at"))
    if (
        len(set(event_ids)) != len(event_ids)
        or timestamps != sorted(timestamps)
        or len(set(timestamps)) != len(timestamps)
    ):
        raise BlindedIntakeError("custody events must have unique IDs and strictly increasing timestamps")
    return {
        "custody_id": value["custody_id"],
        "custodian_id": value["custodian_id"],
        "authorization_record_sha256": value["authorization_record_sha256"],
        "event_count": len(events),
        "event_types": list(event_order),
        "events_fingerprint": _fingerprint(events),
    }


def _private_root(path: Path) -> tuple[Path, int, os.stat_result]:
    if not path.is_absolute() or path.is_symlink():
        raise BlindedIntakeError("private root must be an absolute canonical non-symlink path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise BlindedIntakeError("private root is unavailable") from exc
    if resolved != path:
        raise BlindedIntakeError("private root must be canonical")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise BlindedIntakeError("platform lacks O_NOFOLLOW")
    try:
        descriptor = os.open(resolved, flags | nofollow)
        info = os.fstat(descriptor)
    except OSError as exc:
        raise BlindedIntakeError("private root cannot be held safely") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        os.close(descriptor)
        raise BlindedIntakeError("private root must be an owner-only directory")
    return resolved, descriptor, info


def _publication_parent_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_mode, info.st_uid


def _verify_publication_parent(parent: Path, parent_fd: int, expected: tuple[int, int, int, int]) -> None:
    try:
        held = os.fstat(parent_fd)
        named = os.stat(parent, follow_symlinks=False)
        resolved = parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise BlindedIntakeError("output parent binding changed") from exc
    if not (
        resolved == parent
        and stat.S_ISDIR(held.st_mode)
        and stat.S_ISDIR(named.st_mode)
        and held.st_uid == os.getuid()
        and stat.S_IMODE(held.st_mode) == 0o700
        and _publication_parent_identity(held) == expected
        and _publication_parent_identity(named) == expected
    ):
        raise BlindedIntakeError("output parent binding changed")


def _unlink_if_identity(parent_fd: int, name: str, expected: os.stat_result) -> bool:
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (expected.st_dev, expected.st_ino):
            return False
        os.unlink(name, dir_fd=parent_fd)
    except OSError:
        return False
    return True


def _rename_no_replace(parent_fd: int, source_name: str, destination_name: str) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        symbol = "renameatx_np"
        no_replace_flag = 0x00000004
    elif sys.platform.startswith("linux"):
        symbol = "renameat2"
        no_replace_flag = 1
    else:
        raise BlindedIntakeError("platform cannot provide atomic no-replace publication")
    try:
        rename = getattr(library, symbol)
    except AttributeError as exc:
        raise BlindedIntakeError("platform cannot provide atomic no-replace publication") from exc
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    result = rename(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(destination_name),
        no_replace_flag,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise BlindedIntakeError("output must be write-new")
    unsupported = {errno.ENOSYS, errno.EINVAL, getattr(errno, "ENOTSUP", -1), getattr(errno, "EOPNOTSUPP", -1)}
    if error_number in unsupported:
        raise BlindedIntakeError("output filesystem cannot provide atomic no-replace publication")
    error = OSError(error_number, os.strerror(error_number))
    raise BlindedIntakeError("cannot atomically publish consumer manifest") from error


def _verify_published(
    parent_fd: int,
    name: str,
    payload: bytes,
    written_info: os.stat_result,
    nofollow: int,
) -> None:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0) | nofollow
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise BlindedIntakeError("published consumer manifest is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        chunks = []
        remaining = len(payload) + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        observed = b"".join(chunks)
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not (
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and stat.S_IMODE(before.st_mode) & 0o077 == 0
            and (before.st_dev, before.st_ino) == (written_info.st_dev, written_info.st_ino)
            and before.st_size == len(payload)
            and observed == payload
            and _stable(before) == _stable(after) == _stable(named)
        ):
            raise BlindedIntakeError("published consumer manifest identity or bytes changed")
    finally:
        os.close(descriptor)


def _write_new(output: Path, payload: bytes, private_root: Path) -> None:
    if not output.is_absolute() or output.is_symlink():
        raise BlindedIntakeError("output must be an absolute write-new path")
    try:
        parent = output.parent.resolve(strict=True)
    except OSError as exc:
        raise BlindedIntakeError("output parent is unavailable") from exc
    if parent != output.parent or parent.is_symlink() or output.name in {"", ".", ".."}:
        raise BlindedIntakeError("output path must be canonical with a real parent")
    if parent == private_root or private_root in parent.parents:
        raise BlindedIntakeError("output must be outside the private intake root")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise BlindedIntakeError("platform lacks O_NOFOLLOW")
    parent_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow)
    descriptor = -1
    temporary_name: str | None = None
    temporary_info: os.stat_result | None = None
    written_info: os.stat_result | None = None
    published = False
    try:
        parent_identity = _publication_parent_identity(os.fstat(parent_fd))
        _verify_publication_parent(parent, parent_fd, parent_identity)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        for _ in range(32):
            temporary_name = f".praxis-k562-intake-{secrets.token_hex(16)}.tmp"
            try:
                descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent_fd)
                temporary_info = os.fstat(descriptor)
                break
            except FileExistsError:
                continue
        else:
            raise BlindedIntakeError("cannot reserve a unique temporary publication name")
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError(errno.EIO, "short write")
            remaining = remaining[written:]
        os.fsync(descriptor)
        written_info = os.fstat(descriptor)
        if not (
            stat.S_ISREG(written_info.st_mode) and written_info.st_nlink == 1 and written_info.st_size == len(payload)
        ):
            raise BlindedIntakeError("temporary consumer manifest identity changed")
        named_temporary = os.stat(temporary_name, dir_fd=parent_fd, follow_symlinks=False)
        if _stable(named_temporary) != _stable(written_info):
            raise BlindedIntakeError("temporary consumer manifest path identity changed")
        _verify_publication_parent(parent, parent_fd, parent_identity)
        _rename_no_replace(parent_fd, temporary_name, output.name)
        published = True
        os.fsync(parent_fd)
        _verify_publication_parent(parent, parent_fd, parent_identity)
        _verify_published(parent_fd, output.name, payload, written_info, nofollow)
        _verify_publication_parent(parent, parent_fd, parent_identity)
    except BlindedIntakeError:
        raise
    except OSError as exc:
        raise BlindedIntakeError("cannot persist consumer manifest") from exc
    finally:
        if temporary_info is None and descriptor >= 0:
            try:
                temporary_info = os.fstat(descriptor)
            except OSError:
                pass
        if descriptor >= 0:
            os.close(descriptor)
        cleaned = False
        if not published and temporary_name is not None and temporary_info is not None:
            cleaned = _unlink_if_identity(parent_fd, temporary_name, temporary_info) or cleaned
        if cleaned:
            try:
                os.fsync(parent_fd)
            except OSError:
                pass
        os.close(parent_fd)


def freeze(*, private_root: Path, output: Path) -> dict[str, Any]:
    contract, contract_file_identity = _load_contract()
    root, root_fd, root_info = _private_root(private_root)
    try:
        initial_inventory = set(os.listdir(root_fd))
        if _SCOPE_NAME not in initial_inventory or _CUSTODY_NAME not in initial_inventory:
            raise BlindedIntakeError("private root is missing its two required JSON records")
        scope_payload, scope_identity = _read_small_at(root_fd, _SCOPE_NAME)
        scope = _strict_json(scope_payload, _SCOPE_NAME)
        asset_declarations = _verify_scope(scope, contract)
        expected_inventory = {_SCOPE_NAME, _CUSTODY_NAME, *(item["filename"] for item in asset_declarations)}
        if initial_inventory != expected_inventory:
            raise BlindedIntakeError("private root inventory does not exactly match declared opaque assets")
        custody_payload, custody_identity = _read_small_at(root_fd, _CUSTODY_NAME)
        custody = _strict_json(custody_payload, _CUSTODY_NAME)
        custody_public = _verify_custody(custody, contract, scope_identity["sha256"])
        asset_identities = []
        for declaration in asset_declarations:
            observed = _hash_opaque_at(root_fd, declaration["filename"])
            if observed != {key: declaration[key] for key in ("size_bytes", "sha256")}:
                raise BlindedIntakeError(f"opaque asset identity changed: {declaration['asset_id']}")
            asset_identities.append(
                {
                    "asset_id": declaration["asset_id"],
                    "role": declaration["role"],
                    "source_locator": declaration["source_locator"],
                    "license": declaration["license"],
                    "media_type": declaration["media_type"],
                    **observed,
                }
            )
        if set(os.listdir(root_fd)) != expected_inventory:
            raise BlindedIntakeError("private root inventory changed during verification")
        root_after = os.fstat(root_fd)
        named_root = os.stat(root, follow_symlinks=False)
        if _stable(root_info) != _stable(root_after) or _stable(root_after) != _stable(named_root):
            raise BlindedIntakeError("private root identity changed during verification")
    finally:
        os.close(root_fd)

    verifier_payload, verifier_file_identity = _read_regular_path(Path(__file__).resolve(strict=True), "verifier")
    if verifier_file_identity["sha256"] != _sha256(verifier_payload):
        raise BlindedIntakeError("verifier identity changed")
    contract_payload_sha256 = contract["identity"]["payload_sha256"]
    bundle_basis = {
        "contract_payload_sha256": contract_payload_sha256,
        "scope_manifest_sha256": scope_identity["sha256"],
        "custody_record_sha256": custody_identity["sha256"],
        "asset_identities": asset_identities,
    }
    output_contract = contract["output_contract"]
    manifest = {
        "schema_version": output_contract["schema_version"],
        "record_role": output_contract["record_role"],
        "bundle_id": f"k562-crispra-intake-{_fingerprint(bundle_basis)[:24]}",
        "identity": {
            "payload_sha256": None,
            "payload_hash_algorithm": "sha256(canonical_json(manifest_with_identity.payload_sha256_set_to_null))",
            "contract_payload_sha256": contract_payload_sha256,
            "contract_file": contract_file_identity,
            "verifier_sha256": verifier_file_identity["sha256"],
        },
        "source": {
            "bundle_role": scope["bundle_role"],
            "source_id": scope["source_id"],
            "laboratory_id": scope["laboratory_id"],
            "dataset_fingerprint": scope["dataset_fingerprint"],
            "platform_fingerprint": scope["platform_fingerprint"],
            "source": scope["source"],
            "license": scope["license"],
            "condition_set_sha256": scope["condition_set_sha256"],
            "group_set_sha256": scope["group_set_sha256"],
        },
        "scope": scope["scope"],
        "intake_closure": {
            "condition_counts": scope["condition_counts"],
            "asset_identities": scope["asset_identity_closure"],
        },
        "pair_requirement": contract["input_contract"]["pair_contract"],
        "opaque_asset_identities": asset_identities,
        "input_record_identities": {
            "scope_manifest": scope_identity,
            "custody_record": custody_identity,
        },
        "custody": custody_public,
        "blind_boundary": {
            "outcome_values_in_scope_manifest": False,
            "opaque_asset_bytes_embedded": False,
            "opaque_asset_paths_embedded": False,
            "outcome_decoded": False,
            "candidate_team_received_asset_bytes": False,
            "candidate_outputs_used_for_condition_selection": False,
        },
        "status": {
            "intake_status": "READY_FOR_ESCROW",
            "trusted_pin_required": True,
            "trusted_pin_present": False,
            "evaluation_lock_required": True,
            "evaluation_lock_present": False,
            "evaluation_authorized": False,
            "pair_closure_required": True,
            "pair_closure_present": False,
            "pair_closure_status": "PENDING_SECOND_INDEPENDENT_RECEIPT",
        },
        "states": {
            "benchmark_status": "NOT_RUN",
            "benchmark_passed": None,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
            "registry_or_default_route_changed": False,
        },
    }
    if manifest["status"] != output_contract["maximum_status"] or manifest["states"] != output_contract["states"]:
        raise BlindedIntakeError("output claim ceiling changed")
    copy = json.loads(_canonical_bytes(manifest))
    manifest["identity"]["payload_sha256"] = _fingerprint(copy)
    _write_new(output, _canonical_bytes(manifest) + b"\n", root)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = freeze(private_root=arguments.private_root, output=arguments.output)
    print(json.dumps({"bundle_id": result["bundle_id"], **result["status"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
