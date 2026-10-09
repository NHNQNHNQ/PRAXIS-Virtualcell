"""ActiveLearningAgent(插点 D,进 message bus):产 learning_queue(该测什么的优先队列)。

收 learning_queue_request({report, evidence_level})→ 从 report.provenance.module_plan.entries
+ report 信号(disagreement/OOD/evidence/module 弱支持)派生候选 → acquisition.information_gain
打分 → LearningQueue(降序)→ emit learning_queue_ready。

铁律(不碰裁决):只读 report/evidence_level,只 emit learning_queue;不改 report 任何键、
不回写 verdict、不新增 provenance ledger 条目。abstain 请求可建议补弱模块数据,但不把 abstain 改 accept。
无 module_plan / 无候选 → 空队列 + note(不虚构,红线 6)。零 LLM。
"""
from __future__ import annotations

from praxis_virtualcell.active_learning.acquisition import information_gain
from praxis_virtualcell.active_learning.learning_queue import LearningQueue, LearningQueueItem
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.evidence_level import derive_ood_signal

# 弱支持判据(该补数据)
_WEAK_SUPPORT = {"weak", "unsupported"}


class ActiveLearningAgent(BaseAgent):
    name = "ActiveLearningAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload.get("report", {}) or {}
        ev = message.payload.get("evidence_level", {}) or {}
        ev_level = ev.get("level", "")
        plan = (report.get("provenance") or {}).get("module_plan") or {}
        entries = plan.get("entries") or []
        species = str((report.get("request") or {}).get("species", "")).lower()
        targets = [str(t).strip() for t in
                   ((report.get("request") or {}).get("perturbation_targets") or []) if str(t).strip()]
        target_tag = ",".join(targets) if targets else "unspecified"

        dis = report.get("model_disagreement") or {}
        dis_score = dis.get("score")
        dis_triggered = bool(dis.get("triggered"))
        ood = derive_ood_signal(report)

        items: list[LearningQueueItem] = []
        notes: list[str] = []
        if not entries:
            notes.append("no_module_plan_no_candidates")   # 不可路由请求 → 无有意义候选(红线 6)
            queue = LearningQueue(items=[], notes=notes)
            self._emit(message, bus, queue)
            return

        for e in entries:
            mid = e.get("module")
            weak = (e.get("species_support") in _WEAK_SUPPORT) or bool(e.get("data_gated"))
            signals = {
                "disagreement_score": dis_score,
                "disagreement_triggered": dis_triggered,
                "ood_signal": ood,
                "evidence_level": ev_level,
                "module_weak": weak,
            }
            gain = information_gain(signals)
            drivers: list[str] = []
            if dis_triggered:
                drivers.append("disagreement_high")
            if ood in ("ood", "unknown"):
                drivers.append(f"ood_{ood}")
            if ev_level in ("E3", "E4", "E5"):
                drivers.append(f"evidence_{ev_level}")
            if weak:
                drivers.append("module_weak")
            items.append(LearningQueueItem(
                candidate=f"{mid}@{species}:{target_tag}",
                module=mid, information_gain=gain, drivers=drivers,
                rationale=f"module={mid} support={e.get('species_support')} "
                          f"gated={bool(e.get('data_gated'))} evidence={ev_level} ood={ood}"))
        if report.get("abstain"):
            notes.append("request_abstained_candidates_are_data_gap_suggestions")  # 不改 abstain,仅建议补数据
        queue = LearningQueue(items=items, notes=notes)
        self._emit(message, bus, queue)

    def _emit(self, message: AgentMessage, bus: MessageBus, queue: LearningQueue) -> None:
        bus.send(AgentMessage(
            message_id=message.message_id + ":alq",
            sender=self.name, receiver="client",
            message_type="learning_queue_ready",
            payload={"learning_queue": queue.to_dict()},
            timestamp=message.timestamp, parent_message_id=message.message_id))
