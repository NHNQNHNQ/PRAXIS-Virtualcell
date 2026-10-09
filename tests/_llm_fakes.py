from __future__ import annotations

from collections.abc import AsyncIterator

import httpx


class FakeLLMClient:
    def __init__(self, turns: list[list[dict]]) -> None:
        self._turns = turns
        self._idx = 0

    async def stream_messages(
        self,
        *,
        model,
        messages,
        max_tokens,
        system=None,
        tools=None,
    ) -> AsyncIterator[dict]:
        if self._idx >= len(self._turns):
            yield {"type": "message_stop", "stop_reason": "end_turn", "usage": {}}
            return
        for ev in self._turns[self._idx]:
            yield ev
        self._idx += 1

    async def aclose(self) -> None:
        pass


class RaisingLLMClient:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def stream_messages(self, **kwargs):
        raise self._exc
        yield

    async def aclose(self) -> None:
        pass


def make_prompt_too_long_error() -> httpx.HTTPStatusError:

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


TURN_FINAL_TEXT = [
    {"type": "text", "text": "The answer is 42"},
    {"type": "message_stop", "stop_reason": "end_turn", "usage": {"input_tokens": 5, "output_tokens": 4}},
]


TURN_TOOLUSE = [
    {"type": "text", "text": "I will check."},
    {"type": "tool_use", "id": "tu_1", "name": "echo", "input": {"t": "hi"}},
    {"type": "message_stop", "stop_reason": "tool_use", "usage": {"input_tokens": 7, "output_tokens": 9}},
]


TURN_AFTER_TOOL = [
    {"type": "text", "text": "The tool returned hi; completed"},
    {"type": "message_stop", "stop_reason": "end_turn", "usage": {"input_tokens": 20, "output_tokens": 6}},
]

# m1_turn_boom_tool.sse → tool_use(boom, tb_1) + message_stop(tool_use)
TURN_BOOM_TOOL = [
    {"type": "tool_use", "id": "tb_1", "name": "boom", "input": {}},
    {"type": "message_stop", "stop_reason": "tool_use", "usage": {"input_tokens": 8, "output_tokens": 5}},
]


TURN_MAX_TOKENS = [
    {"type": "text", "text": "Partial truncated output..."},
    {"type": "message_stop", "stop_reason": "max_tokens", "usage": {"input_tokens": 10, "output_tokens": 64}},
]


TURN_COMPACT_SUMMARY = [
    {
        "type": "text",
        "text": ("[Previous summary] The user requested X; three cases were retrieved; the current phase is RETRIEVE."),
    },
    {"type": "message_stop", "stop_reason": "end_turn", "usage": {"input_tokens": 5, "output_tokens": 4}},
]
