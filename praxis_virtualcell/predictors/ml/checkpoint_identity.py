"""Stdlib-only identities and slot metadata for external donor checkpoints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ML_SLOT_CHECKPOINTS: dict[str, tuple[str, str]] = {
    "MockLinear": ("linear_additive", "LinearAdditivePredictor"),
    "MockCPA": ("latent_additive", "LatentAdditivePredictor"),
    "MockGEARS": ("gnn_pert", "GNNPertPredictor"),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_model_version(
    ckpt_stem: str | Path, *, expected_class: str | None = None
) -> str:
    """Bind a donor model version to its config and weight bytes, independent of location."""
    stem = Path(ckpt_stem)
    config_path = Path(f"{stem}.json")
    weights_path = Path(f"{stem}.pt")
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    class_name = config.get("class_name")
    if not isinstance(class_name, str) or not class_name.strip():
        raise ValueError(f"checkpoint config has no class_name: {config_path}")
    if expected_class is not None and class_name != expected_class:
        raise ValueError(
            f"checkpoint class mismatch: expected {expected_class}, got {class_name}"
        )

    identity = {
        "format": "praxis-donor-checkpoint-identity-v1",
        "stem": stem.name,
        "class_name": class_name,
        "json_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "pt_sha256": _sha256_file(weights_path),
    }
    canonical = json.dumps(
        identity, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"donor_ml:{class_name}@sha256:{digest}"
