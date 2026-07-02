"""L4: GEARS same-split / same-metric — donor norman test split + per-cell ΔPearson via donor EvalAgent.

防泄漏:GEARS 用 **donor train/test 扰动划分**(custom split),GEARS train 排除 donor test 扰动。
评估:donor EvalAgent(与表 A 0.7039 同一路径)→ per-cell ΔPearson。gene order 与 donor 恒等(同源 2000 genes)。
adapter:Prediction.mean = ctx.control + (GEARS预测绝对表达 − GEARS_ctrl_mean) → EvalAgent 取 mean−control = GEARS delta。

仅远端 virtualcell env。用法:python gears_donor_eval.py [epochs]   (epochs=1 验证 pipeline,>=20 出真数字)
"""
import pickle
import sys
import time

import numpy as np
import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def _to_condition(p: str) -> str:
    p = str(p)
    if p == "control":
        return "ctrl"
    return p if "+" in p else f"{p}+ctrl"


def donor_conditions():
    """donor load_norman train/test 的扰动 → GEARS condition 格式集合(防泄漏 split 基础)。"""
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
    import pandas as pd_pkg
    import scanpy as sc
    pd_pkg.Series.nonzero = lambda self: self.to_numpy().nonzero()  # GEARS+新pandas 兼容
    from gears import GEARS, PertData

    t_all = time.time()
    # 1) donor 扰动划分(防泄漏)
    train_c, test_c = donor_conditions()

    # 2) PertData 处理 norman(同 gears_norman.py)
    ad = sc.read_h5ad(_DONOR + "/data/raw/tasks_data/unseen_perts/norman2019_comb_stack.h5ad")
    pert = ad.obs["perturbation"].astype(str)
    ad = ad[(~pert.str.contains("IER5L")).values].copy()  # IER5L 不在 GEARS GO graph
    pert = ad.obs["perturbation"].astype(str)
    ad.obs["condition"] = [_to_condition(p) for p in pert]
    ad.obs["cell_type"] = "K562"
    ad.var["gene_name"] = ad.var_names.astype(str)
    pd = PertData("/home/zkyd/data1/mzy/gears_data")
    pd.new_data_process("norman_donor_l4", adata=ad)
    all_c = set(map(str, pd.adata.obs["condition"].unique()))
    print(f"[gears] PertData conditions={len(all_c)}", flush=True)

    # 3) custom split:train 排除 test 扰动 → 防泄漏;从 train 切 10% val
    test_keep = sorted((test_c & all_c) - {"ctrl"})
    train_pool = sorted(((train_c - test_c) & all_c) - {"ctrl"})
    import random
    random.Random(1).shuffle(train_pool)
    n_val = max(1, len(train_pool) // 10)
    split_dict = {"train": train_pool[n_val:], "val": train_pool[:n_val], "test": test_keep}
    print(f"[split] train={len(split_dict['train'])} val={len(split_dict['val'])} test={len(split_dict['test'])}", flush=True)
    sp = "/home/zkyd/data1/mzy/gears_data/l4_split.pkl"
    with open(sp, "wb") as f:
        pickle.dump(split_dict, f)
    pd.prepare_split(split="custom", split_dict_path=sp, seed=1)
    pd.get_dataloader(batch_size=32, test_batch_size=64)

    # 4) 训练 GEARS
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
                self._cache[key] = abs_pred - ctrl_mean  # GEARS delta(同 donor gene order)
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
