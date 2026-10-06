"""小分子活性模型:SMILES → log10-MIC 回归(Morgan 指纹 + RF),自带化学 OOD。

线B(化合物结构→活性)的核心科学件。把 B0.1 qsar_baseline 验证过的方法(Morgan 指纹 +
RandomForest,scaffold split 下 R²=0.565 优于均值/1-NN)固化成**可加载 artifact**,供
default_registry 的 sm_activity predict 闭包按 species 惰性加载。

自包含 artifact(joblib):RF 回归器 + 训练集指纹(packbits 压缩,供化学 OOD 判据)+ 配置。
predict_one 只报事实(预测值 / 对训练集最大 Tanimoto / 是否 OOD),**abstain 决策留给闭包**
(fail-closed:OOD→弃权,见 default_registry)。rdkit 仅在 featurize 惰性 import。
"""
from __future__ import annotations

import numpy as np

from praxis_virtualcell.mdr_gnb.drug_agent.small_molecule_features import (
    morgan_bits, structural_stats,
)

# 每字节 popcount 查表(化学 OOD 的 Tanimoto 用 packbits 后按字节算交集,确定性且省内存)
_POPCOUNT8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.int32)

# --- Phase 16:加法方向结构 sanity gate 常数(独立于 Tanimoto 集合相似度)----------------
# Morgan 位集 Tanimoto 对"加原子/加组分"单调不减(加东西只增位不减位),对超规模/多组分**失明**
# —— 超长同聚物、混合物洗白拿到高相似度绕过 OOD 拿自信 MIC。补规模敏感判据(重原子数/组分数)拦之。
# SM_HAC_MAX = ceil(1.5×训练 max 344)= 516(spike 2026-07-16 全量 27175 化合物 rdkit 实测,
# HAC max=344,0 解析失败;派生出处见 docs/superpowers/plans/2026-07-16-phase16-ood-additivity-gate.md
# §4。倍数留 1.5× 余量覆盖训练相似的合法大分子,零误伤见 golden 负向门;漂移守卫从 parquet 重算断言)。
SM_HAC_MAX = 516
# gate reason code → 面向报告读者的中文说明(供上游 default_registry 闭包组 abstain_reason)。
GATE_REASON_MESSAGES = {
    "compound_multi_component": "多组分输入(训练集为单组分,请提交去盐母体结构)",
    "compound_size_out_of_range": f"结构规模超训练范围(重原子数 > {SM_HAC_MAX})",
}


def _max_tanimoto(q_bits: np.ndarray, train_packed: np.ndarray,
                  train_pop: np.ndarray) -> float:
    """查询指纹对训练集的**最大 Tanimoto 相似度**(纯 numpy,不需 rdkit)。

    q_bits: (n_bits,) uint8 {0,1};train_packed: (n_train, n_bytes) uint8(packbits 后);
    train_pop: (n_train,) 各训练指纹的 popcount。空训练集返回 0.0。
    """
    if train_packed.shape[0] == 0:
        return 0.0
    q_packed = np.packbits(q_bits)
    q_pop = int(_POPCOUNT8[q_packed].sum())
    inter = _POPCOUNT8[train_packed & q_packed].sum(axis=1)      # 逐行交集位数
    union = train_pop + q_pop - inter
    tani = np.zeros(union.shape, dtype=float)
    np.divide(inter, union, out=tani, where=union > 0)          # union=0 处留 0.0,不触发除零告警
    return float(tani.max())


