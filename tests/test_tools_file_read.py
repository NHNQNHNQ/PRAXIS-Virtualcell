from __future__ import annotations

import asyncio
from pathlib import Path

from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.file_read import FileReadTool


def test_file_read_registered_in_chat_registry():
    sel_disc = resolve_agent("virtualcell", user_query="hi")
    reg_disc = build_chat_registry(selection=sel_disc)
    names = [t["name"] for t in reg_disc.anthropic_tools()]
    assert "FileRead" in names

    sel_gen = resolve_agent("general", user_query="hi")
    reg_gen = build_chat_registry(selection=sel_gen)
    assert "FileRead" in [t["name"] for t in reg_gen.anthropic_tools()]


def test_file_read_brains_index_real_file():

    t = FileReadTool()
    r = asyncio.run(t.run({"path": "brains/INDEX.md"}))
    assert r.ok
    v = r.value
    assert v["path"] == "brains/INDEX.md"
    assert v["size_bytes"] > 0
    assert v["content"]
    assert v["truncated"] in (True, False)


def test_file_read_size_cap_truncates(tmp_path: Path):

    root = tmp_path / "repo"
    (root / "brains").mkdir(parents=True)
    big = root / "brains" / "big.md"
    big.write_text("x" * 20000, encoding="utf-8")

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/big.md", "max_chars": 1000}))
    assert r.ok
    assert r.value["truncated"] is True
    assert len(r.value["content"]) <= 1000 + 200


def test_file_read_rejects_escape_outside_repo(tmp_path: Path):

    root = tmp_path / "repo"
    (root / "brains").mkdir(parents=True)
    (root / "brains" / "ok.md").write_text("safe", encoding="utf-8")

    secret = tmp_path / "secret.txt"
    secret.write_text("LEAK", encoding="utf-8")

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "../secret.txt"}))
    assert not r.ok
    assert "\u8d8a\u6743" in (r.error or "") or "\u6c99\u76d2" in (r.error or "") or "escape" in (r.error or "").lower()


def test_file_read_rejects_outside_whitelist(tmp_path: Path):

    root = tmp_path / "repo"
    (root / "praxis2" / "auth").mkdir(parents=True)
    (root / "praxis2" / "auth" / "routes.py").write_text("API_KEY=secret", encoding="utf-8")
    (root / "brains").mkdir()

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "praxis2/auth/routes.py"}))
    assert not r.ok
    assert "allowlisted" in (r.error or "") or "allowed" in (r.error or "").lower()


def test_file_read_rejects_blacklist_dirs(tmp_path: Path):

    root = tmp_path / "repo"
    bad = root / "brains" / "__pycache__"
    bad.mkdir(parents=True)
    (bad / "compiled.pyc").write_text("BIN", encoding="utf-8")

    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/__pycache__/compiled.pyc"}))
    assert not r.ok
    assert "\u9ed1\u540d\u5355" in (r.error or "") or "blacklist" in (r.error or "").lower()


def test_file_read_nonexistent_returns_error(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "brains").mkdir(parents=True)
    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/does_not_exist.md"}))
    assert not r.ok
    assert "\u4e0d\u5b58\u5728" in (r.error or "") or "not found" in (r.error or "").lower()


def test_file_read_rejects_directory(tmp_path: Path):

    root = tmp_path / "repo"
    (root / "brains" / "enzyme").mkdir(parents=True)
    t = FileReadTool(repo_root=root)
    r = asyncio.run(t.run({"path": "brains/enzyme"}))
    assert not r.ok
    assert "\u76ee\u5f55" in (r.error or "") or "directory" in (r.error or "").lower()


def test_file_read_input_schema_complete():
    t = FileReadTool()
    s = t.input_schema()
    assert s["required"] == ["path"]
    assert "path" in s["properties"]
    assert "max_chars" in s["properties"]


def test_file_read_rmcp_op_is_none():

    assert FileReadTool().rmcp_op is None


def test_file_read_missing_path_returns_error():
    t = FileReadTool()
    r = asyncio.run(t.run({}))
    assert not r.ok
