import pytest

from praxis2.runtime.ratelimit import (
    Backpressure,
    RateLimitDecision,
    RateLimiter,
)
from praxis2.server.permission_bridge import PendingPermissionRegistry


def test_channel_b_heavy_job_independent_from_channel_a():
    rl = RateLimiter(
        max_concurrent_per_user=2,
        user_qps=1000.0,
        global_llm_inflight=100,
        max_heavy_jobs_per_user=1,
    )
    rl.acquire_session("u1")
    rl.acquire_session("u1")
    assert rl.acquire_session("u1").allowed is False
    assert rl.acquire_heavy_job("u1").allowed is True
    assert rl.acquire_heavy_job("u1").allowed is False
    rl.release_heavy_job("u1")
    assert rl.acquire_heavy_job("u1").allowed is True


def test_backpressure_from_decision_factory():
    d = RateLimitDecision(
        allowed=False, http_status=429, queue_position=5, reason="\u91cd\u7b97\u529b\u914d\u989d\u4e0a\u9650"
    )
    bp = Backpressure.from_decision(d, eta_s=120.0)
    assert isinstance(bp, Backpressure)
    assert bp.http_status == 429
    assert bp.queue_position == 5
    assert bp.eta_s == 120.0
    assert "\u91cd\u7b97\u529b" in bp.reason


def test_backpressure_from_decision_rejects_allowed_decision():
    d = RateLimitDecision(allowed=True)
    with pytest.raises(ValueError, match="allowed"):
        Backpressure.from_decision(d, eta_s=0.0)


@pytest.mark.asyncio
async def test_pending_permission_registry_uses_get_running_loop():
    reg = PendingPermissionRegistry()
    rid = reg.register(user_id="u_test")
    assert reg.is_pending(rid) is True


def test_pending_permission_registry_register_outside_async_raises():
    reg = PendingPermissionRegistry()
    with pytest.raises(RuntimeError):
        reg.register(user_id="u_test")
