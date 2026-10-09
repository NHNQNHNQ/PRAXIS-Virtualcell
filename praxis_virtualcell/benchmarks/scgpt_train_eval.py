"""Train a donor scGPT head and evaluate in the separate vc-scgpt environment (torch 2.3.1, torchtext 0.18, scGPT,
IPython); torch 2.6 has an incompatible torchtext ABI. Use epochs/max_cells/batch arguments. Full attention over
2000 genes without flash_attn can use about 15GB for large batches. Historical 3 epochs, max_cells=50 gave
delta-Pearson=0.4407.
"""
from __future__ import annotations

import os
import sys
import time

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def main(epochs: int = 3, max_cells: int = 50, batch: int = 8) -> float:
    from pathlib import Path

    scgpt_ckpt = os.environ.get("SCGPT_PRETRAINED_ROOT", "").strip()
    if not scgpt_ckpt:
        raise RuntimeError("Set SCGPT_PRETRAINED_ROOT to the scGPT pretrained assets")

    import scripts.checkpoint as ckpt
    from bench.vcbench.loader import load_vcbench_split
    from coordinator.eval_agent import EvalAgent
    from predictors.pretrained_backbone import PretrainedBackbonePredictor
    from scripts.run_bench import train_predictor

    t0 = time.time()
    train_ds = load_vcbench_split("norman_2019", "train", rng_seed=0, max_cells_per_pert=max_cells)
    test_ds = load_vcbench_split("norman_2019", "test", rng_seed=1, max_cells_per_pert=max_cells)
    gn = list(train_ds.gene_names)
    model = PretrainedBackbonePredictor(
        pert_dim=5120, n_genes=2000, backbone_name="scgpt",
        backbone_kwargs={"gene_names": gn, "ckpt_dir": scgpt_ckpt})
    train_predictor(model, train_ds, epochs=epochs, lr=1e-3, batch_size=batch, device="cuda")
    rep = EvalAgent(batch_size=16, device="cuda").evaluate(model, test_ds)
    dp = float(rep.metrics.delta_pearson)
    print(f"SCGPT_NORMAN_DELTA_PEARSON = {dp} (t={time.time() - t0:.0f}s)")
    outdir = Path(os.environ.get("SCGPT_OUTPUT_ROOT", "runs/scgpt/norman_2019"))
    ckpt.save_predictor(model, outdir, kwargs={
        "pert_dim": 5120, "n_genes": 2000, "backbone_name": "scgpt",
        "backbone_kwargs": {"gene_names": gn, "ckpt_dir": scgpt_ckpt}},
        meta={"delta_pearson": dp, "bench": "norman_2019", "epochs": epochs, "max_cells": max_cells})
    return dp


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if len(a) > 0 else 3, int(a[1]) if len(a) > 1 else 50, int(a[2]) if len(a) > 2 else 8)
