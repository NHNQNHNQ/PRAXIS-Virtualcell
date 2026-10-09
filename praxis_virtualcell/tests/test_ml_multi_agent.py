"""Tests for ml multi agent."""
import os

import pytest

pytestmark = pytest.mark.remote

PREDICTORS = ["linear_additive", "latent_additive", "cpa_style", "gnn_pert",
              "decoder_only", "pretrained_backbone"]


@pytest.mark.parametrize("name", PREDICTORS)
def test_agent_prediction_equals_donor(name):
    import torch

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman
    from praxis_virtualcell.predictors.ml.ml_predictor_agent import MLPredictorAgent

    stem = os.path.join(os.environ["W4B_CKPT_DIR"], name)
    model, _ = build_predictor_from_ckpt(stem)
    ds = load_norman(split="test", max_perts=4, max_cells=8)


    item = next((ds[i] for i in range(len(ds)) if ds[i].kind in model.perturbation_kinds), None)
    assert item is not None, f"{name}: At least one non-control sample is required"
    targets = tuple(item.perturbation.split("+"))

    from predictors.base import Context, Perturbation
    ctx = Context(control=item.control)
    pert = Perturbation(kind=item.kind, targets=targets, meta={"pert_emb": item.pert_emb})
    donor_mean = model.predict(ctx, pert).mean

    agent_mean = MLPredictorAgent(model).predict_tensor(
        item.control, item.pert_emb, kind=item.kind, targets=targets)
    assert torch.allclose(agent_mean, donor_mean, atol=1e-6), name
