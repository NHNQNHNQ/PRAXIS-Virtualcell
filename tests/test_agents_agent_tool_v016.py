"""AgentTool v0.16.0-beta 强化测试(P0 5/5)。

回归:此前 AgentTool.run() 返 placeholder 文字 "AgentTool 隔离设施就绪..." —
模型拿到这个字符串后只能纯文字描述"我想 fork 一个 sub-agent",**真 spawn
动作落空**(幻觉)。

v0.16.0-beta:run() 返结构化 spawn task descriptor + /api/spawn/post 模板,
对齐 v0.15.0 auto→spawn 链路。
"""
from __future__ import annotations

import asyncio

from praxis2.agents.agent_tool import AgentTool


def test_run_with_task_returns_spawn_descriptor():
    t = AgentTool()
    r = asyncio.run(t.run({"task": "在 enzyme brain 检索 Stiffler 2015 case 关键 mutation"}))
    assert r.ok
    v = r.value
    assert isinstance(v, dict), f"v0.16.0-beta 起 value 必须是 dict,得到 {type(v).__name__}"
    desc = v["task_descriptor"]
    assert desc["prompt"] == "在 enzyme brain 检索 Stiffler 2015 case 关键 mutation"
    assert desc["discipline"] is None  # 未传
    assert desc["suggested_model"]
    assert desc["write_prefix"]
    assert desc["sub_agent_id"].startswith("sub-")
    assert desc["sidechain_id"].startswith("sidechain-")
    assert v["spawn_endpoint"] == "/api/spawn/post"
    assert v["spawn_payload_template"]["prompt"] == desc["prompt"]
    assert v["spawn_payload_template"]["model"] == desc["suggested_model"]


def test_run_with_discipline_hint():
    t = AgentTool()
    r = asyncio.run(t.run({
        "task": "跑 vina_gnina_dock 看下 TEM-1 和 benzylpenicillin 复合体",
        "discipline": "DOCK",  # 测大小写归一
    }))
    assert r.ok
    assert r.value["task_descriptor"]["discipline"] == "dock"


def test_run_with_suggested_model():
    t = AgentTool()
    r = asyncio.run(t.run({
        "task": "复杂任务:跑完整 RMCP 链路",
        "suggested_model": "deepseek-v4-pro",
    }))
    assert r.ok
    assert r.value["task_descriptor"]["suggested_model"] == "deepseek-v4-pro"
    assert r.value["spawn_payload_template"]["model"] == "deepseek-v4-pro"


def test_run_missing_task_returns_error():
    t = AgentTool()
    r = asyncio.run(t.run({}))
    assert not r.ok
    assert "task" in (r.error or "").lower()


def test_run_default_write_prefix_candidate():
    """默认 write_prefix 为 _candidate/(§7.4.2 SandboxWriteScope 默认)。"""
    t = AgentTool()
    r = asyncio.run(t.run({"task": "x"}))
    assert r.ok
    assert r.value["task_descriptor"]["write_prefix"] == "_candidate/"


def test_run_custom_write_prefix():
    t = AgentTool()
    r = asyncio.run(t.run({"task": "x", "write_prefix": "_proposed/"}))
    assert r.ok
    assert r.value["task_descriptor"]["write_prefix"] == "_proposed/"


def test_input_schema_v016_new_fields():
    """v0.16.0-beta 加 discipline / suggested_model 字段。"""
    schema = AgentTool().input_schema()
    assert "task" in schema["properties"]
    assert "discipline" in schema["properties"]
    assert "suggested_model" in schema["properties"]
    assert "write_prefix" in schema["properties"]
    assert schema["required"] == ["task"]
