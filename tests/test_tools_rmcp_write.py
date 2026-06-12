"""RMCPWriteCaseTool 单测(v0.16.0 P0)。

回归:rmcp.py 的 ALLOWED_OPS[SEAL] 声明了 write_case op,但没有 Tool 子类
实体——模型在 SEAL 相位"想要落 case"时没有工具可调,只能纯文字描述
"应该把这个 case 存起来"(幻觉)。本工具补这一缝。

第一版:case 写到 brains/<slug>/memory/cases/_proposed/<stem>.md(等审核
inbox 形式),不直接动 store DB。后续 review 流(memory/review.py)可以
approve 后再 put_brain_doc 灌入真位置。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.rmcp_write import RMCPWriteCaseTool


def test_rmcp_write_case_registered_in_chat_registry():
    """所有模式都应注册 RMCPWriteCase(SEAL 相位的核心 op)。"""
    sel_disc = resolve_agent("virtualcell", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "RMCPWriteCase" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    names_gen = [t["name"] for t in reg_gen.anthropic_tools()]
    assert "RMCPWriteCase" in names_gen


def test_rmcp_write_case_persists_to_proposed_inbox(tmp_path: Path):
    """happy path:调 run() → 写入 brains/<slug>/memory/cases/_proposed/<stem>.md。"""
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(t.run({
        "brain": "virtualcell",
        "title": "TEM-1 β-lactamase 进化性 deep mutational scanning",
        "summary": "Stiffler 2015 在 TEM-1 β-lactamase 上做 DMS,发现纯化选择下的进化性...",
        "evidence": [
            {"doi": "10.1016/j.cell.2015.01.035",
             "citation": "Stiffler MA, et al. (2015). Cell 160(5):882-892."}
        ],
    }))
    assert r.ok
    v = r.value
    written = Path(v["written_path"])
    assert written.is_file()
    assert written.parent.name == "_proposed"
    assert written.parent.parent.name == "cases"
    assert written.parent.parent.parent.name == "memory"
    assert written.parent.parent.parent.parent.name == "virtualcell"
    # 文件内容含 frontmatter + body
    text = written.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "doi: \"10.1016/j.cell.2015.01.035\"" in text or "doi: 10.1016/j.cell.2015.01.035" in text
    assert "Stiffler 2015" in text


def test_rmcp_write_case_requires_doi(tmp_path: Path):
    """§安全规则:不杜撰 DOI/引用。evidence 必须含至少 1 个 doi(否则拒)。"""
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(t.run({
        "brain": "virtualcell",
        "title": "无来源",
        "summary": "凭空",
        "evidence": [],
    }))
    assert not r.ok
    assert "doi" in (r.error or "").lower() or "DOI" in (r.error or "")


def test_rmcp_write_case_unknown_brain_rejected(tmp_path: Path):
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(t.run({
        "brain": "this_brain_does_not_exist",
        "title": "x",
        "summary": "y",
        "evidence": [{"doi": "10.0/test"}],
    }))
    assert not r.ok
    assert "未知 brain" in (r.error or "") or "未找到" in (r.error or "")


def test_rmcp_write_case_idempotent_same_title_overwrites(tmp_path: Path):
    """同 brain + 同 title → 同 stem → 后写覆盖前写(便于模型迭代)。"""
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
    # 第二次同 title 不同 summary
    payload2 = dict(payload, summary="v2 summary updated")
    r2 = asyncio.run(t.run(payload2))
    assert r2.ok
    p2 = Path(r2.value["written_path"])
    assert p1 == p2
    assert "v2 summary updated" in p2.read_text()
    assert "v1 summary" not in p2.read_text()


def test_rmcp_write_case_missing_required_returns_error(tmp_path: Path):
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    # 缺 brain
    r = asyncio.run(t.run({"title": "x", "summary": "y",
                          "evidence": [{"doi": "10.0/a"}]}))
    assert not r.ok
    # 缺 title
    r = asyncio.run(t.run({"brain": "virtualcell", "summary": "y",
                          "evidence": [{"doi": "10.0/a"}]}))
    assert not r.ok
    # 缺 summary
    r = asyncio.run(t.run({"brain": "virtualcell", "title": "x",
                          "evidence": [{"doi": "10.0/a"}]}))
    assert not r.ok


def test_rmcp_write_case_rmcp_op_is_write_case(tmp_path: Path):
    """§7.3.7:写/执行类工具必须显式声明 rmcp_op,防相位门静默绕过。
    write_case 属 SEAL 相位白名单(rmcp.py:43-45)。"""
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    assert t.rmcp_op == "write_case"


def test_rmcp_write_case_input_schema_complete(tmp_path: Path):
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    schema = t.input_schema()
    assert set(schema["required"]) == {"brain", "title", "summary", "evidence"}
    for k in ("brain", "title", "summary", "evidence"):
        assert k in schema["properties"]


def test_rmcp_write_case_stem_safe_for_filesystem(tmp_path: Path):
    """title 含空格 / 中文 / 路径分隔符 / 不安全字符 → stem 安全化。"""
    t = RMCPWriteCaseTool(brains_root=tmp_path)
    r = asyncio.run(t.run({
        "brain": "virtualcell",
        "title": "TEM-1 / β-lactamase: deep mutational scanning ★ 2015",
        "summary": "x",
        "evidence": [{"doi": "10.0/a"}],
    }))
    assert r.ok
    p = Path(r.value["written_path"])
    # 文件名不含 / : * 等
    assert "/" not in p.name
    assert ":" not in p.name
    assert "★" not in p.name
    assert p.is_file()
