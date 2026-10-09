"""Tests for mean baseline."""
import pytest

pytestmark = pytest.mark.remote


def test_mean_baseline_sane_range():
    from praxis_virtualcell.benchmarks.mean_baseline import score_mean_baseline

    s = score_mean_baseline()
    assert s["n"] > 0 and s["n_train"] > 0

    assert 0.2 < s["delta_pearson"] < 0.60, s
