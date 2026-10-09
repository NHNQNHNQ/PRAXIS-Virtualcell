"""Tests for ml norman score."""
import os

import pytest

pytestmark = pytest.mark.remote


def test_praxis_linear_norman_matches_donor():
    from praxis_virtualcell.benchmarks.norman_eval import score_linear_ckpt

    stem = os.environ["W4A_LINEAR_CKPT"]
    s_praxis = score_linear_ckpt(stem, split="test")
    s_anchor = float(os.environ["W4A_ANCHOR"])

    assert abs(s_praxis["delta_pearson"] - s_anchor) < 1e-4, (s_praxis, s_anchor)
    assert s_praxis["n"] > 0
