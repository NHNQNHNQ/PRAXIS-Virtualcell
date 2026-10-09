"""Task 3:donor_bridge 远端测试(仅远端 virtualcell 环境;Mac 无 torch → remote skip)。"""
import os

import pytest

pytestmark = pytest.mark.remote


def test_build_linear_from_ckpt_shapes():
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

    stem = os.environ["W4A_LINEAR_CKPT"]  # 远端跑时由 env 给 ckpt stem
    model, cfg = build_predictor_from_ckpt(stem)
    assert cfg["class_name"] == "LinearAdditivePredictor"
    assert model.pert_dim == cfg["kwargs"]["pert_dim"]
    assert model.n_genes == cfg["kwargs"]["n_genes"]


def test_load_norman_has_genes_and_pertdim():
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    ds = load_norman(split="test", max_perts=2)  # 小采样:只验证维度属性
    assert ds.n_genes > 0 and ds.pert_dim > 0
