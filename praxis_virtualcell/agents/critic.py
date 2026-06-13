"""审 trace 诚实性:retrieve-before-predict、ensemble 完整、abstain 诚实、provenance 完整、
不确定性报告、物种一致、abstain/prediction 一致。deterministic(无 LLM);只记 violation,不改 prediction。
注:本 critic 跑在 Report 之前,审 reliability_decided payload 底料(保 offline 报告结构诚实);
语义级审查 LLMReport.narrative 由 LLMCriticAgent(需 key)负责,本 agent 不覆盖 §8.5 的 LLM 部分。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class CriticAgent(BaseAgent):
    name = "Critic"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        bc = p.get("brain_context", {}) or {}
        req = p.get("request", {}) or {}
        rd = p.get("reliability_decision", {}) or {}
        abstain = bool(rd.get("abstain"))
        results = p.get("results", []) or []
        used = set(p.get("models_used", []))
        ensemble = p.get("ensemble")
        appmap = bc.get("model_applicability") or {}
        species = req.get("species")
        notes: list[str] = []
        violations: list[str] = []
        types = [m.message_type for m in bus.trace]
        # 1. retrieve-before-predict
        if "predictor_result" in types:
            if "brain_retrieved" not in types or types.index("brain_retrieved") > types.index("predictor_result"):
                violations.append("predict_before_retrieve")
        # 2. rejected 不得出现在 models_used
        rejected = {r["agent_name"] for r in results if r["status"] != "success"}
        if used & rejected:
            violations.append(f"rejected_model_in_ensemble:{sorted(used & rejected)}")
        # 3. 声称预测但无 success 结果且未 abstain
        if not used and not abstain:
            violations.append("claims_prediction_without_predictor")
        # 4. provenance 完整(§8.4):非 abstain 却无 rules_referenced = 不可追溯(abstain 路径允许空,见 species_brain)
        if not abstain and not (bc.get("rules_referenced") or []):
            violations.append("missing_provenance")
        # 5. success 漏报不确定性(诚实性):success predictor 须带 uncertainty.sigma
        no_sigma = sorted(r["agent_name"] for r in results if r.get("status") == "success"
                          and (r.get("uncertainty") is None or "sigma" not in (r.get("uncertainty") or {})))
        if no_sigma:
            violations.append(f"missing_uncertainty:{no_sigma}")
        # 6. 未被 brain 支持物种的 predictor 进了 used(防御性不变量;正常路由不应命中,抓汇总 bug)
        if species is not None:
            bad = sorted(n for n in used if n in appmap
                         and species not in (appmap[n].get("supported_species") or []))
            if bad:
                violations.append(f"unsupported_species_in_ensemble:{bad}")
        # 7. abstain 与 prediction 残留矛盾(abstain=True 却 payload 仍有 ensemble 预测向量)
        if abstain and ensemble is not None:
            violations.append("abstain_inconsistent_with_prediction")
        notes.append(f"checked retrieve-first, ensemble integrity, abstain honesty, provenance, "
                     f"uncertainty reporting, species consistency, abstain/prediction consistency; violations={violations}")
        bus.send(AgentMessage(message.message_id + ":crit", self.name, "ProvenanceAgent",
            "critic_done", {**p, "critic_notes": notes, "critic_violations": violations},
            message.timestamp, message.message_id))
