import asyncio

from praxis2.tools import bash as bashmod


def test_netns_available_true(monkeypatch):
    class _R:
        returncode = 0

    monkeypatch.setattr(bashmod.subprocess, "run", lambda *a, **k: _R())
    bashmod.netns_available.cache_clear()
    assert bashmod.netns_available() is True


def test_netns_available_false(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no unshare")

    monkeypatch.setattr(bashmod.subprocess, "run", _boom)
    bashmod.netns_available.cache_clear()
    assert bashmod.netns_available() is False


def test_netns_argv_structure():
    argv = bashmod._netns_argv(command="echo hi")
    assert argv[:5] == ["unshare", "--user", "--map-root-user", "--net", "--"]
    assert argv[-3:] == ["/bin/bash", "-c", "echo hi"]


def test_isolation_argv_netns_on_has_net():
    argv = bashmod._isolation_argv(
        command="echo hi",
        sandbox="/s",
        files_root="/f",
        mask="",
        cwd="/s",
        netns=True,
    )
    assert "--net" in argv
    assert "--mount" in argv


def test_isolation_argv_netns_off_no_net():
    argv = bashmod._isolation_argv(
        command="echo hi",
        sandbox="/s",
        files_root="/f",
        mask="",
        cwd="/s",
    )
    assert "--net" not in argv
    assert "--mount" in argv


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


def test_all_off_uses_shell(tmp_path, monkeypatch):
    cap = _capture_shell(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path), {"command": "echo hi"})
    assert cap["cmd"] == "echo hi"


def test_netns_only_uses_exec_with_net(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, netns=True), {"command": "echo hi"})
    assert cap["argv"][0] == "unshare"
    assert "--net" in cap["argv"]
    assert "--mount" not in cap["argv"]
    assert cap["argv"][-3:] == ["/bin/bash", "-c", "echo hi"]
    assert cap["kw"].get("cwd") == str(tmp_path.resolve())


def test_netns_with_isolation_has_mount_and_net(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, isolation=True, netns=True), {"command": "echo hi"})
    assert cap["argv"][0] == "unshare"
    assert "--mount" in cap["argv"] and "--net" in cap["argv"]
    assert "cwd" not in cap["kw"]


def test_netns_with_cgroup_wraps_unshare(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, cgroup=True, netns=True), {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"
    assert "unshare" in cap["argv"] and "--net" in cap["argv"]
    assert cap["kw"].get("cwd") == str(tmp_path.resolve())


def test_netns_all_three_on(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    _run(bashmod.BashTool(sandbox_root=tmp_path, isolation=True, cgroup=True, netns=True), {"command": "echo hi"})
    assert cap["argv"][0] == "systemd-run"
    assert "unshare" in cap["argv"]
    assert "--mount" in cap["argv"] and "--net" in cap["argv"]


def test_netns_injection_safe(tmp_path, monkeypatch):
    cap = _capture_exec(monkeypatch)
    evil = 'x"; rm -rf /; "'
    _run(bashmod.BashTool(sandbox_root=tmp_path, netns=True), {"command": evil})
    assert cap["argv"][-1] == evil
