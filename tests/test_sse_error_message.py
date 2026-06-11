"""M10.1 hotfix: LLM error message 透传到 SSE 前端。

T13 user 报告:任何 LLM 异常都显示「内核不可恢复错误」,无法 debug。
Fix: end event 带 message 字段 → sse.py 透传给前端。"""

from __future__ import annotations


def test_kernel_end_error_with_message_forwards_to_sse():
    from praxis2.server.sse import _map_kernel_event

    ev = {"type": "end", "reason": "error", "message": "litellm 404 model_not_found"}
    out = _map_kernel_event(ev)
    assert out["type"] == "error"
    assert out["message"] == "litellm 404 model_not_found"


def test_kernel_end_error_without_message_falls_back():
    from praxis2.server.sse import _map_kernel_event

    ev = {"type": "end", "reason": "error"}
    out = _map_kernel_event(ev)
    assert out["message"] == "内核不可恢复错误"


def test_thinking_event_maps_to_thinking_delta():
    from praxis2.server.sse import _map_kernel_event

    ev = {"type": "thinking", "text": "let me think..."}
    out = _map_kernel_event(ev)
    assert out["type"] == "thinking_delta"
    assert out["text"] == "let me think..."


def test_thinking_event_with_empty_text():
    from praxis2.server.sse import _map_kernel_event

    out = _map_kernel_event({"type": "thinking"})
    assert out["type"] == "thinking_delta"
    assert out["text"] == ""
