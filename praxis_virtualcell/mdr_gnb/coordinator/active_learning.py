"""MDR-GNB 主动学习 advisory(Phase 5,bacteria 特化)。

复用 VC 领域无关基础:acquisition.information_gain(确定性启发式打分)+ learning_queue.LearningQueue
(gain 降序,可序列化)。在其上叠 AMR 场景语义,产「该测什么」优先队列:
  - 被拒 drug_class(abstain)→ test_drug_class@species(补该药类阳性/阴性菌株)
  - 弱 assay(downgrade 含 mic/rule_fallback)→ switch_assay(换标准 broth microdilution)
  - 弱物种(无 SIR 模型,如 stenotrophomonas)→ bootstrap_isolates(补该物种基线菌株)
  - E2/E3 accept → refine_threshold(精修折点,refinement)

红线:advisory 只加 report.provenance.active_learning,**绝不碰 prediction/verdict/reliability/
ledger 裁决**(byte-identical);返回新 dict 不 mutate 入参。确定性零 LLM/随机。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from praxis_virtualcell.active_learning.acquisition import information_gain
from praxis_virtualcell.active_learning.learning_queue import LearningQueue

# 已训练 SIR 模型的 5 物种(127 model_zoo);其余物种视为弱支持(该 bootstrap 补菌株)
_SPECIES_WITH_SIR = {
    "escherichia_coli", "klebsiella_pneumoniae", "pseudomonas_aeruginosa",
    "acinetobacter_baumannii", "salmonella_enterica",
}
_WEAK_SUPPORT = {"weak", "unsupported"}
_ASSAY_WEAK_KEYS = ("fallback", "assay", "mic")   # downgrade 理由里判「弱 assay」的关键词


@dataclass
class AMRLearningItem:
    """AMR 主动学习候选项(该测什么)。expected_information_gain 复用 VC acquisition 打分。"""
    candidate: str                     # 该测什么(如 "test_drug_class:carbapenems@kpn")
    module: str                        # 归属八模块(多为 genetic_hub)
    action: str                        # test_drug_class / switch_assay / bootstrap_isolates / refine_threshold
    experiment_type: str               # next_experiment | refinement
    expected_information_gain: float   # acquisition.information_gain 打分
    drivers: list[str] = field(default_factory=list)
    rationale: str = ""

    @property
    def information_gain(self) -> float:   # 供 VC LearningQueue 降序排序复用
        return self.expected_information_gain

    def to_dict(self) -> dict:
        return asdict(self)


def _disposition(report: dict) -> str:
    """据现有字段派生 disposition(与 report_markdown._verdict 同序,只读不写回)。"""
    if report.get("abstained"):
        return "abstain"
    if report.get("downgrade_reasons"):
        return "downgrade"
    if report.get("caution_flags"):
        return "caution"
    return "accept"


def _plan_entries(module_plan) -> list[dict]:
    if module_plan is None:
        return []
    if hasattr(module_plan, "to_dict"):
        module_plan = module_plan.to_dict()
    return list(module_plan.get("entries") or [])


def build_amr_learning_queue(report: dict, *, evidence_level: dict | None = None,
                             module_plan=None, request: dict | None = None,
                             disagreement: dict | None = None) -> LearningQueue:
    """据 report + evidence_level(+ 可选 module_plan/request/disagreement)产 AMR advisory 队列。"""
    req = request or {}
    ev = evidence_level or {}
    ev_level = str(ev.get("level", ""))
    species = str(req.get("species", "")).strip()
    drug = str(report.get("drug", "")).strip() or "unknown_drug"
    drug_class = str(req.get("drug_class", "")).strip()
    disp = _disposition(report)
    downgrade = [str(r).lower() for r in (report.get("downgrade_reasons") or [])]

    dis = disagreement or {}
    base = {
        "disagreement_score": dis.get("score"),
        "disagreement_triggered": bool(dis.get("triggered")),
        "ood_signal": "unknown",          # MDR runtime OOD 常态 unknown(诚实,不假装 in_domain)
        "evidence_level": ev_level,
    }

    # 物种弱支持:module_plan 有弱 entry,或物种不在 SIR 模型集(已知无模型)
    entries = _plan_entries(module_plan)
    plan_weak = any(e.get("species_support") in _WEAK_SUPPORT for e in entries)
    species_weak = plan_weak or (bool(species) and species.lower() not in _SPECIES_WITH_SIR)

    sp_tag = species or "unknown_species"
    items: list[AMRLearningItem] = []
    notes: list[str] = []

    def _gain(module_weak: bool) -> float:
        return information_gain({**base, "module_weak": module_weak})

    def _drivers(extra: list[str], module_weak: bool) -> list[str]:
        d = list(extra)
        if base["disagreement_triggered"]:
            d.append("disagreement_high")
        if ev_level in ("E3", "E4", "E5"):
            d.append(f"evidence_{ev_level}")
        if module_weak:
            d.append("module_weak")
        return d

    # 规则 A —— 被拒 drug_class(abstain 或 downgrade)→ test_drug_class@species
    if disp in ("abstain", "downgrade"):
        items.append(AMRLearningItem(
            candidate=f"test_drug_class:{drug_class or drug}@{sp_tag}",
            module="genetic_hub", action="test_drug_class", experiment_type="next_experiment",
            expected_information_gain=_gain(True),
            drivers=_drivers([disp], True),
            rationale=f"disposition={disp} drug_class={drug_class or drug} → 补该药类阳/阴性菌株定标"))

    # 规则 B —— 弱 assay(downgrade 含 mic/rule_fallback)→ switch_assay
    if any(k in r for r in downgrade for k in _ASSAY_WEAK_KEYS):
        items.append(AMRLearningItem(
            candidate=f"switch_assay:broth_microdilution@{sp_tag}:{drug}",
            module="genetic_hub", action="switch_assay", experiment_type="next_experiment",
            expected_information_gain=_gain(False),
            drivers=_drivers(["weak_assay"], False),
            rationale="downgrade 仅 rule fallback/无 MIC → 换标准 broth microdilution 测真 MIC"))

    # 规则 C —— 弱物种(无 SIR 模型)→ bootstrap_isolates
    if species_weak:
        items.append(AMRLearningItem(
            candidate=f"bootstrap_isolates@{sp_tag}",
            module="genetic_hub", action="bootstrap_isolates", experiment_type="next_experiment",
            expected_information_gain=_gain(True),
            drivers=_drivers(["weak_species"], True),
            rationale=f"物种 {sp_tag} 无 SIR 模型 → 补基线菌株 bootstrap 建初版分类器"))

    # 规则 D —— E2/E3 accept → refine_threshold(refinement,精修不改裁决)
    if disp == "accept" and ev_level in ("E2", "E3"):
        items.append(AMRLearningItem(
            candidate=f"refine_threshold:{drug}@{sp_tag}",
            module="genetic_hub", action="refine_threshold", experiment_type="refinement",
            expected_information_gain=_gain(False),
            drivers=_drivers(["accept_refine"], False),
            rationale="accept 但可精修:近折点样本补测以收紧概率标定"))

    # 守卫:caution/downgrade/abstain 必产 next_experiment;accept 必产 refinement(不虚构则补兜底)
    has_next = any(it.experiment_type == "next_experiment" for it in items)
    has_refine = any(it.experiment_type == "refinement" for it in items)
    if disp in ("abstain", "downgrade", "caution") and not has_next:
        items.append(AMRLearningItem(
            candidate=f"collect_more_isolates@{sp_tag}:{drug}",
            module="genetic_hub", action="collect_isolates", experiment_type="next_experiment",
            expected_information_gain=_gain(True),
            drivers=_drivers([disp], True),
            rationale=f"disposition={disp} 无更具体候选 → 补该物种×药物菌株增证"))
    if disp == "accept" and not has_refine:
        items.append(AMRLearningItem(
            candidate=f"refine_threshold:{drug}@{sp_tag}",
            module="genetic_hub", action="refine_threshold", experiment_type="refinement",
            expected_information_gain=_gain(False),
            drivers=_drivers(["accept_refine"], False),
            rationale="accept:低优先级精修候选(近折点补测)"))

    if not items:
        notes.append("no_candidates")
    return LearningQueue(items=items, notes=notes)


def attach_active_learning(report: dict, *, evidence_level: dict | None = None,
                           module_plan=None, request: dict | None = None,
                           disagreement: dict | None = None) -> dict:
    """产 AMR advisory 队列,只读挂 report.provenance.active_learning(返回新 dict,不 mutate 入参)。"""
    queue = build_amr_learning_queue(report, evidence_level=evidence_level,
                                     module_plan=module_plan, request=request,
                                     disagreement=disagreement)
    out = dict(report)
    prov = dict(report.get("provenance") or {})
    prov["active_learning"] = queue.to_dict()
    out["provenance"] = prov
    return out
