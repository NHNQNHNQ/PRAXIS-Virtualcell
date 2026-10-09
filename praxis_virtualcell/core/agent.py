"""Agent base class: communicate through the bus rather than return results or call another agent's internal
methods.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class BaseAgent(ABC):
    name: str = "BaseAgent"

    @abstractmethod
    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        """Read a message and emit 0..n output messages through bus.send."""
