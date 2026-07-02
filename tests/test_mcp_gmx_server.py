"""praxis2.mcp.servers.gmx_server 单元测试。

直接测试 _impl 纯函数(不依赖 mcp 库)。
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def gmod(tmp_path, monkeypatch):
    """重载 gmx_server 模块，将 _SAFE_ROOT 指向临时目录。"""
    monkeypatch.setenv("PRAXIS_GMX_WORK_ROOT", str(tmp_path))
    import importlib

    import praxis2.mcp.servers.gmx_server as m
    importlib.reload(m)
    return m, tmp_path


# ---- write_file_impl ----

def test_write_file_creates_file(gmod):
    m, root = gmod
    result = m.write_file_impl("job-1/topol.top", "[system]\ntest system\n")
    assert result["ok"] is True
    assert (root / "job-1" / "topol.top").read_text() == "[system]\ntest system\n"


def test_write_file_path_traversal_blocked(gmod):
    m, _ = gmod
    with pytest.raises(ValueError, match="越界"):
        m.write_file_impl("../../etc/passwd", "evil")


# ---- run_step_impl ----

def test_run_step_echo(gmod):
    m, _ = gmod
    result = m.run_step_impl("echo hello_world", "job-2")
    assert result["exit_code"] == 0
    assert "hello_world" in result["stdout"]


def test_run_step_nonzero_exit(gmod):
    m, _ = gmod
    result = m.run_step_impl("exit 42", "job-3")
    assert result["exit_code"] == 42


def test_run_step_timeout(gmod):
    m, _ = gmod
    result = m.run_step_impl("sleep 100", "job-4", timeout_s=0.1)
    assert result["exit_code"] == -1
    assert "timeout" in result["stderr"]


# ---- run_background_impl ----

def test_run_background_returns_pid(gmod):
    m, root = gmod
    result = m.run_background_impl("echo bg_done", "job-5")
    assert result["job_id"].startswith("local:")
    pid = result["job_id"][len("local:"):]
    assert pid.isdigit()
    assert (root / "job-5" / "job.pid").read_text().strip() == pid


# ---- poll_job_impl ----

def test_poll_job_done_after_sentinel(gmod):
    m, root = gmod
    work = root / "job-6"
    work.mkdir()
    (work / "job.status").write_text("done")
    (work / "job.pid").write_text("99999")
    result = m.poll_job_impl("local:99999")
    assert result["status"] == "done"


def test_poll_job_failed_dead_pid(gmod):
    m, root = gmod
    work = root / "job-7"
    work.mkdir()
    (work / "job.pid").write_text("99998")
    with patch.object(m.os, "kill", side_effect=ProcessLookupError):
        result = m.poll_job_impl("local:99998")
    assert result["status"] == "failed"


def test_poll_job_unknown_prefix(gmod):
    m, _ = gmod
    result = m.poll_job_impl("slurm:12345")
    assert result["status"] == "unknown"


# ---- get_file_impl ----

def test_get_file_small(gmod):
    m, root = gmod
    f = root / "job-8" / "md.log"
    f.parent.mkdir()
    f.write_text("line1\nline2\nline3\n")
    result = m.get_file_impl("job-8/md.log")
    assert result["truncated"] is False
    assert "line1" in result["content"]
    assert result["size"] > 0


def test_get_file_truncated(gmod):
    m, root = gmod
    f = root / "job-9" / "big.log"
    f.parent.mkdir()
    f.write_text("x" * 20000)
    result = m.get_file_impl("job-9/big.log", max_bytes=100)
    assert result["truncated"] is True
    assert len(result["content"]) <= 100
    assert result["size"] == 20000


def test_get_file_not_found(gmod):
    m, _ = gmod
    result = m.get_file_impl("no-such-file.txt")
    assert "error" in result
    assert result["size"] == 0
