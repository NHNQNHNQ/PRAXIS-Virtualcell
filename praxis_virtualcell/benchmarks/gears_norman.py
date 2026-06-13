"""Week 4c Phase 1:GEARS 原生 norman 训练 + eval。

仅在 `virtualcell` env 跑(torch 2.6 + PyG 2.8 + cell-gears 0.0.2)。用 donor norman h5ad 适配 GEARS
`PertData`(避免 dataverse 慢下载),复用 donor 本地 gene2go/essential。sys.path 注入 donor(不 vendor)。

GEARS 0.0.2 老包兼容坑(见 finding_w4c_gears):
- monkey-patch `pd.Series.nonzero`(GEARS 用 sparse_X[pandas_Series_mask],新 scipy/pandas 不兼容)。
- 过滤 IER5L(不在 GEARS GO graph,否则训练 KeyError)。

复现:
    conda activate virtualcell
    python -m praxis_virtualcell.benchmarks.gears_norman 5    # epochs

结果(5ep):pearson_de 0.8392(GEARS 指标,**与 donor delta_pearson 不可比**:指标/split 不同)。
"""
from __future__ import annotations

import sys
import time

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def main(epochs: int = 5, gears_data: str = "/home/zkyd/data1/mzy/gears_data") -> dict:
    import pandas as pd_pkg
    import scanpy as sc

    pd_pkg.Series.nonzero = lambda self: self.to_numpy().nonzero()  # GEARS + 新 pandas 兼容
    from gears import GEARS, PertData

    t0 = time.time()
    ad = sc.read_h5ad(_DONOR + "/data/raw/tasks_data/unseen_perts/norman2019_comb_stack.h5ad")
    pert = ad.obs["perturbation"].astype(str)
    ad = ad[(~pert.str.contains("IER5L")).values].copy()  # IER5L 不在 GEARS GO graph
    pert = ad.obs["perturbation"].astype(str)
    ad.obs["condition"] = [("ctrl" if p == "control" else (p if "+" in p else f"{p}+ctrl")) for p in pert]
    ad.obs["cell_type"] = "K562"
    ad.var["gene_name"] = ad.var_names.astype(str)
    pd = PertData(gears_data)
    pd.new_data_process("norman_donor2", adata=ad)
    pd.prepare_split(split="simulation", seed=1)
    pd.get_dataloader(batch_size=32, test_batch_size=64)
    g = GEARS(pd, device="cuda")
    g.model_initialize(hidden_size=64)
    g.train(epochs=epochs)
    from gears.inference import compute_metrics, evaluate
    res = evaluate(pd.dataloader["test_loader"], g.best_model, False, "cuda")
    m, _ = compute_metrics(res)
    out = {k: round(float(m[k]), 4) for k in m if "pearson" in k.lower() or "mse" in k.lower()}
    print(f"GEARS_METRICS: {out} (t={time.time() - t0:.0f}s)")
    return out


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
