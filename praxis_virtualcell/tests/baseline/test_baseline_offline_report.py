"""Tests for baseline offline report."""
import hashlib
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
    assert rd["abstain"] is False, "human AHR gene→expression must produce a prediction rather than abstention"
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
        assert header in md, f"Report is missing section:  {header}"

    for n in range(1, 10):
        assert f"## {n}." in md, f"Report is missing section {n}"


def test_offline_report_bytes_match_frozen_p0_hashes():
    """Freeze structured numerical outputs and the English Markdown presentation."""
    req, out = _offline_result()
    structured = json.dumps(
        out["structured_report"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    markdown = render_report_md(
        {
            "report": out["structured_report"],
            "request": req,
            "provenance": out["provenance"],
            "mode": out["mode"],
            "llm_enabled": out["llm_enabled"],
        }
    ).encode("utf-8")

    assert hashlib.sha256(structured).hexdigest() == (
        "27a16eef2493bf953c4e572f3480d9c80e4013b5f92ebca4b8bfe0f59722228b"
    )
    assert hashlib.sha256(markdown).hexdigest() == (
        "4584316659f225cd48d74f61d11605f10a169e89cddba74db886b2a792d934d8"
    )
