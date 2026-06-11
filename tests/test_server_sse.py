from praxis2.server.sse import SSE_EVENT_TYPES, sse_event_stream, to_sse_message


def test_sse_event_types_cover_full_set():
    # §7.6.3 完整集(契约:不多不少,前端按此消费,不改前端)
    assert SSE_EVENT_TYPES == {
        "text_delta", "tool_start", "tool_end", "tool_progress",
        "stream_event", "phase_change", "compact_boundary",
        "control_request", "control_cancel_request", "auth_status",
        "final", "error", "queue_position",
    }


def test_to_sse_message_wire_format():
    # SSE 线格式:event: <type>\ndata: <json>\n\n(前端 EventSource 协议)
    msg = to_sse_message({"type": "text_delta", "text": "你好"}, event_id=7)
    assert msg.startswith("event: text_delta\n")
    assert 'data: {"type": "text_delta"' in msg or '"text": "你好"' in msg
    assert '"event_id": 7' in msg
    assert msg.endswith("\n\n")  # SSE 帧分隔


def test_kernel_text_event_maps_to_text_delta():
    # 内核 query() yield {"type":"text","text":...} → 前端 text_delta
    out = list(_drain(sse_event_stream(iter([
        {"type": "text", "text": "片段"},
    ]))))
    assert len(out) == 1
    assert "event: text_delta" in out[0]
    assert "片段" in out[0]


def test_kernel_tool_use_maps_to_tool_start():
    out = list(_drain(sse_event_stream(iter([
        {"type": "tool_use", "id": "tu1", "name": "echo", "input": {"t": 1}},
    ]))))
    assert "event: tool_start" in out[0]
    assert "tu1" in out[0] and "echo" in out[0]


def test_kernel_tool_result_maps_to_tool_end():
    out = list(_drain(sse_event_stream(iter([
        {"type": "tool_result", "tool_use_id": "tu1",
         "is_error": False, "content": "ok"},
    ]))))
    assert "event: tool_end" in out[0]
    assert "tu1" in out[0]


def test_kernel_end_maps_to_final():
    out = list(_drain(sse_event_stream(iter([
        {"type": "end", "reason": "stop"},
    ]))))
    assert "event: final" in out[0]
    assert "stop" in out[0]


def test_kernel_end_error_reason_maps_to_error_event():
    out = list(_drain(sse_event_stream(iter([
        {"type": "end", "reason": "error"},
    ]))))
    assert "event: error" in out[0]


def test_phase_change_and_compact_boundary_passthrough():
    # phase_change / compact_boundary 直通(已是前端协议名)
    out = list(_drain(sse_event_stream(iter([
        {"type": "phase_change", "to": "execute"},
        {"type": "compact_boundary", "tool_schema_synced": True},
    ]))))
    assert "event: phase_change" in out[0]
    assert "event: compact_boundary" in out[1]
    assert "tool_schema_synced" in out[1]  # compact 后同步 tool 声明(§7.6.3)


def test_unknown_kernel_event_falls_to_stream_event_not_dropped():
    # 未知内核事件不静默丢 → 包成 stream_event(可观测,前端容错)
    out = list(_drain(sse_event_stream(iter([
        {"type": "some_future_event", "x": 1},
    ]))))
    assert "event: stream_event" in out[0]


def _drain(gen):
    """sse_event_stream 是 generator;event_id 由其内部自增填充。"""
    return gen
