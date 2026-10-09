import os

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime


@pytest.mark.llm
def test_free_text_end_to_end_with_real_deepseek():
    load_env()
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key=os.environ["DEEPSEEK_API_KEY"])
    rt = build_runtime(cfg)
    report = rt.run_workflow_from_text("在 K562 细胞里敲除 AHR 基因,预测单细胞转录组变化")
    assert report.get("narrative")  # 有 LLM 中文叙述
    assert "MockCPA" in report["models_used"]  # AHR 已知 → 预测成功
    assert report["abstain"] is False
    types = [m.message_type for m in rt.bus.trace]
    assert "request_parsed" in types and "llm_narrative" in types
