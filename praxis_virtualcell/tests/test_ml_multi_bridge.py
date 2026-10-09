"""Tests for ml multi bridge."""
import os

import pytest

pytestmark = pytest.mark.remote

PREDICTORS = ["linear_additive", "latent_additive", "cpa_style", "gnn_pert",
              "decoder_only", "pretrained_backbone"]


@pytest.mark.parametrize("name", PREDICTORS)
def test_build_predictor_shapes(name):
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

    stem = os.path.join(os.environ["W4B_CKPT_DIR"], name)
    model, cfg = build_predictor_from_ckpt(stem)
    assert model.pert_dim == cfg["kwargs"]["pert_dim"]
    assert model.n_genes == cfg["kwargs"]["n_genes"]
