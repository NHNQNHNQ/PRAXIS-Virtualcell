"""Review overstatement, rule violations, omitted uncertainty, and rejected models described as used. Emit notes
and flags without altering predictions.
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (

        'Audit the honesty of a virtual cell prediction report. Check whether rejected models '
        'are described as used, whether claims are overstated, whether uncertainty is '
        'omitted, or whether a prediction is given despite abstention. Return only '
        'JSON:{"notes":[],"flags":[]}. Use concise English labels for flags. Return only JSON.'

)


class LLMCriticAgent(BaseAgent):
    name = "LLMCritic"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload["report"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(report, ensure_ascii=False)}],
            json_mode=True)
        out = {"notes": [], "flags": []}
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                notes, flags = d.get("notes"), d.get("flags")






                out["notes"] = [n for n in notes if isinstance(n, str)] if isinstance(notes, list) else []
                out["flags"] = [f for f in flags if isinstance(f, str)] if isinstance(flags, list) else []




            except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
                out["flags"] = ["llm_parse_failed"]
        else:
            out["flags"] = ["llm_unavailable"]
        bus.send(AgentMessage(message.message_id + ":llmcrit", self.name, "client",
            "llm_critic_notes", out, message.timestamp, message.message_id))
