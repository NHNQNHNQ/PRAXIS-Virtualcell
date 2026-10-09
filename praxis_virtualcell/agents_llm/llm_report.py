"""Convert a structured report to English prose while preserving abstention, used/rejected models, reliability, and
provenance without fabrication.
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (

        'Rewrite the structured virtual cell prediction report as concise English scientific '
        'prose. Faithfully preserve whether the system abstained, which models were used or '
        'rejected, reliability, and key provenance. Do not invent numerical predictions or '
        'conclusions absent from the report. Return narrative text only, without JSON.'

)


class LLMReportAgent(BaseAgent):
    name = "LLMReport"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload["report"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(report, ensure_ascii=False)}],
            max_tokens=800)
        narrative = res.get("content") or ""
        bus.send(AgentMessage(message.message_id + ":llmrep", self.name, "client",
            "llm_narrative", {"narrative": narrative}, message.timestamp, message.message_id))
