from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.llm,
    pytest.mark.remote,
]


@pytest.fixture
async def client():
    base = os.environ.get("PRAXIS_ANTHROPIC_BASE_URL", "")
    key = os.environ.get("PRAXIS_ANTHROPIC_API_KEY", "")
    if not (base and key):
        pytest.skip("PRAXIS_ANTHROPIC_BASE_URL + PRAXIS_ANTHROPIC_API_KEY required")
    from praxis2.llm.client import LLMClient

    c = LLMClient(api_key=key, base_url=base)
    yield c
    await c.aclose()


async def test_simple_text_streaming(client):
    events = []
    async for ev in client.stream_messages(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "Say exactly 'hello' and stop."}],
        max_tokens=20,
    ):
        events.append(ev)
    text_events = [e for e in events if e["type"] == "text"]
    stop_events = [e for e in events if e["type"] == "message_stop"]
    assert text_events, f"no text events, got: {[e['type'] for e in events]}"
    assert len(stop_events) == 1
    assert stop_events[0]["stop_reason"] in ("end_turn", "max_tokens")


async def test_tool_call_flow(client):

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]
    events = []
    async for ev in client.stream_messages(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "Use get_weather tool to check Tokyo weather."}],
        max_tokens=200,
        tools=tools,
    ):
        events.append(ev)
    tool_events = [e for e in events if e["type"] == "tool_use"]
    assert tool_events, f"expected tool_use, got: {[e['type'] for e in events]}"
    assert tool_events[0]["name"] == "get_weather"
    assert "city" in tool_events[0]["input"]
    stop_events = [e for e in events if e["type"] == "message_stop"]
    assert stop_events[0]["stop_reason"] in ("tool_use", "end_turn")


async def test_system_prompt_pass_through(client):

    events = []
    async for ev in client.stream_messages(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "Say only 'OK', nothing else."}],
        max_tokens=20,
        system="You are extremely terse. Always reply with one word.",
    ):
        events.append(ev)
    text = "".join(e["text"] for e in events if e["type"] == "text")

    assert len(text.strip()) <= 10 or "ok" in text.lower(), f"expected terse reply, got: {text!r}"


async def test_finish_reason_max_tokens(client):
    events = []
    async for ev in client.stream_messages(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "Write a long essay about cells, 500 words min."}],
        max_tokens=10,
    ):
        events.append(ev)
    stop = [e for e in events if e["type"] == "message_stop"][0]
    assert stop["stop_reason"] == "max_tokens"


async def test_invalid_model_raises_status_error(client):
    import httpx

    with pytest.raises((httpx.HTTPStatusError, RuntimeError)):
        async for _ in client.stream_messages(
            model="nonexistent-model-xyz-12345",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
        ):
            pass


async def test_assistant_with_tool_use_history_round_trip(client):

    messages = [
        {"role": "user", "content": "What's the weather in Tokyo?"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check."},
                {"type": "tool_use", "id": "T1", "name": "get_weather", "input": {"city": "Tokyo"}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "T1", "content": "Sunny, 25C"},
            ],
        },
    ]
    events = []
    async for ev in client.stream_messages(
        model="deepseek-v4-flash",
        messages=messages,
        max_tokens=50,
    ):
        events.append(ev)
    text = "".join(e["text"] for e in events if e["type"] == "text")

    assert text, f"expected follow-up reply, got: {[e['type'] for e in events]}"
