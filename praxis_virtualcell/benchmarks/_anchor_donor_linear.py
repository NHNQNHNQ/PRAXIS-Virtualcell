"""M1:远端加载 donor linear ckpt,EvalAgent 在 Norman test 上算 ΔPearson,对照 ckpt 记录的 S0。

仅远端 `virtualcell` 环境跑(import torch + donor,sys.path 注入 donor 不 vendor)。
用法:python -m praxis_virtualcell.benchmarks._anchor_donor_linear <ckpt_stem>

复现配方(见 docs/findings/finding_w4a_env.md):
- linear_additive deterministic 不可训 → ckpt + 同采样 = 逐位复现 S0=0.6638587
- 训练时 test split 配置:max_cells_per_pert=200, rng_seed=seed+1=1, esm2 features(loader 默认)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def main(ckpt_stem: str) -> None:
    cfg = json.loads(Path(ckpt_stem + ".json").read_text(encoding="utf-8"))
    from bench.vcbench.loader import load_vcbench_split
    from coordinator.eval_agent import EvalAgent
    from predictors.linear_additive import LinearAdditivePredictor

    model = LinearAdditivePredictor(**cfg["kwargs"])
    # .pt 是 bundle dict(含 state_dict);torch>=2.6 须 weights_only=False
    bundle = torch.load(ckpt_stem + ".pt", map_location="cpu", weights_only=False)
    state = bundle["state_dict"] if isinstance(bundle, dict) and "state_dict" in bundle else bundle
    model.load_state_dict(state)
    model.eval()

    # 复现训练时 eval 配置:max_cells_per_pert=200, rng_seed=1
    ds = load_vcbench_split("norman_2019", "test", max_cells_per_pert=200, rng_seed=1)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, ds)
    print("S0_recorded =", cfg["meta"].get("delta_pearson"))
    print("S_eval delta_pearson =", rep.metrics.delta_pearson)
    print("cosine =", rep.metrics.cosine, "n =", rep.n_samples)


if __name__ == "__main__":
    main(sys.argv[1])
