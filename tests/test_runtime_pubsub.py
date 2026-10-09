import pytest

from praxis2.runtime.pubsub import InMemoryEventBus, SessionChannel


async def test_publish_routes_to_session_subscriber():

    bus = InMemoryEventBus()
    s1_seen: list[dict] = []
    s2_seen: list[dict] = []
    await bus.subscribe("s1", lambda ev: s1_seen.append(ev))
    await bus.subscribe("s2", lambda ev: s2_seen.append(ev))
    await bus.publish("s1", {"type": "text_delta", "text": "hi"})
    assert len(s1_seen) == 1 and s1_seen[0]["text"] == "hi"
    assert s2_seen == []


async def test_event_id_monotonic_per_session():

    bus = InMemoryEventBus()
    ids: list[int] = []
    await bus.subscribe("s1", lambda ev: ids.append(ev["event_id"]))
    await bus.publish("s1", {"type": "text_delta", "text": "a"})
    await bus.publish("s1", {"type": "text_delta", "text": "b"})
    await bus.publish("s1", {"type": "text_delta", "text": "c"})
    assert ids == [1, 2, 3]


async def test_replay_after_last_event_id():

    bus = InMemoryEventBus(replay_buffer=10)
    await bus.publish("s1", {"type": "text_delta", "text": "1"})
    await bus.publish("s1", {"type": "text_delta", "text": "2"})
    await bus.publish("s1", {"type": "text_delta", "text": "3"})
    missed = await bus.replay("s1", last_event_id=1)
    assert [e["text"] for e in missed] == ["2", "3"]


async def test_session_channel_user_scoped():

    c1 = SessionChannel(user_id="u1", session_id="s1")
    c2 = SessionChannel(user_id="u2", session_id="s1")
    assert c1.name() != c2.name()
    assert c1.name() == "u1:s1"


async def test_multiple_subscribers_same_session_all_receive():

    bus = InMemoryEventBus()
    a: list[dict] = []
    b: list[dict] = []
    await bus.subscribe("s1", lambda ev: a.append(ev))
    await bus.subscribe("s1", lambda ev: b.append(ev))
    await bus.publish("s1", {"type": "final"})
    assert len(a) == 1 and len(b) == 1


@pytest.mark.integration
async def test_redis_event_bus_smoke():

    from praxis2.runtime.pubsub import RedisEventBus

    bus = RedisEventBus("redis://localhost:6379/0")
    await bus.publish("s1", {"type": "final"})
    await bus.aclose()
