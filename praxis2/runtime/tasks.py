import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMEOUT = "timeout"


_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.PENDING: frozenset({TaskState.QUEUED, TaskState.KILLED}),
    TaskState.QUEUED: frozenset(
        {
            TaskState.RUNNING,
            TaskState.SUBMITTED,
            TaskState.KILLED,
        }
    ),
    TaskState.SUBMITTED: frozenset({TaskState.RUNNING, TaskState.KILLED}),
    TaskState.RUNNING: frozenset(
        {
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.KILLED,
            TaskState.TIMEOUT,
        }
    ),
    TaskState.COMPLETED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.KILLED: frozenset(),
    TaskState.TIMEOUT: frozenset(),
}


@dataclass
class TaskRecord:
    task_id: str
    user_id: str
    session_id: str
    kind: str
    state: TaskState = TaskState.PENDING
    meta: dict[str, Any] = field(default_factory=dict)


class TaskRegistry:
    def __init__(self, *, event_bus: Any = None) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._bus = event_bus

    async def create(self, *, user_id: str, session_id: str, kind: str) -> str:
        if not user_id:
            raise ValueError("Task requires a nonempty user_id")
        tid = uuid.uuid4().hex
        self._tasks[tid] = TaskRecord(task_id=tid, user_id=user_id, session_id=session_id, kind=kind)
        return tid

    async def get(self, user_id: str, task_id: str) -> "TaskRecord | None":
        rec = self._tasks.get(task_id)
        if rec is None or rec.user_id != user_id:
            return None
        return rec

    async def list_tasks(self, user_id: str) -> list[TaskRecord]:
        return [r for r in self._tasks.values() if r.user_id == user_id]

    async def transition(self, user_id: str, task_id: str, to: TaskState) -> None:
        rec = await self.get(user_id, task_id)
        if rec is None:
            raise ValueError(f"Task {task_id!r}does not exist or belongs to another user")
        if to not in _TRANSITIONS[rec.state]:
            raise ValueError(f"Invalid Task transition:{rec.state.value} → {to.value}")
        rec.state = to
        if self._bus is not None:
            await self._bus.publish(
                rec.session_id,
                {
                    "type": "task_state",
                    "task_id": task_id,
                    "state": to.value,
                    "kind": rec.kind,
                },
            )

    async def stop(self, user_id: str, task_id: str) -> None:

        await self.transition(user_id, task_id, TaskState.KILLED)
