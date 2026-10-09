import httpx
import respx

from praxis2.core.compact import AutoCompactor, MicroCompactor
from praxis2.core.state import State
from praxis2.llm.client import AnthropicClient
from tests._llm_fakes import TURN_COMPACT_SUMMARY, FakeLLMClient
from tests.cassette import load


class _S:
    model = "m"
    max_tokens = 256
    compact_keep_recent = 2


async def test_autocompact_summarizes_keeps_pinned_task_and_recent():
    client = FakeLLMClient(turns=[TURN_COMPACT_SUMMARY])
    st = State()
    st.messages = [
        {"role": "user", "content": "\u539f\u59cb\u4efb\u52a1:\u505a X"},  # idx0 = pinned
        {"role": "assistant", "content": "\u4e2d\u95f4\u601d\u80031"},
        {"role": "user", "content": "\u4e2d\u95f4\u89c2\u5bdf2"},
        {"role": "assistant", "content": "\u4e2d\u95f4\u601d\u80033"},
        {"role": "user", "content": "\u6700\u8fd11"},
        {"role": "assistant", "content": "\u6700\u8fd12"},
    ]
    st.original_task_idx = 0
    await AutoCompactor(client, _S()).compact(st)
    txt = str(st.messages)
    assert "\u539f\u59cb\u4efb\u52a1:\u505a X" in txt
    assert "Previous summary" in txt
    assert "\u6700\u8fd12" in txt
    assert "\u4e2d\u95f4\u601d\u80031" not in txt
    await client.aclose()


@respx.mock
async def test_autocompact_circuit_breaker_gives_up_after_failures():
    respx.post("https://up.example/v1/messages").mock(return_value=httpx.Response(500, text="boom"))
    client = AnthropicClient(api_key="sk", base_url="https://up.example")
    st = State()
    st.messages = [{"role": "user", "content": f"m{i}"} for i in range(8)]
    st.original_task_idx = 0
    st.auto_compact_tracking["consecutive_failures"] = 3
    before = list(st.messages)
    await AutoCompactor(client, _S()).compact(st)
    assert st.messages == before
    await client.aclose()


@respx.mock
async def test_autocompact_no_orphaned_tool_pair_across_boundary():

    respx.post("https://up.example/v1/messages").mock(
        return_value=httpx.Response(
            200, text=load("m4_compact_summary.sse"), headers={"content-type": "text/event-stream"}
        )
    )
    client = AnthropicClient(api_key="sk", base_url="https://up.example")
    st = State()
    st.messages = [
        {"role": "user", "content": "\u539f\u59cb\u4efb\u52a1"},  # 0
        {"role": "assistant", "content": "\u4e2d\u95f4"},  # 1
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "x", "input": {}}]},  # 2
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "r"}]},  # 3
        {"role": "assistant", "content": "\u7b54"},  # 4
    ]
    st.original_task_idx = 0

    await AutoCompactor(client, _S()).compact(st)
    tus = {
        b["id"]
        for m in st.messages
        if m["role"] == "assistant" and isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_use"
    }
    trs = {
        b["tool_use_id"]
        for m in st.messages
        if m["role"] == "user" and isinstance(m["content"], list)
        for b in m["content"]
        if b.get("type") == "tool_result"
    }
    assert trs <= tus
    assert tus <= trs
    await client.aclose()


async def test_autocompact_ptl_defense_truncates_and_retries_once():

    class _PtlThenSuccess:
        def __init__(self):
            self._called = 0
            self.call_count = 0

        async def stream_messages(self, **kwargs):
            self._called += 1
            self.call_count += 1
            if self._called == 1:
                raise RuntimeError("prompt is too long")
                yield
            for ev in TURN_COMPACT_SUMMARY:
                yield ev

        async def aclose(self):
            pass

    client = _PtlThenSuccess()
    st = State()
    st.messages = [{"role": "user", "content": f"m{i}"} for i in range(8)]
    st.original_task_idx = 0
    await AutoCompactor(client, _S()).compact(st)
    assert client.call_count == 2
    assert "Previous summary" in str(st.messages)
    assert st.auto_compact_tracking["consecutive_failures"] == 0
    await client.aclose()


@respx.mock
async def test_autocompact_no_duplicate_pin_when_task_in_retained():

    respx.post("https://up.example/v1/messages").mock(
        return_value=httpx.Response(
            200, text=load("m4_compact_summary.sse"), headers={"content-type": "text/event-stream"}
        )
    )
    client = AnthropicClient(api_key="sk", base_url="https://up.example")
    st = State()
    st.messages = [
        {"role": "user", "content": "\u4e2d\u95f41"},
        {"role": "assistant", "content": "\u4e2d\u95f42"},
        {"role": "user", "content": "\u539f\u59cb\u4efb\u52a1\u5728\u5c3e\u90e8"},
        {"role": "assistant", "content": "\u6700\u8fd1"},
    ]
    st.original_task_idx = 2
    await AutoCompactor(client, _S()).compact(st)
    cnt = sum("\u539f\u59cb\u4efb\u52a1\u5728\u5c3e\u90e8" in str(m["content"]) for m in st.messages)
    assert cnt == 1
    await client.aclose()


def test_microcompact_clears_old_tool_results_keeps_structure():
    st = State()
    st.messages = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "read", "input": {}}]},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "t1",
                    "content": "\u5de8\u5927\u7684\u65e7\u6587\u4ef6\u5185\u5bb9" * 50,
                }
            ],
        },
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t2", "name": "read", "input": {}}]},
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "t2", "content": "\u6700\u8fd1\u7ed3\u679c,\u4fdd\u7559"}
            ],
        },
    ]
    MicroCompactor(max_age_turns=1).compact_local(st)

    t1 = st.messages[1]["content"][0]
    t2 = st.messages[3]["content"][0]
    assert t1["tool_use_id"] == "t1" and "cleared" in t1["content"]
    assert "\u5de8\u5927\u7684\u65e7\u6587\u4ef6\u5185\u5bb9" not in str(st.messages)
    assert t2["content"] == "\u6700\u8fd1\u7ed3\u679c,\u4fdd\u7559"
