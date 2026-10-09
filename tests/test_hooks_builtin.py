from praxis2.core.state import State
from praxis2.hooks.builtin import (
    StopDecision,
    anti_retrieval_threshold,
    doi_required,
    evidence_chain_required,
    make_rmcp_stop_gate,
)


class _T:
    name = "write_case"


def _ok(content):
    return {"type": "tool_result", "tool_use_id": "tu1", "is_error": False, "content": content}


def test_doi_required_vetoes_when_no_doi():
    out = doi_required(_T(), {"id": "tu1"}, _ok("\u6848\u4f8b\u6b63\u6587,\u65e0 DOI"), State())
    assert out is not None and out["is_error"] is True
    assert out["tool_use_id"] == "tu1"
    assert "DOI" in out["content"] and "Required condition" in out["content"]


def test_doi_required_passes_when_doi_present():
    out = doi_required(_T(), {"id": "tu1"}, _ok("\u6848\u4f8b doi:10.1000/xyz123 \u5df2\u5f15"), State())
    assert out is None


def test_doi_required_ignores_already_error_result():
    err = {
        "type": "tool_result",
        "tool_use_id": "tu1",
        "is_error": True,
        "content": "\u5de5\u5177\u672c\u5c31\u5931\u8d25",
    }
    assert doi_required(_T(), {"id": "tu1"}, err, State()) is None


def test_evidence_chain_required_vetoes_when_field_missing():
    out = evidence_chain_required(_T(), {"id": "tu1"}, _ok("\u4ea7\u51fa,\u4f46\u65e0 evidence \u5b57\u6bb5"), State())
    assert out is not None and out["is_error"] is True
    assert "evidence field" in out["content"] and "Required condition" in out["content"]


def test_evidence_chain_required_passes_when_evidence_present():
    out = evidence_chain_required(_T(), {"id": "tu1"}, _ok('\u7ed3\u679c evidence: ["case:42"] \u5df2\u9644'), State())
    assert out is None


def test_anti_retrieval_threshold_vetoes_below_ratio():
    bad = _ok("\u53cd\u5411\u7528\u4f8b passed=1 total=4")
    out = anti_retrieval_threshold(_T(), {"id": "tu1"}, bad, State())
    assert out is not None and out["is_error"] is True
    assert "Reverse filtering" in out["content"] and "Required condition" in out["content"]


def test_anti_retrieval_threshold_passes_at_or_above_ratio():
    good = _ok("\u53cd\u5411\u7528\u4f8b passed=4 total=4")
    assert anti_retrieval_threshold(_T(), {"id": "tu1"}, good, State()) is None


def test_stop_gate_vetoes_when_evidence_or_antifilter_incomplete():
    gate = make_rmcp_stop_gate()
    st = State()
    dec = gate(st)
    assert dec.veto is True
    assert "Evidence chain" in dec.message or "Reverse filtering" in dec.message
    assert "Required condition" in dec.message


def test_stop_gate_passes_when_both_ok():
    gate = make_rmcp_stop_gate()
    st = State()
    st.tool_use_context["evidence_ok"] = True
    st.tool_use_context["anti_filter_ok"] = True
    dec = gate(st)
    assert isinstance(dec, StopDecision)
    assert dec.veto is False
