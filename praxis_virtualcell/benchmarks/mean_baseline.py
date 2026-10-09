"""Perturbation-agnostic mean baseline under the donor Norman split and EvalAgent protocol. Predict control plus
the average training noncontrol delta, ignoring pert_emb. Historical max_cells=200, train seed=0/test seed=1:
delta-Pearson=0.4615, cosine=0.9850, n=18874, n_train=25463. Six bases gave 0.6183–0.6716, Coordinator 0.7039,
and frozen scGPT 0.4407; these are protocol-bound results.
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


def _build_mean_predictor(mean_delta):
    """Build MeanPerturbationPredictor with a lazy donor import so local imports work without torch."""
    import torch  # noqa: F401
    from predictors.base import Prediction, Predictor

    class MeanPerturbationPredictor(Predictor):
        def __init__(self, md):
            super().__init__()
            self.register_buffer("mean_delta", md)

        @property
        def name(self) -> str:
            return "mean_perturbation_baseline"

        def supports(self, pert) -> bool:
            return pert.kind in ("gene_ko", "gene_combo", "control")

        def predict(self, ctx, pert):
            ctrl = ctx.control
            if ctrl.dim() == 1:
                ctrl = ctrl.unsqueeze(0)
            if pert.kind == "control" or not pert.targets:
                mean = ctrl
            else:
                mean = ctrl + self.mean_delta.to(ctrl.device, ctrl.dtype)
            return Prediction(mean=mean)

        def provenance(self) -> dict:
            return {"name": self.name, "kind": "naive_mean_perturbation"}

    return MeanPerturbationPredictor(mean_delta)


def compute_mean_delta(ds):
    """Average training noncontrol (target−control) deltas across cells; return (mean_delta, n_used)."""
    import torch
    from bench.vcbench.loader import collate_perturbation
    from torch.utils.data import DataLoader

    loader = DataLoader(ds, batch_size=64, shuffle=False, collate_fn=collate_perturbation)
    tot = None
    n = 0
    for batch in loader:
        control = batch["control"]
        target = batch["target"]
        perts = batch["perturbation"]
        mask = torch.tensor([p != "control" for p in perts])
        if int(mask.sum()) == 0:
            continue
        d = (target[mask] - control[mask]).sum(0)
        tot = d if tot is None else tot + d
        n += int(mask.sum())
    return tot / n, n


def score_mean_baseline(*, test_seed: int = 1, train_seed: int = 0) -> dict[str, Any]:
    import torch
    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    train_ds = load_norman(split="train", seed=train_seed)
    test_ds = load_norman(split="test", seed=test_seed)
    mean_delta, n_train = compute_mean_delta(train_ds)
    model = _build_mean_predictor(mean_delta)
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, test_ds)
    return {"delta_pearson": rep.metrics.delta_pearson, "cosine": rep.metrics.cosine,
            "n": rep.n_samples, "n_train": n_train}


def main() -> None:
    s = score_mean_baseline()
    print(f"MEAN_BASELINE_DELTA_PEARSON = {s['delta_pearson']} cosine = {s['cosine']} "
          f"n = {s['n']} (mean_delta from n_train={s['n_train']})")


if __name__ == "__main__":
    main()
