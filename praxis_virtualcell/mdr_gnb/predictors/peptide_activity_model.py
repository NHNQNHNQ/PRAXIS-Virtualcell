"""抗菌肽活性模型:序列 → log10-MIC(µM)回归(理化+组成特征 + RF),自带序列 OOD。

线B B5-肽 的核心科学件,仿 SmallMoleculeModel(小分子):把 B5 baseline 验证过的方法
(peptide_vector 20 组成+6 理化 + RF,序列相似度连通分量防泄漏下 R²=0.29 优于均值/1-NN)固化成
可加载 artifact,供 default_registry 的 peptide_activity predict 闭包按 species 惰性加载。

自包含 artifact(joblib):RF + 训练序列的 k-mer 集(供序列 OOD 判据)+ 配置。predict_one 只报事实
(预测值 / 对训练集最大 k-mer Jaccard / 是否 OOD),abstain 决策留给闭包。**确定性**:predict 用
tree_preds 固定顺序均值(不调 rf.predict,避 RF 并行累加 ULP 噪声)。序列 OOD = 对训练集最大 Jaccard
(k-mer)——肽的"序列空间外"对应小分子的"化学空间外",与 B5 baseline 同款。
"""
from __future__ import annotations

import numpy as np

from praxis_virtualcell.mdr_gnb.drug_agent.peptide_features import peptide_vector

KMER = 3                    # 序列 OOD 的 k-mer 长度(与 B5 baseline 一致)

# --- Phase 16:加法方向长度 sanity gate 常数(独立于 k-mer Jaccard 集合相似度)-----------
# k-mer Jaccard 对"加重复单元"单调不减,对超长序列**失明** —— Magainin-2×500(11500 残基)拿到
# 高 Jaccard 绕过 OOD 拿自信 MIC。补长度判据拦之。
# PEP_LEN_MAX = ceil(1.5×训练 max 53)= 80(spike 全量 774 序列实测,长度 max=53;派生出处见
# docs/superpowers/plans/2026-07-16-phase16-ood-additivity-gate.md §4。零误伤见 golden 负向门,
# 漂移守卫从 parquet 重算断言)。
PEP_LEN_MAX = 80


def _kmers(seq: str, k: int = KMER) -> frozenset:
    """序列的 k-mer 集合(序列相似度基元)。短于 k 时退化为整串。"""
    if len(seq) < k:
        return frozenset({seq})
    return frozenset(seq[i:i + k] for i in range(len(seq) - k + 1))


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _max_jaccard(q: frozenset, train_kms: list) -> float:
    """查询序列 k-mer 集对训练集的最大 Jaccard(序列 OOD 判据)。空训练集返 0.0。"""
    if not train_kms:
        return 0.0
    return max(_jaccard(q, tk) for tk in train_kms)


class PeptideActivityModel:
    """序列 → log10-MIC(µM)回归 + 序列 OOD。artifact 自包含,加载确定性。"""

    def __init__(self, ood_threshold: float = 0.3, n_estimators: int = 300,
                 random_state: int = 0, kmer: int = KMER):
        self.ood_threshold = ood_threshold      # 对训练集最大 k-mer Jaccard 低于此 = 序列空间外
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.kmer = kmer
        self._rf = None
        self._train_kms: list = []              # 训练序列的 k-mer 集(供 OOD)
        self.train_size = 0
        self.n_invalid_dropped = 0

    # ---- 训练 ----
    def fit(self, sequences: list[str], y: list[float]) -> "PeptideActivityModel":
        """在 (序列, log10-MIC) 上训 RF;丢弃 invalid 序列并计数;存训练 k-mer 集供 OOD。"""
        from sklearn.ensemble import RandomForestRegressor

        X_rows, y_keep, train_kms = [], [], []
        n_invalid = 0
        for seq, yi in zip(sequences, y):
            try:
                vec = peptide_vector(seq)
            except ValueError:                  # invalid 序列(非标准 AA/空)诚实丢弃
                n_invalid += 1
                continue
            X_rows.append(vec)
            y_keep.append(float(yi))
            train_kms.append(_kmers(seq, self.kmer))
        if not X_rows:
            raise ValueError("无有效肽序列,无法训练")
        X = np.asarray(X_rows, dtype=np.float64)
        yv = np.asarray(y_keep, dtype=float)
        self._rf = RandomForestRegressor(n_estimators=self.n_estimators,
                                         random_state=self.random_state, n_jobs=-1)
        self._rf.fit(X, yv)
        self._train_kms = train_kms
        self.train_size = X.shape[0]
        self.n_invalid_dropped = n_invalid
        return self

    # ---- 预测(只报事实,abstain 决策留给闭包)----
    def predict_one(self, sequence: str) -> dict:
        """单肽预测。ok=False → invalid 序列(invalid_sequence)/加法方向 gate 触发
        (peptide_length_out_of_range);ok=True → log10_mic/mic_um/max_jaccard/is_ood/std。"""
        if self._rf is None:
            return {"ok": False, "reason": "model_not_fitted"}
        try:
            vec = peptide_vector(sequence)
        except ValueError:
            return {"ok": False, "reason": "invalid_sequence"}
        # --- Phase 16:加法方向长度 sanity gate(独立于下方 k-mer Jaccard,fail-closed 弃权)----
        # 置于特征化之后:非法字符集仍先归为 invalid_sequence(更精准);合法但超长(如 Magainin×500)
        # 才走长度 gate。k-mer Jaccard 对"加重复单元"单调失明,这里用长度判据补缺口。
        if len(sequence) > PEP_LEN_MAX:
            return {"ok": False, "reason": "peptide_length_out_of_range"}
        X = vec.reshape(1, -1)
        # 逐树固定顺序均值 → 确定性(不调 rf.predict 的并行累加)
        tree_preds = np.array([t.predict(X)[0] for t in self._rf.estimators_])
        log10_mic = float(tree_preds.mean())
        std = float(tree_preds.std())
        max_jac = _max_jaccard(_kmers(sequence, self.kmer), self._train_kms)
        return {
            "ok": True,
            "log10_mic": log10_mic,
            "mic_um": float(10.0 ** log10_mic),
            "max_jaccard": max_jac,
            "is_ood": bool(max_jac < self.ood_threshold),
            "std": std,
        }

    # ---- 持久化 ----
    def save(self, path) -> None:
        import joblib
        from pathlib import Path

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path) -> "PeptideActivityModel":
        import joblib

        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"artifact 不是 {cls.__name__}:{type(obj)!r}")
        return obj
