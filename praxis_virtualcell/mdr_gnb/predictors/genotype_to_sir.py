"""基因型 → SIR 直接分类器(NCBI-only 适配)。

决策变更(2026-07-03):NCBI 无定量 MIC,不走计划的"MIC 回归→折点→SIR"两阶段;
改为直接在基因型 one-hot 特征上训 R vs 非R 二分类(sklearn LogisticRegression,
L2 + class_weight='balanced' 应对 R/S 不平衡)。单类训练退化为常数预测,不臆造。

**红队警示(G2)**:特征即 AMRFinderPlus 输出,与 rule_baseline 同源;ST 分组去泄漏后
本分类器相对规则法的增量可能坍缩到不显著——如实报告。
"""
from __future__ import annotations

import numpy as np


class GenotypeToSIR:
    """基因型特征 → P(R) 的二分类器。

    model:'logreg'(默认,L2 LogisticRegression)| 'rf'(RandomForest,更强非线性容量)。
    G2 复检用:同源特征下换 rf 判别瓶颈是模型容量还是特征同源(红队预期同源特征下天花板一致)。
    """

    def __init__(self, C: float = 1.0, random_state: int = 0, model: str = "logreg"):
        self.C = C
        self.random_state = random_state
        self.model = model
        self._clf = None
        self._const: int | None = None
        # 可选:特征词表(基因/突变名,与训练 X 的列一一对应),供接线时把
        # amr_profile 对齐成模型输入顺序;save 时一并存,artifact 自包含。
        self.feature_names: list[str] | None = None

    def save(self, path) -> None:
        """joblib 存整个实例(含 _clf/_const/feature_names),artifact 自包含。"""
        import joblib
        from pathlib import Path

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path) -> "GenotypeToSIR":
        """从 joblib artifact 恢复实例(需类定义在 import 路径可用)。"""
        import joblib

        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"artifact 不是 {cls.__name__}:{type(obj)!r}")
        return obj

    def fit(self, X, y) -> "GenotypeToSIR":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        classes = np.unique(y)
        if len(classes) < 2:
            # 单类:退化为常数,不臆造另一类
            self._const = int(classes[0])
            self._clf = None
            return self
        if self.model == "rf":
            from sklearn.ensemble import RandomForestClassifier

            self._clf = RandomForestClassifier(
                n_estimators=300, class_weight="balanced_subsample",
                n_jobs=-1, random_state=self.random_state,
            )
        else:
            from sklearn.linear_model import LogisticRegression

            self._clf = LogisticRegression(
                C=self.C, class_weight="balanced", max_iter=1000,
                random_state=self.random_state,
            )
        self._clf.fit(X, y)
        self._const = None
        return self

    def predict_proba_r(self, X) -> np.ndarray:
        """返回 P(R=1) 一维数组。"""
        X = np.asarray(X, dtype=float)
        if self._clf is None:
            return np.full(len(X), float(self._const), dtype=float)
        j = list(self._clf.classes_).index(1)
        if hasattr(self._clf, "estimators_"):
            # 逐树 predict_proba 按 estimators_ 固定顺序取 → 均值即 RF 的 predict_proba 定义。
            # **确定性关键**:不调 self._clf.predict_proba(它在 n_jobs 并行下按**线程完成顺序**
            # 把各树结果累加进共享数组,浮点加法不满足结合律 → 末位 ULP 随机漂 → sir_prob 变 →
            # trace_hash 不再逐字恒定,砸平台"同输入同输出"红线)。同 small_molecule_model 既有做法。
            # 列号 j 为何能直接套到树上:森林在 _validate_y_class_weight 里用
            # np.unique(y, return_inverse=True) 把 y 编码后才喂树,故 tree.classes_ 恒是 [0..K-1]
            # 编码值、**不等于** forest.classes_(标签 {3,7} 时森林 [3,7]、树 [0,1])。但 np.unique
            # 返回升序唯一值 → 编码保序 → 树 predict_proba 的第 j 列**按位置**恒对应
            # forest.classes_[j],与标签取值无关。故按位置取 j 正确。
            return np.mean([t.predict_proba(X)[:, j] for t in self._clf.estimators_], axis=0)
        return self._clf.predict_proba(X)[:, j]

    def predict(self, X, threshold: float = 0.5) -> np.ndarray:
        """按阈值(默认 0.5)输出二分类 R=1/非R=0。"""
        return (self.predict_proba_r(X) >= threshold).astype(int)
