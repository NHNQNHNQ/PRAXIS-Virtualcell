from __future__ import annotations

import json

import httpx
import pytest
import respx

from praxis2.llm.client import LLMClient


@respx.mock
async def test_messages_non_streaming_returns_dict():

    fake_resp = {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi there"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
    }
    respx.post("https://up.example/v1/chat/completions").mock(return_value=httpx.Response(200, json=fake_resp))
    client = LLMClient(api_key="sk-x", base_url="https://up.example")
    out = await client.messages(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
    )
    assert out["choices"][0]["message"]["content"] == "Hi there"
    await client.aclose()


@respx.mock
async def test_http_400_raises_status_error():

    err_body = {"error": {"message": "Invalid model name", "code": "invalid_request_error"}}
    respx.post("https://up.example/v1/chat/completions").mock(return_value=httpx.Response(400, json=err_body))
    client = LLMClient(api_key="bad", base_url="https://up.example")
    with pytest.raises(httpx.HTTPStatusError):
        await client.messages(
            model="foo",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=1,
        )
    await client.aclose()


def test_backward_alias_anthropic_client():

    from praxis2.llm.client import AnthropicClient, LLMClient

    assert AnthropicClient is LLMClient


def test_translate_messages_simple_user():
    from praxis2.llm.client import _translate_messages_anthropic_to_openai

    out = _translate_messages_anthropic_to_openai(
        messages=[{"role": "user", "content": "hello"}],
        system="be terse",
    )
    assert out == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hello"},
    ]


def test_translate_messages_assistant_with_tool_use():

    from praxis2.llm.client import _translate_messages_anthropic_to_openai

    out = _translate_messages_anthropic_to_openai(
        messages=[
            {"role": "user", "content": "search x"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me search."},
                    {"type": "tool_use", "id": "T1", "name": "search", "input": {"q": "x"}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "T1", "content": "found"},
                ],
            },
        ],
        system=None,
    )

    assistant = out[1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "Let me search."
    assert assistant["tool_calls"][0]["id"] == "T1"
    assert assistant["tool_calls"][0]["function"]["name"] == "search"
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {"q": "x"}

    assert out[2] == {"role": "tool", "tool_call_id": "T1", "content": "found"}


def test_translate_messages_tool_result_list_content():

    from praxis2.llm.client import _translate_messages_anthropic_to_openai

    out = _translate_messages_anthropic_to_openai(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "T2",
                        "content": [{"type": "text", "text": "part1"}, {"type": "text", "text": "part2"}],
                    },
                ],
            }
        ],
        system=None,
    )
    assert out == [{"role": "tool", "tool_call_id": "T2", "content": "part1part2"}]
