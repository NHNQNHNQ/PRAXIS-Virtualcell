"""§11.3 LRU + 空闲 TTL 会话池。QueryEngine 不常驻全量:命中复用,
未命中调用方从 store 重建。**驱逐只丢内存副本,权威态在 store**
(§11.8 有状态点清单:会话热缓存可丢失可重建,丢失不破坏正确性)。

池 key 含 user_id(§11.6 多租户:不同 user 同 session_id 不串)。
内存池等价单 worker 热缓存——多 worker 下各 worker 各自池,权威态
统一在 store(无 sticky,横扩前提,§11.3)。"""

import time
from collections import OrderedDict
from typing import Any


class SessionPool:
    """LRU(max_size 上限)+ 空闲 TTL(idle_ttl_s)双驱逐。
    get 命中刷新最近使用 + 续期;过期即驱逐返回 None。"""

    def __init__(self, *, max_size: int, idle_ttl_s: float) -> None:
        self._max = max_size
        self._ttl = idle_ttl_s
        # key -> (value, last_access_ts);OrderedDict 末尾=最近使用
        self._d: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    @staticmethod
    def _key(user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"  # 含 user_id:多租户隔离(§11.6)

    def get(self, user_id: str, session_id: str) -> Any | None:
        k = self._key(user_id, session_id)
        item = self._d.get(k)
        if item is None:
            return None
        value, ts = item
        if time.monotonic() - ts > self._ttl:
            del self._d[k]  # 空闲超 TTL → 驱逐(权威态在 store,可重建)
            return None
        self._d.move_to_end(k)  # 刷新 LRU 最近使用
        self._d[k] = (value, time.monotonic())  # 续期
        return value

    def put(self, user_id: str, session_id: str, value: Any) -> None:
        k = self._key(user_id, session_id)
        self._d[k] = (value, time.monotonic())
        self._d.move_to_end(k)
        while len(self._d) > self._max:
            self._d.popitem(last=False)  # 驱逐最久未用(只丢内存副本)
