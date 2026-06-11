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
    """命令跑完即 ok=True,exit_code 非零在 value(模型自判)。"""
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
    assert "沙盒" in err or "越权" in err or "escape" in err.lower()


def test_timeout_kills(tmp_path: Path):
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "sleep 5", "timeout_s": 1})
    assert not r.ok
    assert "超时" in (r.error or "") or "timeout" in (r.error or "").lower()


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
    """timeout_s 超上限被 clamp(不抛)。"""
    t = BashTool(sandbox_root=tmp_path, max_timeout_s=5.0)
    r = _run(t, {"command": "echo ok", "timeout_s": 9999})
    assert r.ok


def test_huge_output_capped_not_ooming(tmp_path: Path):
    """I-1 回归:无限输出命令(cat /dev/zero)被流式 drain 读够即停 + kill,
    buffer 有界(不读完无限流),truncated=True,且早停远快于 timeout(不是卡到超时)。"""
    import time as _time
    t = BashTool(sandbox_root=tmp_path, max_output_bytes=1000, default_timeout_s=10)
    t0 = _time.monotonic()
    r = _run(t, {"command": "cat /dev/zero"})  # 无限输出
    dt = _time.monotonic() - t0
    assert r.ok, f"应早停 + kill 返回 ok=True,得到 error={r.error}"
    assert r.value["truncated"] is True
    assert len(r.value["stdout"]) <= 1300, f"buffer 应有界(~max+chunk),得到 {len(r.value['stdout'])}"
    assert dt < 5, f"应早停(读够 1000 字节即 kill),不应卡到 10s timeout,实际 {dt:.1f}s"


def test_drain_exception_returns_ok_false_not_raise(tmp_path: Path, monkeypatch):
    """I-1 回归:drain 内 stream.read 抛非超时异常 → ok=False 兜底,不裸冒泡(防 500),
    且无 task 泄漏 / 进程僵尸。"""
    import asyncio as _aio
    from praxis2.tools import bash as bash_mod

    real_create = _aio.create_subprocess_shell

    async def _patched(*a, **kw):
        proc = await real_create(*a, **kw)
        # 让 stdout.read 抛 RuntimeError(模拟管道损坏)
        async def _boom(*_a, **_kw):
            raise RuntimeError("simulated pipe error")
        proc.stdout.read = _boom
        return proc

    monkeypatch.setattr(bash_mod.asyncio, "create_subprocess_shell", _patched)
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "echo hi"})
    assert not r.ok  # 不冒泡,返回 ok=False
    assert "读取命令输出失败" in (r.error or "") or "RuntimeError" in (r.error or "")


def test_subprocess_env_sanitized(tmp_path: Path, monkeypatch):
    """I-1 回归:子进程 env 滤掉机密(PRAXIS_*/。*KEY/TOKEN/SECRET/PASSWORD),
    防 BashTool 命令(env/printenv)读出上游 API key。非机密(PATH)保留。"""
    monkeypatch.setenv("PRAXIS_FAKE_SECRET", "leak-me-123")
    monkeypatch.setenv("MY_API_KEY", "key-456")
    monkeypatch.setenv("HARMLESS_VAR", "ok-789")
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "env"})  # 注:env 命令本身经 BashTool 执行(policy 在另一层)
    assert r.ok
    out = r.value["stdout"]
    assert "leak-me-123" not in out, "PRAXIS_ 机密应被裁剪"
    assert "key-456" not in out, "*KEY 机密应被裁剪"
    assert "HARMLESS_VAR" in out or "ok-789" in out, "非机密应保留"
    # PATH 必须保留(否则子进程找不到命令)
    assert "PATH" in out


def test_timeout_s_non_numeric_returns_recovery_hint(tmp_path: Path):
    """timeout_s 非数字('abc')→ ok=False + recovery_hint(不裸抛 ValueError)。"""
    t = BashTool(sandbox_root=tmp_path)
    r = _run(t, {"command": "echo hi", "timeout_s": "abc"})
    assert r.ok is False
    assert "timeout_s" in (r.error or "")
    assert r.recovery_hint
    assert "120" in r.recovery_hint  # hint 含上限提示,对模型可执行
