"""B.2(reviewer M6 C2 + M6 carry #8):EventBus 接进 SSE wire +
Last-Event-ID 重放 + RedisEventBus 缓冲 trim/TTL。

修复前:`InMemoryEventBus` / `RedisEventBus` 完整建好,但 `_chat_stream` 没接 →
§11.4 多 worker pub/sub + Last-Event-ID replay 设计路径完全是死代码;
`RedisEventBus.publish` 没 ZREMRANGEBYRANK / EXPIRE,buffer 无界增长 + 闲置永驻。

修复后:`_App` 持 `event_bus`(默认 InMemoryEventBus,可注入);`_chat_stream` 每 ev
经 bus.publish 拿 event_id 再发 SSE frame;reconnect 带 Last-Event-ID header → replay 历史;
RedisEventBus.publish 加 ZREMRANGEBYRANK 保最近 N + EXPIRE idle TTL 防 OOM。
"""

from __future__ import annotations

import time

import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session

# ── EventBus 基础(publish 改返带 event_id 的 dict) ────────────────


@pytest.mark.asyncio
async def test_inmemory_publish_returns_event_with_id():
    """InMemoryEventBus.publish 返回带 event_id 的 ev,caller 拿去发 SSE frame。"""
    from praxis2.runtime.pubsub import InMemoryEventBus

    bus = InMemoryEventBus()
    ev = await bus.publish("c1", {"type": "x"})
    assert ev["event_id"] == 1
    assert ev["type"] == "x"
    ev2 = await bus.publish("c1", {"type": "y"})
    assert ev2["event_id"] == 2


@pytest.mark.asyncio
async def test_replay_returns_events_after_last_event_id():
    """断线重连续传:last_event_id=1 → 只补 event_id>1 的(b, c)。"""
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
    """publish 超过 max_recent 后,ZREMRANGEBYRANK 移除旧 event(防 OOM)。"""
    import json

    import fakeredis.aioredis

    from praxis2.runtime.pubsub import RedisEventBus

    # 跳过 __init__ 的 redis.from_url(fakeredis 直接注入)
    bus = RedisEventBus.__new__(RedisEventBus)
    bus._r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    bus._max_recent = 3
    bus._idle_ttl_s = 60

    for i in range(5):
        await bus.publish("c1", {"type": f"ev{i}"})

    # 缓冲应只剩 3 条(最近 ev2/ev3/ev4),老的 ev0/ev1 被 trim
    raw = await bus._r.zrange("sse:buf:c1", 0, -1)
    assert len(raw) == 3
    types = [json.loads(x)["type"] for x in raw]
    assert types == ["ev2", "ev3", "ev4"]


@pytest.mark.asyncio
async def test_redis_bus_sets_idle_ttl():
    """publish 后 buf/seq key 都有 EXPIRE TTL(闲置 session 不永驻)。"""
    import fakeredis.aioredis

    from praxis2.runtime.pubsub import RedisEventBus

    bus = RedisEventBus.__new__(RedisEventBus)
    bus._r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    bus._max_recent = 1000
    bus._idle_ttl_s = 600

    await bus.publish("c1", {"type": "x"})

    ttl_buf = await bus._r.ttl("sse:buf:c1")
    assert 0 < ttl_buf <= 600, f"buf TTL 应 (0, 600],实际 {ttl_buf}"

    ttl_seq = await bus._r.ttl("sse:seq:c1")
    assert 0 < ttl_seq <= 600, f"seq TTL 应 (0, 600],实际 {ttl_seq}"


@pytest.mark.asyncio
async def test_redis_bus_publish_returns_event_with_id():
    """RedisEventBus.publish 也返 dict 含 event_id(与 InMemory 同语义)。"""
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


# ── _chat_stream 集成测试 ──────────────────────────────────────────


