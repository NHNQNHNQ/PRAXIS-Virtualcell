from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_inmemory_publish_returns_event_with_id():

    from praxis2.runtime.pubsub import InMemoryEventBus

    bus = InMemoryEventBus()
    ev = await bus.publish("c1", {"type": "x"})
    assert ev["event_id"] == 1
    assert ev["type"] == "x"
    ev2 = await bus.publish("c1", {"type": "y"})
    assert ev2["event_id"] == 2


@pytest.mark.asyncio
async def test_replay_returns_events_after_last_event_id():

    from praxis2.runtime.pubsub import InMemoryEventBus

    bus = InMemoryEventBus()
    await bus.publish("c1", {"type": "a"})
    await bus.publish("c1", {"type": "b"})
    await bus.publish("c1", {"type": "c"})
    out = await bus.replay("c1", last_event_id=1)
    assert [e["type"] for e in out] == ["b", "c"]
    assert [e["event_id"] for e in out] == [2, 3]


# ── Redis bus trim + TTL(M6 carry #8) ─────────────────────────────


@pytest.mark.asyncio
async def test_redis_bus_trims_recent_n():

    import json

    import fakeredis.aioredis

    from praxis2.runtime.pubsub import RedisEventBus

    bus = RedisEventBus.__new__(RedisEventBus)
    bus._r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    bus._max_recent = 3
    bus._idle_ttl_s = 60

    for i in range(5):
        await bus.publish("c1", {"type": f"ev{i}"})

    raw = await bus._r.zrange("sse:buf:c1", 0, -1)
    assert len(raw) == 3
    types = [json.loads(x)["type"] for x in raw]
    assert types == ["ev2", "ev3", "ev4"]


@pytest.mark.asyncio
async def test_redis_bus_sets_idle_ttl():

    import fakeredis.aioredis

    from praxis2.runtime.pubsub import RedisEventBus

    bus = RedisEventBus.__new__(RedisEventBus)
    bus._r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    bus._max_recent = 1000
    bus._idle_ttl_s = 600

    await bus.publish("c1", {"type": "x"})

    ttl_buf = await bus._r.ttl("sse:buf:c1")
    assert 0 < ttl_buf <= 600, f"buf TTL must be in (0, 600]; observed {ttl_buf}"

    ttl_seq = await bus._r.ttl("sse:seq:c1")
    assert 0 < ttl_seq <= 600, f"seq TTL must be in (0, 600]; observed {ttl_seq}"


@pytest.mark.asyncio
async def test_redis_bus_publish_returns_event_with_id():

    import fakeredis.aioredis

    from praxis2.runtime.pubsub import RedisEventBus

    bus = RedisEventBus.__new__(RedisEventBus)
    bus._r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    bus._max_recent = 1000
    bus._idle_ttl_s = 3600

    ev = await bus.publish("c1", {"type": "x"})
    assert ev["event_id"] == 1
    ev2 = await bus.publish("c1", {"type": "y"})
    assert ev2["event_id"] == 2
