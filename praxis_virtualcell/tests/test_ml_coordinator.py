"""Tests for ml coordinator."""
import os

import pytest

pytestmark = pytest.mark.remote


def test_coordinator_latent_gnn_runs():
    from praxis_virtualcell.benchmarks.coordinator_eval import score_coordinator

    s = score_coordinator(os.environ["W4B_CKPT_DIR"], ["latent_additive", "gnn_pert"])
    assert s["n"] > 0

    assert s["delta_pearson"] > 0.6, s


def test_coordinator_strong_combo_reaches_070():
    from praxis_virtualcell.benchmarks.coordinator_eval import score_coordinator


    s = score_coordinator(os.environ["W4B_CKPT_DIR"], ["cpa_style", "decoder_only", "gnn_pert"])
    assert s["delta_pearson"] > 0.70, s
