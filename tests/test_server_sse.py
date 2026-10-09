from praxis2.server.sse import SSE_EVENT_TYPES, sse_event_stream, to_sse_message


def test_sse_event_types_cover_full_set():

    assert SSE_EVENT_TYPES == {
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


def test_to_sse_message_wire_format():

    msg = to_sse_message({"type": "text_delta", "text": "\u4f60\u597d"}, event_id=7)
    assert msg.startswith("event: text_delta\n")
    assert 'data: {"type": "text_delta"' in msg or '"text": "\u4f60\u597d"' in msg
    assert '"event_id": 7' in msg
    assert msg.endswith("\n\n")


def test_kernel_text_event_maps_to_text_delta():

    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "text", "text": "\u7247\u6bb5"},
                    ]
                )
            )
        )
    )
    assert len(out) == 1
    assert "event: text_delta" in out[0]
    assert "\u7247\u6bb5" in out[0]


def test_kernel_tool_use_maps_to_tool_start():
    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "tool_use", "id": "tu1", "name": "echo", "input": {"t": 1}},
                    ]
                )
            )
        )
    )
    assert "event: tool_start" in out[0]
    assert "tu1" in out[0] and "echo" in out[0]


def test_kernel_tool_result_maps_to_tool_end():
    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "tool_result", "tool_use_id": "tu1", "is_error": False, "content": "ok"},
                    ]
                )
            )
        )
    )
    assert "event: tool_end" in out[0]
    assert "tu1" in out[0]


def test_kernel_end_maps_to_final():
    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "end", "reason": "stop"},
                    ]
                )
            )
        )
    )
    assert "event: final" in out[0]
    assert "stop" in out[0]


def test_kernel_end_error_reason_maps_to_error_event():
    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "end", "reason": "error"},
                    ]
                )
            )
        )
    )
    assert "event: error" in out[0]


def test_phase_change_and_compact_boundary_passthrough():

    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "phase_change", "to": "execute"},
                        {"type": "compact_boundary", "tool_schema_synced": True},
                    ]
                )
            )
        )
    )
    assert "event: phase_change" in out[0]
    assert "event: compact_boundary" in out[1]
    assert "tool_schema_synced" in out[1]


def test_unknown_kernel_event_falls_to_stream_event_not_dropped():

    out = list(
        _drain(
            sse_event_stream(
                iter(
                    [
                        {"type": "some_future_event", "x": 1},
                    ]
                )
            )
        )
    )
    assert "event: stream_event" in out[0]


def _drain(gen):

    return gen
