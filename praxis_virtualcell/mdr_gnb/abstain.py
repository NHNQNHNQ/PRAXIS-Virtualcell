"""GNB abstain 硬规则(确定性,fail-closed)。任一触发即 abstain,原因全量报告(不短路)。
阈值集中此处,供审计;由 reliability/coordinator 在预测前调用,拦截不可靠预测。"""
from __future__ import annotations

from dataclasses import dataclass, field

MIN_MIC_SAMPLES = 30           # G2 组合门:MIC 回归最低样本数,不足降分类/abstain
MAX_MODEL_DISAGREEMENT = 0.5   # ensemble 分歧上限(pairwise 距离 [0,1])


@dataclass
class AbstainContext:
    species: str
    species_confident: bool
    genome_quality_ok: bool
    drug: str
    drug_in_training_dist: bool
    mechanism_conflict: bool
    n_mic_samples: int
    model_disagreement: float
    combo_gate_status: str      # pass/degrade_classification/abstain_only/excluded


@dataclass
class AbstainDecision:
    abstain: bool
    reasons: list[str] = field(default_factory=list)


def evaluate_abstain(ctx: AbstainContext) -> AbstainDecision:
    reasons: list[str] = []
    if not ctx.species_confident:
        reasons.append("species_uncertain")
    if not ctx.genome_quality_ok:
        reasons.append("genome_quality_poor")
    if not ctx.drug_in_training_dist:
        reasons.append("drug_out_of_training_distribution")
    if ctx.mechanism_conflict:
        reasons.append("mechanism_conflict")
    if ctx.n_mic_samples < MIN_MIC_SAMPLES:
        reasons.append("insufficient_mic_samples")
    if ctx.model_disagreement > MAX_MODEL_DISAGREEMENT:
        reasons.append("model_disagreement_too_high")
    if ctx.combo_gate_status == "excluded":
        reasons.append("combo_gate_excluded")
    return AbstainDecision(abstain=bool(reasons), reasons=reasons)
