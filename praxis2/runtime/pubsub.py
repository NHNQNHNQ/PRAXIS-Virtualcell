from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class SessionChannel:
    user_id: str
    session_id: str

    def name(self) -> str:
        if not self.user_id or not self.session_id:
            raise ValueError("SessionChannel requires nonempty user_id and session_id")
        return f"{self.user_id}:{self.session_id}"


class InMemoryEventBus:
    def __init__(self, *, replay_buffer: int = 100) -> None:
        self._subs: dict[str, list[Callable[[dict], None]]] = {}
        self._seq: dict[str, int] = {}
        self._buffer: dict[str, list[dict]] = {}
        self._buf_max = replay_buffer

    async def subscribe(self, session_id: str, handler: Callable[[dict], None]) -> None:
        self._subs.setdefault(session_id, []).append(handler)

    async def publish(self, session_id: str, event: dict) -> dict:

        self._seq[session_id] = self._seq.get(session_id, 0) + 1
        ev = {**event, "event_id": self._seq[session_id]}
        buf = self._buffer.setdefault(session_id, [])
        buf.append(ev)
        if len(buf) > self._buf_max:
            del buf[: len(buf) - self._buf_max]
        for h in self._subs.get(session_id, []):
            h(ev)
        return ev

    async def replay(self, session_id: str, *, last_event_id: int) -> list[dict]:

        return [e for e in self._buffer.get(session_id, []) if e["event_id"] > last_event_id]


class RedisEventBus:
    def __init__(
        self,
        url: str,
        *,
        max_recent: int = 1000,
        idle_ttl_s: int = 3600,
    ) -> None:

        import redis.asyncio as aioredis

        self._r = aioredis.from_url(url)
        self._max_recent = max_recent
        self._idle_ttl_s = idle_ttl_s

    async def publish(self, session_id: str, event: dict) -> dict:

        import json

        seq = await self._r.incr(f"sse:seq:{session_id}")
        ev = {**event, "event_id": seq}
        payload = json.dumps(ev, ensure_ascii=False)
        buf_key = f"sse:buf:{session_id}"
        await self._r.zadd(buf_key, {payload: seq})

        await self._r.zremrangebyrank(buf_key, 0, -self._max_recent - 1)

        await self._r.expire(buf_key, self._idle_ttl_s)
        await self._r.expire(f"sse:seq:{session_id}", self._idle_ttl_s)
        await self._r.publish(f"sse:ch:{session_id}", payload)
        return ev

    async def replay(self, session_id: str, *, last_event_id: int) -> list[dict]:
        import json

        raw = await self._r.zrangebyscore(f"sse:buf:{session_id}", f"({last_event_id}", "+inf")
        return [json.loads(x) for x in raw]

    async def aclose(self) -> None:
        await self._r.aclose()
