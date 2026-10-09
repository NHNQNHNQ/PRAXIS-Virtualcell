from praxis2.runtime.ratelimit import (
    Backpressure,
    RateLimiter,
    TokenBucket,
)


def test_token_bucket_allows_within_capacity_then_throttles():
    b = TokenBucket(capacity=2, refill_per_s=0.0)
    assert b.try_take() is True
    assert b.try_take() is True
    assert b.try_take() is False


def test_token_bucket_refills_over_time():
    b = TokenBucket(capacity=1, refill_per_s=100.0)
    assert b.try_take() is True
    assert b.try_take() is False
    import time

    time.sleep(0.05)
    assert b.try_take() is True


def test_per_user_concurrent_session_cap():
    rl = RateLimiter(max_concurrent_per_user=2, user_qps=1000.0, global_llm_inflight=100)
    assert rl.acquire_session("u1").allowed is True
    assert rl.acquire_session("u1").allowed is True
    d = rl.acquire_session("u1")
    assert d.allowed is False
    assert d.http_status == 429
    assert d.queue_position >= 1

    assert rl.acquire_session("u2").allowed is True
    rl.release_session("u1")
    assert rl.acquire_session("u1").allowed is True


def test_per_user_qps_token_bucket():
    rl = RateLimiter(max_concurrent_per_user=999, user_qps=2.0, global_llm_inflight=100)
    d1 = rl.check_qps("u1")
    d2 = rl.check_qps("u1")
    d3 = rl.check_qps("u1")
    assert d1.allowed and d2.allowed
    assert d3.allowed is False and d3.http_status == 429


def test_global_llm_inflight_gate():

    rl = RateLimiter(max_concurrent_per_user=999, user_qps=1000.0, global_llm_inflight=1)
    g1 = rl.acquire_llm_slot("u1")
    assert g1.allowed is True
    g2 = rl.acquire_llm_slot("u2")
    assert g2.allowed is False
    assert g2.queue_position >= 1
    rl.release_llm_slot("u1")
    assert rl.acquire_llm_slot("u2").allowed is True


def test_backpressure_event_shape_for_sse():

    bp = Backpressure(http_status=429, queue_position=3, eta_s=12.0, reason="Per-user concurrent session limit")
    ev = bp.to_sse_event()
    assert ev["type"] == "error"
    assert ev["http_status"] == 429
    assert ev["queue_position"] == 3
    assert ev["eta_s"] == 12.0
    assert "limit" in ev["message"]
