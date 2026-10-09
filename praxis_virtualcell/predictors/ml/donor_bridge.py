"""rich↔torch 适配基础:复用 donor 代码(sys.path 注入)加载 predictor + Norman。

仅远端 `virtualcell` 环境 import(import torch + donor)。Mac 不 import(测试标 remote → skip)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

_CLASSES: dict[str, Any] = {}


def _cls(name: str):
    """按 ckpt json 的 class_name 查 donor predictor 类(全 CamelCase)。"""
    if not _CLASSES:
        from predictors.cpa_style import CPAStylePredictor
        from predictors.decoder_only import DecoderOnlyPredictor
        from predictors.gnn_pert import GNNPertPredictor
        from predictors.latent_additive import LatentAdditivePredictor
        from predictors.linear_additive import LinearAdditivePredictor
        from predictors.pretrained_backbone import PretrainedBackbonePredictor

        for c in (LinearAdditivePredictor, LatentAdditivePredictor, CPAStylePredictor,
                  GNNPertPredictor, DecoderOnlyPredictor, PretrainedBackbonePredictor):
            _CLASSES[c.__name__] = c
    return _CLASSES[name]


def build_predictor_from_ckpt(ckpt_stem: str):
    """ckpt_stem = .../norman_2019/linear_additive(无扩展)。读 .json 重建 + load .pt bundle。返回 (model, cfg)。"""
    cfg = json.loads(Path(ckpt_stem + ".json").read_text(encoding="utf-8"))
    model = _cls(cfg["class_name"])(**cfg["kwargs"])
    # donor .pt 是 bundle dict(含 state_dict);torch>=2.6 须 weights_only=False
    bundle = torch.load(ckpt_stem + ".pt", map_location="cpu", weights_only=False)
    state = bundle["state_dict"] if isinstance(bundle, dict) and "state_dict" in bundle else bundle
    model.load_state_dict(state)
    model.eval()
    return model, cfg


def load_norman(split: str = "test", *, max_perts: int | None = None,
                max_cells: int | None = 200, seed: int = 1):
    """加载 Norman split。默认 max_cells=200, seed=1 复现训练时 test 采样(见 finding_w4a_env.md)。"""
    from bench.vcbench.loader import load_vcbench_split

    kw: dict[str, Any] = {"rng_seed": seed}
    if max_perts is not None:
        kw["max_perts"] = max_perts
    if max_cells is not None:
        kw["max_cells_per_pert"] = max_cells
    return load_vcbench_split("norman_2019", split, **kw)
