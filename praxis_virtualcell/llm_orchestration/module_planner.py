"""Generate module candidates from an LLM, sanitize to the allowed set, and hand them to deterministic
ModuleRouter. The LLM cannot create authoritative ModulePlan, set engines/verdicts/predictions, or override hard
rules. Failure falls back to the deterministic primary; all 3 authority flags remain False.
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC

_SYS = (

        'Suggest biological function modules for a virtual cell experiment. Return only '
        'JSON:{"selected_modules":[],"reasoning_summary":"","risk_flags":[]}.Module names in '
        'selected_modules must come from the supplied candidates; do not invent names or '
        'select outside the candidate list. Select relevant modules only; do not choose '
        'engines, give numerical predictions, or change verdicts. Return only JSON.'

)


class LLMModulePlanner(BaseAgent):
    name = "LLMModulePlanner"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        raw = message.payload["request"]
        req = normalize_request(raw)
        module_support = message.payload.get("module_support", {})
        mismatch_queries = message.payload.get("mismatch_queries", {})
        primary = module_rules.pick_primary(req)
        candidates = SC.build_candidate_modules(req, module_support)

        user = json.dumps({"request": raw, "candidates": candidates,
                           "deterministic_primary": primary}, ensure_ascii=False)
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
            json_mode=True)
        mc = SC.sanitize_llm_plan(res.get("content"), candidates, primary=primary)
        mc["selected"] = mc.pop("selected_modules")
        bus.send(AgentMessage(
            message_id=message.message_id + ":mcllm",
            sender=self.name, receiver="ModuleRouterAgent",
            message_type="module_candidates_llm",
            payload={"request": raw, "module_support": module_support,
                     "mismatch_queries": mismatch_queries, "module_candidates": mc},
            timestamp=message.timestamp, parent_message_id=message.message_id))
