"""FileReadTool 单测(v0.16.0-beta P0 3/5)。

回归:此前模型在 chat 里想"看看 brains/<slug>/skills/workflows/<name>/SKILL.md
怎么写的"只能问用户复制粘贴 — 没有工具能读 repo 内文件(SkillExec 只调
skill,BrainQuery 只返摘录)。本工具补"读 repo 内安全路径"这一缝。

沙盒(v0.16.0-beta 第一版):仅 repo 内 brains/ + docs/ 路径,绝对路径
转相对,黑名单(.git/.venv/__pycache__/node_modules)。后续 v0.18 跨会话
记忆时一起接入 user storage。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.file_read import FileReadTool


def test_file_read_registered_in_chat_registry():
    sel_disc = resolve_agent("enzyme", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "FileRead" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    assert "FileRead" in [t["name"] for t in reg_gen.anthropic_tools()]


def test_file_read_brains_index_real_file():
    """e2e 真盘:读 brains/INDEX.md 应成功(repo 内,在沙盒白名单)。"""
    t = FileReadTool()
    r = asyncio.run(t.run({"path": "brains/INDEX.md"}))
    assert r.ok
    v = r.value
    assert v["path"] == "brains/INDEX.md"
    assert v["size_bytes"] > 0
    assert v["content"]
    assert v["truncated"] in (True, False)


def test_file_read_size_cap_truncates(tmp_path: Path):
    """大文件应被截断到 max_chars,truncated=True。"""
    root = tmp_path / "repo"
    (root / "brains").mkdir(parents=True)
    big = root / "brains" / "big.md"
    big.write_text("x" * 20000, encoding="utf-8")

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/big.md", "max_chars": 1000}))
    assert r.ok
    assert r.value["truncated"] is True
    assert len(r.value["content"]) <= 1000 + 200  # 含截断标记


def test_file_read_rejects_escape_outside_repo(tmp_path: Path):
    """../ 越权 → 拒绝。"""
    root = tmp_path / "repo"
    (root / "brains").mkdir(parents=True)
    (root / "brains" / "ok.md").write_text("safe", encoding="utf-8")
    # tmp_path 同级建一个 secret(模拟越权目标)
    secret = tmp_path / "secret.txt"
    secret.write_text("LEAK", encoding="utf-8")

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "../secret.txt"}))
    assert not r.ok
    assert "越权" in (r.error or "") or "沙盒" in (r.error or "") or "escape" in (r.error or "").lower()


def test_file_read_rejects_outside_whitelist(tmp_path: Path):
    """非白名单顶层目录(如 praxis2/auth/routes.py)→ 拒绝。"""
    root = tmp_path / "repo"
    (root / "praxis2" / "auth").mkdir(parents=True)
    (root / "praxis2" / "auth" / "routes.py").write_text("API_KEY=secret", encoding="utf-8")
    (root / "brains").mkdir()

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "praxis2/auth/routes.py"}))
    assert not r.ok
    assert "白名单" in (r.error or "") or "allowed" in (r.error or "").lower()


def test_file_read_rejects_blacklist_dirs(tmp_path: Path):
    """黑名单目录(.git/.venv/__pycache__)→ 拒绝(即使在 brains/ 内)。"""
    root = tmp_path / "repo"
    bad = root / "brains" / "__pycache__"
    bad.mkdir(parents=True)
    (bad / "compiled.pyc").write_text("BIN", encoding="utf-8")

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/__pycache__/compiled.pyc"}))
    assert not r.ok
    assert "黑名单" in (r.error or "") or "blacklist" in (r.error or "").lower()


def test_file_read_nonexistent_returns_error(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "brains").mkdir(parents=True)
    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/does_not_exist.md"}))
    assert not r.ok
    assert "不存在" in (r.error or "") or "not found" in (r.error or "").lower()


def test_file_read_rejects_directory(tmp_path: Path):
    """读目录(非文件)→ 拒绝。"""
    root = tmp_path / "repo"
    (root / "brains" / "enzyme").mkdir(parents=True)
    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/enzyme"}))
    assert not r.ok
    assert "目录" in (r.error or "") or "directory" in (r.error or "").lower()


def test_file_read_input_schema_complete():
    t = FileReadTool()
    s = t.input_schema()
    assert s["required"] == ["path"]
    assert "path" in s["properties"]
    assert "max_chars" in s["properties"]


def test_file_read_rmcp_op_is_none():
    """读类工具不受相位门(BrainQuery 同理)。"""
    assert FileReadTool().rmcp_op is None


def test_file_read_missing_path_returns_error():
    t = FileReadTool()
    r = asyncio.run(t.run({}))
    assert not r.ok
