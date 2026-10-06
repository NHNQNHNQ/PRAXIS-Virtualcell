"""build_report:结构化报告,不编造结构外结论。分离 abstain_reasons(真弃权)与
downgrade_reasons(降级但仍出结果),固定免责声明(D2:仅科研筛选,非临床用药决策)。
abstain=True 一律隐藏 prediction;critic_violations 原样透出供审计。"""
from __future__ import annotations

from typing import Any

DISCLAIMER = ("本结果由 PRAXIS-MDR-GNB 计算模型产出,仅供科研筛选,不构成临床用药决策;"
              "临床药敏须以标准化 AST 与本地折点为准。")


def _mic_range(ens: dict[str, Any] | None) -> str | None:
    if not ens or "mic_scalar" not in ens:
        return None
    m = ens["mic_scalar"]
    return f"~{m:.3g} mg/L"


def _activity(ens: dict[str, Any] | None) -> dict[str, Any] | None:
    """sm_activity 预测浮出:log10-MIC + 折算 mic(µg/mL)+ 不确定度(RF std)+ 化学近邻度 + OOD。

    B3:除标量外浮出 RF 各树 std(不确定度)、对训练集 max_tanimoto(化学近邻=可信度)、
    is_ood 标志——让报告能诚实展示"这条预测有多可信、离训练化学空间多远"。
    """
    if not ens or "log10_mic" not in ens:
        return None
    out = {"log10_mic": round(float(ens["log10_mic"]), 4),
           "mic_ug_ml": round(float(ens.get("mic_ug_ml", 10.0 ** ens["log10_mic"])), 4)}
    std = ens.get("uncertainty_std")
    out["uncertainty_std"] = round(float(std), 4) if std is not None else None
    tan = ens.get("max_tanimoto")
    out["max_tanimoto"] = round(float(tan), 4) if tan is not None else None
    out["is_ood"] = bool(ens.get("is_ood", False))
    return out


def _peptide_activity(ens: dict[str, Any] | None) -> dict[str, Any] | None:
    """peptide_activity 预测浮出:log10-MIC + mic(µM)+ 不确定度 + 序列近邻度(max_jaccard)+ OOD。

    B5-肽:仿 _activity,但肽是序列近邻度(k-mer Jaccard)而非化学 Tanimoto、单位 µM。
    """
    if not ens or "log10_mic" not in ens:
        return None
    out = {"log10_mic": round(float(ens["log10_mic"]), 4),
           "mic_um": round(float(ens.get("mic_um", 10.0 ** ens["log10_mic"])), 4)}
    std = ens.get("uncertainty_std")
    out["uncertainty_std"] = round(float(std), 4) if std is not None else None
    jac = ens.get("max_jaccard")
    out["max_jaccard"] = round(float(jac), 4) if jac is not None else None
    out["is_ood"] = bool(ens.get("is_ood", False))
    return out


def build_report(*, task_id: str, drug: str,
                 ensemble_result: dict[str, Any],
                 abstain: bool, abstain_reasons: list[str],
                 downgrade_reasons: list[str], caution_flags: list[str],
                 breakpoint_source: str, critic_violations: list[str],
                 provenance: dict[str, Any],
                 mechanism: dict[str, Any] | None = None) -> dict[str, Any]:
    kind = ensemble_result.get("output_kind")
    ens = None if abstain else ensemble_result.get("ensemble")
    return {
        "task_id": task_id,
        "drug": drug,
        "abstained": abstain,
        "mic_range": _mic_range(ens) if kind == "mic_scalar" else None,
        "sir": (ens or {}).get("sir") if kind == "sir_class" else None,
        "sir_prob": (ens or {}).get("sir_prob") if kind == "sir_class" else None,
        "activity": _activity(ens) if kind == "sm_activity" else None,
        "peptide_activity": _peptide_activity(ens) if kind == "peptide_activity" else None,
        # 机制段(B4):与 activity 分栏,互不冒充;None=非化合物查询或未跑机制融合
        "mechanism": mechanism,
        "output_kind": kind,
        "abstain_reasons": list(abstain_reasons),
        "downgrade_reasons": list(downgrade_reasons),
        "caution_flags": list(caution_flags),
        "breakpoint_source": breakpoint_source,
        "critic_violations": list(critic_violations),
        "provenance": dict(provenance),
        "disclaimer": DISCLAIMER,
    }
