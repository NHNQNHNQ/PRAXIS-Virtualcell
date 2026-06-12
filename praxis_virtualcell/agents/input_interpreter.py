"""offline:把结构化 dict 校验成 VirtualCellRequest(NL 解析是 W3 的 LLM agent)。"""
from __future__ import annotations

from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest


class InputInterpreterAgent(BaseAgent):
    name = "InputInterpreter"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = VirtualCellRequest.from_dict(message.payload["request_dict"])
        bus.send(AgentMessage(message.message_id + ":parsed", self.name,
            "BioObjectNormalizer", "request_parsed", {"request": asdict(req)},
            message.timestamp, message.message_id))
