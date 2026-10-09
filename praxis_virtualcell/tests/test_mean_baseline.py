"""S2(W8):mean-perturbation naive baseline 同协议得分。仅远端(需 torch + donor)。

Mac 无 torch → remote 标记自动 skip。远端实测 delta_pearson=0.4615(见 mean_baseline 模块 docstring)。
"""
import pytest

pytestmark = pytest.mark.remote


def test_mean_baseline_sane_range():
    from praxis_virtualcell.benchmarks.mean_baseline import score_mean_baseline

    s = score_mean_baseline()
    assert s["n"] > 0 and s["n_train"] > 0
    # naive baseline 应明显低于训练 base(最强 cpa 0.6716),且 > 0(norman 扰动有共享方向)
    assert 0.2 < s["delta_pearson"] < 0.60, s
