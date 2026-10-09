"""Tests for ml donor bridge."""
import os

import pytest

pytestmark = pytest.mark.remote


def test_build_linear_from_ckpt_shapes():
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

    stem = os.environ["W4A_LINEAR_CKPT"]
    model, cfg = build_predictor_from_ckpt(stem)
    assert cfg["class_name"] == "LinearAdditivePredictor"
    assert model.pert_dim == cfg["kwargs"]["pert_dim"]
    assert model.n_genes == cfg["kwargs"]["n_genes"]


def test_load_norman_has_genes_and_pertdim():
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    ds = load_norman(split="test", max_perts=2)
    assert ds.n_genes > 0 and ds.pert_dim > 0
