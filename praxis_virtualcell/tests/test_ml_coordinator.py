"""Task 3(W4b):praxis 复用 donor Coordinator 在 Norman 跑通 + 分数合理。仅远端。

断言阈值据 Task3 实测(_anchor_coordinator)固化;此处用基本合理性下界。
"""
import os

import pytest

pytestmark = pytest.mark.remote


def test_coordinator_latent_gnn_runs():
    from praxis_virtualcell.benchmarks.coordinator_eval import score_coordinator

    s = score_coordinator(os.environ["W4B_CKPT_DIR"], ["latent_additive", "gnn_pert"])
    assert s["n"] > 0
    # ensemble 应 ≥ 合理下界(组合内单 base 在 0.64~0.67;ensemble 不应崩到 0.6 以下)
    assert s["delta_pearson"] > 0.6, s


def test_coordinator_strong_combo_reaches_070():
    from praxis_virtualcell.benchmarks.coordinator_eval import score_coordinator

    # 强组合复现 ~0.70(实测 cpa+decoder+gnn=0.7020, all-5=0.7039)
    s = score_coordinator(os.environ["W4B_CKPT_DIR"], ["cpa_style", "decoder_only", "gnn_pert"])
    assert s["delta_pearson"] > 0.70, s
