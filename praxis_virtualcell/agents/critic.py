"""审 trace:retrieve-before-predict、rejected 是否被写进 used、是否声称未发生的预测。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class CriticAgent(BaseAgent):
    name = "Critic"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        notes: list[str] = []
        violations: list[str] = []
        # 1. retrieve-before-predict:trace 里 brain_retrieved 必须早于任何 predictor_result
        types = [m.message_type for m in bus.trace]
        if "predictor_result" in types:
            if "brain_retrieved" not in types or types.index("brain_retrieved") > types.index("predictor_result"):
                violations.append("predict_before_retrieve")
        # 2. rejected 不得出现在 models_used
        used = set(p.get("models_used", []))
        rejected = {r["agent_name"] for r in p.get("results", []) if r["status"] != "success"}
        if used & rejected:
            violations.append(f"rejected_model_in_ensemble:{sorted(used & rejected)}")
        # 3. 声称预测但无 success 结果且未 abstain
        rd = p.get("reliability_decision", {})
        if not used and not rd.get("abstain"):
            violations.append("claims_prediction_without_predictor")
        notes.append(f"checked retrieve-first, ensemble integrity, abstain honesty; violations={violations}")
        bus.send(AgentMessage(message.message_id + ":crit", self.name, "ProvenanceAgent",
            "critic_done", {**p, "critic_notes": notes, "critic_violations": violations},
            message.timestamp, message.message_id))
