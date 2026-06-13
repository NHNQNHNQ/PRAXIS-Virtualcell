"""据 abstain rules + 模型分歧(§8.3) + core 失败(§8.2) + cell_type 裁 reliability/abstain。
合并 disagreement 与 core/cell_type 两路降级:abstain 类优先,降级类在非 abstain 分支各降一档。"""
from __future__ import annotations

from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage, ReliabilityDecision


class ReliabilityAgent(BaseAgent):
    name = "Reliability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        used = p.get("models_used", [])
        bc = p.get("brain_context", {})
        req = p.get("request", {})
        results = p.get("results", [])
        generic = bc.get("generic", {})
        abstain_rules = generic.get("default_abstain_rules", {}).get("abstain_if", [])
        reasons: list[str] = []
        failed: list[str] = []
        abstain = False
        # 退化输入:无有效扰动目标 → abstain
        targets = [t for t in (req.get("perturbation_targets") or []) if str(t).strip()]
        if not targets:
            abstain = True
            reasons.append("no_perturbation_specified")
        # core predictor failed(§8.2 abstain 类):核心 predictor run_prediction 抛异常 → status=='failed'
        core_set = set((generic.get("core_predictors") or {}).get("core", []))
        core_failed = [r.get("agent_name") for r in results
                       if r.get("status") == "failed" and r.get("agent_name") in core_set]
        if core_failed and "core_predictor_failed" in abstain_rules:
            abstain = True
            reasons.append("core_predictor_failed")
            failed.extend(core_failed)
        # 全 reject / species 未支持
        if not used:
            abstain = True
            if not bc.get("species_supported", True) and "species_not_supported" in abstain_rules:
                reasons.append("species_not_supported")
            reasons.append("all_predictors_rejected" if "all_predictors_rejected" in abstain_rules
                           else "no_successful_predictor")
        # model disagreement(§8.3):pairwise cosine 分歧度,阈值由 brain 配置(缺省 0.5)
        dis = p.get("disagreement")
        score = dis.get("score") if dis else None
        threshold = generic.get("default_abstain_rules", {}).get("disagreement_threshold", 0.5)
        disagreement_high = score is not None and score > threshold
        if disagreement_high and "model_disagreement_too_high" in abstain_rules:
            abstain = True
            reasons.append("model_disagreement_too_high")
            if "model_disagreement" not in failed:
                failed.append("model_disagreement")
        # reliability 基线
        if abstain:
            reliability = "low"
        elif len(used) >= 2 and p.get("ensemble"):
            reliability = "high"
        elif used:
            reliability = "medium"
        else:
            reliability = "low"
        # 降级类(非 abstain):分歧高 → 降一档;cell_type 全不覆盖 → 降一档(§8 medium-low)
        if disagreement_high and not abstain:
            reliability = "medium" if reliability == "high" else "low"
            reasons.append("downgrade:model_disagreement_too_high")  # 非 abstain 降级理由(report 可追溯,§8.4)
            if "model_disagreement" not in failed:
                failed.append("model_disagreement")
        req_ct = req.get("cell_type")
        if req_ct and used and not abstain:
            appmap = bc.get("model_applicability") or {}
            declaring = [n for n in used if appmap.get(n, {}).get("supported_cell_types") is not None]
            unsupported = [n for n in declaring if req_ct not in appmap[n]["supported_cell_types"]]
            if declaring and len(unsupported) == len(declaring):
                reasons.append("downgrade:cell_type_not_supported")  # downgrade 前缀:非 abstain,区别于 abstain 原因
                reliability = "medium" if reliability == "high" else ("low" if reliability == "medium" else reliability)
        md = {**dis, "threshold": threshold, "triggered": disagreement_high} if dis else None
        rd = ReliabilityDecision(reliability=reliability, abstain=abstain,
                                 reasons=reasons, failed_checks=failed, model_disagreement=md)
        bus.send(AgentMessage(message.message_id + ":rel", self.name, "Critic",
            "reliability_decided", {**p, "reliability_decision": asdict(rd)},
            message.timestamp, message.message_id))
