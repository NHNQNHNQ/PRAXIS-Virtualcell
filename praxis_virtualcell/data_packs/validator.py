"""Deterministic path, size, and hash validation for a local Pack."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath

from praxis_virtualcell.data_packs.errors import (
    PackAssetHashMismatch,
    PackAssetMissing,
    PackAssetSizeMismatch,
    PackManifestError,
    PackPathError,
)
from praxis_virtualcell.data_packs.manifest import PackManifest, load_manifest


def resolve_asset_path(root: Path, declared: str) -> Path:
    relative = PurePosixPath(declared)
    if (
        "\\" in declared
        or relative.is_absolute()
        or PureWindowsPath(declared).is_absolute()
        or not relative.parts
        or any(part in (".", "..") for part in relative.parts)
        or str(relative) != declared
    ):
        raise PackPathError(f"unsafe asset path: {declared!r}")
    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PackAssetMissing(f"declared asset is missing: {declared}") from exc
    if not resolved.is_relative_to(root):
        raise PackPathError(f"asset escapes Pack root: {declared!r}")
    if not resolved.is_file():
        raise PackAssetMissing(f"declared asset is not a regular file: {declared}")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_pack(pack_root: str | Path) -> PackManifest:
    root_path = Path(pack_root)
    try:
        root = root_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PackManifestError(f"Pack root does not exist: {root_path}") from exc
    if not root.is_dir():
        raise PackManifestError(f"Pack root is not a directory: {root_path}")

    try:
        manifest_path = resolve_asset_path(root, "manifest.yaml")
    except (PackAssetMissing, PackPathError) as exc:
        raise PackManifestError(f"Pack manifest must remain inside Pack root: {exc}") from exc
    manifest = load_manifest(manifest_path)
    for asset in manifest.assets:
        path = resolve_asset_path(root, asset.path)
        actual_size = path.stat().st_size
        if actual_size != asset.size_bytes:
            raise PackAssetSizeMismatch(
                f"asset size mismatch for {asset.id}: expected {asset.size_bytes}, got {actual_size}"
            )
        actual_hash = _sha256(path)
        if actual_hash != asset.sha256:
            raise PackAssetHashMismatch(
                f"asset hash mismatch for {asset.id}: expected {asset.sha256}, got {actual_hash}"
            )
    return manifest
