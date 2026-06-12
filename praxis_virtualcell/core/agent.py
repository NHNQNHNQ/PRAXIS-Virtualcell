"""agent 基类:只经 bus 产出,不返回值、不互调他者内部方法。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class BaseAgent(ABC):
    name: str = "BaseAgent"

    @abstractmethod
    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        """读 message,做工作,经 bus.send 产出 0..n 条输出消息。"""
