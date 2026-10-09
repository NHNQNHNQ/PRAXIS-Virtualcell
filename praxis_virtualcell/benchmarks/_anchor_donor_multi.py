"""Evaluate multiple donor checkpoints against their delta-Pearson anchors in the remote environment. Use the same
Norman test set (max_cells=200, seed=1). pretrained_backbone uses mock_backbone here, not actual scGPT.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

PREDICTORS = ["linear_additive", "latent_additive", "cpa_style", "gnn_pert",
              "decoder_only", "pretrained_backbone"]


def main(ckpt_dir: str) -> None:
    import torch
    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    ds = load_norman(split="test")  # max_cells=200, seed=1
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ea = EvalAgent(batch_size=64, device=dev)
    print(f"{'predictor':24s} {'S0':>11s} {'S_eval':>11s} {'diff':>10s}")
    for name in PREDICTORS:
        stem = str(Path(ckpt_dir) / name)
        model, cfg = build_predictor_from_ckpt(stem)
        s0 = cfg["meta"].get("delta_pearson")
        rep = ea.evaluate(model, ds)
        se = rep.metrics.delta_pearson
        print(f"{name:24s} {s0:>11.6f} {se:>11.6f} {abs(s0 - se):>10.2e}")


if __name__ == "__main__":
    main(sys.argv[1])
