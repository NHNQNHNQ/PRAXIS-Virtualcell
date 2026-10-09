# praxis2/llm/client.py
"""Stream text and tool calls from an OpenAI-compatible provider."""

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
    ) -> dict[str, Any]:

        payload = self._build_payload(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            stream=False,
        )
        resp = await self._http.post(
            "/v1/chat/completions",
            headers=self._headers,
            json=payload,
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
    ):

        payload = self._build_payload(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            stream=True,
        )
        payload["stream_options"] = {"include_usage": True}
        async with self._http.stream(
            "POST",
            "/v1/chat/completions",
            headers=self._headers,
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                await resp.aread()
                body_preview = resp.text[:500] if resp.text else ""
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code} from /v1/chat/completions: {body_preview}",
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
        return payload

    async def aclose(self) -> None:
        await self._http.aclose()


AnthropicClient = LLMClient


def _translate_messages_anthropic_to_openai(
    messages: list[dict[str, Any]],
    system: str | list[dict] | None,
) -> list[dict[str, Any]]:

    out: list[dict[str, Any]] = []

    if system:
        if isinstance(system, list):
            sys_text = "".join(b.get("text", "") for b in system if isinstance(b, dict) and b.get("type") == "text")
        else:
            sys_text = system
        out.append({"role": "system", "content": sys_text})

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        # plain text content
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue

        if role == "user":
            user_texts: list[str] = []
            for block in content:
                btype = block.get("type")
                if btype == "tool_result":
                    tool_content = block.get("content", "")
                    if isinstance(tool_content, list):
                        tool_content = "".join(b.get("text", "") for b in tool_content if isinstance(b, dict))
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(tool_content),
                        }
                    )
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
                    tool_calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(
                                    block.get("input", {}),
                                    ensure_ascii=False,
                                ),
                            },
                        }
                    )
            assistant_msg: dict[str, Any] = {"role": "assistant"}
            text_content = "".join(texts)

            assistant_msg["content"] = text_content if text_content else None
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            out.append(assistant_msg)

    return out
