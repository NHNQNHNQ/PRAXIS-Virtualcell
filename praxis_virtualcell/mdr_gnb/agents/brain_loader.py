"""物种 brain .yaml 加载器(兼容 schema)。每物种 brain/ 下多文件或单 rules.yaml,
统一产出五键 dict:rules / resistance_mechanisms / negative_cases / assay_boundaries /
species_specific_breakpoints。缺文件/缺键降级为空,不崩(fail-safe,由 abstain 兜底)。"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

_SCHEMA_KEYS = ("rules", "resistance_mechanisms", "negative_cases",
                "assay_boundaries", "species_specific_breakpoints")
_EMPTY: dict[str, Any] = {
    "rules": [], "resistance_mechanisms": [], "negative_cases": [],
    "assay_boundaries": [], "species_specific_breakpoints": {},
}


def _load_yaml(p: Path) -> Any:
    if not p.is_file():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_species_brain_documents(
    single_document: Any,
    overlays: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the five-key brain schema from already captured YAML documents.

    ``rules.yaml`` is the single-file base document.  The four other schema
    keys may be supplied as independent overlay documents.  Keeping this
    normalization separate from filesystem I/O lets one execution consume the
    exact bytes whose hashes were recorded in its governance snapshot.
    """
    brain = {k: (dict(_EMPTY[k]) if isinstance(_EMPTY[k], dict) else list(_EMPTY[k]))
             for k in _SCHEMA_KEYS}
    merged: dict[str, Any] = {}
    if isinstance(single_document, dict):
        merged.update(single_document)
    # ``rules.yaml`` is the base document, not an overlay for its own ``rules``
    # key.  Loading it again as ``rules.yaml`` used to replace ``brain['rules']``
    # with the entire document instead of its rules list.
    overlay_docs = overlays or {}
    for key in _SCHEMA_KEYS:
        if key == "rules":
            continue
        per = overlay_docs.get(key)
        if per is not None:
            merged[key] = per
    for key in _SCHEMA_KEYS:
        if key in merged and merged[key] is not None:
            brain[key] = deepcopy(merged[key])
    return brain


def load_species_brain(brain_dir: Path) -> dict[str, Any]:
    """Read one species brain from disk for legacy/non-snapshotted callers."""
    root = Path(brain_dir)
    if not root.is_dir():
        return load_species_brain_documents(None)
    # 优先单文件 rules.yaml(含全部五键);再允许四个独立文件覆盖。
    return load_species_brain_documents(
        _load_yaml(root / "rules.yaml"),
        {
            key: _load_yaml(root / f"{key}.yaml")
            for key in _SCHEMA_KEYS
            if key != "rules"
        },
    )
