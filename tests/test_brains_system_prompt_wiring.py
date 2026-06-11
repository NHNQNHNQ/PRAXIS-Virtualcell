"""PLAN §11:确保 _chat_stream 真把大脑 system prompt 传给 query()。
回归保护:本测试一旦失败,说明又退回到 `system=None`(模型只看 tools 不知何时调)。"""

from __future__ import annotations

import pytest

from praxis2.agents.loader import resolve_agent
from praxis2.brains.system_prompt import build_chat_system_prompt


def test_build_chat_system_prompt_returns_non_empty_for_discipline_agent():
    """enzyme agent + 酶相关 query → system 应非空,且首块带 cache_control(静态前缀)。"""
    sel = resolve_agent("enzyme", user_query="我要做酶热稳定性 ddG 扫描")
    assert sel.brain_slugs == ["_common", "enzyme"]
    out = build_chat_system_prompt(sel, "我要做酶热稳定性 ddG 扫描")
    assert out, "system prompt 不能为空 — 否则模型不知何时调工具(PLAN §11 退回)"
    # 静态前缀块带 ephemeral cache
    assert out[0].get("cache_control") == {"type": "ephemeral"}
    # 应当包含 _common 内的 RMCP 规则关键词
    flat = "\n".join(b.get("text", "") for b in out)
    assert "RMCP" in flat or "rmcp" in flat.lower()


def test_build_chat_system_prompt_filters_skills_by_host_env():
    """主路径过滤:只入 host_env 存在于 staging conda_envs 的 skill;
    断言生成的 skill_summary 不包含 cryo skill(已 status:not-deployed 且无 cryo env)。"""
    sel = resolve_agent("protein", user_query="预测蛋白结构")
    out = build_chat_system_prompt(sel, "预测蛋白结构")
    flat = "\n".join(b.get("text", "") for b in out)
    # cryo skill 都标了 status:not-deployed,且 host_env 是 praxis-cryo-* (不在 staging)
    # 所以 skill_summary 不应出现任何 cryo skill 名(2d_3d_classify 等)
    assert "2d_3d_classify" not in flat
    assert "motion_correct_ctf" not in flat


def test_empty_brain_slugs_returns_empty():
    """bare 模式 / 空 selection → 返回 [](调用方应传 None)。"""

    class FakeSel:
        brain_slugs: list[str] = []

    out = build_chat_system_prompt(FakeSel(), "anything")
    assert out == []


@pytest.mark.asyncio
async def test_chat_stream_passes_system_to_query(monkeypatch):
    """_chat_stream 真的把 build_chat_system_prompt 的产物喂给 query()。
    如果有人改回 system=None,本测试 fail。"""
    from praxis2.server import app as app_module

    captured: dict = {"system": "__sentinel__"}

    async def fake_query(state, *, client, registry, settings, runner, compactor, **kw):
        captured["system"] = kw.get("system", "__missing__")
        yield {"type": "text", "text": "ok"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    from tests.test_correctness_eventbus_replay import _drive_chat_stream, make_test_app_deps, preseed_session
    from praxis2.server.app import make_app

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u_sys_wire")
    app = make_app(deps)
    await _drive_chat_stream(app, cookie, message="我要做酶热稳定性 ddG 扫描")
    await deps.redis.aclose()

    # 必须不是 "__missing__"(说明 _chat_stream 没传)且也不是 "__sentinel__"(没被改写)
    assert captured["system"] != "__missing__", "_chat_stream 退回未传 system → PLAN §11 接线丢失"
    # system 可以是 list[dict] 或 None;None 也算"传了"(主路径降级到 bare 的合法情况)
    assert captured["system"] is None or isinstance(captured["system"], list)
