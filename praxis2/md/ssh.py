"""asyncssh 封装 — 每次新 connect / async with close。

不维护 connection pool — 简化(M11.2 carry 提到优化点)。
ssh-key 路径取 SshConfig.key_path,known_hosts 用宽松 (StrictHostKeyChecking=no
等价)避免运维负担。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SshConfig:
    host: str
    user: str
    key_path: str
    timeout_s: float = 15.0


async def _connect(cfg: SshConfig):
    """每次新建 connect — caller 用 async with cm。"""
    import asyncssh  # noqa: PLC0415 — lazy:SshConfig 可在无 asyncssh 环境导入
    return await asyncssh.connect(
        host=cfg.host,
        username=cfg.user,
        client_keys=[cfg.key_path],
        known_hosts=None,                  # 宽松,M11.2 carry 加 host pinning
        connect_timeout=cfg.timeout_s,
    )


async def ssh_run(
    cfg: SshConfig, cmd: str, *, stdin: bytes | None = None,
) -> str:
    """跑 cmd, 返 stdout. 非 0 exit code 抛 RuntimeError(含 stderr)。"""
    async with await _connect(cfg) as conn:
        result = await conn.run(cmd, input=stdin, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ssh_failed cmd={cmd!r} rc={result.returncode} "
            f"stderr={(result.stderr or '').strip()[:500]}"
        )
    return result.stdout or ""


async def ssh_write_file(
    cfg: SshConfig, remote_path: str, content: bytes,
) -> None:
    """SFTP 写文件到 remote_path. 覆盖已存在。"""
    async with await _connect(cfg) as conn:
        async with await conn.start_sftp_client() as sftp:
            async with sftp.open(remote_path, "wb") as f:
                await f.write(content)
