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
    assert out["message"] == "Unrecoverable kernel error"


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
