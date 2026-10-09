"""Evaluate the reused donor Coordinator/SubAgent/predictor stack on Norman with EvalAgent to check score
preservation in the remote environment.
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

COMBOS = [
    ["latent_additive", "gnn_pert"],
    ["cpa_style", "decoder_only", "gnn_pert"],
    ["linear_additive", "latent_additive", "cpa_style", "gnn_pert", "decoder_only"],
]


def score_coordinator(ckpt_dir: str, predictor_names: list[str], *,
                      split: str = "test", seed: int = 1) -> dict[str, Any]:
    import torch
    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.coordinator_bridge import build_coordinator
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    coord = build_coordinator(ckpt_dir, predictor_names, device=dev)
    ds = load_norman(split=split, seed=seed)  # max_cells=200, seed=1
    rep = EvalAgent(batch_size=64, device=dev).evaluate(coord, ds)
    return {"delta_pearson": rep.metrics.delta_pearson, "cosine": rep.metrics.cosine,
            "n": rep.n_samples, "predictors": list(predictor_names)}


def main(ckpt_dir: str) -> None:
    print(f"{'combo':52s} {'dp':>10s} {'n':>8s}")
    for combo in COMBOS:
        s = score_coordinator(ckpt_dir, combo)
        print(f"{'+'.join(combo):52s} {s['delta_pearson']:>10.6f} {s['n']:>8d}")


if __name__ == "__main__":
    main(sys.argv[1])
