import asyncio
from pathlib import Path

from praxis2.tools.bash import BashTool


def _run(tool, payload):
    return asyncio.run(tool.run(payload))


def test_echo_in_sandbox(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "echo hello"})
    assert r.ok
    assert r.value["stdout"].strip() == "hello"
    assert r.value["exit_code"] == 0
    assert r.value["duration_ms"] >= 0


def test_nonzero_exit_still_ok(tmp_path: Path):

    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "sh -c 'exit 3'"})
    assert r.ok
    assert r.value["exit_code"] == 3


def test_cwd_default_is_sandbox(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "pwd"})
    assert r.ok
    assert str(tmp_path.resolve()) in r.value["stdout"]


def test_cwd_subdir_ok(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "pwd", "cwd": "sub"})
    assert r.ok
    assert "sub" in r.value["stdout"]


def test_cwd_escape_rejected(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "pwd", "cwd": "../../etc"})
    assert not r.ok
    err = r.error or ""
    assert "\u6c99\u76d2" in err or "\u8d8a\u6743" in err or "escape" in err.lower()


def test_timeout_kills(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "sleep 5", "timeout_s": 1})
    assert not r.ok
    assert "timed out" in (r.error or "") or "timeout" in (r.error or "").lower()


def test_timeout_kills_shell_children(tmp_path: Path):

    import time as _time

    sentinel = tmp_path / "survived"
    t = BashTool(sandbox_root=tmp_path, default_timeout_s=1)
    r = _run(t, {"command": "(sleep 2; touch survived) & wait"})
    assert not r.ok
    _time.sleep(2.0)
    assert not sentinel.exists()


def test_timeout_includes_wait_after_pipes_close(tmp_path: Path):

    import time as _time

    t = BashTool(sandbox_root=tmp_path, default_timeout_s=1)
    t0 = _time.monotonic()
    r = _run(t, {"command": "exec >/dev/null 2>&1; sleep 5 & wait"})
    dt = _time.monotonic() - t0
    assert not r.ok
    assert "timed out" in (r.error or "") or "timeout" in (r.error or "").lower()
    assert dt < 2, f"proc.wait after EOF must respect the one-second deadline; observed {dt:.1f}s"


def test_cancellation_kills_process_group_after_pipes_close(tmp_path: Path):

    sentinel = tmp_path / "survived-cancel"
    t = BashTool(sandbox_root=tmp_path, default_timeout_s=10)

    async def _cancel() -> None:
        task = asyncio.create_task(
            t.run(
                {
                    "command": "exec >/dev/null 2>&1; (sleep 1; touch survived-cancel) & wait",
                }
            )
        )
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("BashTool.run \u5e94\u4f20\u64ad\u8c03\u7528\u65b9\u7684 CancelledError")
        await asyncio.sleep(1.25)

    asyncio.run(_cancel())
    assert not sentinel.exists()


def test_output_truncated(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path, max_output_bytes=100)
    r = _run(t, {"command": "for i in $(seq 1 1000); do echo line$i; done"})
    assert r.ok
    assert r.value["truncated"] is True
    assert len(r.value["stdout"]) <= 200


def test_missing_command(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {})
    assert not r.ok


def test_sandbox_root_auto_created(tmp_path: Path):
    root = tmp_path / "newroot"
    assert not root.exists()
    t = BashTool(sandbox_root=root)
    r = _run(t, {"command": "pwd"})
    assert r.ok
    assert root.exists()


def test_rmcp_op_none(tmp_path: Path):
    assert BashTool(sandbox_root=tmp_path).rmcp_op is None


def test_input_schema(tmp_path: Path):
    s = BashTool(sandbox_root=tmp_path).input_schema()
    assert s["required"] == ["command"]
    assert "command" in s["properties"]
    assert "cwd" in s["properties"]
    assert "timeout_s" in s["properties"]


def test_timeout_clamped(tmp_path: Path):

    t = BashTool(sandbox_root=tmp_path, max_timeout_s=5.0)
    r = _run(t, {"command": "echo ok", "timeout_s": 9999})
    assert r.ok


def test_huge_output_capped_not_ooming(tmp_path: Path):

    import time as _time

    t = BashTool(sandbox_root=tmp_path, max_output_bytes=1000, default_timeout_s=10)
    t0 = _time.monotonic()
    # `& wait` guarantees a shell child on macOS and Linux; killing only the
    # direct shell would leave cat holding the pipes and make this time out.
    r = _run(t, {"command": "cat /dev/zero & wait"})
    dt = _time.monotonic() - t0
    assert r.ok, f"Expected early termination with ok=True; error={r.error}"
    assert r.value["truncated"] is True
    assert len(r.value["stdout"]) <= 1300, (
        f"Buffer must be bounded by max plus one chunk; observed {len(r.value['stdout'])}"
    )
    assert dt < 5, f"Expected termination after 1000 bytes before the timeout; observed {dt:.1f}s"


def test_drain_exception_returns_ok_false_not_raise(tmp_path: Path, monkeypatch):

    import asyncio as _aio
    import time as _time

    from praxis2.tools import bash as bash_mod

    real_create = _aio.create_subprocess_shell

    async def _patched(*a, **kw):
        proc = await real_create(*a, **kw)

        async def _boom(*_a, **_kw):
            raise RuntimeError("simulated pipe error")

        proc.stdout.read = _boom
        return proc

    monkeypatch.setattr(bash_mod.asyncio, "create_subprocess_shell", _patched)
    t = BashTool(sandbox_root=tmp_path, default_timeout_s=10)
    t0 = _time.monotonic()
    r = _run(t, {"command": "sleep 5"})
    dt = _time.monotonic() - t0
    assert not r.ok
    assert "\u8bfb\u53d6\u547d\u4ee4\u8f93\u51fa\u5931\u8d25" in (r.error or "") or "RuntimeError" in (r.error or "")
    assert dt < 2, f"A failed drain must terminate the group before the other stream EOF; observed {dt:.1f}s"


def test_subprocess_env_sanitized(tmp_path: Path, monkeypatch):

    monkeypatch.setenv("PRAXIS_FAKE_SECRET", "leak-me-123")
    monkeypatch.setenv("MY_API_KEY", "key-456")
    monkeypatch.setenv("HARMLESS_VAR", "ok-789")
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "env"})
    assert r.ok
    out = r.value["stdout"]
    assert "leak-me-123" not in out, "PRAXIS_ \u673a\u5bc6\u5e94\u88ab\u88c1\u526a"
    assert "key-456" not in out, "*KEY \u673a\u5bc6\u5e94\u88ab\u88c1\u526a"
    assert "HARMLESS_VAR" in out or "ok-789" in out, "\u975e\u673a\u5bc6\u5e94\u4fdd\u7559"

    assert "PATH" in out


def test_timeout_s_non_numeric_returns_recovery_hint(tmp_path: Path):

    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "echo hi", "timeout_s": "abc"})
    assert r.ok is False
    assert "timeout_s" in (r.error or "")
    assert r.recovery_hint
    assert "120" in r.recovery_hint
