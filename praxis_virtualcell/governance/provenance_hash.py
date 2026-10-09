"""Deterministic per-call canonical sha256 records for model name/version, input/output hashes, and evidence;
provide completeness checks for governance gates.
"""
from __future__ import annotations

import hashlib
import json
import re

_REQUIRED = ("model_name", "model_version", "input_hash", "output_hash")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canon_sha256(obj) -> str:
    """Compute canonical JSON sha256 using the same deterministic pattern as runtime trace identity."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def compute_call_provenance(model_name: str, model_version: str | None,
                            model_input, output, evidence) -> dict:
    """Create per_call provenance with canonical input/output hashes. Rejected calls hash the request; failed
    preparation can hash an empty dictionary; successful calls hash prepared input. Convert NumPy values to
    lists/native floats before hashing to avoid string coercion.
    """
    return {
        "model_name": model_name,
        "model_version": model_version,
        "input_hash": _canon_sha256(model_input),
        "output_hash": _canon_sha256(output),
        "evidence_source": list(evidence) if evidence else [],
    }


def check_call_provenance(per_call) -> list[str]:
    """Return required keys that are missing, empty, or have invalid hash format; empty means complete."""
    if not isinstance(per_call, dict):
        return list(_REQUIRED)
    invalid = [key for key in ("model_name", "model_version") if not per_call.get(key)]
    invalid.extend(
        key for key in ("input_hash", "output_hash")
        if not isinstance(per_call.get(key), str) or not _SHA256.fullmatch(per_call[key])
    )
    return invalid
