from __future__ import annotations

from collections.abc import AsyncIterator

from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_FINAL_TEXT, TURN_MAX_TOKENS


class _RecordingClient:
    def __init__(self, turns: list[list[dict]]) -> None:
        self._turns = turns
        self._idx = 0
        self.max_tokens_seen: list[int] = []

    async def stream_messages(
        self,
        *,
        model,
        messages,
        max_tokens,
        system=None,
        tools=None,
    ) -> AsyncIterator[dict]:
        self.max_tokens_seen.append(max_tokens)
        if self._idx >= len(self._turns):
            yield {"type": "message_stop", "stop_reason": "end_turn", "usage": {}}
            return
        for ev in self._turns[self._idx]:
            yield ev
        self._idx += 1

    async def aclose(self) -> None:
        pass


def _runner():
    return SerialToolRunner(
        ToolRegistry(),
        recovery_budget=3,
        permission=AllowAllPermission(),
    )


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_max_tokens_recovery_boosts_budget_on_retry():

    client = _RecordingClient(turns=[TURN_MAX_TOKENS, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u5199\u957f\u6587"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=ToolRegistry(),
            settings=_settings(),
            runner=_runner(),
            compactor=MinimalCompactor(),
        )
    ]

    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.max_output_tokens_recovery_count == 1

    assert len(client.max_tokens_seen) == 2
    assert client.max_tokens_seen[0] == 64
    assert client.max_tokens_seen[1] > client.max_tokens_seen[0]
    await client.aclose()


async def test_max_tokens_boost_resets_per_query():

    client = _RecordingClient(turns=[TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u77ed\u95ee"}]
    _ = [
        e
        async for e in query(
            st,
            client=client,
            registry=ToolRegistry(),
            settings=_settings(),
            runner=_runner(),
            compactor=MinimalCompactor(),
        )
    ]

    assert client.max_tokens_seen[0] == 64
    assert st.max_output_tokens_recovery_count == 0
    await client.aclose()


def _big_settings():

    class S:
        model = "m"
        max_tokens = 200_000
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_max_tokens_boost_capped_at_model_ceiling():

    client = _RecordingClient(turns=[TURN_MAX_TOKENS, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u5199\u66f4\u957f\u7684\u6587"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=ToolRegistry(),
            settings=_big_settings(),
            runner=_runner(),
            compactor=MinimalCompactor(),
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert len(client.max_tokens_seen) == 2
    assert client.max_tokens_seen[0] == 200_000

    assert client.max_tokens_seen[1] == 393_216

    assert st.max_tokens_boost == 200_000
    await client.aclose()
