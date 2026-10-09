"""Encode kernel events as server-sent events."""

import json
from collections.abc import Iterator

SSE_EVENT_TYPES = {
    "text_delta",
    "tool_start",
    "tool_end",
    "tool_progress",
    "stream_event",
    "phase_change",
    "compact_boundary",
    "control_request",
    "control_cancel_request",
    "auth_status",
    "final",
    "error",
    "queue_position",
}


def to_sse_message(payload: dict, *, event_id: int) -> str:

    body = {**payload, "event_id": event_id}
    return f"event: {payload['type']}\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"


def _map_kernel_event(ev: dict) -> dict:

    t = ev.get("type")
    if t == "text":
        return {"type": "text_delta", "text": ev.get("text", "")}
    if t == "tool_use":
        return {
            "type": "tool_start",
            "tool_use_id": ev.get("id"),
            "name": ev.get("name"),
            "input": ev.get("input", {}),
        }
    if t == "tool_result":
        return {
            "type": "tool_end",
            "tool_use_id": ev.get("tool_use_id"),
            "is_error": ev.get("is_error", False),
            "content": ev.get("content", ""),
        }
    if t == "thinking":
        return {"type": "thinking_delta", "text": ev.get("text", "")}
    if t == "end":
        if ev.get("reason") == "error":
            msg = ev.get("message") or "Unrecoverable kernel error"
            return {"type": "error", "reason": "error", "message": msg}
        return {"type": "final", "reason": ev.get("reason")}
    if t in SSE_EVENT_TYPES:
        return dict(ev)

    return {"type": "stream_event", "original": ev}


def sse_event_stream(kernel_events: Iterator[dict]) -> Iterator[str]:

    seq = 0
    for ev in kernel_events:
        seq += 1
        yield to_sse_message(_map_kernel_event(ev), event_id=seq)


def sse_frame(event: dict, *, event_id: int) -> str:

    return to_sse_message(_map_kernel_event(event), event_id=event_id)
