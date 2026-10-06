"""MDR-GNB E0-E5 证据等级薄层(Phase 4)。

复用 VC governance/evidence_level.map_evidence_level(决策 B:证据等级读现有信号映射 E0-E5,
**不重写治理、不回写 verdict、永不 promote**)。本适配器:把 MDR report 字段(abstained/
abstain_reasons/downgrade_reasons/caution_flags)转成 VC-shaped report → map → 加 combo_gate
精化(只更保守)→ 只读挂到 report.provenance.evidence_level。

红线:证据等级不领导裁决——只加 provenance 键,绝不回写 prediction/verdict/abstain;
abstain/downgrade 永不被抬成 accept 级(E2/E3)。runtime OOD seen_in_train 常态 None → unknown。
"""
from __future__ import annotations

from praxis_virtualcell.governance.evidence_level import map_evidence_level


def attach_evidence_level(report: dict, *, combo_gate_status: str | None = None,
                          disagreement: dict | None = None,
                          request: dict | None = None) -> dict:
    """读 MDR report → E0-E5,只读挂 provenance.evidence_level(返回新 dict,不 mutate 入参)。"""
    vc_report = {
        "abstain": bool(report.get("abstained")),
        "abstain_reasons": list(report.get("abstain_reasons") or []),
        "downgrade_reasons": list(report.get("downgrade_reasons") or []),
        "caution_flags": {"flags": report.get("caution_flags") or []},
        "model_disagreement": disagreement or {},
        "request": request or {},
        "seen_in_train": None,      # MDR runtime 常态 → unknown OOD(不假装 in_domain,红线)
        "reliability": None,
    }
    ev = map_evidence_level(vc_report)
    ev = dict(ev)
    ev["rationale"] = list(ev.get("rationale", []))

    # combo_gate 精化:只更保守,永不 promote(abstain 侧 E0/E1 保持)
    if combo_gate_status:
        ev["combo_gate_status"] = combo_gate_status
        ev["rationale"].append(f"combo_gate:{combo_gate_status}")
        if not vc_report["abstain"]:
            # 非 abstain 时:combo 降级/排除 → 至少 E4(降级但仍出结果,不抬成 E2/E3)
            if combo_gate_status in ("excluded", "degrade_classification"):
                ev["level"] = "E4"
                ev["rationale"].append("combo_gate_conservative_downgrade")

    # 只读挂 provenance(浅拷贝 report,不 mutate 入参;裁决字段一字不动)
    out = dict(report)
    prov = dict(report.get("provenance") or {})
    prov["evidence_level"] = ev
    out["provenance"] = prov
    return out
