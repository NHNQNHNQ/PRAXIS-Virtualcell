import asyncio

from praxis2.tools import bash as bashmod


def test_scope_available_true(monkeypatch):
    class _R:
        returncode = 0

    monkeypatch.setattr(bashmod.subprocess, "run", lambda *a, **k: _R())
    bashmod.scope_available.cache_clear()
    assert bashmod.scope_available() is True


def test_scope_available_false(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no systemd-run")

    monkeypatch.setattr(bashmod.subprocess, "run", _boom)
    bashmod.scope_available.cache_clear()
    assert bashmod.scope_available() is False


def test_cgroup_argv_structure():
    argv = bashmod._cgroup_argv(mem_mb=512, cpu_pct=200)
    assert argv[:4] == ["systemd-run", "--user", "--scope", "--quiet"]
    assert "MemoryMax=512M" in argv
    assert "CPUQuota=200%" in argv
    assert argv[-1] == "--"


def _run(tool, payload):
    return asyncio.run(tool.run(payload))


def _capture_exec(monkeypatch):
    cap = {}

    async def fake_exec(*argv, **kw):
        cap["argv"] = list(argv)
        cap["kw"] = kw
        raise RuntimeError("stop")

    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_exec", fake_exec)
    return cap


def _capture_shell(monkeypatch):
    cap = {}

    async def fake_shell(cmd, **kw):
        cap["cmd"] = cmd
        cap["kw"] = kw
        raise RuntimeError("stop")

    monkeypatch.setattr(bashmod.asyncio, "create_subprocess_shell", fake_shell)
    return cap


def test_off_off_uses_shell(tmp_path, monkeypatch):
    cap = _capture_shell(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path), {"command": "echo hi"})
    assert cap["cmd"] == "echo hi"


def test_cgroup_on_isolation_off(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(
        bashmod.BashTool(sandbox_root=tmp_path, cgroup=True, cgroup_mem_mb=256, cgroup_cpu_pct=100),
        {"command": "echo hi"},
    )
    assert cap["argv"][0] == "systemd-run"
    assert "MemoryMax=256M" in cap["argv"]
    assert cap["argv"][-3:] == ["/bin/bash", "-c", "echo hi"]  # inner = bash -c command
    assert cap["kw"].get("cwd") == str(tmp_path.resolve())


def test_cgroup_on_isolation_on(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True, isolation=True), {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"
    assert "unshare" in cap["argv"]
    assert "cwd" not in cap["kw"]


def test_cgroup_injection_safe(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    evil = 'x"; rm -rf /; "'
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True), {"command": evil})
    assert cap["argv"][-1] == evil


def test_isolation_on_cgroup_off_uses_exec(tmp_path, monkeypatch):

    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, isolation=True), {"command": "echo hi"})
    assert cap["argv"][0] == "unshare"
    assert "systemd-run" not in cap["argv"]
    assert "cwd" not in cap["kw"]
