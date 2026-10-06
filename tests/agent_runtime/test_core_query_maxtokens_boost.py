"""Bug B(2026-05-30):推理模型(deepseek-v4-pro)reasoning_content 烧光
max_tokens → content=0 → FE 空响应。

根因:query.py max_tokens recovery 时 continue 重试,但传给 client 的
max_tokens 是固定 settings.max_tokens → 下一轮同样烧光 → 确定性 0 输出。

治本:recovery 时倍增 max_tokens(state.max_tokens_boost 累加),让重试轮
拿到更大预算,reasoning + content 都能出。
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from ._llm_fakes import TURN_FINAL_TEXT, TURN_MAX_TOKENS


class _RecordingClient:
    """记录每次 stream_messages 收到的 max_tokens,按 turns 顺序 yield。"""

    def __init__(self, turns: list[list[dict]]) -> None:
        self._turns = turns
        self._idx = 0
        self.max_tokens_seen: list[int] = []

    async def stream_messages(
        self, *, model, messages, max_tokens, system=None, tools=None,
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
        ToolRegistry(), recovery_budget=3, permission=AllowAllPermission(),
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
    """max_tokens 截断 → recovery 重试时,下一轮 client 收到更大的 max_tokens。

    这是 Bug B 的核心:不提预算的重试对推理模型是确定性 0 输出。
    """
    # turn 1: max_tokens 截断 → recovery → turn 2: 终答
    client = _RecordingClient(turns=[TURN_MAX_TOKENS, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "写长文"}]
    events = [
        e async for e in query(
            st, client=client, registry=ToolRegistry(), settings=_settings(),
            runner=_runner(), compactor=MinimalCompactor(),
        )
    ]
    # 终答正常
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.max_output_tokens_recovery_count == 1
    # ★ 核心断言:第 2 轮(recovery 重试)收到的 max_tokens 严格大于第 1 轮
    assert len(client.max_tokens_seen) == 2
    assert client.max_tokens_seen[0] == 64  # 第 1 轮 = settings.max_tokens
    assert client.max_tokens_seen[1] > client.max_tokens_seen[0]  # 重试翻倍
    await client.aclose()


async def test_max_tokens_boost_resets_per_query():
    """boost 是 State 实例字段,新 State 不带旧 boost(不跨 query 泄漏)。"""
    client = _RecordingClient(turns=[TURN_FINAL_TEXT])
    st = State()  # 全新 state
    st.messages = [{"role": "user", "content": "短问"}]
    _ = [
        e async for e in query(
            st, client=client, registry=ToolRegistry(), settings=_settings(),
            runner=_runner(), compactor=MinimalCompactor(),
        )
    ]
    # 无截断 → 无 boost → 第 1 轮就是裸 settings.max_tokens
    assert client.max_tokens_seen[0] == 64
    assert st.max_output_tokens_recovery_count == 0
    await client.aclose()


def _big_settings():
    """触顶用:base + 1 次 boost 就会超 393216(deepseek-v4-pro 实测上限)。"""
    class S:
        model = "m"
        max_tokens = 200_000
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_max_tokens_boost_capped_at_model_ceiling():
    """boost 累加 + base 超过 393216 时,实际传给 client 的 max_tokens 被 cap。

    防御性:litellm 对 deepseek-v4-pro 强制 [1, 393216],累加越界会直接 400。
    """
    # turn1: 200_000 截断 → recovery → turn2: 应为 400_000,但 cap 在 393216
    client = _RecordingClient(turns=[TURN_MAX_TOKENS, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "写更长的文"}]
    events = [
        e async for e in query(
            st, client=client, registry=ToolRegistry(), settings=_big_settings(),
            runner=_runner(), compactor=MinimalCompactor(),
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert len(client.max_tokens_seen) == 2
    assert client.max_tokens_seen[0] == 200_000
    # ★ 核心:本应 400_000,被 cap 在 deepseek-v4-pro 实测上限
    assert client.max_tokens_seen[1] == 393_216
    # boost 字段本身可以累计超 ceiling,cap 只在传给 client 时生效
    assert st.max_tokens_boost == 200_000
    await client.aclose()
