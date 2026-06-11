"""§7.5.5 完整 Task 生命周期状态机。

pending → queued → running → completed/failed/killed,每 task 独立
task_id + 元数据(M6 内存;真后端 PG 进 store,接口位)。状态变化经
pub/sub 路由到持 SSE 连接的 worker(§11.4,M6 内存 EventBus,Redis 版
integration)。**重算力 task(submitted 态)+ HPC 提交留 M7**
(总纲 §7.5.5/§11.5,M6 不碰重算力)。状态机硬约束:非法跃迁抛
(体例同 M3 core/rmcp PhaseError,代码层强制非自律)。"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    SUBMITTED = "submitted"  # M7 重算力:已交 HPC 调度器,等真正起跑
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMEOUT = "timeout"      # M7 重算力:超 wall_time_s+grace 仍未完成


# 合法跃迁表(M6 5 态全保留 + M7 重算力 submitted/timeout 扩,零回归)
_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.PENDING: frozenset({TaskState.QUEUED, TaskState.KILLED}),
    TaskState.QUEUED: frozenset({
        TaskState.RUNNING,    # M6 轻量通道(零回归)
        TaskState.SUBMITTED,  # M7 重算力通道
        TaskState.KILLED,
    }),
    TaskState.SUBMITTED: frozenset({TaskState.RUNNING, TaskState.KILLED}),
    TaskState.RUNNING: frozenset({
        TaskState.COMPLETED, TaskState.FAILED,
        TaskState.KILLED, TaskState.TIMEOUT,  # M7 新增
    }),
    TaskState.COMPLETED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.KILLED: frozenset(),
    TaskState.TIMEOUT: frozenset(),  # 终态,同 KILLED 区分:KILLED=主动,TIMEOUT=阻塞超时
}


@dataclass
class TaskRecord:
    task_id: str
    user_id: str
    session_id: str
    kind: str  # llm_chat | ...(重算力 kind + submitted 态 M7)
    state: TaskState = TaskState.PENDING
    meta: dict[str, Any] = field(default_factory=dict)


class TaskRegistry:
    """Task 元数据 + 状态机(M6 内存;真后端 PG 接口位)。
    可选 event_bus:状态变化经 pub/sub 路由跨 worker(§7.5.5/§11.4)。"""

    def __init__(self, *, event_bus: Any = None) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._bus = event_bus

    async def create(
        self, *, user_id: str, session_id: str, kind: str
    ) -> str:
        if not user_id:
            raise ValueError("Task 需非空 user_id(§11.6)")
        tid = uuid.uuid4().hex
        self._tasks[tid] = TaskRecord(
            task_id=tid, user_id=user_id, session_id=session_id, kind=kind
        )
        return tid

    async def get(self, user_id: str, task_id: str) -> "TaskRecord | None":
        rec = self._tasks.get(task_id)
        if rec is None or rec.user_id != user_id:  # 跨租户读不到(§11.6)
            return None
        return rec

    async def list_tasks(self, user_id: str) -> list[TaskRecord]:
        return [r for r in self._tasks.values() if r.user_id == user_id]

    async def transition(
        self, user_id: str, task_id: str, to: TaskState
    ) -> None:
        rec = await self.get(user_id, task_id)
        if rec is None:
            raise ValueError(f"Task {task_id!r} 不存在或跨租户(§11.6)")
        if to not in _TRANSITIONS[rec.state]:
            raise ValueError(
                f"非法 Task 跃迁:{rec.state.value} → {to.value}"
            )
        rec.state = to
        if self._bus is not None:  # §7.5.5 状态变化经 pub/sub 跨 worker 路由
            await self._bus.publish(rec.session_id, {
                "type": "task_state", "task_id": task_id,
                "state": to.value, "kind": rec.kind,
            })

    async def stop(self, user_id: str, task_id: str) -> None:
        """主动停止 → killed(running/queued/pending 均可停)。"""
        await self.transition(user_id, task_id, TaskState.KILLED)
