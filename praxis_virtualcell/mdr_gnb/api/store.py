"""内存 job store(阶段 9.1)。按 task_id 存预测记录,供 /trace 取回。
单进程科研工具定位;9.2 起可叠加 SQLite/PG 持久化(store 接口保持不变)。"""
from __future__ import annotations

from typing import Any


class JobStore:
    """线程安全无关的简单内存字典(TestClient 单线程;生产单进程 uvicorn)。
    每个 app 实例独占一个 → 测试隔离。"""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def put(self, task_id: str, record: dict[str, Any]) -> None:
        self._jobs[task_id] = record

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self._jobs.get(task_id)

    def has(self, task_id: str) -> bool:
        return task_id in self._jobs

    def all_ids(self) -> list[str]:
        return list(self._jobs.keys())
