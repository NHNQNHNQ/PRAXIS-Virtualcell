import pytest

from praxis2.runtime.ratelimit import (
    Backpressure,
    RateLimiter,
    TokenBucket,
)


def test_token_bucket_allows_within_capacity_then_throttles():
    b = TokenBucket(capacity=2, refill_per_s=0.0)  # 不回填,纯容量测试
    assert b.try_take() is True
    assert b.try_take() is True
    assert b.try_take() is False  # 桶空 → 拒(背压,不静默丢)


def test_token_bucket_refills_over_time():
    b = TokenBucket(capacity=1, refill_per_s=100.0)
    assert b.try_take() is True
    assert b.try_take() is False
    import time
    time.sleep(0.05)  # 100/s × 0.05s ≈ 5 个回填,封顶 capacity=1
    assert b.try_take() is True


def test_per_user_concurrent_session_cap():
    rl = RateLimiter(max_concurrent_per_user=2, user_qps=1000.0,
                     global_llm_inflight=100)
    assert rl.acquire_session("u1").allowed is True
    assert rl.acquire_session("u1").allowed is True
    d = rl.acquire_session("u1")
    assert d.allowed is False
    assert d.http_status == 429          # 过载 429(S10,不崩)
    assert d.queue_position >= 1         # 排队位次(SSE queue_position 事件)
    # 不同用户不受 u1 占用影响(每用户独立配额)
    assert rl.acquire_session("u2").allowed is True
    rl.release_session("u1")
    assert rl.acquire_session("u1").allowed is True  # 释放后可再获取


def test_per_user_qps_token_bucket():
    rl = RateLimiter(max_concurrent_per_user=999, user_qps=2.0,
                     global_llm_inflight=100)
    d1 = rl.check_qps("u1")
    d2 = rl.check_qps("u1")
    d3 = rl.check_qps("u1")
    assert d1.allowed and d2.allowed
    assert d3.allowed is False and d3.http_status == 429


def test_global_llm_inflight_gate():
    # 全局 LLM 上游并发闸(配合 D4 单上游,超过最大在飞则排队,§11.2)
    rl = RateLimiter(max_concurrent_per_user=999, user_qps=1000.0,
                     global_llm_inflight=1)
    g1 = rl.acquire_llm_slot("u1")
    assert g1.allowed is True
    g2 = rl.acquire_llm_slot("u2")
    assert g2.allowed is False           # 全局闸满 → 排队(不雪崩)
    assert g2.queue_position >= 1
    rl.release_llm_slot("u1")
    assert rl.acquire_llm_slot("u2").allowed is True


def test_backpressure_event_shape_for_sse():
    # 过载经 SSE error/queue_position 事件回吐(§7.6.3,不静默丢)
    bp = Backpressure(http_status=429, queue_position=3, eta_s=12.0,
                       reason="每用户并发会话上限")
    ev = bp.to_sse_event()
    assert ev["type"] == "error"
    assert ev["http_status"] == 429
    assert ev["queue_position"] == 3
    assert ev["eta_s"] == 12.0
    assert "上限" in ev["message"]


@pytest.mark.asyncio
async def test_ratelimiter_acquire_email_send_with_redis():
    """M9:60s/email send-code 频控经 RateLimiter.acquire_email_send。"""
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    rl = RateLimiter(
        max_concurrent_per_user=5,
        user_qps=10.0,
        global_llm_inflight=100,
        max_heavy_jobs_per_user=0,
    )
    d1 = await rl.acquire_email_send("a@b.com", redis_client=client, ttl_s=60)
    assert d1.allowed
    d2 = await rl.acquire_email_send("a@b.com", redis_client=client, ttl_s=60)
    assert not d2.allowed
    assert d2.reason == "email_send_throttled_60s"
    await client.aclose()
