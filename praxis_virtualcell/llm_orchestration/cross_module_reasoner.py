"""Advisory cross-module LLM review: receive cross_module_review and emit llm_cross_module_notes with notes/flags.
Review biological plausibility and consistency without modifying entries, verdicts, or predictions; record
observations in provenance.
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (

        'Review the cross-module consistency and biological plausibility of a virtual cell '
        'ModulePlan. Check whether the primary/secondary combination is reasonable, whether '
        'modules conflict, and whether clearly relevant modules are missing. Provide '
        'observations and risk flags only; do not modify the plan or verdict and do not give '
        'numerical predictions. Return only JSON:{"notes":[],"flags":[]}. Use concise English '
        'labels for flags. Return only JSON.'

)


class LLMCrossModuleReasoner(BaseAgent):
    name = "LLMCrossModuleReasoner"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        module_plan = message.payload["module_plan"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(module_plan, ensure_ascii=False)}],
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
        bus.send(AgentMessage(
            message_id=message.message_id + ":xmod",
            sender=self.name, receiver="client",
            message_type="llm_cross_module_notes", payload=out,
            timestamp=message.timestamp, parent_message_id=message.message_id))
