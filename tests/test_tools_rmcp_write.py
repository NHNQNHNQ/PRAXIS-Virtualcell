from __future__ import annotations

import asyncio
from pathlib import Path

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.rmcp_write import RMCPWriteCaseTool


def test_rmcp_write_case_registered_in_chat_registry():

    sel_disc = resolve_agent("virtualcell", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "RMCPWriteCase" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    names_gen = [t["name"] for t in reg_gen.anthropic_tools()]
    assert "RMCPWriteCase" in names_gen


def test_rmcp_write_case_persists_to_proposed_inbox(tmp_path: Path):

    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "title": "TEM-1 \u03b2-lactamase \u8fdb\u5316\u6027 deep mutational scanning",
                "summary": (
                    "Stiffler 2015 \u5728 TEM-1 \u03b2-lactamase \u4e0a\u505a DMS,"
                    "\u53d1\u73b0\u7eaf\u5316\u9009\u62e9\u4e0b\u7684\u8fdb\u5316"
                    "\u6027..."
                ),
                "evidence": [
                    {
                        "doi": "10.1016/j.cell.2015.01.035",
                        "citation": "Stiffler MA, et al. (2015). Cell 160(5):882-892.",
                    }
                ],
            }
        )
    )
    assert r.ok
    v = r.value
    written = Path(v["written_path"])
    assert written.is_file()
    assert written.parent.name == "_proposed"
    assert written.parent.parent.name == "cases"
    assert written.parent.parent.parent.name == "memory"
    assert written.parent.parent.parent.parent.name == "virtualcell"

    text = written.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert 'doi: "10.1016/j.cell.2015.01.035"' in text or "doi: 10.1016/j.cell.2015.01.035" in text
    assert "Stiffler 2015" in text


def test_rmcp_write_case_requires_doi(tmp_path: Path):

    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "title": "\u65e0\u6765\u6e90",
                "summary": "\u51ed\u7a7a",
                "evidence": [],
            }
        )
    )
    assert not r.ok
    assert "doi" in (r.error or "").lower() or "DOI" in (r.error or "")


def test_rmcp_write_case_unknown_brain_rejected(tmp_path: Path):
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(
        t.run(
            {
                "brain": "this_brain_does_not_exist",
                "title": "x",
                "summary": "y",
                "evidence": [{"doi": "10.0/test"}],
            }
        )
    )
    assert not r.ok
    assert "Unknown brain" in (r.error or "") or "not found" in (r.error or "")


def test_rmcp_write_case_idempotent_same_title_overwrites(tmp_path: Path):

    t = RMCPWriteCaseTool(brains_root=tmp_path)
    payload = {
        "brain": "virtualcell",
        "title": "TEM-1 DMS evolvability",
        "summary": "v1 summary",
        "evidence": [{"doi": "10.0/a"}],
    }
    r1 = asyncio.run(t.run(payload))
    assert r1.ok
    p1 = Path(r1.value["written_path"])
    assert "v1 summary" in p1.read_text()

    payload2 = dict(payload, summary="v2 summary updated")
    r2 = asyncio.run(t.run(payload2))
    assert r2.ok
    p2 = Path(r2.value["written_path"])
    assert p1 == p2
    assert "v2 summary updated" in p2.read_text()
    assert "v1 summary" not in p2.read_text()


def test_rmcp_write_case_missing_required_returns_error(tmp_path: Path):
    t = RMCPWriteCaseTool(brains_root=tmp_path)

    r = asyncio.run(t.run({"title": "x", "summary": "y", "evidence": [{"doi": "10.0/a"}]}))
    assert not r.ok

    r = asyncio.run(t.run({"brain": "virtualcell", "summary": "y", "evidence": [{"doi": "10.0/a"}]}))
    assert not r.ok

    r = asyncio.run(t.run({"brain": "virtualcell", "title": "x", "evidence": [{"doi": "10.0/a"}]}))
    assert not r.ok


def test_rmcp_write_case_rmcp_op_is_write_case(tmp_path: Path):

    t = RMCPWriteCaseTool(brains_root=tmp_path)
    assert t.rmcp_op == "write_case"


def test_rmcp_write_case_input_schema_complete(tmp_path: Path):
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    schema = t.input_schema()
    assert set(schema["required"]) == {"brain", "title", "summary", "evidence"}
    for k in ("brain", "title", "summary", "evidence"):
        assert k in schema["properties"]


def test_rmcp_write_case_stem_safe_for_filesystem(tmp_path: Path):

    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(
        t.run(
            {
                "brain": "virtualcell",
                "title": "TEM-1 / β-lactamase: deep mutational scanning ★ 2015",
                "summary": "x",
                "evidence": [{"doi": "10.0/a"}],
            }
        )
    )
    assert r.ok
    p = Path(r.value["written_path"])

    assert "/" not in p.name
    assert ":" not in p.name
    assert "★" not in p.name
    assert p.is_file()
