"""S2(W8):mean-perturbation naive baseline —— 同 donor norman split + 同 EvalAgent + per-cell ΔPearson。

满足项目 ≥3 baseline 不变量,给统一准确性表一个 same-protocol 下界。仅远端 virtualcell env 跑。

baseline 定义(扰动预测文献标准 naive):perturbation-agnostic,对任何扰动都预测
`control + 训练集平均 delta`(mean_delta = 训练集所有非 control 细胞 (target-control) 的平均),
忽略 pert_emb。它无法捕捉扰动特异效应,故应明显低于训练 predictor。

实测(donor norman, max_cells=200, train seed=0 / test seed=1):
    MEAN_BASELINE_DELTA_PEARSON = 0.4615  (cosine 0.9850, n=18874, mean_delta from n_train=25463)
→ 低于 6 base(0.6183~0.6716)与 Coordinator(0.7039);亦高于 scGPT frozen 0.4407(诚实:冻结基础模型反不如平均 baseline)。

用法:conda activate virtualcell; python -m praxis_virtualcell.benchmarks.mean_baseline
"""
from __future__ import annotations

import sys
from typing import Any

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def _build_mean_predictor(mean_delta):
    """构造 MeanPerturbationPredictor(在函数内 import donor base,避免 Mac 无 torch 时 import 失败)。"""
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
    """训练集所有非 control 细胞 (target-control) 的平均 delta [n_genes]。返回 (mean_delta, n_used)。"""
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
