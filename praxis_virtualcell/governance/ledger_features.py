"""M2.1 Step 1:Ledger 列审计 + 无泄漏特征提取 + perturbation-level split。

**防泄漏铁律(M2 plan 坑1)**:predictor 的真实 dp 训练时知道、真实预测时不知道,
所以 `delta_pearson` / `per_predictor_delta_pearson` 只能当 **label**,**严禁当 feature**。
推理期真能算到的(分歧 / OOD flag / 路由结果)才是 feature。

把 ledger 列分三类:
- INFERENCE_FEATURES:预测新扰动时可得 → 可当特征。
- LABELS:真实准度,推理期不可得 → 只作训练目标。
- DIAGNOSTIC:现行规则决策(reliability/abstain),作 baseline 对照,不当特征。

split 必须 **perturbation-level**(坑2):ledger 每条 = 一个扰动,故按条目分组即 leave-perturbation-out。
"""
from __future__ import annotations

# 推理期可得(预测一个新扰动时就能算出来)
INFERENCE_FEATURES = (
    "disagreement_score",          # ensemble pairwise-cosine 分歧(从 3 predictor 输出算,推理可得)
    "disagreement_n_zero_pairs",   # 零向量对数(审计/退化信号)
    "disagreement_n_models",       # 参与 predictor 数
    "seen_in_train",               # OOD flag:该扰动是否在训练集(查表可得,非 ground-truth 准度)
    "n_models_used",               # 路由后实际参与数
)

# 训练标签(真实准度;推理期 N::不可得:: → 绝不可当 feature)
LABELS = (
    "delta_pearson",                  # 可靠性回归 target(该扰动整体准度)
    "per_predictor_delta_pearson",    # router label 源(argmax = best predictor)
)

# 诊断列:现行**规则**决策,作对照 baseline(不当 feature,避免与 learned 自指)
DIAGNOSTIC = ("reliability", "abstain", "abstain_reasons", "downgrade_reasons")


def _row(entry) -> dict:
    """从 LedgerEntry 取推理期特征行(只取 INFERENCE_FEATURES,seen_in_train→0/1,缺失→None)。"""
    d = entry.as_dict() if hasattr(entry, "as_dict") else dict(entry)
    out = {}
    for f in INFERENCE_FEATURES:
        if f == "n_models_used":
            out[f] = len(d.get("models_used") or [])
        elif f == "seen_in_train":
            v = d.get("seen_in_train")
            out[f] = None if v is None else int(bool(v))
        else:
            out[f] = d.get(f)
    return out


def extract_features(entries) -> list[dict]:
    """推理期特征矩阵(list of dict)。**断言不含任何 LABEL 列**(编译期防泄漏)。"""
    assert not (set(INFERENCE_FEATURES) & set(LABELS)), "feature/label 不可重叠(泄漏)"
    return [_row(e) for e in entries]


def reliability_target(entry) -> float | None:
    """可靠性回归 target = 该扰动整体 delta_pearson(label,非 feature)。"""
    d = entry.as_dict() if hasattr(entry, "as_dict") else dict(entry)
    return d.get("delta_pearson")


def router_label(entry) -> str | None:
    """router 标签 = per_predictor_delta_pearson 的 argmax(best predictor;label,非 feature)。"""
    d = entry.as_dict() if hasattr(entry, "as_dict") else dict(entry)
    pp = d.get("per_predictor_delta_pearson")
    if not pp:
        return None
    return max(pp, key=pp.get)


def leave_perturbation_out_folds(entries, k: int = 5) -> list[tuple[list[int], list[int]]]:
    """perturbation-level k-fold(坑2):每条 ledger = 一个扰动,按索引取模分 fold。
    返回 [(train_idx, test_idx), ...]。确定性(无随机),便于复现。"""
    n = len(entries)
    folds = []
    for f in range(k):
        test = [i for i in range(n) if i % k == f]
        train = [i for i in range(n) if i % k != f]
        if test and train:
            folds.append((train, test))
    return folds


def audit_columns() -> dict:
    """返回审计三分类(供 finding / 检查用)。"""
    return {"inference_features": list(INFERENCE_FEATURES),
            "labels": list(LABELS),
            "diagnostic": list(DIAGNOSTIC)}
