"""LocalJobRunner — 在远端用 nohup 提交 gmx 任务,替代 SLURM sbatch。

适用场景:.53 无 SLURM,直接在 praxis-md-cuda conda env 里跑 gmx。

job.sh 末尾写 STATUS 哨兵文件(done / failed),poll_status 据此判断。
slurm_job_id 字段复用存 "local:{pid}",poll_worker 检测前缀路由。
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from praxis2.md.ssh import SshConfig

log = logging.getLogger(__name__)

_SSH_RUN_NOCHECK_LOCK: asyncio.Lock | None = None  # 仅防并发日志混乱


def _import_ssh():
    from praxis2.md.ssh import ssh_run, ssh_write_file  # noqa: PLC0415
    return ssh_run, ssh_write_file


async def _ssh_run_rc(cfg: "SshConfig", cmd: str) -> int:
    """跑 cmd,返 exit code(不抛 RuntimeError)。"""
    ssh_run, _ = _import_ssh()
    try:
        await ssh_run(cfg, cmd)
        return 0
    except RuntimeError as e:
        msg = str(e)
        # ssh_run 的 RuntimeError: "ssh_failed cmd=... rc=N ..."
        if "rc=" in msg:
            try:
                return int(msg.split("rc=")[1].split()[0])
            except (IndexError, ValueError):
                pass
        return 1


async def submit(cfg: "SshConfig", work_dir: str, script_bytes: bytes) -> str:
    """写 job.sh + nohup 跑,返回 PID 字符串。

    job.sh 由 sbatch.py 生成,其末尾已有 STATUS 哨兵(done/failed)写入。
    #SBATCH 注释行被 bash 忽略,脚本可直接 bash 运行。
    """
    ssh_run, ssh_write_file = _import_ssh()
    await ssh_run(cfg, f"mkdir -p {work_dir}")
    await ssh_write_file(cfg, f"{work_dir}/job.sh", script_bytes)
    # setsid 使 job.sh 成为新进程组 leader → cancel 时 kill -- -PID 杀整棵进程树
    # (mdrun fork 的子进程都在同组);< /dev/null 脱离 ssh stdin,使 ssh 立即返回
    pid_raw = await ssh_run(
        cfg,
        f"cd {work_dir} && "
        f"setsid bash job.sh > {work_dir}/stdout.log 2>{work_dir}/stderr.log < /dev/null & "
        f"echo $!",
    )
    pid = pid_raw.strip()
    if not pid.isdigit():
        raise RuntimeError(f"local_runner: nohup 未返回 PID, got: {pid!r}")
    await ssh_run(cfg, f"echo {pid} > {work_dir}/job.pid")
    log.info("local_runner: submitted job at %s pid=%s", work_dir, pid)
    return pid


async def poll_status(
    cfg: "SshConfig", work_dir: str, pid: str,
) -> str:
    """查询本地任务状态,返 queued / running / done / failed。

    优先读 STATUS 哨兵文件(权威);文件缺失时检查 PID 是否存活。
    """
    ssh_run, _ = _import_ssh()
    try:
        sentinel = await ssh_run(
            cfg, f"cat {work_dir}/job.status 2>/dev/null; true"
        )
        sentinel = sentinel.strip()
    except Exception:  # noqa: BLE001
        sentinel = ""

    if sentinel == "done":
        return "done"
    if sentinel == "failed":
        return "failed"

    # 哨兵未写:检查 PID 存活
    rc = await _ssh_run_rc(cfg, f"kill -0 {pid} 2>/dev/null")
    if rc == 0:
        return "running"

    # PID 已死但无哨兵 → 被 kill/OOM 等外部终止
    log.warning(
        "local_runner: pid %s dead but no sentinel at %s, marking failed",
        pid, work_dir,
    )
    return "failed"


def parse_local_job_id(slurm_job_id: str) -> str | None:
    """'local:{pid}' → pid 字符串;非 local 前缀返 None。"""
    if slurm_job_id and slurm_job_id.startswith("local:"):
        return slurm_job_id[len("local:"):]
    return None
