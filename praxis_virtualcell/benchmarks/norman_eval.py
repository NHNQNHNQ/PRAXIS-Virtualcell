"""Load the donor linear predictor through the ML adapter and evaluate Norman with the same checkpoint, loader, and
EvalAgent metric in the remote environment.
"""
from __future__ import annotations

import os
import sys
from typing import Any

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def score_linear_ckpt(ckpt_stem: str, *, split: str = "test", seed: int = 1) -> dict[str, Any]:
    import torch
    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    model, _ = build_predictor_from_ckpt(ckpt_stem)
    ds = load_norman(split=split, seed=seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, ds)
    return {"delta_pearson": rep.metrics.delta_pearson, "cosine": rep.metrics.cosine,
            "n": rep.n_samples}
