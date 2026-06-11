"""BashTool 文件系统真隔离(unshare userns)单测(v0.18 子项目1)。"""
import asyncio
from pathlib import Path

import pytest

from praxis2.tools import bash as bashmod


def test_userns_available_true_when_unshare_succeeds(monkeypatch):
    """unshare 探测 returncode=0 → 可用。"""
    class _R:
        returncode = 0

    monkeypatch.setattr(bashmod.subprocess, "run", lambda *a, **k: _R())
    bashmod.userns_available.cache_clear()
    assert bashmod.userns_available() is True


def test_userns_available_false_when_unshare_fails(monkeypatch):
    """unshare 探测非 0 / 抛异常 → 不可用。"""
    def _boom(*a, **k):
        raise OSError("no unshare")

    monkeypatch.setattr(bashmod.subprocess, "run", _boom)
    bashmod.userns_available.cache_clear()
    assert bashmod.userns_available() is False


def test_mask_paths_default_expands_home(monkeypatch):
    monkeypatch.setenv("HOME", "/home/tester")
    paths = bashmod._mask_paths("")
    assert "/home/tester/praxis2.env" in paths
    assert "/home/tester/.ssh" in paths


def test_mask_paths_appends_extra():
    paths = bashmod._mask_paths("/data/x,/data/y")
    assert "/data/x" in paths
    assert "/data/y" in paths


def test_isolation_argv_structure():
    argv = bashmod._isolation_argv(
        command="echo hi",
        sandbox="/fr/u1",
        files_root="/fr",
        mask="/home/t/.ssh\n/home/t/praxis2.env",
        cwd="/fr/u1/sub",
    )
    assert argv[:5] == ["unshare", "--user", "--map-root-user", "--mount", "--"]
    assert argv[5:8] == ["/bin/sh", "-c", bashmod.SETUP_TEMPLATE]
    # 位置参数:$0 名 + $1 sandbox / $2 files_root / $3 command / $4 mask / $5 cwd
    assert argv[8] == "praxis-bash"
    assert argv[9] == "/fr/u1"
    assert argv[10] == "/fr"
    assert argv[11] == "echo hi"
    assert argv[12] == "/home/t/.ssh\n/home/t/praxis2.env"
    assert argv[13] == "/fr/u1/sub"


def test_isolation_argv_command_injection_safe():
    """恶意 command 只是 $3 的值,不破坏 SETUP 脚本结构。"""
    evil = 'x"; rm -rf /; "'
    argv = bashmod._isolation_argv(
        command=evil, sandbox="/fr/u1", files_root="/fr", mask="", cwd="/fr/u1",
    )
    assert argv[11] == evil  # 原样作为位置参数,SETUP_TEMPLATE 不含它
    assert evil not in bashmod.SETUP_TEMPLATE


def test_mask_paths_no_empty_lines():
    """空 extra 不产生空行(p.strip() 过滤)。"""
    paths = bashmod._mask_paths("")
    assert "" not in paths.split("\n")


def _run(tool, payload):
    return asyncio.run(tool.run(payload))


def test_isolation_off_uses_shell(tmp_path, monkeypatch):
    """isolation off(默认)→ create_subprocess_shell,零回归。"""
    captured = {}

    async def fake_shell(cmd, **kw):
        captured["mode"] = "shell"
        captured["cmd"] = cmd
        raise RuntimeError("stop-after-capture")

    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_shell", fake_shell)
    t = bashmod.BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "echo hi"})
    assert captured["mode"] == "shell"
    assert captured["cmd"] == "echo hi"
    assert r.ok is False  # spawn 失败兜底(stop-after-capture)


def test_isolation_on_uses_exec_unshare(tmp_path, monkeypatch):
    """isolation on → create_subprocess_exec("unshare", ...)。"""
    captured = {}

    async def fake_exec(*argv, **kw):
        captured["argv"] = list(argv)
        raise RuntimeError("stop-after-capture")

    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_exec", fake_exec)
    t = bashmod.BashTool(sandbox_root=tmp_path, isolation=True)
    r = _run(t, {"command": "echo hi"})
    assert captured["argv"][0] == "unshare"
    assert "--map-root-user" in captured["argv"]
    assert captured["argv"][11] == "echo hi"  # 位置 11 = $3 command(防参数顺序变静默失效)
    assert r.ok is False
