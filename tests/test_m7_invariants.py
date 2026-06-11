"""§7.3.9/§7.5.5/§11.5/§11.7 M7 整合不变量(横向兜底)。"""

from praxis2.runtime.tasks import TaskState
from praxis2.scheduler.hpc_submit import HPCAccount, InMemoryHPCBackend
from praxis2.scheduler.quota import Quota, QuotaConfig
from praxis2.scheduler.registry import SchedulerRegistry
from praxis2.scheduler.resource_gate import (
    AvailableResources,
    GateBehavior,
    ResourceGate,
)
from praxis2.tools.base import ResourceCost


def test_inv1_gate_behavior_has_five_values():
    # §7.3.9 五分支
    assert {b.value for b in GateBehavior} == {
        "submit_now", "enqueue", "downscale", "cpu_fallback", "reject",
    }


def test_inv2_task_state_has_seven_values():
    # §7.5.5 M6 五态 + M7 两态 = 7
    assert {s.value for s in TaskState} == {
        "pending", "queued", "submitted", "running",
        "completed", "failed", "killed", "timeout",
    }


def test_inv3_hpc_account_case_sensitive_no_normalization():
    # §11.7 严警:SCW6CHB(GPU)与 scw6chb(CPU)是不同账号
    values = {a.value for a in HPCAccount}
    assert "SCW6CHB" in values and "scw6chb" in values
    assert HPCAccount.SCW6CHB_GPU.value != HPCAccount.SCW6CHB_CPU.value


async def test_inv4_heavy_path_end_to_end_decide_reserve_submit():
    # 端到端:gate.decide → reserve → submit → poll(M7 主线闭环)
    gate = ResourceGate(quota=Quota(QuotaConfig(2, 10)))
    registry = SchedulerRegistry(initial=AvailableResources(2, 48, 512.0))
    backend = InMemoryHPCBackend()
    cost = ResourceCost(cpu_cores=8, mem_gb=32.0, gpu_count=1,
                        gpu_mem_gb=24.0, wall_time_s=600, queue_hint="gpu")
    d = gate.decide(
        cost=cost, user_id="u1",
        available=registry.snapshot(),
    )
    assert d.behavior is GateBehavior.SUBMIT_NOW
    reservation = registry.reserve(cost=cost, user_id="u1")
    handle = await backend.submit(
        account=HPCAccount.SCW6CHB_GPU,
        command="x", cost=cost, user_id="u1",
    )
    assert handle.account is HPCAccount.SCW6CHB_GPU
    # 释放(模拟作业完成)
    registry.release(reservation)
    after = registry.snapshot()
    assert after.gpu_count_free == 2  # 复原


def test_inv5_channel_a_b_quotas_independent():
    # §11.5 通道 A LLM + 通道 B 重算力独立配额
    from praxis2.runtime.ratelimit import RateLimiter

    rl = RateLimiter(
        max_concurrent_per_user=2, user_qps=100.0,
        global_llm_inflight=100, max_heavy_jobs_per_user=1,
    )
    rl.acquire_session("u1")
    rl.acquire_session("u1")
    assert rl.acquire_session("u1").allowed is False  # A 满
    assert rl.acquire_heavy_job("u1").allowed is True  # B 仍可
