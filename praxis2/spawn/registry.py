"""SpawnRegistry — 进程内 task_id → asyncio.Task 字典,用于 cancel。

设计:不持久化(进程崩 → 丢)。M11 carry 加 startup hook 把
stale running → failed。
"""
from __future__ import annotations

import asyncio


class SpawnRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def register(self, task_id: str, task: asyncio.Task) -> None:
        self._tasks[task_id] = task

    def cancel(self, task_id: str) -> bool:
        """cancel 指定 task。返 True=找到并发起 cancel,False=没找到/已完成。"""
        task = self._tasks.get(task_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def unregister(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())