async def _drive_chat_stream(
    app, cookie: str, *, message: str = "hi", last_event_id: str | None = None,
):
    """直接走 ASGI,可选携 Last-Event-ID header 模拟 SSE reconnect。"""
    arrivals: list[tuple[float, bytes]] = []
    t0 = time.perf_counter()

    async def receive():
        import json as _json

        return {
            "type": "http.request",
            "body": _json.dumps({"message": message, "session_id": "s1"}).encode(),
            "more_body": False,
        }

    async def send(msg):
        if msg["type"] == "http.response.body":
            body = msg.get("body", b"")
            if body:
                arrivals.append((time.perf_counter() - t0, body))

    headers = [(b"cookie", cookie.encode())]
    if last_event_id is not None:
        headers.append((b"last-event-id", last_event_id.encode()))

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat/stream",
        "headers": headers,
        "query_string": b"",
    }
    await app(scope, receive, send)
    return arrivals


@pytest.mark.asyncio
async def test_chat_stream_publishes_to_bus_alongside_sse(monkeypatch):
    """query 产的 ev 同时落 bus(后续 reconnect 可 replay)。"""
    from praxis2.server import app as app_module
    from praxis2.server.app import make_app

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        yield {"type": "text", "text": "hello"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u_replay1")
    app = make_app(deps)

    await _drive_chat_stream(app, cookie)

    # bus 应记下了刚才的事件(channel = user_id:session_id)
    channel = "u_replay1:s1"
    replayed = await app._app.event_bus.replay(channel, last_event_id=0)
    types = [e["type"] for e in replayed]
    # text → 映射为 text_delta;end → 映射为 final
    assert "text_delta" in types
    assert "final" in types

    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_stream_with_last_event_id_replays_missed(monkeypatch):
    """先在 bus 预置 3 个历史 event(模拟之前 worker 留下的),client reconnect 带
    Last-Event-ID=1 → 应先收到 event_id=2,3 的 replay,再收到新 query 产的 event。"""
    from praxis2.server import app as app_module
    from praxis2.server.app import make_app

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        yield {"type": "text", "text": "new"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u_replay2")
    app = make_app(deps)

    # 预置 3 个历史 event 到 bus
    channel = "u_replay2:s1"
    await app._app.event_bus.publish(channel, {"type": "text_delta", "text": "old1"})
    await app._app.event_bus.publish(channel, {"type": "text_delta", "text": "old2"})
    await app._app.event_bus.publish(channel, {"type": "text_delta", "text": "old3"})

    # client 带 Last-Event-ID=1 reconnect
    arrivals = await _drive_chat_stream(app, cookie, last_event_id="1")

    # 拼帧 → 应能看到 event_id=2 的 old2、event_id=3 的 old3,然后才是新 event
    blob = b"".join(b for _, b in arrivals)
    assert b'"text": "old2"' in blob
    assert b'"text": "old3"' in blob
    # 不应再发 old1(<= last_event_id=1 不重发)
    assert b'"text": "old1"' not in blob
    # 新 query 产的 event 也应被推
    assert b'"text": "new"' in blob

    # event_id 应连续:replay 后 4, 5(新 text_delta + final)
    import re

    ids = [int(m.group(1)) for m in re.finditer(rb'"event_id":\s*(\d+)', blob)]
    # 期望:2(replay old2), 3(replay old3), 4(new text_delta), 5(final)
    assert ids == [2, 3, 4, 5], f"event_id 序列异常:{ids}"

    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_chat_stream_without_last_event_id_no_replay(monkeypatch):
    """无 Last-Event-ID header 时不 replay,直接走新 query 流。"""
    from praxis2.server import app as app_module
    from praxis2.server.app import make_app

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        yield {"type": "text", "text": "fresh"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u_replay3")
    app = make_app(deps)

    # 预置历史
    channel = "u_replay3:s1"
    await app._app.event_bus.publish(channel, {"type": "text_delta", "text": "stale"})

    # 不带 Last-Event-ID(模拟首连)
    arrivals = await _drive_chat_stream(app, cookie)

    blob = b"".join(b for _, b in arrivals)
    # stale 历史不应被自动 replay(无 Last-Event-ID)
    assert b'"text": "stale"' not in blob
    assert b'"text": "fresh"' in blob

    await deps.redis.aclose()
