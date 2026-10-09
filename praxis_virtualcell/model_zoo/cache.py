"""Local model cache with optional size/sha256 version locks. Namespace assets under model_name; root is
configurable. Missing or mismatched assets return available=False, rejecting corrupt or wrong-version weights.
"""
from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_DEFAULT_ROOT = Path.home() / ".cache" / "praxis_virtualcell" / "model_zoo"


@dataclass
class AssetStatus:
    available: bool
    path: str | None
    reason: str


@dataclass(frozen=True)
class ArtifactSnapshot:
    """Private, immutable artifact bytes passed to one direct-v2 wrapper."""

    entries: tuple[tuple[str, bytes, str, int], ...]

    def __post_init__(self) -> None:
        names: set[str] = set()
        for filename, data, sha256, size_bytes in self.entries:
            if (
                not isinstance(filename, str)
                or not filename
                or filename in names
                or type(data) is not bytes
                or not isinstance(sha256, str)
                or len(sha256) != 64
                or not isinstance(size_bytes, int)
                or size_bytes < 0
                or len(data) != size_bytes
                or hashlib.sha256(data).hexdigest() != sha256
            ):
                raise ValueError("artifact snapshot is not an exact byte binding")
            names.add(filename)

    @classmethod
    def empty(cls) -> ArtifactSnapshot:
        """Private test-only/no-asset handoff with the same invariant."""

        return cls(())

    @property
    def asset_bytes(self) -> dict[str, bytes]:
        return {filename: data for filename, data, _sha256, _size in self.entries}

    def is_intact(self) -> bool:
        try:
            self.__post_init__()
        except (TypeError, ValueError):
            return False
        return True


class ModelCache:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or _DEFAULT_ROOT)

    def asset_path(self, model_name: str, asset: str) -> Path:
        """Return a model-namespaced asset path so models cannot overwrite one another."""
        for value in (model_name, asset):
            if not isinstance(value, str):
                raise ValueError("cache identity must be a canonical relative path")
            path = PurePosixPath(value)
            if (
                not value
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in value
                or "\x00" in value
                or str(path) != value
            ):
                raise ValueError("cache identity must be a canonical relative path")
        if "/" in model_name:
            raise ValueError("model_name must be a canonical relative name")
        return self.root / model_name / asset

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _read_cache_asset(
        self,
        model_name: str,
        asset: str,
        *,
        expected_size_bytes: int,
    ) -> bytes:
        """Read one cache asset via non-symlink directory descriptors."""

        if not (hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")):
            raise OSError("safe artifact snapshots require no-follow directory descriptors")
        self.asset_path(model_name, asset)
        root_descriptor = os.open(
            self.root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        descriptors = [root_descriptor]
        try:
            parts = (model_name, *PurePosixPath(asset).parts)
            for part in parts[:-1]:
                descriptors.append(
                    os.open(
                        part,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=descriptors[-1],
                    )
                )
            descriptor = os.open(
                parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=descriptors[-1],
            )
            descriptors.append(descriptor)
            file_stat = os.fstat(descriptor)
            if not stat.S_ISREG(file_stat.st_mode):
                raise OSError("artifact is not a regular file")
            if file_stat.st_size != expected_size_bytes:
                raise OSError("artifact size does not match declared binding")
            chunks: list[bytes] = []
            remaining = expected_size_bytes
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    raise OSError("artifact ended before declared binding")
                if len(chunk) > remaining:
                    raise OSError("artifact read exceeds declared binding")
                chunks.append(chunk)
                remaining -= len(chunk)
            final_stat = os.fstat(descriptor)
            if (
                not stat.S_ISREG(final_stat.st_mode)
                or final_stat.st_size != expected_size_bytes
                or (final_stat.st_dev, final_stat.st_ino) != (file_stat.st_dev, file_stat.st_ino)
            ):
                raise OSError("artifact changed while reading")
            return b"".join(chunks)
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def snapshot(
        self,
        bindings: tuple[tuple[str, str, str, int, str], ...],
        *,
        max_live_snapshot_payload_bytes: int | None = None,
        max_snapshot_entries_per_execution: int | None = None,
    ) -> ArtifactSnapshot:
        """Seal exact declared cache bytes before direct-v2 wrapper construction."""

        if (max_live_snapshot_payload_bytes is None) != (max_snapshot_entries_per_execution is None):
            raise ValueError("artifact snapshot budget must provide bytes and entry limits together")
        if max_live_snapshot_payload_bytes is not None:
            if (
                type(max_live_snapshot_payload_bytes) is not int
                or type(max_snapshot_entries_per_execution) is not int
                or max_live_snapshot_payload_bytes <= 0
                or max_snapshot_entries_per_execution <= 0
            ):
                raise ValueError("artifact snapshot budget limits must be positive integers")
            if (
                len(bindings) > max_snapshot_entries_per_execution
                or sum(binding[3] for binding in bindings) > max_live_snapshot_payload_bytes
            ):
                raise ValueError("artifact snapshot budget exceeded before reading bytes")

        entries: list[tuple[str, bytes, str, int]] = []
        try:
            for model_name, filename, sha256, size_bytes, expected_path in bindings:
                path = self.asset_path(model_name, filename)
                if str(path) != expected_path:
                    raise ValueError("artifact cache path binding drifted")
                data = self._read_cache_asset(
                    model_name,
                    filename,
                    expected_size_bytes=size_bytes,
                )
                if len(data) != size_bytes or hashlib.sha256(data).hexdigest() != sha256:
                    raise ValueError("artifact bytes do not match the declared binding")
                entries.append((filename, data, sha256, size_bytes))
        except (OSError, ValueError) as exc:
            raise ValueError("cannot seal an exact artifact snapshot") from exc
        return ArtifactSnapshot(tuple(entries))

    def check(
        self,
        model_name: str,
        asset: str,
        *,
        sha256: str | None = None,
        size_bytes: int | None = None,
    ) -> AssetStatus:
        """Check asset existence and optional size/sha256 locks; fail closed on missing/mismatched assets."""
        p = self.asset_path(model_name, asset)
        if not p.is_file():
            return AssetStatus(False, None, f"asset_not_found: {asset}")
        try:
            resolved = p.resolve(strict=True)
            root = self.root.resolve(strict=True)
        except OSError:
            return AssetStatus(False, None, f"asset_not_found: {asset}")
        if not resolved.is_relative_to(root):
            return AssetStatus(False, None, "asset_path_escape")
        if size_bytes is not None and p.stat().st_size != size_bytes:
            return AssetStatus(False, None, "size_mismatch: declared asset size")
        if sha256 is not None:
            actual = self._sha256(p)
            if actual != sha256:
                return AssetStatus(
                    False,
                    None,
                    f"sha256_mismatch: expected {sha256[:12]}… got {actual[:12]}…",
                )
        return AssetStatus(True, str(p), "ok")
