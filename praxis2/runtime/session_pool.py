import time
from collections import OrderedDict
from typing import Any


class SessionPool:
    def __init__(self, *, max_size: int, idle_ttl_s: float) -> None:
        self._max = max_size
        self._ttl = idle_ttl_s

        self._d: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    @staticmethod
    def _key(user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"

    def get(self, user_id: str, session_id: str) -> Any | None:
        k = self._key(user_id, session_id)
        item = self._d.get(k)
        if item is None:
            return None
        value, ts = item
        if time.monotonic() - ts > self._ttl:
            del self._d[k]
            return None
        self._d.move_to_end(k)
        self._d[k] = (value, time.monotonic())
        return value

    def put(self, user_id: str, session_id: str, value: Any) -> None:
        k = self._key(user_id, session_id)
        self._d[k] = (value, time.monotonic())
        self._d.move_to_end(k)
        while len(self._d) > self._max:
            self._d.popitem(last=False)
