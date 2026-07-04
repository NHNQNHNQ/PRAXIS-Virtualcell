"""acquisition:information gain 启发式优先级分(纯函数,确定性,零 LLM/随机)。

诚实(避免过度承诺):这是 **v1 启发式优先级分**(deterministic heuristic),**不是**贝叶斯期望
信息增益(EIG)的严格计算。用现有确定性信号加权:分歧越高、越 OOD、证据越弱、模块越弱 → 越该优先测。
可复现(无 wall-clock/随机),缺信号 fail-safe 到 0 基线(不崩、不 NaN)。
"""
from __future__ import annotations

# 权重常量(确定性;调参留 v1.2.x,当前为可解释的等权量级)
_W_DISAGREEMENT = 1.0
_W_DIS_TRIGGERED = 0.5
_W_OOD = {"ood": 1.0, "unknown": 0.6, "in_domain": 0.0}
# 证据等级 → gain 贡献(E2 最低=最该少测,E5 最高=最该测;E0/E1 abstain 由 agent 侧决定是否入队)
_W_EVIDENCE = {"E0": 0.2, "E1": 0.3, "E2": 0.0, "E3": 0.4, "E4": 0.8, "E5": 1.0}
_W_MODULE_WEAK = 0.5


def information_gain(signals: dict) -> float:
    """确定性加权。signals 键(全可选,缺则 fail-safe 到 0 贡献):
    disagreement_score(float)、disagreement_triggered(bool)、ood_signal(str)、
    evidence_level(str E0..E5)、module_weak(bool)。"""
    dis = signals.get("disagreement_score")
    dis = float(dis) if isinstance(dis, (int, float)) else 0.0
    g = _W_DISAGREEMENT * max(0.0, min(1.0, dis))
    if signals.get("disagreement_triggered"):
        g += _W_DIS_TRIGGERED
    g += _W_OOD.get(str(signals.get("ood_signal", "")), 0.0)
    g += _W_EVIDENCE.get(str(signals.get("evidence_level", "")), 0.0)
    if signals.get("module_weak"):
        g += _W_MODULE_WEAK
    return round(g, 6)
