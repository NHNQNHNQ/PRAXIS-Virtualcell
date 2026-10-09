from __future__ import annotations

import asyncio

from praxis2.agents.agent_tool import AgentTool


def test_run_with_task_returns_spawn_descriptor():
    t = AgentTool()
    r = asyncio.run(t.run({"task": "\u5728 enzyme brain \u68c0\u7d22 Stiffler 2015 case \u5173\u952e mutation"}))
    assert r.ok
    v = r.value
    assert isinstance(v, dict), f"The descriptor must be a dictionary; observed {type(v).__name__}"
    desc = v["task_descriptor"]
    assert desc["prompt"] == "\u5728 enzyme brain \u68c0\u7d22 Stiffler 2015 case \u5173\u952e mutation"
    assert desc["discipline"] is None
    assert desc["suggested_model"]
    assert desc["write_prefix"]
    assert desc["sub_agent_id"].startswith("sub-")
    assert desc["sidechain_id"].startswith("sidechain-")
    assert v["spawn_endpoint"] == "/api/spawn/post"
    assert v["spawn_payload_template"]["prompt"] == desc["prompt"]
    assert v["spawn_payload_template"]["model"] == desc["suggested_model"]


def test_run_with_discipline_hint():
    t = AgentTool()
    r = asyncio.run(
        t.run(
            {
                "task": "\u8dd1 vina_gnina_dock \u770b\u4e0b TEM-1 \u548c benzylpenicillin \u590d\u5408\u4f53",
                "discipline": "DOCK",
            }
        )
    )
    assert r.ok
    assert r.value["task_descriptor"]["discipline"] == "dock"


def test_run_with_suggested_model():
    t = AgentTool()
    r = asyncio.run(
        t.run(
            {
                "task": "\u590d\u6742\u4efb\u52a1:\u8dd1\u5b8c\u6574 RMCP \u94fe\u8def",
                "suggested_model": "deepseek-v4-pro",
            }
        )
    )
    assert r.ok
    assert r.value["task_descriptor"]["suggested_model"] == "deepseek-v4-pro"
    assert r.value["spawn_payload_template"]["model"] == "deepseek-v4-pro"


def test_run_missing_task_returns_error():
    t = AgentTool()
    r = asyncio.run(t.run({}))
    assert not r.ok
    assert "task" in (r.error or "").lower()


def test_run_default_write_prefix_candidate():

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

    schema = AgentTool().input_schema()
    assert "task" in schema["properties"]
    assert "discipline" in schema["properties"]
    assert "suggested_model" in schema["properties"]
    assert "write_prefix" in schema["properties"]
    assert schema["required"] == ["task"]
