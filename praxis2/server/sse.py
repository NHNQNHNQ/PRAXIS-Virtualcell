"""§7.6.3 内核事件 dict → SSE text/event-stream 完整消息集映射。

M1 query() yield 内核事件({"type":"text"|"tool_use"|"tool_result"|"end"
|"phase_change"|"compact_boundary"|...}),本模块映射为前端 SSE 协议。
**前端原样接入**:消息集 shape 由契约测试锁死(§5⑥),契约测试只断言
形状不实现/不改前端(§6.6 前端已设计后端适配)。未知内核事件不静默丢
→ 包 stream_event(前端容错 + 可观测)。断线重连 event_id 防乱序(§11.4)。"""

import json
from collections.abc import Iterator

# §7.6.3 完整集(契约:前端按此消费,不改前端;queue_position 为
# §11.2 背压排队位次,与 error 配套)
SSE_EVENT_TYPES = {
    "text_delta", "tool_start", "tool_end", "tool_progress",
    "stream_event", "phase_change", "compact_boundary",
    "control_request", "control_cancel_request", "auth_status",
    "final", "error", "queue_position",
}


def to_sse_message(payload: dict, *, event_id: int) -> str:
    """SSE 线格式:event: <type>\\ndata: <json>\\n\\n。event_id 注入
    data(断线重连续传依据,§11.4 防乱序)。"""
    body = {**payload, "event_id": event_id}
    return (
        f"event: {payload['type']}\n"
        f"data: {json.dumps(body, ensure_ascii=False)}\n\n"
    )


def _map_kernel_event(ev: dict) -> dict:
    """内核事件 → 前端 SSE 协议名(§7.6.3)。已是前端协议名的直通。"""
    t = ev.get("type")
    if t == "text":
        return {"type": "text_delta", "text": ev.get("text", "")}
    if t == "tool_use":
        return {
            "type": "tool_start", "tool_use_id": ev.get("id"),
            "name": ev.get("name"), "input": ev.get("input", {}),
        }
    if t == "tool_result":
        return {
            "type": "tool_end", "tool_use_id": ev.get("tool_use_id"),
            "is_error": ev.get("is_error", False),
            "content": ev.get("content", ""),
        }
    if t == "thinking":
        # M10.5:LLM reasoning_content / chain-of-thought 流式增量
        # FE 暂不渲染独立 UI,走 stream_event 兜底分支不挂(v0.12 加 thinking UI)
        return {"type": "thinking_delta", "text": ev.get("text", "")}
    if t == "end":
        # 内核终止原因 error → 前端 error 事件;其余 → final
        if ev.get("reason") == "error":
            msg = ev.get("message") or "内核不可恢复错误"
            return {"type": "error", "reason": "error", "message": msg}
        return {"type": "final", "reason": ev.get("reason")}
    if t in SSE_EVENT_TYPES:
        return dict(ev)  # 已是前端协议名(phase_change/compact_boundary/...)
    # 未知内核事件不静默丢(前端容错 + 可观测,§12)
    return {"type": "stream_event", "original": ev}


def sse_event_stream(kernel_events: Iterator[dict]) -> Iterator[str]:
    """把内核事件迭代器转成 SSE 线格式串流(event_id 自增,§11.4)。

    legacy buffered 接口,保留给同步聚合场景(契约测试 / 离线导出)。B.1 之后
    `_chat_stream` 走 `sse_frame` 真流式,不再经此函数。"""
    seq = 0
    for ev in kernel_events:
        seq += 1
        yield to_sse_message(_map_kernel_event(ev), event_id=seq)


def sse_frame(event: dict, *, event_id: int) -> str:
    """B.1:单事件 SSE 帧(§11.4 event_id 由调用方维护跨调用单调)。

    真流式 `_chat_stream` 用此函数 — 每收到一个 kernel ev 就立即出帧,不再先 drain
    再 fan-out(对治 reviewer M6 C1:首字节延迟 = 总耗时 → AI 卡死)。
    """
    return to_sse_message(_map_kernel_event(event), event_id=event_id)
