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
    # §5⑦ 起步:default prompt 结构/hash 锁定。任何改动须自觉同步镜像,否则失败
    # → prompt drift 被回归网拦住。
    expected = [
        Section("identity", "你是 PRAXIS-2 科研多 agent 系统的内核助手。"),
        Section("safety", "遵守科学严谨纪律:先检索证据再执行;不杜撰 DOI 或引用。"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
    ]
    actual = get_default_system_prompt()
    assert [s.name for s in actual] == [s.name for s in expected]
    assert section_hash(actual) == section_hash(expected)


@respx.mock
async def test_single_path_query_consumes_prompt_and_dumps_request(tmp_path):
    # §3 关键不变量 + §7.2.1:唯一一条组装路径 → query() 消费 → API 实收 system。
    # M10.5 切 OpenAI /v1/chat/completions 后,client 把 Anthropic-shape system
    # (list[dict] 含 cache_control)翻成 messages[0].role='system'+content=str。
    # cache_control 是 Anthropic 特有,litellm/OpenAI 协议不传到 wire — 但
    # --dump-prompts JSONL 仍保留原 dict(query.py:75-78 直接 dump 参数,见
    # on_request callsite),供调试 / drift 检测。
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
    st.messages = [{"role": "user", "content": "你好"}]
    # 唯一组装入口 → 持久化挂 ToolUseContext → 作为 system 传入 query()
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
            system=api_system or None,  # §7.2.3 契约:空结果传 None,绝不发 system=[]
            on_request=make_jsonl_recorder(str(dump)),
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    # API 实收(OpenAI wire):system → messages[0].role='system', content=str
    # = Anthropic list[dict] 中所有 text 拼接(client._translate_messages_anthropic_to_openai)
    sent = json.loads(route.calls[0].request.content)
    assert sent["messages"][0]["role"] == "system"
    expected_sys_text = "".join(
        b.get("text", "") for b in api_system
        if isinstance(b, dict) and b.get("type") == "text"
    )
    assert sent["messages"][0]["content"] == expected_sys_text
    assert sent["messages"][1] == {"role": "user", "content": "你好"}
    # --dump-prompts:dump 保留 query() 参数原貌(含 cache_control list[dict]),
    # 与 wire 解耦 — drift 比对靠 dump 而不是 wire,wire 经 client 翻译已变形
    lines = dump.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    dumped = json.loads(lines[0])
    assert dumped["system"] == api_system  # dump 仍保留 list[dict] + cache_control
    assert dumped["messages"] == st.messages  # dump 的 messages 与 state 一致(强断言)
    await client.aclose()


@respx.mock
async def test_empty_override_omits_system_from_api_request(tmp_path):
    # §7.2.3 契约闭环:override=[] → to_api_system=[] → 调用方传 None
    # → API 请求体 messages[] 不含 role='system' 条目(绝不发空 system,
    # 旧 Anthropic /v1/messages 会 400;OpenAI /v1/chat/completions M10.5 后
    # 的等价表现:messages[0] 直接是 user,没有 system 条目)。
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
    st.messages = [{"role": "user", "content": "你好"}]
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
    # OpenAI 协议下没有顶层 system 字段(M10.5 切协议后已不发)
    assert "system" not in sent
    # 关键不变量:messages[] 也不含 role='system' 条目(空 system 不变成
    # 空 system message,而是完全省略)
    assert all(m["role"] != "system" for m in sent["messages"])
    assert sent["messages"][0] == {"role": "user", "content": "你好"}
    await client.aclose()
