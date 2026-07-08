"""唯一通讯通道:agent 只经 bus 收发,不互调内部方法。bus 记全量 trace 可 replay。"""
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
        """runtime build/run 时注入本次 run 的 trace_id/task_id,供 send 回填。"""
        self._ctx = {"trace_id": trace_id, "task_id": task_id}

    def _backfill(self, message: AgentMessage) -> None:
        if message.trace_id is None:
            message.trace_id = self._ctx.get("trace_id") or f"trace_{message.message_id}"
        if message.task_id is None:
            message.task_id = self._ctx.get("task_id") or f"task_{message.message_id}"

    def _validate(self, message: AgentMessage) -> None:
        # 硬字段用 falsy 判断:空串/None 均视为缺失(schema 化 handoff 要求非空)
        # trace_id/task_id 不在此列,由 _backfill 兜底
        for f in _REQUIRED:
            if not getattr(message, f):
                raise SchemaError(f"message 缺必需字段: {f}")
        # payload 必须是结构化 dict:单独用 isinstance 校验(而非 falsy),以放行合法的空 dict {} 但拒绝自由文本字符串
        if not isinstance(message.payload, dict):
            raise SchemaError(
                f"payload 必须是 dict(禁止自由文本 handoff),实际: {type(message.payload).__name__}")

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
