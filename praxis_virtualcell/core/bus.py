"""Message bus as the sole agent communication channel; record a complete replayable trace."""

from __future__ import annotations

import json
from dataclasses import asdict

from praxis_virtualcell.core.exceptions import SchemaError
from praxis_virtualcell.core.message import AgentMessage

_REQUIRED = ("message_id", "sender", "receiver", "message_type", "timestamp", "schema_version")


class MessageBus:
    def __init__(self) -> None:
        self._trace: list[AgentMessage] = []
        self._inbox: dict[str, list[AgentMessage]] = {}
        self._ctx: dict[str, str] = {}

    def set_context(self, *, trace_id: str, task_id: str) -> None:
        """Inject the current run's trace_id/task_id during build/run for send() to populate."""
        self._ctx = {"trace_id": trace_id, "task_id": task_id}

    def _backfill(self, message: AgentMessage) -> None:
        if message.trace_id is None:
            message.trace_id = self._ctx.get("trace_id") or f"trace_{message.message_id}"
        if message.task_id is None:
            message.task_id = self._ctx.get("task_id") or f"task_{message.message_id}"

    def _validate(self, message: AgentMessage) -> None:

        for f in _REQUIRED:
            if not getattr(message, f):
                raise SchemaError(f"message missing required field: {f}")

        if not isinstance(message.payload, dict):
            raise SchemaError(
                f"payload must be a dict (free-text handoffs are forbidden); received: {type(message.payload).__name__}"
            )

    def send(self, message: AgentMessage) -> None:
        self._validate(message)
        self._backfill(message)
        self.record_trace(message)
        self._inbox.setdefault(message.receiver, []).append(message)

    def record_trace(self, message: AgentMessage) -> None:
        self._trace.append(message)

    def get_messages(self, agent_name: str) -> list[AgentMessage]:
        return list(self._inbox.get(agent_name, []))

    @property
    def trace(self) -> list[AgentMessage]:
        return list(self._trace)

    def has_message_type(self, message_type: str) -> bool:
        return any(m.message_type == message_type for m in self._trace)

    def latest(self, message_type: str) -> AgentMessage | None:
        for m in reversed(self._trace):
            if m.message_type == message_type:
                return m
        return None

    def export_trace(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self._trace], f, ensure_ascii=False, indent=2)
