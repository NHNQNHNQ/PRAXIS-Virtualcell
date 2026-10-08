"""Resolve small shared dataset indexes without copying source assets."""
from __future__ import annotations

import json
from pathlib import Path


def dataset_file(root: str | Path, name: str, manifest: dict | None = None) -> Path:
    directory = Path(root)
    if manifest is None:
        manifest = json.loads((directory / "manifest.json").read_text())
    shared = manifest.get("shared_files", {}).get(name)
    if shared is None:
        return directory / name
    if not isinstance(shared, dict) or set(shared) != {"path"} or not isinstance(shared["path"], str):
        raise ValueError("invalid_shared_dataset_index")
    # Every caller verifies its receipt before consuming the shared file. The
    # pointer preserves one copy of private source/answer indexes across versions.
    return (directory / shared["path"]).resolve()
