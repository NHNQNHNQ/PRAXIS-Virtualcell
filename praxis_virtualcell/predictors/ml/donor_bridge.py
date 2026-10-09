"""Reuse donor code through sys.path to load predictors and Norman data; requires torch and donor dependencies."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

import torch  # noqa: E402

_CLASSES: dict[str, Any] = {}


def _cls(name: str):
    """Resolve the donor predictor class from CamelCase class_name in checkpoint JSON."""
    if not _CLASSES:
        from predictors.cpa_style import CPAStylePredictor
        from predictors.decoder_only import DecoderOnlyPredictor
        from predictors.gnn_pert import GNNPertPredictor
        from predictors.latent_additive import LatentAdditivePredictor
        from predictors.linear_additive import LinearAdditivePredictor
        from predictors.pretrained_backbone import PretrainedBackbonePredictor

        for c in (LinearAdditivePredictor, LatentAdditivePredictor, CPAStylePredictor,
                  GNNPertPredictor, DecoderOnlyPredictor, PretrainedBackbonePredictor):
            _CLASSES[c.__name__] = c
    return _CLASSES[name]


def build_predictor_from_ckpt(ckpt_stem: str):
    """Read an extensionless checkpoint stem such as norman_2019/linear_additive, rebuild from .json, load the .pt
    bundle, and return (model,cfg).
    """
    cfg = json.loads(Path(ckpt_stem + ".json").read_text(encoding="utf-8"))
    model = _cls(cfg["class_name"])(**cfg["kwargs"])

    bundle = torch.load(ckpt_stem + ".pt", map_location="cpu", weights_only=False)
    state = bundle["state_dict"] if isinstance(bundle, dict) and "state_dict" in bundle else bundle
    model.load_state_dict(state)
    model.eval()
    return model, cfg


def load_norman(split: str = "test", *, max_perts: int | None = None,
                max_cells: int | None = 200, seed: int = 1):
    """Load Norman with default max_cells=200 and seed=1 to preserve historical test sampling."""
    from bench.vcbench.loader import load_vcbench_split

    kw: dict[str, Any] = {"rng_seed": seed}
    if max_perts is not None:
        kw["max_perts"] = max_perts
    if max_cells is not None:
        kw["max_cells_per_pert"] = max_cells
    return load_vcbench_split("norman_2019", split, **kw)
