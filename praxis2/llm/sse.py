# praxis2/llm/sse.py


from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

_STOP_REASON_MAP = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "stop",
}


async def parse_stream_response(
    resp: httpx.Response,
) -> AsyncIterator[dict[str, Any]]:

    tool_call_buf: dict[int, dict[str, Any]] = {}
    last_usage: dict[str, Any] = {}

    async for line in resp.aiter_lines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if payload == "[DONE]":
            break
        try:
            ev = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if isinstance(ev, dict) and "error" in ev:
            err = ev["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise RuntimeError(f"LLM upstream error: {msg}")

        if ev.get("usage"):
            last_usage = ev["usage"]

        choices = ev.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}
        finish_reason = choice.get("finish_reason")

        content = delta.get("content")
        if content:
            yield {"type": "text", "text": content}

        reasoning = delta.get("reasoning_content")
        if reasoning:
            yield {"type": "thinking", "text": reasoning}

        for tc in delta.get("tool_calls") or []:
            idx = tc.get("index", 0)
            buf = tool_call_buf.setdefault(
                idx,
                {
                    "id": "",
                    "name": "",
                    "arguments_buf": "",
                },
            )
            if tc.get("id"):
                buf["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                buf["name"] = fn["name"]
            if fn.get("arguments"):
                buf["arguments_buf"] += fn["arguments"]

        if finish_reason is not None:
            for idx in sorted(tool_call_buf):
                buf = tool_call_buf[idx]
                try:
                    args_dict = json.loads(buf["arguments_buf"]) if buf["arguments_buf"] else {}
                except json.JSONDecodeError:
                    args_dict = {"__raw__": buf["arguments_buf"]}
                yield {
                    "type": "tool_use",
                    "id": buf["id"],
                    "name": buf["name"],
                    "input": args_dict,
                }
            tool_call_buf.clear()
            yield {
                "type": "message_stop",
                "stop_reason": _STOP_REASON_MAP.get(finish_reason, finish_reason),
                "usage": last_usage,
            }

    if last_usage:
        yield {"type": "usage", "usage": last_usage}
