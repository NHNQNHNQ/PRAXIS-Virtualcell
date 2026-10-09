"""GEARS same-split/same-metric evaluation using donor Norman train/test perturbations and donor per-cell
delta-Pearson. Exclude donor test perturbations from GEARS training. Preserve the same 2000-gene order; adapter
mean=control+(GEARS expression−GEARS control mean). Historical donor reference is 0.7039. Remote execution;
epochs=1 checks the pipeline and >=20 supports full evaluation.
"""  # noqa: E501
import os
import pickle
import sys
import time

import numpy as np

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

import torch  # noqa: E402


def _to_condition(p: str) -> str:
    p = str(p)
    if p == "control":
        return "ctrl"
    return p if "+" in p else f"{p}+ctrl"


def donor_conditions():
    """Convert donor train/test perturbations to GEARS condition sets for leakage-safe splits."""
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman
    out = {}
    for split in ("train", "test"):
        ds = load_norman(split, seed=1)
        s = set()
        for i in range(len(ds)):
            s.add(_to_condition(ds[i].perturbation))
        out[split] = s
        print(f"[donor] {split}: {len(ds)} cells, {len(s)} distinct conditions", flush=True)
    return out["train"], out["test"]


def main(epochs: int = 20):
    gears_data = os.environ.get("GEARS_DATA_ROOT", "").strip()
    if not gears_data:
        raise RuntimeError("Set GEARS_DATA_ROOT to the external GEARS data directory")
    import pandas as pd_pkg
    import scanpy as sc
    pd_pkg.Series.nonzero = lambda self: self.to_numpy().nonzero()
    from gears import GEARS, PertData

    t_all = time.time()

    train_c, test_c = donor_conditions()


    ad = sc.read_h5ad(_DONOR + "/data/raw/tasks_data/unseen_perts/norman2019_comb_stack.h5ad")
    pert = ad.obs["perturbation"].astype(str)
    ad = ad[(~pert.str.contains("IER5L")).values].copy()
    pert = ad.obs["perturbation"].astype(str)
    ad.obs["condition"] = [_to_condition(p) for p in pert]
    ad.obs["cell_type"] = "K562"
    ad.var["gene_name"] = ad.var_names.astype(str)
    pd = PertData(gears_data)
    pd.new_data_process("norman_donor_l4", adata=ad)
    all_c = set(map(str, pd.adata.obs["condition"].unique()))
    print(f"[gears] PertData conditions={len(all_c)}", flush=True)


    test_keep = sorted((test_c & all_c) - {"ctrl"})
    train_pool = sorted(((train_c - test_c) & all_c) - {"ctrl"})
    import random
    random.Random(1).shuffle(train_pool)
    n_val = max(1, len(train_pool) // 10)
    split_dict = {"train": train_pool[n_val:], "val": train_pool[:n_val], "test": test_keep}
    print(f"[split] train={len(split_dict['train'])} val={len(split_dict['val'])} test={len(split_dict['test'])}", flush=True)  # noqa: E501
    sp = os.path.join(gears_data, "l4_split.pkl")
    with open(sp, "wb") as f:
        pickle.dump(split_dict, f)
    pd.prepare_split(split="custom", split_dict_path=sp, seed=1)
    pd.get_dataloader(batch_size=32, test_batch_size=64)


    g = GEARS(pd, device="cuda")
    g.model_initialize(hidden_size=64)
    t0 = time.time()
    g.train(epochs=epochs)
    print(f"[train] {epochs}ep done t={time.time()-t0:.0f}s", flush=True)

    # 5) GearsDonorAdapter + donor EvalAgent
    from coordinator.eval_agent import EvalAgent
    from predictors.base import Prediction, Predictor

    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    ctrl = pd.adata[pd.adata.obs["condition"] == "ctrl"]
    ctrl_mean = torch.tensor(np.asarray(ctrl.X.mean(0)).ravel(), dtype=torch.float32)
    vocab = set(g.pert_list)

    class GearsDonorAdapter(Predictor):
        def __init__(self):
            super().__init__()
            self.name = "gears"
            self._cache = {}

        def supports(self, pert) -> bool:
            if pert.kind == "control":
                return True
            return len(pert.targets) > 0 and all(t in vocab for t in pert.targets)

        def predict(self, ctx, pert):
            c = ctx.control
            if c.dim() == 1:
                c = c.unsqueeze(0)
            if pert.kind == "control":
                return Prediction(mean=c)
            key = "_".join(pert.targets)
            if key not in self._cache:
                res = g.predict([list(pert.targets)])
                k = next(iter(res))  # GEARS dict key
                abs_pred = torch.tensor(np.asarray(res[k]).ravel(), dtype=torch.float32)
                self._cache[key] = abs_pred - ctrl_mean
            d = self._cache[key].to(c.device)
            return Prediction(mean=c + d, meta={"predictor": "gears"})

        def provenance(self):
            return {"predictor": "gears", "data": "norman_donor_l4", "split": "donor_aligned"}

    ds = load_norman("test", seed=1)
    rep = EvalAgent(batch_size=64, device="cuda").evaluate(GearsDonorAdapter(), ds)
    dp = float(rep.metrics.delta_pearson)
    print(f"GEARS_DONOR_EVAL: delta_pearson={dp:.6f} cosine={float(rep.metrics.cosine):.6f} "
          f"n={rep.n_samples} epochs={epochs} total_t={time.time()-t_all:.0f}s", flush=True)
    return dp


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
