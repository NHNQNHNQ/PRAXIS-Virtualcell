"""ModuleRouterAgent(插点 B):进 message bus,产 ModulePlan。

收 module_route({request(归一后), module_support, mismatch_queries})→ 用 module_rules 定
primary/secondary → 对每个命中 module 复用 route_table.route() 落 engine/disposition/reason →
叠加 module_support 的 support/verdict、MODULES 的 display_name/pillars、mismatch → 合成 ModulePlan。

OFFLINE 全程零 LLM(不 import agents_llm)。LLM 版 module plan 留 Phase 4,那时 LLM 产 primary/secondary
后必须过滤成本模块的合法候选(复用"只能从候选选"约束),再走本 agent 同样的 route/verdict 合成。
铁律:物种 unsupported / mismatch → verdict 降级不 accept;route engine 与 MODULES[mid].engines
漂移 → 记 note(供 governance 检查),不崩不迁就。
"""
from __future__ import annotations

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.llm_orchestration import safety_contract as SC
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.module_plan import ModulePlan, ModulePlanEntry
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ModuleRouterAgent(BaseAgent):
    name = "ModuleRouterAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        raw = message.payload["request"]
        req = normalize_request(raw)                 # 复用归一,不自造
        module_support = message.payload.get("module_support", {})
        mismatch_queries = message.payload.get("mismatch_queries", {})
        species = req["species"]

        primary = module_rules.pick_primary(req)   # 决策 P1:primary 永由确定性规则定,LLM 不改
        notes: list[str] = []
        # Phase 4:若带 LLM 候选(module_candidates.selected),secondary 从 LLM 选中集派生
        # (决策 P2:LLM 只增删 secondary,且必 ⊆ candidate 全集)。无候选(OFFLINE)→ Phase 3 原路径。
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
        # 1) 落 engine:复用 route()(单一真相源)。
        # 注:route() 是请求级路由(非 module 级),secondary 复用同一路由结果;
        # module 级路由(每个 module 独立落 engine)留 Phase 4,避免将来漂移检查误报。
        dec = route(req)
        # 2) engine 与 module 定义漂移检查(不崩,记 note 供 governance)
        legal_engines = M.MODULES[mid]["engines"]
        if legal_engines and dec.engine not in legal_engines and dec.engine != "reject":
            notes.append(
                f"engine_module_drift: {mid} 定义 engines={legal_engines} 但 route 落 {dec.engine}")
        # 3) 物种 support/verdict(来自 SpeciesContext)
        sup = module_support.get(mid, {"support": "unsupported", "verdict": "reject",
                                       "display_name": mid, "models": [], "tools": []})
        # 4) mismatch:decision M3 推 query → SpeciesContext 暴露的 verdict
        mq = module_rules.mismatch_query_for(req, mid)
        mismatch = mismatch_queries.get(mq) if mq else None
        return ModulePlanEntry(
            module=mid,
            display_name=sup.get("display_name", M.display_name(mid, species=species)),
            role=role,
            engine=dec.engine,
            route_disposition=dec.disposition,
            species_support=sup["support"],
            species_verdict=sup["verdict"],
            caution_flags=list(dec.caution_flags),
            data_gated=dec.data_gated,
            pillars=list(M.MODULES[mid]["pillars"]),
            available_models=list(sup.get("models", [])),
            reason=dec.reason,
            mismatch=mismatch,
        )
