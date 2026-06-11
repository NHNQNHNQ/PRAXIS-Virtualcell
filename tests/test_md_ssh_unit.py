"""ssh.py 单元 — mock asyncssh.connect,验证 ssh_run / ssh_write_file 接口。"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from praxis2.md.ssh import SshConfig, ssh_run, ssh_write_file


def _cfg() -> SshConfig:
    return SshConfig(
        host="10.0.0.1", user="zkyd",
        key_path="/tmp/fake-key", timeout_s=15.0,
    )


@pytest.mark.asyncio
async def test_ssh_run_returns_stdout():
    cfg = _cfg()
    mock_result = MagicMock()
    mock_result.stdout = "ok\n"
    mock_result.returncode = 0

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("praxis2.md.ssh.asyncssh.connect", AsyncMock(return_value=mock_conn)):
        out = await ssh_run(cfg, "echo ok")
    assert out == "ok\n"
    mock_conn.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_ssh_run_with_stdin():
    cfg = _cfg()
    mock_result = MagicMock(stdout="received", returncode=0)
    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("praxis2.md.ssh.asyncssh.connect", AsyncMock(return_value=mock_conn)):
        out = await ssh_run(cfg, "cat", stdin=b"hello")
    assert out == "received"
    call_kwargs = mock_conn.run.call_args.kwargs
    assert call_kwargs.get("input") == b"hello"


@pytest.mark.asyncio
async def test_ssh_run_nonzero_raises():
    cfg = _cfg()
    mock_result = MagicMock(stdout="", stderr="boom", returncode=1)
    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("praxis2.md.ssh.asyncssh.connect", AsyncMock(return_value=mock_conn)):
        with pytest.raises(RuntimeError, match="ssh_failed.*boom"):
            await ssh_run(cfg, "false")


@pytest.mark.asyncio
async def test_ssh_write_file_uses_sftp():
    cfg = _cfg()
    mock_sftp = AsyncMock()
    mock_sftp.__aenter__ = AsyncMock(return_value=mock_sftp)
    mock_sftp.__aexit__ = AsyncMock(return_value=None)

    mock_file = AsyncMock()
    mock_file.write = AsyncMock()
    mock_file.__aenter__ = AsyncMock(return_value=mock_file)
    mock_file.__aexit__ = AsyncMock(return_value=None)
    mock_sftp.open = MagicMock(return_value=mock_file)

    mock_conn = AsyncMock()
    mock_conn.start_sftp_client = AsyncMock(return_value=mock_sftp)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("praxis2.md.ssh.asyncssh.connect", AsyncMock(return_value=mock_conn)):
        await ssh_write_file(cfg, "/remote/path.txt", b"content")

    mock_file.write.assert_awaited_once_with(b"content")
