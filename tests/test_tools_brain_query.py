from __future__ import annotations

import asyncio
from pathlib import Path

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.brain_query import BrainQueryTool


def test_brain_query_registered_in_chat_registry():

    sel_disc = resolve_agent("virtualcell", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "BrainQuery" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    names_gen = [t["name"] for t in reg_gen.anthropic_tools()]
    assert "BrainQuery" in names_gen


def test_brain_query_returns_hits_for_virtualcell_seed():

    t = BrainQueryTool()
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "query": "perturbation perturbation transcriptome \u9884\u6d4b Norman",
                "top_k": 3,
            }
        )
    )
    assert r.ok
    v = r.value
    assert v["brain"] == "virtualcell"
    assert v["degraded_to_bare"] is False
    assert len(v["hits"]) >= 1
    stems = [h["stem"] for h in v["hits"]]

    assert any("vcell" in s.lower() for s in stems), f"Expected the VirtualCell seed case; observed {stems}"
    top_hit = v["hits"][0]
    assert top_hit["kind"] in ("cases", "rules", "skills", "neg_cases")
    assert top_hit["excerpt"]


def test_brain_query_top_k_caps_hits():
    t = BrainQueryTool()
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "query": "\u9176 \u50ac\u5316 \u52a8\u529b\u5b66 \u6587\u732e",
                "top_k": 2,
            }
        )
    )
    assert r.ok
    assert len(r.value["hits"]) <= 2


def test_brain_query_unknown_brain_returns_error():
    t = BrainQueryTool()
    r = asyncio.run(
        t.run(
            {
                "brain": "this_brain_does_not_exist_xyz",
                "query": "anything",
            }
        )
    )
    assert not r.ok
    assert "Unknown brain" in (r.error or "") or "not found" in (r.error or "")


def test_brain_query_missing_required_returns_error():
    t = BrainQueryTool()
    r1 = asyncio.run(t.run({"query": "x"}))
    assert not r1.ok
    r2 = asyncio.run(t.run({"brain": "virtualcell"}))
    assert not r2.ok


def test_brain_query_no_overlap_degrades_to_bare_explicit():

    t = BrainQueryTool()
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "query": "\u5b8c\u5168\u65e0\u5173\u7684\u70f9\u996a\u98df\u8c31\u5185\u5bb9 zzzzzzz_no_overlap",
                "top_k": 3,
            }
        )
    )
    assert r.ok
    assert r.value["degraded_to_bare"] is True
    assert r.value["hits"] == []
    assert "Retrieval fallback" in r.value["reason"] or "bare" in r.value["reason"]


def test_brain_query_kinds_filter():

    t = BrainQueryTool()
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "query": "perturbation cross-species benchmark",
                "top_k": 5,
                "kinds": ["rules"],
            }
        )
    )
    assert r.ok

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

    t = BrainQueryTool()
    assert t.rmcp_op is None


def test_brain_query_with_custom_brains_root(tmp_path: Path):

    root = tmp_path / "brains"
    cdir = root / "foo" / "memory" / "cases"
    cdir.mkdir(parents=True)
    (cdir / "c1.md").write_text("foo \u5b66\u79d1:\u7279\u5b9a\u5173\u952e\u8bcd widget \u6d4b\u8bd5", encoding="utf-8")

    t = BrainQueryTool(brains_root=root)
    r = asyncio.run(t.run({"brain": "foo", "query": "widget \u6d4b\u8bd5", "top_k": 1}))
    assert r.ok
    assert len(r.value["hits"]) == 1
    assert r.value["hits"][0]["stem"] == "c1"
