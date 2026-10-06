"""9.3 Redis 缓存 + 轻量 job 状态(可选)。

定位:纯性能/临时状态,**不做科学证据来源**(红线)。缓存的是已算好的确定性响应
(task_id 内容寻址 → 缓存命中与重算逐字相等),不改任何科学结论。缺 Redis 则整层不启用。
"""
from __future__ import annotations

import json
from typing import Any

_RESP_PREFIX = "mdr:resp:"
_STATUS_PREFIX = "mdr:status:"
_DEFAULT_TTL = 3600  # 1h;科研工具够用,过期即重算(确定性,不丢正确性)


def make_redis_client(url: str | None):
    """从 URL 建 redis 客户端;url 为空返回 None(不启用缓存)。
    真连接失败留给调用方 ping 探测,这里只建对象。"""
    if not url:
        return None
    import redis
    return redis.Redis.from_url(url, decode_responses=True)


class PredictionCache:
    """按 task_id 缓存 /predict 响应 + 存临时 job 状态。client 依赖注入(prod=redis,test=fakeredis)。"""

    def __init__(self, client, *, ttl: int = _DEFAULT_TTL) -> None:
        self._r = client
        self._ttl = ttl

    # ---- 响应缓存 ----
    def get(self, task_id: str) -> dict[str, Any] | None:
        raw = self._r.get(_RESP_PREFIX + task_id)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def set(self, task_id: str, response: dict[str, Any]) -> None:
        blob = json.dumps(response, ensure_ascii=False, sort_keys=True)
        self._r.set(_RESP_PREFIX + task_id, blob, ex=self._ttl)

    # ---- 轻量 job 状态 ----
    def set_status(self, job_id: str, status: str) -> None:
        self._r.set(_STATUS_PREFIX + job_id, status, ex=self._ttl)

    def get_status(self, job_id: str) -> str | None:
        v = self._r.get(_STATUS_PREFIX + job_id)
        if v is None:
            return None
        return v.decode("utf-8") if isinstance(v, bytes) else v
