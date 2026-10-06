"""MDR ensembler:弃 agents/ensemble.py 的 delta 向量假设,按 output_kind 分派聚合语义。

  mic_scalar   log2 尺度几何均值(MIC 天然对数分布);分歧=预测间 log2 极差
  sir_class    S/I/R 概率均值 + argmax;分歧=mean class entropy(越均匀=越分歧)
  synergy      FIC 指数均值;分歧=极差
  sm_activity  log10-MIC 尺度均值(化合物活性同 log 分布);分歧=预测间 log10 极差

只聚合 status==success;rejected/failed 单列。空/单模型语义明确。混 output_kind 报错
(同一 drug 的一次预测不得混标量与分类)。分歧值交由 abstain(model_disagreement_too_high)判。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MDRPredictorResult:
    agent_name: str
    status: str                       # success/rejected/failed
    output_kind: str                  # mic_scalar/sir_class/synergy/...
    prediction: dict[str, Any] | None
    uncertainty: dict[str, Any] | None
    evidence: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleResult:
    output_kind: str | None
    ensemble: dict[str, Any] | None
    disagreement: dict[str, Any]
    models_used: list[str] = field(default_factory=list)
    models_rejected: list[str] = field(default_factory=list)
    models_failed: list[str] = field(default_factory=list)


_SIR_LABELS = ("S", "I", "R")


def _entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0.0)


def aggregate(results: list[MDRPredictorResult]) -> EnsembleResult:
    used = [r for r in results if r.status == "success"]
    used_names = [r.agent_name for r in used]
    rejected = [r.agent_name for r in results if r.status == "rejected"]
    failed = [r.agent_name for r in results if r.status == "failed"]

    if not used:
        return EnsembleResult(None, None,
                              {"score": None, "reason": "no_models"},
                              [], rejected, failed)

    kinds = {r.output_kind for r in used}
    if len(kinds) > 1:
        raise ValueError(f"一次聚合不得混 output_kind:{sorted(kinds)}")
    kind = kinds.pop()

    if kind == "mic_scalar":
        logs = [math.log2(r.prediction["mic_scalar"]) for r in used]
        mean_log = sum(logs) / len(logs)
        ens = {"mic_scalar": 2.0 ** mean_log}
        dis = {"metric": "log2_range",
               "log2_range": (max(logs) - min(logs)) if len(logs) > 1 else 0.0,
               "n_models": len(logs)}
        # 归一到 [0,1] 供 abstain 阈值:log2_range/8 截断(8 个 doubling ≈ 满分歧)
        dis["score"] = min(1.0, dis["log2_range"] / 8.0)

    elif kind == "sir_class":
        acc = {lbl: 0.0 for lbl in _SIR_LABELS}
        for r in used:
            pr = r.prediction["sir_prob"]
            for lbl in _SIR_LABELS:
                acc[lbl] += pr.get(lbl, 0.0)
        probs = {lbl: acc[lbl] / len(used) for lbl in _SIR_LABELS}
        sir = max(_SIR_LABELS, key=lambda l: probs[l])
        ens = {"sir_prob": probs, "sir": sir}
        ent = _entropy([probs[l] for l in _SIR_LABELS])
        dis = {"metric": "mean_class_entropy", "entropy": ent,
               "score": ent / math.log2(len(_SIR_LABELS)),  # 归一 [0,1]
               "n_models": len(used)}

    elif kind == "synergy":
        fics = [r.prediction["fic_index"] for r in used]
        ens = {"fic_index": sum(fics) / len(fics)}
        rng = (max(fics) - min(fics)) if len(fics) > 1 else 0.0
        dis = {"metric": "fic_range", "fic_range": rng,
               "score": min(1.0, rng), "n_models": len(fics)}

    elif kind == "sm_activity":
        # 化合物活性天然 log 分布(同 MIC),在 log10-MIC 尺度取均值;分歧=预测间 log10 极差
        logs = [r.prediction["log10_mic"] for r in used]
        mean_log = sum(logs) / len(logs)
        # 不确定度=各模型 RF std 均值;化学近邻度 max_tanimoto 取最保守(min);is_ood 任一为真
        stds = [(r.uncertainty or {}).get("sigma") for r in used]
        stds = [s for s in stds if s is not None]
        tans = [r.prediction.get("max_tanimoto") for r in used
                if r.prediction.get("max_tanimoto") is not None]
        ens = {"log10_mic": mean_log, "mic_ug_ml": 10.0 ** mean_log,
               "uncertainty_std": (sum(stds) / len(stds)) if stds else None,
               "max_tanimoto": min(tans) if tans else None,
               "is_ood": any(bool(r.prediction.get("is_ood")) for r in used)}
        rng = (max(logs) - min(logs)) if len(logs) > 1 else 0.0
        dis = {"metric": "log10_range", "log10_range": rng,
               "n_models": len(logs)}
        # 归一到 [0,1] 供 abstain 阈值:4 个数量级(log10 差 4)≈ 满分歧
        dis["score"] = min(1.0, rng / 4.0)

    elif kind == "peptide_activity":
        # 抗菌肽活性同 log 分布,log10-MIC(µM)尺度均值;序列近邻度 max_jaccard 取最保守(min)
        logs = [r.prediction["log10_mic"] for r in used]
        mean_log = sum(logs) / len(logs)
        stds = [(r.uncertainty or {}).get("sigma") for r in used]
        stds = [s for s in stds if s is not None]
        jacs = [r.prediction.get("max_jaccard") for r in used
                if r.prediction.get("max_jaccard") is not None]
        ens = {"log10_mic": mean_log, "mic_um": 10.0 ** mean_log,
               "uncertainty_std": (sum(stds) / len(stds)) if stds else None,
               "max_jaccard": min(jacs) if jacs else None,
               "is_ood": any(bool(r.prediction.get("is_ood")) for r in used)}
        rng = (max(logs) - min(logs)) if len(logs) > 1 else 0.0
        dis = {"metric": "log10_range", "log10_range": rng, "n_models": len(logs)}
        dis["score"] = min(1.0, rng / 4.0)

    else:
        raise ValueError(f"未支持聚合的 output_kind:{kind}")

    return EnsembleResult(kind, ens, dis, used_names, rejected, failed)
