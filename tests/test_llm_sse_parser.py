"""M10.5:parse_stream_response 单元测(纯函数,不经 client)。"""
from __future__ import annotations

import httpx

from praxis2.llm.sse import parse_stream_response
from tests.cassette import load


def _fake_response(text: str) -> httpx.Response:
    return httpx.Response(
        200, text=text, headers={"content-type": "text/event-stream"},
    )


async def test_parse_text_then_tooluse_then_stop():
    sse = load("openai_stream_text_tooluse.sse")
    resp = _fake_response(sse)
    events = [e async for e in parse_stream_response(resp)]
    texts = [e["text"] for e in events if e["type"] == "text"]
    tools = [e for e in events if e["type"] == "tool_use"]
    stops = [e for e in events if e["type"] == "message_stop"]
    assert "".join(texts) == "Hello"
    assert tools == [{
        "type": "tool_use", "id": "tu_1", "name": "search",
        "input": {"q": "x"},
    }]
    assert len(stops) == 1
    assert stops[0]["stop_reason"] == "tool_use"
    assert stops[0]["usage"]["completion_tokens"] == 7


async def test_parse_reasoning_yields_thinking_event():
    sse = load("openai_stream_reasoning.sse")
    resp = _fake_response(sse)
    events = [e async for e in parse_stream_response(resp)]
    thinks = [e["text"] for e in events if e["type"] == "thinking"]
    texts = [e["text"] for e in events if e["type"] == "text"]
    assert "".join(thinks) == "Let me think about this... Step 1: parse."
    assert "".join(texts) == "Answer is 42"
