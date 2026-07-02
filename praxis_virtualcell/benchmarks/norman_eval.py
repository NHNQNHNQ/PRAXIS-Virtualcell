"""praxis 侧:经 ml 适配加载 donor linear,复用 donor EvalAgent 在 Norman 上算分。

证迁移到 praxis_virtualcell 后分数与 donor 一致(同 ckpt/loader/metric)。仅远端跑。
"""
from __future__ import annotations

import sys
from typing import Any

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def score_linear_ckpt(ckpt_stem: str, *, split: str = "test", seed: int = 1) -> dict[str, Any]:
    import torch
    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    model, _ = build_predictor_from_ckpt(ckpt_stem)
    ds = load_norman(split=split, seed=seed)  # 默认 max_cells=200 → 复现 anchor 配方
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, ds)
    return {"delta_pearson": rep.metrics.delta_pearson, "cosine": rep.metrics.cosine,
            "n": rep.n_samples}
