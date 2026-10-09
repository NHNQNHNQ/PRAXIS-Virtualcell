"""Tests for ml linear agent."""
import os

import pytest

pytestmark = pytest.mark.remote


def test_agent_prediction_equals_donor():
    import torch

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman
    from praxis_virtualcell.predictors.ml.linear_additive_agent import LinearAdditivePredictorAgent

    model, _ = build_predictor_from_ckpt(os.environ["W4A_LINEAR_CKPT"])
    ds = load_norman(split="test", max_perts=4, max_cells=8)


    item = next((ds[i] for i in range(len(ds)) if ds[i].kind in model.perturbation_kinds), None)
    assert item is not None, "At least one non-control sample is required"
    targets = tuple(item.perturbation.split("+"))

    from predictors.base import Context, Perturbation
    ctx = Context(control=item.control)
    pert = Perturbation(kind=item.kind, targets=targets, meta={"pert_emb": item.pert_emb})
    donor_mean = model.predict(ctx, pert).mean

    agent = LinearAdditivePredictorAgent(model)
    agent_mean = agent.predict_tensor(item.control, item.pert_emb, kind=item.kind, targets=targets)
    assert torch.allclose(agent_mean, donor_mean, atol=1e-6), (
        "Wrapped predictions must match the donor element by element"
    )
