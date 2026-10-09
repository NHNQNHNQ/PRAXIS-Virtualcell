from praxis2.runtime.tasks import TaskState
from praxis2.scheduler.resource_gate import (
    GateBehavior,
)


def test_inv1_gate_behavior_has_five_values():

    assert {b.value for b in GateBehavior} == {
        "submit_now",
        "enqueue",
        "downscale",
        "cpu_fallback",
        "reject",
    }


def test_inv2_task_state_has_seven_values():

    assert {s.value for s in TaskState} == {
        "pending",
        "queued",
        "submitted",
        "running",
        "completed",
        "failed",
        "killed",
        "timeout",
    }


def test_inv5_channel_a_b_quotas_independent():

    from praxis2.runtime.ratelimit import RateLimiter

    rl = RateLimiter(
        max_concurrent_per_user=2,
        user_qps=100.0,
        global_llm_inflight=100,
        max_heavy_jobs_per_user=1,
    )
    rl.acquire_session("u1")
    rl.acquire_session("u1")
    assert rl.acquire_session("u1").allowed is False
    assert rl.acquire_heavy_job("u1").allowed is True
