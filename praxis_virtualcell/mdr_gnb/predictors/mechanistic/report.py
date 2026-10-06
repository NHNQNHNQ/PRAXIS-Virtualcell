"""机理层报告 + gate 判定:把三支柱结果落成 reports/mechanistic/*.md,并给出
机理层能否作为机制解释来源的最终决定(D4 / Gate G3)。"""
from __future__ import annotations

from pathlib import Path

from .falsifiability import AblationResult

_DISCLAIMER = (
    "> **免责声明**:本平台为科研筛选工具,非临床用药决策依据;"
    "所有机理陈述均受本页可证伪验证结论约束,未通过验证的机制不作为解释来源。"
)


def mechanism_gate_decision(ablation: AblationResult, consistency: dict) -> dict:
    """机理层只有在(消融证明做功)且(干预一致性全过)时才允许作机制解释。"""
    allow = bool(ablation.mechanism_helps) and bool(consistency.get("all_consistent"))
    if allow:
        action = "允许:机理层可在报告中作为机制解释来源。"
    else:
        reasons = []
        if not ablation.mechanism_helps:
            reasons.append("消融显示机理层未提升预测")
        if not consistency.get("all_consistent"):
            reasons.append("干预一致性未全过")
        action = (
            "降级:" + "、".join(reasons) + ";"
            "报告仅保留'代谢靶 FBA + 其余 abstain',禁止机理话术包装 latent。"
        )
    return {"allow_mechanism_explanation": allow, "action": action}


def build_mechanistic_report(
    *,
    species: str,
    drug: str,
    ablation: AblationResult,
    consistency: dict,
    supervision: dict,
    out_dir: str | Path = "data/mdr_gnb/reports/mechanistic",
) -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    decision = mechanism_gate_decision(ablation, consistency)

    lines: list[str] = []
    lines.append(f"# 机理虚拟细胞层可证伪报告 — {species} × {drug}")
    lines.append("")
    lines.append(_DISCLAIMER)
    lines.append("")
    lines.append("## 1. 消融(机理层是否真做功)")
    lines.append("")
    lines.append(f"- 含机理层 VME: {ablation.with_mechanism['vme']:.4f}")
    lines.append(f"- 去机理层 VME: {ablation.without_mechanism['vme']:.4f}")
    lines.append(f"- ΔVME(去-含): {ablation.vme_delta:+.4f}")
    lines.append(f"- ΔMajorError(去-含): {ablation.major_error_delta:+.4f}")
    lines.append(f"- 结论:{ablation.conclusion}")
    lines.append("")
    lines.append("## 2. 干预一致性(状态是否朝已知生物学方向移动)")
    lines.append("")
    lines.append(f"- 总判定:{'全部一致' if consistency['all_consistent'] else '存在方向错误'}")
    for c in consistency["checks"]:
        flag = "✓" if c["consistent"] else "✗"
        dims = ", ".join(
            f"{d}:Δ{v['delta']:+.3f}(期望{v['expected']},{'对' if v['ok'] else '错'})"
            for d, v in c["dims"].items()
        )
        ref = "" if c["phenotype_ref_ok"] is None else f";表型对照{'通过' if c['phenotype_ref_ok'] else '不通过'}"
        lines.append(f"- [{flag}] {c['intervention']}: {dims}{ref}")
        lines.append(f"    - 生物学:{c['biology']}")
    lines.append("")
    lines.append("## 3. 独立机理监督(外排活性/β-内酰胺酶水解等相关性)")
    lines.append("")
    for dim, r in supervision.items():
        if r["status"].startswith("verified"):
            lines.append(
                f"- {dim}: {r['status']}(Spearman={r.get('spearman', float('nan')):.3f}, n={r.get('n')})"
            )
        else:
            lines.append(f"- {dim}: **未验证** — {r.get('note', '缺独立功能数据')}")
    lines.append("")
    lines.append("## 4. 最终 Gate 判定")
    lines.append("")
    lines.append(
        f"- 允许机理作机制解释: **{decision['allow_mechanism_explanation']}**"
    )
    lines.append(f"- 处置:{decision['action']}")
    lines.append("")

    path = out_dir / f"{species}_{drug}_mechanistic.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
