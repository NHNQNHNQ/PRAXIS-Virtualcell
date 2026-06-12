"""Task 5:praxis 复用 EvalAgent 复现 Norman 分数 == anchor。仅远端(Mac remote skip)。"""
import os

import pytest

pytestmark = pytest.mark.remote


def test_praxis_linear_norman_matches_donor():
    from praxis_virtualcell.benchmarks.norman_eval import score_linear_ckpt

    stem = os.environ["W4A_LINEAR_CKPT"]
    s_praxis = score_linear_ckpt(stem, split="test")
    s_anchor = float(os.environ["W4A_ANCHOR"])  # Task 2 记录的 S_anchor
    # 同 ckpt+loader+EvalAgent → 应逐位一致(浮点容差)
    assert abs(s_praxis["delta_pearson"] - s_anchor) < 1e-4, (s_praxis, s_anchor)
    assert s_praxis["n"] > 0
