import json

import httpx
import respx

from praxis2.core.prompt import (
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
    Section,
    build_effective_system_prompt,
    get_default_system_prompt,
    render_and_persist,
    section_hash,
)
from praxis2.core.prompt_debug import make_jsonl_recorder
from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.llm.client import AnthropicClient
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests.cassette import load


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


def test_migration_regression_net_default_prompt_pinned():

    expected = [
        Section("identity", "You are the kernel assistant of the PRAXIS VirtualCell agent framework."),
        Section("safety", "Retrieve scientific evidence before execution. Do not invent DOI citations or sources."),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
    ]
    actual = get_default_system_prompt()
    assert [s.name for s in actual] == [s.name for s in expected]
    assert section_hash(actual) == section_hash(expected)


@respx.mock
async def test_single_path_query_consumes_prompt_and_dumps_request(tmp_path):

    dump = tmp_path / "prompts.jsonl"
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = AnthropicClient(api_key="sk", base_url="https://up.example")
    route = respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=load("openai_final_text.sse"),
            headers={"content-type": "text/event-stream"},
        )
    )
    st = State()
    st.messages = [{"role": "user", "content": "\u4f60\u597d"}]

    api_system = render_and_persist(st, build_effective_system_prompt())
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            system=api_system or None,
            on_request=make_jsonl_recorder(str(dump)),
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    sent = json.loads(route.calls[0].request.content)
    assert sent["messages"][0]["role"] == "system"
    expected_sys_text = "".join(
        b.get("text", "") for b in api_system if isinstance(b, dict) and b.get("type") == "text"
    )
    assert sent["messages"][0]["content"] == expected_sys_text
    assert sent["messages"][1] == {"role": "user", "content": "\u4f60\u597d"}

    lines = dump.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    dumped = json.loads(lines[0])
    assert dumped["system"] == api_system
    assert dumped["messages"] == st.messages
    await client.aclose()


@respx.mock
async def test_empty_override_omits_system_from_api_request(tmp_path):

    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = AnthropicClient(api_key="sk", base_url="https://up.example")
    route = respx.post("https://up.example/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=load("openai_final_text.sse"),
            headers={"content-type": "text/event-stream"},
        )
    )
    st = State()
    st.messages = [{"role": "user", "content": "\u4f60\u597d"}]
    api_system = render_and_persist(st, build_effective_system_prompt(override=[]))
    assert api_system == []
    async for _ in query(
        st,
        client=client,
        registry=reg,
        settings=_settings(),
        runner=runner,
        compactor=MinimalCompactor(),
        system=api_system or None,
    ):
        pass
    sent = json.loads(route.calls[0].request.content)

    assert "system" not in sent

    assert all(m["role"] != "system" for m in sent["messages"])
    assert sent["messages"][0] == {"role": "user", "content": "\u4f60\u597d"}
    await client.aclose()
