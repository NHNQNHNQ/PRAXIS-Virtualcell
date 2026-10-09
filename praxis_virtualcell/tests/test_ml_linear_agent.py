"""Task 4:praxis 包装预测 == donor 原预测(逐元素)。仅远端 virtualcell 环境(Mac remote skip)。"""
import os

import pytest

pytestmark = pytest.mark.remote


def test_agent_prediction_equals_donor():
    import torch

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman
    from praxis_virtualcell.predictors.ml.linear_additive_agent import LinearAdditivePredictorAgent

    model, _ = build_predictor_from_ckpt(os.environ["W4A_LINEAR_CKPT"])
    ds = load_norman(split="test", max_perts=4, max_cells=8)

    # ds[i] 返回 PerturbationSample(属性访问);选第一个 linear 支持的非 control 样本
    item = next((ds[i] for i in range(len(ds)) if ds[i].kind in model.perturbation_kinds), None)
    assert item is not None, "需要至少一个 non-control 样本"
    targets = tuple(item.perturbation.split("+"))

    from predictors.base import Context, Perturbation
    ctx = Context(control=item.control)
    pert = Perturbation(kind=item.kind, targets=targets, meta={"pert_emb": item.pert_emb})
    donor_mean = model.predict(ctx, pert).mean

    agent = LinearAdditivePredictorAgent(model)
    agent_mean = agent.predict_tensor(item.control, item.pert_emb, kind=item.kind, targets=targets)
    assert torch.allclose(agent_mean, donor_mean, atol=1e-6), "包装后预测应与 donor 逐元素一致"
