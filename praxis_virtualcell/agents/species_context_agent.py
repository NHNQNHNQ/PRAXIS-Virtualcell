"""SpeciesContextAgent(插点 A):进 message bus,读 brains/virtualcell/<species>/module_support.yaml,
对 8 个模块逐一给 support/verdict/display_name/models/tools,并暴露 biological_mismatch 查询表。

供 ModuleRouterAgent 定 primary/secondary 模块的合法性前置。纯读 yaml,零 LLM、零管线依赖。
铁律:未声明模块 → unsupported/reject(不静默);物种别名(bacteria M3=energy/redox)经 registry.display_name。
"""
from __future__ import annotations

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class SpeciesContextAgent(BaseAgent):
    name = "SpeciesContextAgent"

    def __init__(self, registry: ModuleRegistry | None = None) -> None:
        self._reg = registry or ModuleRegistry()

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload.get("request", {})
        species = str(req.get("species", "")).strip().lower()
        module_support: dict[str, dict] = {}
        for mid in M.MODULE_ORDER:
            rec = self._reg.support(species, mid)
            module_support[mid] = {
                "support": rec["support"],
                "verdict": self._reg.default_verdict(species, mid),
                "display_name": self._reg.display_name(species, mid),
                "models": list(rec.get("models", [])),
                "tools": list(rec.get("tools", [])),
                "reason": rec.get("reason", ""),
            }
        # 暴露该物种声明的 biological_mismatch(query→verdict),供 router 命中降级
        mismatch_queries: dict[str, str] = {}
        for m in (self._reg._load(species).get("biological_mismatch") or []):
            if m.get("query"):
                mismatch_queries[m["query"]] = m.get("verdict", "caution")
        bus.send(AgentMessage(
            message_id=message.message_id + ":spctx",
            sender=self.name, receiver="ModuleRouterAgent",
            message_type="species_context_ready",
            payload={"species": species, "module_support": module_support,
                     "mismatch_queries": mismatch_queries},
            timestamp=message.timestamp, parent_message_id=message.message_id))
