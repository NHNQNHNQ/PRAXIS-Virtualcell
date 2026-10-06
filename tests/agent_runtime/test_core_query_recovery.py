import httpx

from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.llm.retry import WithheldKind, classify_withheld_error
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from ._llm_fakes import (
    TURN_FINAL_TEXT,
    TURN_MAX_TOKENS,
    FakeLLMClient,
    make_prompt_too_long_error,
)
from .cassette import load


def _runner():
    return SerialToolRunner(ToolRegistry(), recovery_budget=3, permission=AllowAllPermission())


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


def test_classify_withheld_prompt_too_long():
    resp = httpx.Response(400, text=load("m1_prompt_too_long.json"))
    exc = httpx.HTTPStatusError("400", request=httpx.Request("POST", "http://x"), response=resp)
    assert classify_withheld_error(exc) == WithheldKind.PROMPT_TOO_LONG
    # 非 prompt-too-long 的 400 不误判
    other = httpx.Response(400, text='{"error":{"message":"bad field"}}')
    exc2 = httpx.HTTPStatusError("400", request=httpx.Request("POST", "http://x"), response=other)
    assert classify_withheld_error(exc2) == WithheldKind.UNKNOWN


async def test_prompt_too_long_triggers_compact_then_retry_succeeds():
    # turn 1: 抛 400 prompt-too-long → reactive compact → turn 2: 终答
    ptl_error = make_prompt_too_long_error()

    class _PtlThenSuccess:
        """首次抛 PTL 错误,之后 yield 正常 turn。"""
        def __init__(self):
            self._called = 0

        async def stream_messages(self, **kwargs):
            self._called += 1
            if self._called == 1:
                raise ptl_error
                yield  # 保持 async generator(unreachable)
            for ev in TURN_FINAL_TEXT:
                yield ev

        async def aclose(self):
            pass

    client = _PtlThenSuccess()
    st = State()
    # 造足够长历史让 MinimalCompactor 有东西可砍
    st.messages = [{"role": "user", "content": f"m{i}"} for i in range(8)]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=ToolRegistry(),
            settings=_settings(),
            runner=_runner(),
            compactor=MinimalCompactor(),
            system="助手",
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.transition == "reactive_compact_done"  # 走过恢复分支
    assert len(st.messages) < 8 + 2  # 历史被压过(留余量给重试追加的轮)
    await client.aclose()


async def test_max_output_tokens_recovery_basic_then_done():
    # turn 1: max_tokens → recovery → turn 2: 终答
    client = FakeLLMClient(turns=[TURN_MAX_TOKENS, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "写长文"}]
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
    assert st.max_output_tokens_recovery_count == 1
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    await client.aclose()
