"""Phase 0 基线特征化:pin v0.8 离线行为,升级过程若改变则红灯。
只读断言现有行为;若与期望不符=升级引入的真实回归,停下排查,不改此测试迁就。"""
import json
from pathlib import Path

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.io.report_markdown import render_report_md
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_EXAMPLE = Path(__file__).resolve().parents[3] / "examples" / "ahr_k562.json"


def _offline_result():
    req = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    return req, run_query(req, config=RuntimeConfig(mode=Mode.OFFLINE))


def test_offline_run_is_zero_llm():
    _, out = _offline_result()
    assert out["mode"] == "offline"
    assert out["llm_enabled"] is False
    assert out["llm_used_for_prediction"] is False


def test_offline_ahr_accepts_and_reports_reliability():
    _, out = _offline_result()
    rd = out["reliability_decision"]
    assert rd["abstain"] is False, "human AHR gene→expression 应可预测,非弃权"
    assert rd["reliability"] in {"high", "medium", "low"}


def test_offline_report_md_has_nine_sections():
    req, out = _offline_result()
    job_like = {
        "report": out["structured_report"],
        "request": req,
        "provenance": out["provenance"],
        "mode": out["mode"],
        "llm_enabled": out["llm_enabled"],
    }
    md = render_report_md(job_like)
    for header in ("# PRAXIS-VirtualCell Report", "## 1. Question", "## 2. Cell Context"):
        assert header in md, f"报告缺段落: {header}"
    # 9 段:段落编号 1..9 全在
    for n in range(1, 10):
        assert f"## {n}." in md, f"报告缺第 {n} 段"
