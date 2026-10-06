# praxis2/llm/sse.py
"""OpenAI /v1/chat/completions 流式 SSE → 规范事件(M10.5 重写)。

旧 Anthropic /v1/messages parser 已删(v0.12 cleanup window 内代码不留)。

产出 4 类规范事件(对应总纲 §7.1.3):
- {"type":"text",         "text": <增量>}
- {"type":"thinking",     "text": <增量>}                # M10.5 新加
- {"type":"tool_use",     "id","name","input": <dict>}   # finish_reason 时 flush
- {"type":"message_stop", "stop_reason","usage": dict}

错误:upstream 200 + body 含 'error' 字段 → 抛 RuntimeError;
HTTP 非 2xx → caller 应在 resp.raise_for_status() 抛 httpx.HTTPStatusError
之前/之后调用,本函数只处理 200 流。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

# OpenAI finish_reason → 内部 stop_reason
_STOP_REASON_MAP = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
    "content_filter": "stop",
}


async def parse_stream_response(
    resp: httpx.Response,
) -> AsyncIterator[dict[str, Any]]:
    """OpenAI /v1/chat/completions stream → 4 类规范事件。

    tool_calls 跨多 chunk partial JSON arguments 内部累积,finish_reason
    出现时一次性 flush 出 tool_use 事件(已 json.loads input)。
    """
    tool_call_buf: dict[int, dict[str, Any]] = {}
    last_usage: dict[str, Any] = {}

    async for line in resp.aiter_lines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            ev = json.loads(payload)
        except json.JSONDecodeError:
            continue   # 跳过 malformed line(不抛,容错继续)

        # 错误体(litellm 偶尔 200 + {"error":...} 返,对齐 Anthropic 行为)
        if isinstance(ev, dict) and "error" in ev:
            err = ev["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise RuntimeError(f"LLM upstream error: {msg}")

        # usage 可能在最后一帧(stream_options.include_usage=true 时)
        if ev.get("usage"):
            last_usage = ev["usage"]

        choices = ev.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}
        finish_reason = choice.get("finish_reason")

        # 文本流
        content = delta.get("content")
        if content:
            yield {"type": "text", "text": content}

        # reasoning / thinking(deepseek-v4 / R1 风格)
        reasoning = delta.get("reasoning_content")
        if isinstance(reasoning, str):
            yield {"type": "thinking", "text": reasoning}

        # tool_calls 流(partial JSON args 累积)
        for tc in delta.get("tool_calls") or []:
            idx = tc.get("index", 0)
            buf = tool_call_buf.setdefault(idx, {
                "id": "", "name": "", "arguments_buf": "",
            })
            if tc.get("id"):
                buf["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                buf["name"] = fn["name"]
            if fn.get("arguments"):
                buf["arguments_buf"] += fn["arguments"]

        # finish_reason 出现:flush 累积 tool_calls + emit message_stop
        if finish_reason is not None:
            for idx in sorted(tool_call_buf):
                buf = tool_call_buf[idx]
                try:
                    args_dict = (
                        json.loads(buf["arguments_buf"])
                        if buf["arguments_buf"]
                        else {}
                    )
                except json.JSONDecodeError:
                    # 极端情况:partial JSON 没拼完 → 保留 raw 供 caller 调试
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

    # OpenAI include_usage 的 usage 是最后一帧(choices 空 → 上面 continue,不触发
    # message_stop);而 message_stop 在 finish_reason 帧就发了(此时 usage 尚空)→ 流
    # 读完后补发一次真实 usage,chat 据此扣费(query.py 累计 type==usage)。
    if last_usage:
        yield {"type": "usage", "usage": last_usage}
