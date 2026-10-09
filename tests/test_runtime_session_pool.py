import time

from praxis2.runtime.session_pool import SessionPool


def test_get_miss_returns_none():
    p = SessionPool(max_size=2, idle_ttl_s=100)
    assert p.get("u1", "s1") is None  # 未入池 → miss(调用方据此从 store 重建)


def test_put_then_get_hit():
    p = SessionPool(max_size=2, idle_ttl_s=100)
    p.put("u1", "s1", {"messages": [1]})
    assert p.get("u1", "s1") == {"messages": [1]}


def test_lru_eviction_drops_least_recently_used():
    p = SessionPool(max_size=2, idle_ttl_s=100)
    p.put("u1", "s1", "S1")
    p.put("u1", "s2", "S2")
    p.get("u1", "s1")             # s1 变最近使用
    p.put("u1", "s3", "S3")      # 超容 → 驱逐最久未用 s2
    assert p.get("u1", "s2") is None    # s2 被驱逐(只丢内存副本)
    assert p.get("u1", "s1") == "S1"    # s1 仍在
    assert p.get("u1", "s3") == "S3"


def test_idle_ttl_eviction():
    p = SessionPool(max_size=10, idle_ttl_s=0.02)
    p.put("u1", "s1", "S1")
    time.sleep(0.03)
    assert p.get("u1", "s1") is None    # 空闲超 TTL → 驱逐(权威态在 store,可重建)


def test_pool_is_user_scoped_no_cross_tenant_bleed():
    # §11.6:不同 user 同 session_id 不串(多租户隔离,池 key 含 user_id)
    p = SessionPool(max_size=10, idle_ttl_s=100)
    p.put("u1", "s1", "U1S1")
    assert p.get("u2", "s1") is None
    p.put("u2", "s1", "U2S1")
    assert p.get("u1", "s1") == "U1S1"
    assert p.get("u2", "s1") == "U2S1"
