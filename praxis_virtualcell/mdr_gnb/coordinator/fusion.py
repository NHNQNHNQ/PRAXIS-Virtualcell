"""生产融合层:rule-first 融合 + 证据分层门控(G2R 成果落地)。

有意改 SIR(非 advisory):把 ML 预测与版本冻结 AMRFinderPlus 规则法融合——
  rule 判 R → 判 R(规则强信号兜底);否则用 ML(阈值 t)。
**安全保证**:rule=R 永不被翻成 S → per-ST VME ≤ 规则(G2R 已验证的核心机制)。

门控(evidence_tiers.yaml,run_g2r_evidence_sweep 产):
  strong    —— 该组合融合显著优于冻结 AMRFinderPlus,正常输出。
  practical —— 不劣于规则但未显著优于,输出带 warning。
  no_baseline —— 规则表未收录该药,无对照 → ML-only + warning(无规则验证)。
  untiered —— 未评估。

现状(Phase 1):部署 **阈值 0.5 的鲁棒版**(模型无关、恒 VME≤规则)。per-combo tuned t*
(evidence_tiers.yaml 记录)+ 机制特征重训是下一步(需模型与 t* 匹配,use_tuned_threshold=True 启用)。
确定性:yaml 读 + 规则均确定性,abstained/非 sir_class 原样返回(fail-closed 保留)。
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR

_TIERS_PATH = Path(__file__).resolve().parents[2] / "model_zoo" / "evidence_tiers.yaml"
_DB = "2024-01-frozen"

_TIER_WARNING = {
    "strong": None,
    "practical": "practical_tier:融合不劣于规则但未显著优于",
    "no_baseline": "no_baseline:冻结规则表未收录该药,ML-only 无规则验证",
    "untiered": "untiered:该组合未做 G2R 评估",
}


def evidence_tiers_from_document(document: Mapping[str, Any] | None) -> dict:
    """Normalize one already-parsed evidence document into the fusion lookup."""
    doc = document or {}
    return {(e["species"], e["drug"]): e for e in doc.get("evidence_tiers", [])}


def load_evidence_tiers(path: str | Path | None = None) -> dict:
    """读 evidence_tiers.yaml → {(species, drug): entry}。缺文件 → 空(降级 untiered)。"""
    p = Path(path or _TIERS_PATH)
    if not p.exists():
        return {}
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return evidence_tiers_from_document(doc)


def fuse_sir(sir_result: dict, *, species: str, drug: str, amr_profile: dict,
             tiers: dict | None = None, rule=None, use_tuned_threshold: bool = False) -> dict:
    """rule-first 融合 + 证据分层标签。返回新 dict(不 mutate 入参)。
    abstained/非 sir_class → 原样返回(fail-closed 保留);rule=R 永不翻 S(安全自检)。"""
    if sir_result.get("abstained") or sir_result.get("output_kind") != "sir_class":
        return dict(sir_result)
    tiers = tiers if tiers is not None else load_evidence_tiers()
    rule = rule or RuleBaselineSIR(db_version=_DB)
    genes = ",".join(k for k, v in (amr_profile or {}).items() if v)
    try:
        rule_r = 1 if rule.predict_one_genotype(drug, genes) == "R" else 0
        has_baseline = True
    except KeyError:
        rule_r, has_baseline = 0, False        # 规则表未收录该药 → no_baseline

    p_r = float((sir_result.get("sir_prob") or {}).get("R", 0.0))
    ml_sir = sir_result.get("sir")
    tinfo = tiers.get((species, drug), {})
    tier = tinfo.get("tier", "untiered")
    t_star = tinfo.get("t_star")
    t = float(t_star) if (use_tuned_threshold and t_star is not None) else 0.5

    if has_baseline:
        fused_r = (rule_r == 1) or (p_r >= t)
        method = "rule_first_fusion"
    else:
        fused_r = p_r >= 0.5
        method = "ml_only_no_baseline"
        tier = "no_baseline"
    fused_sir = "R" if fused_r else "S"
    assert not (has_baseline and rule_r == 1 and fused_sir == "S"), "融合违反安全保证:rule=R 被翻成 S"

    out = dict(sir_result)
    out["sir"] = fused_sir
    out["fusion"] = {
        "method": method, "evidence_tier": tier, "threshold": round(t, 3),
        "rule_pred": ("R" if rule_r == 1 else "S") if has_baseline else None,
        "ml_sir": ml_sir, "ml_prob_r": round(p_r, 4),
        "warning": _TIER_WARNING.get(tier),
    }
    return out
