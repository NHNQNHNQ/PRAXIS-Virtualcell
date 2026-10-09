"""Native GEARS Norman training/evaluation in the virtualcell environment (torch 2.6, PyG 2.8, cell-gears 0.0.2).
Adapt local donor H5AD and gene2go/essential assets; patch Series.nonzero and exclude IER5L for compatibility.
Historical 5-epoch pearson_de=0.8392 uses a different metric/split from donor delta-Pearson and is not directly
comparable.
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


def main(epochs: int = 5, gears_data: str | None = None,
         save_dir: str | None = None) -> dict:
    gears_data = gears_data or os.environ.get("GEARS_DATA_ROOT", "").strip()
    if not gears_data:
        raise RuntimeError("Set GEARS_DATA_ROOT or pass gears_data explicitly")
    import pandas as pd_pkg
    import scanpy as sc

    pd_pkg.Series.nonzero = lambda self: self.to_numpy().nonzero()
    from gears import GEARS, PertData

    t0 = time.time()
    ad = sc.read_h5ad(_DONOR + "/data/raw/tasks_data/unseen_perts/norman2019_comb_stack.h5ad")
    pert = ad.obs["perturbation"].astype(str)
    ad = ad[(~pert.str.contains("IER5L")).values].copy()
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
    if save_dir:
        g.save_model(save_dir)
        print(f"GEARS_SAVED: {save_dir}")
    return out


if __name__ == "__main__":

    _epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    _save = sys.argv[2] if len(sys.argv) > 2 else None
    main(_epochs, save_dir=_save)
