"""§11.4 SSE 跨 worker 投递抽象。

用户 SSE 长连接落某 worker;事件可能由另一 worker/后台作业产生 →
按 session_id channel 经 pub/sub 投递,持连 worker 订阅下发。断线重连
带 last_event_id,按 event_id 续传补发(防乱序/丢事件,§7.6.3)。

内存 InMemoryEventBus 单进程订阅/发布 + event_id 续传正确性可测;
真 RedisEventBus(pub/sub)标 integration(M6 校准②,真分布式实测
留装 docker 后,类比 v1 §7 多 worker 路径写好未启用)。
**有状态点清单(§11.8 已全部解耦)**:SSE 长连接 = Redis pub/sub 路由。"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class SessionChannel:
    """channel 名含 user_id(§11.6:不同 user 同 session_id 不串)。"""

    user_id: str
    session_id: str

    def name(self) -> str:
        if not self.user_id or not self.session_id:
            raise ValueError("SessionChannel 需非空 user_id/session_id(§11.6)")
        return f"{self.user_id}:{self.session_id}"


class InMemoryEventBus:
    """单进程订阅/发布。每 session 自增 event_id(断线重连续传依据);
    replay_buffer 保留最近 N 条供 replay(last_event_id 之后补发)。"""

    def __init__(self, *, replay_buffer: int = 100) -> None:
        self._subs: dict[str, list[Callable[[dict], None]]] = {}
        self._seq: dict[str, int] = {}
        self._buffer: dict[str, list[dict]] = {}
        self._buf_max = replay_buffer

    async def subscribe(
        self, session_id: str, handler: Callable[[dict], None]
    ) -> None:
        self._subs.setdefault(session_id, []).append(handler)

    async def publish(self, session_id: str, event: dict) -> dict:
        """publish 同时返带 event_id 的 ev(B.2:caller 拿去发 SSE frame,
        不再 nonlocal seq 各算各的;event_id 单一源)。"""
        self._seq[session_id] = self._seq.get(session_id, 0) + 1
        ev = {**event, "event_id": self._seq[session_id]}
        buf = self._buffer.setdefault(session_id, [])
        buf.append(ev)
        if len(buf) > self._buf_max:
            del buf[: len(buf) - self._buf_max]
        for h in self._subs.get(session_id, []):
            h(ev)  # 同 session 多订阅者(多标签页)全收(广播)
        return ev

    async def replay(
        self, session_id: str, *, last_event_id: int
    ) -> list[dict]:
        """断线重连:补发 event_id > last_event_id 的(不重发已收,§11.4)。"""
        return [
            e for e in self._buffer.get(session_id, [])
            if e["event_id"] > last_event_id
        ]


class RedisEventBus:
    """真 Redis pub/sub 跨 worker 投递 + event_id 续传(Redis ZSET 缓冲)。
    M6 接口位 + 标 integration(总纲校准②,真分布式实测留装 docker 后)。
    内存版已锁死路由/单调 event_id/续传正确性;本类语义对齐。"""

    def __init__(
        self, url: str, *, max_recent: int = 1000, idle_ttl_s: int = 3600,
    ) -> None:
        """max_recent / idle_ttl_s:M6 carry #8 —— ZSET 限最近 N + idle TTL,
        防 buffer 无界增长 + 闲置 session 永驻 OOM。"""
        import redis.asyncio as aioredis

        self._r = aioredis.from_url(url)
        self._max_recent = max_recent
        self._idle_ttl_s = idle_ttl_s

    async def publish(self, session_id: str, event: dict) -> dict:
        """publish + trim + EXPIRE,返带 event_id 的 ev(与 InMemory 同语义)。"""
        import json

        seq = await self._r.incr(f"sse:seq:{session_id}")
        ev = {**event, "event_id": seq}
        payload = json.dumps(ev, ensure_ascii=False)
        buf_key = f"sse:buf:{session_id}"
        await self._r.zadd(buf_key, {payload: seq})
        # M6 carry #8:trim 到最近 N(防 OOM 无界增长,§11.4)
        await self._r.zremrangebyrank(buf_key, 0, -self._max_recent - 1)
        # 闲置 TTL:每次 publish 续期 buf + seq,长期无活动 session 自动回收
        await self._r.expire(buf_key, self._idle_ttl_s)
        await self._r.expire(f"sse:seq:{session_id}", self._idle_ttl_s)
        await self._r.publish(f"sse:ch:{session_id}", payload)
        return ev

    async def replay(
        self, session_id: str, *, last_event_id: int
    ) -> list[dict]:
        import json

        raw = await self._r.zrangebyscore(
            f"sse:buf:{session_id}", f"({last_event_id}", "+inf"
        )
        return [json.loads(x) for x in raw]

    async def aclose(self) -> None:
        await self._r.aclose()
