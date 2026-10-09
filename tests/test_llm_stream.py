from __future__ import annotations

import httpx
import pytest
import respx

from praxis2.llm.client import LLMClient
from tests.cassette import load


@respx.mock
async def test_stream_yields_text_then_tooluse_then_stop():
    sse = load("openai_stream_text_tooluse.sse")
    respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=sse,
            headers={"content-type": "text/event-stream"},
        )
    )
    client = LLMClient(api_key="sk", base_url="https://up.example")
    events = [
        e
        async for e in client.stream_messages(
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=64,
        )
    ]
    texts = [e["text"] for e in events if e["type"] == "text"]
    tools = [e for e in events if e["type"] == "tool_use"]
    stops = [e for e in events if e["type"] == "message_stop"]
    assert "".join(texts) == "Hello"
    assert tools == [
        {
            "type": "tool_use",
            "id": "tu_1",
            "name": "search",
            "input": {"q": "x"},
        }
    ]
    assert stops and stops[0]["stop_reason"] == "tool_use"
    assert stops[0]["usage"]["completion_tokens"] == 7
    await client.aclose()


@respx.mock
async def test_stream_yields_thinking_event():
    sse = load("openai_stream_reasoning.sse")
    respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=sse,
            headers={"content-type": "text/event-stream"},
        )
    )
    client = LLMClient(api_key="sk", base_url="https://up.example")
    events = [
        e
        async for e in client.stream_messages(
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=64,
        )
    ]
    thinks = [e["text"] for e in events if e["type"] == "thinking"]
    texts = [e["text"] for e in events if e["type"] == "text"]
    assert "".join(thinks) == "Let me think about this... Step 1: parse."
    assert "".join(texts) == "Answer is 42"
    await client.aclose()


@respx.mock
async def test_stream_raises_on_http_error():

    err_body = '{"error":{"message":"Invalid model","code":"invalid_request_error"}}'
    respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(
            400,
            text=err_body,
            headers={"content-type": "application/json"},
        )
    )
    client = LLMClient(api_key="sk", base_url="https://up.example")
    with pytest.raises(httpx.HTTPStatusError):
        [
            e
            async for e in client.stream_messages(
                model="m",
                messages=[],
                max_tokens=1,
            )
        ]
    await client.aclose()
