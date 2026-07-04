"""evidence_level:E0–E5 证据等级映射(治理层之上的薄映射,纯函数,零 LLM/bus 依赖)。

决策 B(路线图 §6-B):证据等级读现有 reliability/OOD/disagreement/learned 信号映射 E0–E5,
**不重写治理、不回写 verdict**;E2=匹配扰动数据 in-domain→accept **与现有 disposition 对齐**
(不领先治理:abstain/downgrade 请求不得映射成 E2/E3 accept 级)。

runtime OOD 真实情况(实读 reliability.py:136):seen_in_train 多为 None → OOD proxy fail-closed
退回 caution_flags/非母种代理,None 时记 unknown(不假装 in_domain,红线 6)。
"""
from __future__ import annotations

# 硬拒 abstain 原因(→ E0)
_HARD_REJECT = {"species_not_supported", "all_predictors_rejected",
                "no_perturbation_specified", "no_successful_predictor"}
# 提示跨物种/OOD 的 caution flag 关键词
_OOD_CAUTION_KEYS = ("ortholog", "cross_species", "cross-species", "projected")


def derive_ood_signal(report: dict) -> str:
    """runtime OOD 信号:in_domain / ood / unknown。
    seen_in_train 优先(True=in_domain,False=ood);None → 看 caution/物种 → unknown(不假装 in_domain)。"""
    seen = report.get("seen_in_train")
    if seen in (True, 1):
        return "in_domain"
    if seen in (False, 0):
        return "ood"
    # None:runtime 常态 → 保守 unknown(即使 human 无 caution 也不当 in_domain)
    return "unknown"


def _has_ood_caution(report: dict) -> bool:
    flags = report.get("caution_flags") or {}
    blob = " ".join(str(v).lower() for v in flags.values())
    if any(k in blob for k in _OOD_CAUTION_KEYS):
        return True
    species = str((report.get("request") or {}).get("species", "")).lower()
    return bool(species) and species != "human"


def map_evidence_level(report: dict) -> dict:
    """读 report 现有信号 → E0–E5(保守优先,不回写 verdict)。返回新 dict,不 mutate report。"""
    abstain = bool(report.get("abstain"))
    reliability = report.get("reliability")
    downgrade = list(report.get("downgrade_reasons") or [])
    abstain_reasons = list(report.get("abstain_reasons") or [])
    dis = report.get("model_disagreement") or {}
    dis_triggered = bool(dis.get("triggered"))
    learned = report.get("learned_reliability") or {}
    learned_fallback = bool(learned.get("fallback"))
    ood = derive_ood_signal(report)
    rationale: list[str] = []

    # abstain 分支(E0/E1)
    if abstain:
        if any(r in _HARD_REJECT for r in abstain_reasons):
            rationale.append("hard_reject_abstain")
            level = "E0"
        else:
            rationale.append("abstain")
            level = "E1"
        return {"level": level, "rationale": rationale, "ood_signal": ood,
                "aligned_with_disposition": True}

    # 非 abstain:先处理降级/高不确定(E4/E5,不得被抬成 accept 级)
    if dis_triggered:
        rationale.append("disagreement_triggered")
    if learned_fallback:
        rationale.append("learned_fallback")
    if downgrade:
        rationale.append("downgrade")

    if dis_triggered or learned_fallback or reliability == "low":
        # 强分歧未 abstain / learned 退回 / 低可靠 → 最不确定的 accept 级
        rationale.append("high_uncertainty")
        level = "E5"
    elif downgrade:
        level = "E4"
    else:
        # accept 级(E2/E3):现有 disposition 已 accept(非 abstain、无 downgrade)
        if ood == "in_domain" and not _has_ood_caution(report) and reliability == "high":
            rationale.append("in_domain_high_reliability")
            level = "E2"
        else:
            rationale.append("accept_with_caution_or_unknown_ood")
            level = "E3"
    return {"level": level, "rationale": rationale, "ood_signal": ood,
            "aligned_with_disposition": True}
