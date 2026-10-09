import pytest

from praxis2.runtime.pubsub import InMemoryEventBus, SessionChannel


async def test_publish_routes_to_session_subscriber():
    # §11.4 按 session_id channel 投递:订阅 s1 的收到 s1 的事件,不收 s2
    bus = InMemoryEventBus()
    s1_seen: list[dict] = []
    s2_seen: list[dict] = []
    await bus.subscribe("s1", lambda ev: s1_seen.append(ev))
    await bus.subscribe("s2", lambda ev: s2_seen.append(ev))
    await bus.publish("s1", {"type": "text_delta", "text": "hi"})
    assert len(s1_seen) == 1 and s1_seen[0]["text"] == "hi"
    assert s2_seen == []  # s2 订阅者不串(跨会话隔离)


async def test_event_id_monotonic_per_session():
    # 每 session event_id 单调递增(断线重连续传依据,§11.4 防乱序)
    bus = InMemoryEventBus()
    ids: list[int] = []
    await bus.subscribe("s1", lambda ev: ids.append(ev["event_id"]))
    await bus.publish("s1", {"type": "text_delta", "text": "a"})
    await bus.publish("s1", {"type": "text_delta", "text": "b"})
    await bus.publish("s1", {"type": "text_delta", "text": "c"})
    assert ids == [1, 2, 3]


async def test_replay_after_last_event_id():
    # 断线重连:带 last_event_id 续传补发其后事件,不重发已收(§11.4)
    bus = InMemoryEventBus(replay_buffer=10)
    await bus.publish("s1", {"type": "text_delta", "text": "1"})
    await bus.publish("s1", {"type": "text_delta", "text": "2"})
    await bus.publish("s1", {"type": "text_delta", "text": "3"})
    missed = await bus.replay("s1", last_event_id=1)
    assert [e["text"] for e in missed] == ["2", "3"]  # 只补 >1 的


async def test_session_channel_user_scoped():
    # §11.6:channel 含 user_id 防跨租户(不同 user 同 session_id 不串)
    c1 = SessionChannel(user_id="u1", session_id="s1")
    c2 = SessionChannel(user_id="u2", session_id="s1")
    assert c1.name() != c2.name()
    assert c1.name() == "u1:s1"


async def test_multiple_subscribers_same_session_all_receive():
    # 同 session 多 SSE 连接(多标签页)都收到(广播语义)
    bus = InMemoryEventBus()
    a: list[dict] = []
    b: list[dict] = []
    await bus.subscribe("s1", lambda ev: a.append(ev))
    await bus.subscribe("s1", lambda ev: b.append(ev))
    await bus.publish("s1", {"type": "final"})
    assert len(a) == 1 and len(b) == 1


@pytest.mark.integration
async def test_redis_event_bus_smoke():
    # 真 Redis pub/sub(无 docker 自动 skip,总纲校准②)
    from praxis2.runtime.pubsub import RedisEventBus

    bus = RedisEventBus("redis://localhost:6379/0")
    await bus.publish("s1", {"type": "final"})
    await bus.aclose()
