"""BrainQueryTool 单测(v0.16.0 P0)。

回归:chat_registry 此前只挂 AgentTool + SkillExec,模型看见 system prompt 里
列出 13 个学科大脑案例 / 规则 / 技能,但没有工具可以"在大脑里查"——
模型只能纯文字回答(幻觉)。本工具补上"检索本学科 brain"的 tool_use 动作。

设计:包装 brains/retrieve.py 的 retrieve_brain + brains/migrate.py 的
migrate_dir_tree。不需要 store / DB,直接读文件系统 brains/<slug>/。
检索类工具不受相位门约束(rmcp_op=None)。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.brain_query import BrainQueryTool


@pytest.fixture(autouse=True)
def isolated_brain_root(tmp_path, monkeypatch):
    import praxis2.tools.brain_query as module

    root = tmp_path / "brains"
    cases = root / "antibacterial" / "memory" / "cases"
    cases.mkdir(parents=True)
    (cases / "compound001.md").write_text(
        "Antibacterial evidence fixture: antibiotic MIC target", encoding="utf-8"
    )
    monkeypatch.setattr(module, "_BRAINS_ROOT_DEFAULT", root)
    monkeypatch.setattr(module, "DISCIPLINE_SLUGS", ("antibacterial",))


def test_brain_query_registered_in_chat_registry():
    """所有模式都应注册 BrainQuery(包括 discipline:学科 agent 必备的检索工具)。"""
    sel_disc = resolve_agent("general", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "BrainQuery" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    names_gen = [t["name"] for t in reg_gen.anthropic_tools()]
    assert "BrainQuery" in names_gen


def test_brain_query_returns_hits_for_antibacterial_seed():
    """antibacterial brain 查扰动种子内容 → 命中 vcell-001 bootstrap case。"""
    t = BrainQueryTool()
    r = asyncio.run(t.run({
        "brain": "antibacterial",
        "query": "antibiotic MIC target",
        "top_k": 3,
    }))
    assert r.ok
    v = r.value
    assert v["brain"] == "antibacterial"
    assert v["degraded_to_bare"] is False
    assert len(v["hits"]) >= 1
    stems = [h["stem"] for h in v["hits"]]
    # antibacterial 种子 case stem:compound001
    assert any("compound001" in s.lower() for s in stems), f"应命中 vcell 种子 case,得到 {stems}"
    top_hit = v["hits"][0]
    assert top_hit["kind"] in ("cases", "rules", "skills", "neg_cases")
    assert top_hit["excerpt"]


def test_brain_query_top_k_caps_hits():
    t = BrainQueryTool()
    r = asyncio.run(t.run({
        "brain": "antibacterial",
        "query": "酶 催化 动力学 文献",
        "top_k": 2,
    }))
    assert r.ok
    assert len(r.value["hits"]) <= 2


def test_brain_query_unknown_brain_returns_error():
    t = BrainQueryTool()
    r = asyncio.run(t.run({
        "brain": "this_brain_does_not_exist_xyz",
        "query": "anything",
    }))
    assert not r.ok
    assert "未知 brain" in (r.error or "") or "未找到" in (r.error or "")


def test_brain_query_missing_required_returns_error():
    t = BrainQueryTool()
    r1 = asyncio.run(t.run({"query": "x"}))  # 无 brain
    assert not r1.ok
    r2 = asyncio.run(t.run({"brain": "antibacterial"}))  # 无 query
    assert not r2.ok


def test_brain_query_no_overlap_degrades_to_bare_explicit():
    """检索 0 命中 → degraded_to_bare=True + reason 显式记录,不静默返空(§3 step 2.5)。"""
    t = BrainQueryTool()
    r = asyncio.run(t.run({
        "brain": "antibacterial",
        "query": "完全无关的烹饪食谱内容 zzzzzzz_no_overlap",
        "top_k": 3,
    }))
    assert r.ok  # 检索为空不是错误,只是降级
    assert r.value["degraded_to_bare"] is True
    assert r.value["hits"] == []
    assert "降级" in r.value["reason"] or "bare" in r.value["reason"]


def test_brain_query_kinds_filter():
    """kinds 过滤:仅检索指定类(cases / rules / skills / neg_cases)。"""
    t = BrainQueryTool()
    r = asyncio.run(t.run({
        "brain": "antibacterial",
        "query": "antibiotic MIC",
        "top_k": 5,
        "kinds": ["rules"],
    }))
    assert r.ok
    # 命中(若有)必须全是 rules
    for h in r.value["hits"]:
        assert h["kind"] == "rules"


def test_brain_query_input_schema_complete():
    t = BrainQueryTool()
    schema = t.input_schema()
    assert schema["required"] == ["brain", "query"]
    assert "brain" in schema["properties"]
    assert "query" in schema["properties"]
    assert "top_k" in schema["properties"]


def test_brain_query_rmcp_op_is_none():
    """§7.3.7:检索类工具不受相位门约束(rmcp_op=None);否则 INIT 相位永远调不了
    BrainQuery(自相矛盾:retrieve 相位本来就是 retrieve_* op 的目标)。"""
    t = BrainQueryTool()
    assert t.rmcp_op is None


def test_brain_query_with_custom_brains_root(tmp_path: Path):
    """支持自定义 brains_root(单测/迁移场景)。"""
    # 构一个最小 brain 目录:brains_root/foo/memory/cases/c1.md
    root = tmp_path / "brains"
    cdir = root / "foo" / "memory" / "cases"
    cdir.mkdir(parents=True)
    (cdir / "c1.md").write_text("foo 学科:特定关键词 widget 测试", encoding="utf-8")

    t = BrainQueryTool(brains_root=root)
    r = asyncio.run(t.run({"brain": "foo", "query": "widget 测试", "top_k": 1}))
    assert r.ok
    assert len(r.value["hits"]) == 1
    assert r.value["hits"][0]["stem"] == "c1"
