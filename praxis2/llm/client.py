# praxis2/llm/client.py
"""OpenAI-compatible Chat Completions 客户端。

支持 DeepSeek 官方地址或已配置网关，并保留原框架 Anthropic 消息块兼容。
历史别名 ``AnthropicClient = LLMClient`` 供原调用方继续使用。
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from praxis2.llm.sse import parse_stream_response


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_s: float = 60.0,
    ) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
        }
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_s,
        )

    async def messages(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        system: str | list[dict] | None = None,
        tools: list[dict[str, Any]] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        """非流式 — query.py 不调,留作工具/调试。"""
        payload = self._build_payload(
            model=model, messages=messages, max_tokens=max_tokens,
            system=system, tools=tools, stream=False,
            thinking=thinking, reasoning_effort=reasoning_effort,
        )
        resp = await self._http.post(
            "/v1/chat/completions", headers=self._headers, json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def stream_messages(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        system: str | list[dict] | None = None,
        tools: list[dict[str, Any]] | None = None,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ):
        """流式 — query.py 调。yields 4 类规范事件。"""
        payload = self._build_payload(
            model=model, messages=messages, max_tokens=max_tokens,
            system=system, tools=tools, stream=True,
            thinking=thinking, reasoning_effort=reasoning_effort,
        )
        payload["stream_options"] = {"include_usage": True}
        async with self._http.stream(
            "POST", "/v1/chat/completions",
            headers=self._headers, json=payload,
        ) as resp:
            # M10.5.1 fix:streaming response 上直接 raise_for_status 会
            # 让 HTTPStatusError 包住未读 body 的 response,上游 repr(exc)
            # 触发 ResponseNotRead。先 aread body 再判错,exception
            # message 直接含 body 关键信息。
            if resp.status_code >= 400:
                await resp.aread()
                body_preview = resp.text[:500] if resp.text else ""
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code} from /v1/chat/completions: "
                    f"{body_preview}",
                    request=resp.request,
                    response=resp,
                )
            async for ev in parse_stream_response(resp):
                yield ev

    def _build_payload(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        system: str | list[dict] | None,
        tools: list[dict[str, Any]] | None,
        stream: bool,
        thinking: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        openai_messages = _translate_messages_anthropic_to_openai(messages, system)
        payload: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        if stream:
            payload["stream"] = True
        if tools:
            payload["tools"] = tools
        if thinking is not None:
            payload["thinking"] = thinking
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        return payload

    async def aclose(self) -> None:
        await self._http.aclose()


# Backward alias(server/app.py + 老测试仍 import 老名)
AnthropicClient = LLMClient


def _translate_messages_anthropic_to_openai(
    messages: list[dict[str, Any]],
    system: str | list[dict] | None,
) -> list[dict[str, Any]]:
    """Anthropic blocks → OpenAI messages; preserve native tool/reasoning history.

    - system top-level → messages[0] role=system
    - {role:'user', content:'str'} → 不变
    - {role:'user', content:[{type:'tool_result', tool_use_id, content}]}
        → 每个 tool_result 一条 role='tool' message
    - {role:'assistant', content:[{type:'text',...}, {type:'tool_use',...}]}
        → 合并为 1 条 assistant message(content + tool_calls 数组)
    """
    out: list[dict[str, Any]] = []

    if system:
        # system 可能是 str 或 list[dict](Anthropic 形)
        if isinstance(system, list):
            sys_text = "".join(
                b.get("text", "") for b in system
                if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            sys_text = system
        out.append({"role": "system", "content": sys_text})

    for msg in messages:
        role = msg["role"]
        content = msg.get("content")

        if role == "tool":
            out.append({
                "role": "tool", "tool_call_id": msg["tool_call_id"], "content": content,
            })
            continue
        if role == "assistant" and (content is None or "tool_calls" in msg):
            out.append({
                key: msg[key] for key in ("role", "content", "tool_calls", "reasoning_content")
                if key in msg
            })
            continue

        # plain text content
        if isinstance(content, str):
            translated = {"role": role, "content": content}
            if role == "assistant" and "reasoning_content" in msg:
                translated["reasoning_content"] = msg["reasoning_content"]
            out.append(translated)
            continue

        # content is list of blocks(Anthropic 形)
        if role == "user":
            user_texts: list[str] = []
            for block in content:
                btype = block.get("type")
                if btype == "tool_result":
                    tool_content = block.get("content", "")
                    if isinstance(tool_content, list):
                        tool_content = "".join(
                            b.get("text", "") for b in tool_content
                            if isinstance(b, dict)
                        )
                    out.append({
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": str(tool_content),
                    })
                elif btype == "text":
                    user_texts.append(block.get("text", ""))
            if user_texts:
                out.append({"role": "user", "content": "".join(user_texts)})

        elif role == "assistant":
            texts: list[str] = []
            tool_calls: list[dict] = []
            for block in content:
                btype = block.get("type")
                if btype == "text":
                    texts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(
                                block.get("input", {}), ensure_ascii=False,
                            ),
                        },
                    })
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            text_content = "".join(texts)
            # OpenAI 允许 content=null 当 tool_calls 存在
            assistant_msg["content"] = text_content if text_content else None
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            if "reasoning_content" in msg:
                assistant_msg["reasoning_content"] = msg["reasoning_content"]
            out.append(assistant_msg)

    return out
