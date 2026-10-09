"""Week 4c Phase 2:scGPT(donor pretrained_backbone, backbone_name='scgpt')训 head on donor norman + eval。

仅在 `vc-scgpt` env 跑(torch 2.3.1 + torchtext 0.18 + scgpt + IPython)。
virtualcell 的 torch 2.6 与 scgpt 依赖的 torchtext ABI 不兼容,故 scGPT 单独 env。sys.path 注入 donor(不 vendor)。

复现:
    conda activate vc-scgpt
    python -m praxis_virtualcell.benchmarks.scgpt_train_eval 3 50 8   # epochs max_cells batch

减规模(max_cells/小 batch)避 OOM:scGPT 无 flash_attn → full attention over 2000 genes 爆显存(~15GB/大 batch)。
结果(3ep / max_cells=50):ΔPearson **0.4407**(frozen backbone 局限,见 finding_w4c_scgpt)。
"""
from __future__ import annotations

import sys
import time

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def main(epochs: int = 3, max_cells: int = 50, batch: int = 8) -> float:
    from pathlib import Path

    import scripts.checkpoint as ckpt
    from bench.vcbench.loader import load_vcbench_split
    from coordinator.eval_agent import EvalAgent
    from predictors.pretrained_backbone import PretrainedBackbonePredictor
    from scripts.run_bench import train_predictor

    scgpt_ckpt = _DONOR + "/data/raw/pretrained/scgpt"
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
    outdir = Path("/home/zkyd/data1/mzy/scgpt_ckpt/norman_2019")
    ckpt.save_predictor(model, outdir, kwargs={
        "pert_dim": 5120, "n_genes": 2000, "backbone_name": "scgpt",
        "backbone_kwargs": {"gene_names": gn, "ckpt_dir": scgpt_ckpt}},
        meta={"delta_pearson": dp, "bench": "norman_2019", "epochs": epochs, "max_cells": max_cells})
    return dp


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if len(a) > 0 else 3, int(a[1]) if len(a) > 1 else 50, int(a[2]) if len(a) > 2 else 8)
