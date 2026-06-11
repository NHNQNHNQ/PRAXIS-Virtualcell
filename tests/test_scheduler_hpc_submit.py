"""§11.5/§11.7 HPC 提交端接口(submit/poll/cancel/timeout)+ 节点账号 StrEnum。"""

import asyncio

import pytest

from praxis2.scheduler.hpc_submit import (
    HPCAccount,
    InMemoryHPCBackend,
    JobHandle,
    JobStatus,
)
from praxis2.tools.base import ResourceCost


def test_hpc_account_strenum_values_match_topology():
    # §11.7 4 个节点账号,**严区分大小写**(SCW6CHB GPU vs scw6chb CPU 不同账号)
    assert HPCAccount.SCW6CHB_GPU.value == "SCW6CHB"     # GPU 包月
    assert HPCAccount.BIO000070_SUBMIT.value == "bio000070"  # 提交端
    assert HPCAccount.A0S001884_BIGMEM.value == "a0s001884"  # 2T 大内存
    assert HPCAccount.SCW6CHB_CPU.value == "scw6chb"     # CPU 按需
    # 大小写不同账号绝不混淆
    assert HPCAccount.SCW6CHB_GPU != HPCAccount.SCW6CHB_CPU
    assert HPCAccount.SCW6CHB_GPU.value != HPCAccount.SCW6CHB_CPU.value


async def test_in_memory_backend_submit_returns_job_handle():
    backend = InMemoryHPCBackend()
    cost = ResourceCost(
        cpu_cores=8, mem_gb=32.0, gpu_count=1, gpu_mem_gb=24.0,
        wall_time_s=600, queue_hint="gpu",
    )
    h = await backend.submit(
        account=HPCAccount.SCW6CHB_GPU,
        command="python -m skills.workflows.af3.run",
        cost=cost,
        user_id="u1",
    )
    assert isinstance(h, JobHandle)
    assert h.account is HPCAccount.SCW6CHB_GPU
    assert h.job_id.startswith("mem-")  # InMemory 前缀
    assert h.timeout_at > h.submitted_at  # wall_time_s + grace


async def test_poll_returns_status_lifecycle():
    backend = InMemoryHPCBackend()
    h = await backend.submit(
        account=HPCAccount.SCW6CHB_GPU,
        command="echo hi", cost=ResourceCost(1, 1.0, 60),
        user_id="u1",
    )
    s = await backend.poll(h)
    assert s in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.COMPLETED)
    # InMemory 模拟:fast-finish — 多次 poll 后必达 COMPLETED
    for _ in range(10):
        s = await backend.poll(h)
        if s is JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.005)
    assert s is JobStatus.COMPLETED


async def test_cancel_running_job_returns_killed():
    backend = InMemoryHPCBackend(simulate_run_s=0.05)
    h = await backend.submit(
        account=HPCAccount.SCW6CHB_GPU,
        command="sleep", cost=ResourceCost(1, 1.0, 60),
        user_id="u1",
    )
    await backend.cancel(h)
    s = await backend.poll(h)
    assert s is JobStatus.KILLED


async def test_timeout_detected_when_wall_time_exceeded():
    backend = InMemoryHPCBackend(simulate_run_s=10.0)  # 模拟跑 10s
    h = await backend.submit(
        account=HPCAccount.SCW6CHB_GPU,
        command="long", cost=ResourceCost(1, 1.0, wall_time_s=0),  # 超时阈 0s
        user_id="u1",
    )
    # 任意 poll 在 timeout_at 后 → TIMEOUT
    await asyncio.sleep(0.01)
    s = await backend.poll(h)
    assert s is JobStatus.TIMEOUT


async def test_jobhandle_user_scoped_no_cross_tenant_read():
    # §11.6 job_id 含 user_id(防跨租户 poll 别人 job 状态)
    backend = InMemoryHPCBackend()
    h_u1 = await backend.submit(
        account=HPCAccount.SCW6CHB_GPU,
        command="x", cost=ResourceCost(1, 1.0, 60),
        user_id="u1",
    )
    # u2 持有 u1 的 job_id 但 user_id 不匹配 → poll 返 None 或抛(实现选 None)
    with pytest.raises(PermissionError):
        await backend.poll_for_user(h_u1, user_id="u2")


@pytest.mark.integration
async def test_async_ssh_backend_smoke():
    # 真 SSH 投到 bio000070(无 asyncssh / 无 ssh-key 自动 skip,M7 校准②)
    from praxis2.scheduler.hpc_submit import AsyncSSHBackend

    backend = AsyncSSHBackend(host="bio000070.example", username="bio000070")
    await backend.aclose()