class SmallMoleculeModel:
    """SMILES → log10-MIC 回归 + 化学 OOD。artifact 自包含,加载确定性。"""

    def __init__(self, n_bits: int = 2048, radius: int = 2,
                 ood_threshold: float = 0.3, n_estimators: int = 300,
                 random_state: int = 0):
        self.n_bits = n_bits
        self.radius = radius
        self.ood_threshold = ood_threshold          # 对训练集最大 Tanimoto 低于此 = 化学空间外
        self.n_estimators = n_estimators
        self.random_state = random_state
        self._rf = None
        self._train_packed = None                   # (n_train, n_bytes) uint8
        self._train_pop = None                      # (n_train,) popcount
        self.train_size = 0
        self.n_invalid_dropped = 0

    # ---- 训练 ----
    def fit(self, smiles_list: list[str], y: list[float]) -> "SmallMoleculeModel":
        """在 (SMILES, log10-MIC) 上训 RF;丢弃 invalid SMILES 并计数;存训练指纹供 OOD。"""
        from sklearn.ensemble import RandomForestRegressor

        X_rows, y_keep = [], []
        n_invalid = 0
        for smi, yi in zip(smiles_list, y):
            bits = morgan_bits(smi, self.n_bits, self.radius)
            if bits is None:
                n_invalid += 1
                continue
            X_rows.append(bits)
            y_keep.append(float(yi))
        if not X_rows:
            raise ValueError("无有效 SMILES,无法训练")
        X = np.asarray(X_rows, dtype=np.uint8)
        yv = np.asarray(y_keep, dtype=float)
        self._rf = RandomForestRegressor(n_estimators=self.n_estimators,
                                         random_state=self.random_state, n_jobs=-1)
        self._rf.fit(X, yv)
        self._train_packed = np.packbits(X, axis=1)             # 压缩训练指纹
        self._train_pop = _POPCOUNT8[self._train_packed].sum(axis=1)
        self.train_size = X.shape[0]
        self.n_invalid_dropped = n_invalid
        return self

    # ---- 预测(只报事实,abstain 决策留给闭包)----
    def predict_one(self, smiles: str) -> dict:
        """单化合物预测。返回 dict:
          ok=False → invalid SMILES(reason=invalid_smiles)/加法方向 gate 触发
                     (reason=compound_multi_component / compound_size_out_of_range);
          ok=True  → log10_mic / mic_ug_ml / max_tanimoto / is_ood / std(RF 各树 std)。
        """
        if self._rf is None:
            return {"ok": False, "reason": "model_not_fitted"}
        bits = morgan_bits(smiles, self.n_bits, self.radius)
        if bits is None:
            return {"ok": False, "reason": "invalid_smiles"}
        # --- Phase 16:加法方向结构 sanity gate(独立于下方 Tanimoto,fail-closed 弃权)------
        # Tanimoto 对"加原子/加组分"单调不减、对超规模/多组分失明;这里用规模敏感判据补缺口。
        # 多组分先判(训练集 100% 单组分,指纹 union 会洗白 OOD 组分 → 拒之,提示提交去盐母体);
        # 再判超规模(HAC>SM_HAC_MAX)。诚实"拒绝",不静默取最大片段返回母体 MIC。
        stats = structural_stats(smiles)
        if stats is not None:                       # bits 非 None ⟹ SMILES 合法 ⟹ stats 恒非 None
            if stats["n_fragments"] > 1:
                return {"ok": False, "reason": "compound_multi_component"}
            if stats["heavy_atom_count"] > SM_HAC_MAX:
                return {"ok": False, "reason": "compound_size_out_of_range"}
        X = bits.reshape(1, -1).astype(np.uint8)
        # 逐树预测按 estimators_ 固定顺序拼 → 均值=RF 预测,std=树间分歧。
        # **确定性关键**:不调 self._rf.predict(并行 n_jobs 累加有 ULP 噪声),自己按固定顺序求均值。
        tree_preds = np.array([t.predict(X)[0] for t in self._rf.estimators_])
        log10_mic = float(tree_preds.mean())
        std = float(tree_preds.std())
        max_tan = _max_tanimoto(bits, self._train_packed, self._train_pop)
        return {
            "ok": True,
            "log10_mic": log10_mic,
            "mic_ug_ml": float(10.0 ** log10_mic),
            "max_tanimoto": max_tan,
            "is_ood": bool(max_tan < self.ood_threshold),
            "std": std,
        }

    # ---- 持久化(自包含 artifact)----
    def save(self, path) -> None:
        import joblib
        from pathlib import Path

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path) -> "SmallMoleculeModel":
        import joblib

        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"artifact 不是 {cls.__name__}:{type(obj)!r}")
        return obj
