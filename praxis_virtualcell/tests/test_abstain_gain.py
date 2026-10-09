"""S4(W8):abstain_gain / risk-coverage 正向。仅远端(需 torch + donor + GPU)。

Mac 无 torch → remote 标记自动 skip。远端实测:弃权高分歧扰动后保留集 ΔPearson 单调上升
(coverage 0.74 → dp 0.7536,+0.082 vs 满覆盖 0.6716,见 abstain_gain 模块 docstring + manifest)。
"""
import pytest

pytestmark = pytest.mark.remote


def test_risk_coverage_positive():
    from praxis_virtualcell.benchmarks.abstain_gain import risk_coverage

    r = risk_coverage(taus=[1.0, 0.3])  # 满覆盖参考 + 一档强弃权
    rows = r["rows"]
    assert rows[0]["coverage"] == pytest.approx(1.0, abs=1e-6)
    assert rows[-1]["coverage"] < 1.0  # 确有弃权
    # 弃权后保留集 ΔPearson 应明显高于满覆盖参考(观测 +0.036~0.084;留 GPU 抖动余量)
    assert rows[-1]["dp_keep"] > r["reference_full_coverage"] + 0.01, r
