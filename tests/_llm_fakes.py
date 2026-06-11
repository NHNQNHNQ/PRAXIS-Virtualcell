"""测试 fake LLM client — yields 预制规范事件序列,不经 HTTP/SSE。

替代 M0-M10 用 respx + Anthropic SSE cassette 的 mock 模式。
M10.5 之后:query.py 测试关心 query orchestration(text/tool_use/message_stop
编排),不关心 wire format。
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx


class FakeLLMClient:
    """构造时传若干 turns,每 turn 是规范事件 list。

    每次 stream_messages() 调用,yield 下一个 turn 的事件,然后 advance。
    用 turns=[turn1, turn2, ...] 模拟多 turn 对话。

    Example:
        client = FakeLLMClient(turns=[
            [{"type":"text","text":"hi"},
             {"type":"message_stop","stop_reason":"end_turn","usage":{}}],
        ])
    """
    def __init__(self, turns: list[list[dict]]) -> None:
        self._turns = turns
        self._idx = 0

    async def stream_messages(
        self, *, model, messages, max_tokens, system=None, tools=None,
    ) -> AsyncIterator[dict]:
        if self._idx >= len(self._turns):
            # 超 turn → 默认 stop
            yield {"type": "message_stop", "stop_reason": "end_turn", "usage": {}}
            return
        for ev in self._turns[self._idx]:
            yield ev
        self._idx += 1

    async def aclose(self) -> None:
        pass


class RaisingLLMClient:
    """模拟 LLM 错误 — stream_messages() 抛 Exception。"""
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def stream_messages(self, **kwargs):
        raise self._exc
        yield  # 保持 async generator(unreachable)

    async def aclose(self) -> None:
        pass


def make_prompt_too_long_error() -> httpx.HTTPStatusError:
    """构造触发 WithheldKind.PROMPT_TOO_LONG 的 400 异常。"""
    resp = httpx.Response(
        400,
        text='{"type":"error","error":{"type":"invalid_request_error",'
             '"message":"prompt is too long: 250000 tokens > 200000 maximum"}}',
    )
    return httpx.HTTPStatusError(
        "400 Bad Request",
        request=httpx.Request("POST", "http://fake/v1/chat/completions"),
        response=resp,
    )


# ---- 规范事件序列常量(对应老 cassette 解析后的输出)----

# m1_turn_final_text.sse → text("答案是 42") + message_stop(end_turn)
TURN_FINAL_TEXT = [
    {"type": "text", "text": "答案是 42"},
    {"type": "message_stop", "stop_reason": "end_turn",
     "usage": {"input_tokens": 5, "output_tokens": 4}},
]

# m1_turn_tooluse.sse → text("我来查一下") + tool_use(echo, tu_1) + message_stop(tool_use)
TURN_TOOLUSE = [
    {"type": "text", "text": "我来查一下"},
    {"type": "tool_use", "id": "tu_1", "name": "echo", "input": {"t": "hi"}},
    {"type": "message_stop", "stop_reason": "tool_use",
     "usage": {"input_tokens": 7, "output_tokens": 9}},
]

# m1_turn_after_tool.sse → text("工具返回 hi,完成") + message_stop(end_turn)
TURN_AFTER_TOOL = [
    {"type": "text", "text": "工具返回 hi,完成"},
    {"type": "message_stop", "stop_reason": "end_turn",
     "usage": {"input_tokens": 20, "output_tokens": 6}},
]

# m1_turn_boom_tool.sse → tool_use(boom, tb_1) + message_stop(tool_use)
TURN_BOOM_TOOL = [
    {"type": "tool_use", "id": "tb_1", "name": "boom", "input": {}},
    {"type": "message_stop", "stop_reason": "tool_use",
     "usage": {"input_tokens": 8, "output_tokens": 5}},
]

# m1_maxtokens_then_done.sse → text("截断的一半…") + message_stop(max_tokens)
TURN_MAX_TOKENS = [
    {"type": "text", "text": "截断的一半…"},
    {"type": "message_stop", "stop_reason": "max_tokens",
     "usage": {"input_tokens": 10, "output_tokens": 64}},
]

# m4_compact_summary.sse → text("【前段摘要】...") + message_stop(end_turn)
TURN_COMPACT_SUMMARY = [
    {"type": "text", "text": "【前段摘要】用户最初要求 X;已检索 3 案例;当前 RETRIEVE 相位"},
    {"type": "message_stop", "stop_reason": "end_turn",
     "usage": {"input_tokens": 5, "output_tokens": 4}},
]
