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
    return {"type": "tool_result", "tool_use_id": "tu1", "is_error": False,
            "content": content}


def test_doi_required_vetoes_when_no_doi():
    out = doi_required(_T(), {"id": "tu1"}, _ok("案例正文,无 DOI"), State())
    assert out is not None and out["is_error"] is True
    assert out["tool_use_id"] == "tu1"
    assert "DOI" in out["content"] and "满足条件" in out["content"]  # 可执行满足条件


def test_doi_required_passes_when_doi_present():
    out = doi_required(
        _T(), {"id": "tu1"}, _ok("案例 doi:10.1000/xyz123 已引"), State()
    )
    assert out is None  # 不替换 → 放行


def test_doi_required_ignores_already_error_result():
    err = {"type": "tool_result", "tool_use_id": "tu1", "is_error": True,
           "content": "工具本就失败"}
    assert doi_required(_T(), {"id": "tu1"}, err, State()) is None  # 不二次否决


def test_evidence_chain_required_vetoes_when_field_missing():
    out = evidence_chain_required(
        _T(), {"id": "tu1"}, _ok("产出,但无 evidence 字段"), State()
    )
    assert out is not None and out["is_error"] is True
    assert "证据链" in out["content"] and "满足条件" in out["content"]


def test_evidence_chain_required_passes_when_evidence_present():
    out = evidence_chain_required(
        _T(), {"id": "tu1"}, _ok('结果 evidence: ["case:42"] 已附'), State()
    )
    assert out is None


def test_anti_retrieval_threshold_vetoes_below_ratio():
    bad = _ok("反向用例 passed=1 total=4")  # 25% < 默认 0.8
    out = anti_retrieval_threshold(_T(), {"id": "tu1"}, bad, State())
    assert out is not None and out["is_error"] is True
    assert "反向过滤" in out["content"] and "满足条件" in out["content"]


def test_anti_retrieval_threshold_passes_at_or_above_ratio():
    good = _ok("反向用例 passed=4 total=4")
    assert anti_retrieval_threshold(_T(), {"id": "tu1"}, good, State()) is None


def test_stop_gate_vetoes_when_evidence_or_antifilter_incomplete():
    gate = make_rmcp_stop_gate()
    st = State()  # 无 evidence_ok / anti_filter_ok
    dec = gate(st)
    assert dec.veto is True
    assert "证据链" in dec.message or "反向过滤" in dec.message
    assert "满足条件" in dec.message


def test_stop_gate_passes_when_both_ok():
    gate = make_rmcp_stop_gate()
    st = State()
    st.tool_use_context["evidence_ok"] = True
    st.tool_use_context["anti_filter_ok"] = True
    dec = gate(st)
    assert isinstance(dec, StopDecision)
    assert dec.veto is False
