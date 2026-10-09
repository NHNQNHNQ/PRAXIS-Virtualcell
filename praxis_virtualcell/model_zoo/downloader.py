"""Resolve model sources without downloading large remote models. cobra_bundled/local sources can be resolved
locally; remote identifiers require manual fetch and remain unavailable. Missing/unrecognized sources fail
closed.
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_source(entry: dict) -> dict:
    """Return source status/availability metadata; status is resolved or requires_manual_fetch."""
    source = entry.get("source")
    if not source:
        raise ValueError(f"model_zoo entry {entry.get('name')} missing source field")

    if source.startswith("cobra_bundled"):

        return {"status": "resolved", "available": True, "fetch": "none",
                "path": None, "reason": "cobra-bundled asset, loaded via cobra"}

    if source.startswith("local:"):
        rel = source.split("local:", 1)[1]
        p = (_REPO_ROOT / rel)
        if not p.is_file():
            return {"status": "requires_manual_fetch", "available": False, "fetch": "manual",
                    "path": str(p), "reason": f"declared local asset missing: {rel}"}
        return {"status": "resolved", "available": True, "fetch": "none",
                "path": str(p), "reason": "local repo asset"}

    if source.startswith("remote:") or source.startswith("self_trained:"):

        req = entry.get("requires", [])
        return {"status": "requires_manual_fetch", "available": False, "fetch": "manual",
                "path": None,
                "reason": f"remote/self-trained weights require manual fetch (requires={req}); "
                          "Phase 2 does not download large models"}

    raise ValueError(f"model_zoo entry {entry.get('name')} has an unrecognized source scheme: {source}")
