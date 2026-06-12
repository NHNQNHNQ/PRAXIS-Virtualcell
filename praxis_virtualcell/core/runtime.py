"""注册 + 派发 + 驱动 workflow。predictor fan-out 也走 bus(no fake multi-agent)。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.exceptions import UnknownAgentError
from praxis_virtualcell.core.message import AgentMessage


class AgentRuntime:
    def __init__(self, config: RuntimeConfig, *, bus: MessageBus,
                 clock: Clock, idgen: IdGen) -> None:
        self.config = config
        self.bus = bus
        self.clock = clock
        self.idgen = idgen
        self._agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def mk_message(self, sender: str, receiver: str, message_type: str,
                   payload: dict, parent_message_id: str | None = None) -> AgentMessage:
        return AgentMessage(self.idgen.next(), sender, receiver, message_type,
                            payload, self.clock.now(), parent_message_id)

    def dispatch_message(self, message: AgentMessage) -> None:
        agent = self._agents.get(message.receiver)
        if agent is None:
            raise UnknownAgentError(f"未注册 agent: {message.receiver}")
        self.bus.send(message)
        agent.handle(message, self.bus)

    def _dispatch_collect(self, message: AgentMessage, expected_type: str) -> AgentMessage:
        self.dispatch_message(message)
        out = self.bus.latest(expected_type)
        if out is None:
            raise RuntimeError(f"{message.receiver} 未产出 {expected_type}")
        return out

    # run_workflow / export_outputs 在 Task 10 补。
