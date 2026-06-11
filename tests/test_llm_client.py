"""M10.5:LLMClient OpenAI /v1/chat/completions 路径测试。"""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from praxis2.llm.client import LLMClient


@respx.mock
async def test_messages_non_streaming_returns_dict():
    """非流式 messages() 返 OpenAI completion dict。"""
    fake_resp = {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Hi there"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
    }
    respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=fake_resp)
    )
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
    """litellm 400 → httpx.HTTPStatusError 冒泡。"""
    err_body = {"error": {"message": "Invalid model name", "code": "invalid_request_error"}}
    respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(400, json=err_body)
    )
    client = LLMClient(api_key="bad", base_url="https://up.example")
    with pytest.raises(httpx.HTTPStatusError):
        await client.messages(
            model="foo",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=1,
        )
    await client.aclose()


def test_backward_alias_anthropic_client():
    """server/app.py + 老测试仍 import AnthropicClient,必须 alias 不破。"""
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
    """混合 text + tool_use → 单 assistant message 含 tool_calls。"""
    from praxis2.llm.client import _translate_messages_anthropic_to_openai
    out = _translate_messages_anthropic_to_openai(
        messages=[
            {"role": "user", "content": "search x"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Let me search."},
                {"type": "tool_use", "id": "T1", "name": "search",
                 "input": {"q": "x"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "T1",
                 "content": "found"},
            ]},
        ],
        system=None,
    )
    # 第 2 条 = assistant with content + tool_calls
    assistant = out[1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "Let me search."
    assert assistant["tool_calls"][0]["id"] == "T1"
    assert assistant["tool_calls"][0]["function"]["name"] == "search"
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {"q": "x"}
    # 第 3 条 = role=tool 单条
    assert out[2] == {"role": "tool", "tool_call_id": "T1", "content": "found"}


def test_translate_messages_tool_result_list_content():
    """tool_result.content 是 list of blocks → join text。"""
    from praxis2.llm.client import _translate_messages_anthropic_to_openai
    out = _translate_messages_anthropic_to_openai(
        messages=[{"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "T2",
             "content": [{"type": "text", "text": "part1"},
                          {"type": "text", "text": "part2"}]},
        ]}],
        system=None,
    )
    assert out == [{"role": "tool", "tool_call_id": "T2", "content": "part1part2"}]
