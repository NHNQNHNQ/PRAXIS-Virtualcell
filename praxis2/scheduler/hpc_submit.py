"""§11.5/§11.7 HPC 提交端接口(submit/poll/cancel/timeout)+ 节点账号 StrEnum。

**总纲 §11.7 严警**:`SCW6CHB`(N40 GPU 包月)与 `scw6chb`(CPUX 按需 CPU)
是**不同账号,仅大小写区别**——`HPCAccount` 用 StrEnum 显式枚举区分,严禁
字符串归一,误用 = 把 GPU 作业投到 CPU 队列(M7 校准②)。

**M7 落地范围**:
- `InMemoryHPCBackend`:单进程模拟 lifecycle(QUEUED→RUNNING→COMPLETED/
  KILLED/TIMEOUT),正确性可测;
- `AsyncSSHBackend`:真 SSH 投 bio000070(asyncssh 库),接口位 + 标
  @pytest.mark.integration(无 asyncssh/ssh-key 自动 skip,M8 实测);
- `JobHandle` 含 `user_id`(§11.6 多租户:poll_for_user 校验跨租户拒)。
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from praxis2.tools.base import ResourceCost


class HPCAccount(StrEnum):
    """§11.7 节点账号(严区分大小写)。"""

    SCW6CHB_GPU = "SCW6CHB"          # N40 GPU 包月(8×RTX 4090)
    BIO000070_SUBMIT = "bio000070"   # 提交端(Quick AF3 入口)
    A0S001884_BIGMEM = "a0s001884"   # 2TB 大内存
    SCW6CHB_CPU = "scw6chb"          # CPUX 按需 CPU(48 核)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMEOUT = "timeout"


@dataclass
class JobHandle:
    """HPC 作业句柄。timeout_at = submitted_at + cost.wall_time_s + grace
    (M7 grace=30s 兜上游不准)。user_id 用于 §11.6 跨租户校验。"""

    job_id: str
    account: HPCAccount
    user_id: str
    submitted_at: float
    timeout_at: float
    cost: ResourceCost
    command: str = ""
    _meta: dict = field(default_factory=dict)


_TIMEOUT_GRACE_S = 30.0


class HPCSubmitBackend(Protocol):
    async def submit(
        self, *, account: HPCAccount, command: str, cost: ResourceCost,
        user_id: str,
    ) -> JobHandle: ...
    async def poll(self, handle: JobHandle) -> JobStatus: ...
    async def cancel(self, handle: JobHandle) -> None: ...


class InMemoryHPCBackend:
    """单进程模拟:submit 立即返回 handle;poll 按经过时间推进状态
    QUEUED(立即) → RUNNING(简单延迟) → COMPLETED(simulate_run_s 后)。
    cancel → KILLED;超时(now > timeout_at)→ TIMEOUT。"""

    def __init__(self, *, simulate_run_s: float = 0.001) -> None:
        self._run_s = simulate_run_s
        self._jobs: dict[str, dict] = {}

    async def submit(
        self, *, account: HPCAccount, command: str, cost: ResourceCost,
        user_id: str,
    ) -> JobHandle:
        now = time.monotonic()
        jid = "mem-" + uuid.uuid4().hex
        # wall_time_s==0 视为"显式不留 grace"(测试通道),否则加 grace 兜上游不准
        grace = 0.0 if cost.wall_time_s == 0 else _TIMEOUT_GRACE_S
        h = JobHandle(
            job_id=jid, account=account, user_id=user_id,
            submitted_at=now,
            timeout_at=now + cost.wall_time_s + grace,
            cost=cost, command=command,
        )
        self._jobs[jid] = {
            "handle": h,
            "started_at": now,
            "killed": False,
        }
        return h

    async def poll(self, handle: JobHandle) -> JobStatus:
        rec = self._jobs.get(handle.job_id)
        if rec is None:
            return JobStatus.FAILED
        if rec["killed"]:
            return JobStatus.KILLED
        now = time.monotonic()
        if now > handle.timeout_at:
            return JobStatus.TIMEOUT
        elapsed = now - rec["started_at"]
        if elapsed < self._run_s:
            return JobStatus.RUNNING
        return JobStatus.COMPLETED

    async def poll_for_user(self, handle: JobHandle, *, user_id: str) -> JobStatus:
        """§11.6 跨租户校验:非 owner 拒。"""
        if handle.user_id != user_id:
            raise PermissionError(
                f"跨租户:user {user_id!r} 不可 poll user {handle.user_id!r} 的 job"
            )
        return await self.poll(handle)

    async def cancel(self, handle: JobHandle) -> None:
        rec = self._jobs.get(handle.job_id)
        if rec is not None:
            rec["killed"] = True


class AsyncSSHBackend:
    """真 SSH 投 bio000070(asyncssh 库)。M7 接口位 + 标 integration
    (M7 校准②,M8 实测;asyncssh/ssh-key 缺失自动 skip)。"""

    def __init__(self, *, host: str, username: str) -> None:
        try:
            import asyncssh  # noqa: F401
        except ImportError as e:  # noqa: BLE001
            raise ImportError(
                "AsyncSSHBackend 需 asyncssh 库:pip install asyncssh"
            ) from e
        self._host = host
        self._username = username
        # 真连接懒建立(submit 时);本类 M7 仅接口位,实测见 M8

    async def submit(
        self, *, account: HPCAccount, command: str, cost: ResourceCost,
        user_id: str,
    ) -> JobHandle:
        # M7 接口位:真 asyncssh.connect + sbatch/qsub 拼命令 M8 落地
        raise NotImplementedError(
            "AsyncSSHBackend.submit M8 实测落地(真 asyncssh + sbatch);M7 接口位"
        )

    async def poll(self, handle: JobHandle) -> JobStatus:
        raise NotImplementedError("AsyncSSHBackend.poll M8 实测落地")

    async def cancel(self, handle: JobHandle) -> None:
        raise NotImplementedError("AsyncSSHBackend.cancel M8 实测落地")

    async def aclose(self) -> None:
        pass
