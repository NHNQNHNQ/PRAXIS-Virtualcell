"""Tests for abstain gain."""
import pytest

pytestmark = pytest.mark.remote


def test_risk_coverage_positive():
    from praxis_virtualcell.benchmarks.abstain_gain import risk_coverage

    r = risk_coverage(taus=[1.0, 0.3])
    rows = r["rows"]
    assert rows[0]["coverage"] == pytest.approx(1.0, abs=1e-6)
    assert rows[-1]["coverage"] < 1.0

    assert rows[-1]["dp_keep"] > r["reference_full_coverage"] + 0.01, r
