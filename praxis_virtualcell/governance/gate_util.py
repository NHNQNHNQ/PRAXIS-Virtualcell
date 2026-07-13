"""三个 C2 governance gate 共用的 override helper。C1 gate 保持内联不动。
一致原则(同 C1):只 override report 对外 abstain/prediction/abstain_reasons,原判记 provenance
供审计;reliability/critic 裁决数值不经此路径(gate 只读已组装 report)。确定性,无 LLM。"""
from __future__ import annotations


def apply_governance_gate(report: dict, reason: str, prov_key: str, detail: dict) -> bool:
    """gate 命中时调用。返回是否真触发了 override(原未 abstain → True)。
    - 原未 abstain:override 对外 abstain=True/prediction=None/abstain_reasons+=reason。
    - 原已 abstain:不重复 override,仅记 provenance(gate_abstained=False)。
    两种情况都记 provenance[prov_key](detail + gate_abstained + reliability_original_abstain)。"""
    original = report.get("abstain", False)
    gated = not original
    if gated:
        report["abstain"] = True
        report["prediction"] = None
        report.setdefault("abstain_reasons", []).append(reason)
    report.setdefault("provenance", {})[prov_key] = {
        **detail, "gate_abstained": gated, "reliability_original_abstain": original}
    return gated
