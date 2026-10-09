"""Build ModulePlan from normalized requests, support metadata, and mismatch queries using deterministic module
rules and route_table. Unsupported/mismatched biology cannot receive accept. Engine-definition drift becomes an
audit note. Optional LLM candidates must pass the same allowlist and verdict composition.
"""
from __future__ import annotations

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.module_plan import ModulePlan, ModulePlanEntry
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC


class ModuleRouterAgent(BaseAgent):
    name = "ModuleRouterAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        raw = message.payload["request"]
        req = normalize_request(raw)
        module_support = message.payload.get("module_support", {})
        mismatch_queries = message.payload.get("mismatch_queries", {})
        species = req["species"]

        primary = module_rules.pick_primary(req)
        notes: list[str] = []


        mc = message.payload.get("module_candidates")
        if mc and mc.get("selected") is not None:
            candidates = SC.build_candidate_modules(req, module_support)
            secondary = [m for m in mc["selected"]
                         if m != primary and m in candidates]
            for flag in (mc.get("risk_flags") or []):
                notes.append(f"llm_{flag}" if not str(flag).startswith("llm_") else str(flag))
        else:
            secondary = module_rules.pick_secondary(req, primary)

        entries: list[ModulePlanEntry] = []
        for mid, role in [(primary, "primary")] + [(s, "secondary") for s in secondary]:
            entries.append(self._build_entry(
                req, species, mid, role, module_support, mismatch_queries, notes))

        plan = ModulePlan(species=species, request=req, primary=primary,
                          secondary=secondary, entries=entries, notes=notes)
        bus.send(AgentMessage(
            message_id=message.message_id + ":mplan",
            sender=self.name, receiver="EnsembleCoordinator",
            message_type="module_plan_ready", payload=plan.to_dict(),
            timestamp=message.timestamp, parent_message_id=message.message_id))

    def _build_entry(self, req, species, mid, role, module_support,
                     mismatch_queries, notes) -> ModulePlanEntry:



        dec = route(req)

        legal_engines = M.MODULES[mid]["engines"]
        if legal_engines and dec.engine not in legal_engines and dec.engine != "reject":
            notes.append(
                f"engine_module_drift: {mid} declares engines={legal_engines} but routing selected {dec.engine}")

        sup = module_support.get(mid, {"support": "unsupported", "verdict": "reject",
                                       "display_name": mid, "models": [], "tools": []})

        mq = module_rules.mismatch_query_for(req, mid)
        mismatch = mismatch_queries.get(mq) if mq else None




        disposition = dec.disposition
        caution = list(dec.caution_flags)
        reason = dec.reason
        if mid in module_rules.gene_set_secondary(req):


            if disposition in ("accept", "caution"):
                disposition = "downgrade"
            caution += [f"rule_based:{mid}_gene_set", "evidence_limited"]
            reason = (f"{reason} | rule_based_gene_set_advisory" if reason
                      else "rule_based_gene_set_advisory")

        return ModulePlanEntry(
            module=mid,
            display_name=sup.get("display_name", M.display_name(mid, species=species)),
            role=role,
            engine=dec.engine,
            route_disposition=disposition,
            species_support=sup["support"],
            species_verdict=sup["verdict"],
            caution_flags=caution,
            data_gated=dec.data_gated,
            pillars=list(M.MODULES[mid]["pillars"]),
            available_models=list(sup.get("models", [])),
            reason=reason,
            mismatch=mismatch,
        )
