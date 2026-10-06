"""特征矩阵构建(NCBI-only 适配):AMRFinderPlus 基因型 → X;ST → group;SIR → y。

特征源为 NCBI ncbi_amr_genotypes 列(逗号分隔 token):
  - `=POINT` 后缀 → 点突变特征 `mut=<基名>`(如 gyrA_S83I=POINT → mut=gyrA_S83I);
  - 其余(含 =MISTRANSLATION/=PARTIAL/=HMM 等修饰)→ 基因特征 `gene=<基名>`。

词表(feature_names)在 build 时从传入 rows(应为 train 折)冻结,transform 用同一词表
变换任意集合,未见特征丢弃、缺失特征补 0,从结构上杜绝 test 引入新列的隐性泄漏。

**红队警示**:这些特征本身就是 AMRFinderPlus 输出,与 rule_baseline 同源;ST 分组去泄漏后
ML 相对规则法的增量可能坍缩到不显著(G2 如实报告)。NCBI 无定量 MIC,故只出 SIR 标签。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 二分类(R vs 非R,VME 口径)与三分类映射;兼容单字母与 BV-BRC 全称
_SIR_BIN = {
    "S": 0, "I": 0, "R": 1,
    "SUSCEPTIBLE": 0, "INTERMEDIATE": 0, "RESISTANT": 1,
}
_SIR3 = {
    "S": 0, "I": 1, "R": 2,
    "SUSCEPTIBLE": 0, "INTERMEDIATE": 1, "RESISTANT": 2,
}


def parse_genotypes(genotype_str: str) -> set[str]:
    """NCBI ncbi_amr_genotypes 串 → 特征 token 集合(gene=… / mut=…)。"""
    toks: set[str] = set()
    for raw in (genotype_str or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        base, _, modifier = raw.partition("=")
        base = base.strip()
        if not base:
            continue
        if modifier.strip().upper() == "POINT":
            toks.add(f"mut={base}")
        else:
            toks.add(f"gene={base}")
    return toks


@dataclass
class FeatureSpec:
    """冻结词表规格(feature_names 在 train 折冻结,随模型保存)。"""

    feature_names: list[str]

    @staticmethod
    def transform(spec: "FeatureSpec", rows: list[dict]) -> np.ndarray:
        """用冻结词表把 rows 变换为 one-hot 矩阵;未见特征丢弃、缺失补 0。"""
        idx = {name: i for i, name in enumerate(spec.feature_names)}
        X = np.zeros((len(rows), len(spec.feature_names)), dtype=np.float32)
        for r, row in enumerate(rows):
            for tok in parse_genotypes(row.get("ncbi_amr_genotypes", "")):
                j = idx.get(tok)
                if j is not None:
                    X[r, j] = 1.0
        return X


@dataclass
class FeatureMatrix:
    X: np.ndarray           # (n, d) 基因/突变 one-hot
    group: np.ndarray       # ST(谱系分组单位)
    y_sir: np.ndarray       # 二分类 R=1 vs 非R=0
    y_sir3: np.ndarray      # 三分类 S/I/R
    strain_ids: np.ndarray
    spec: FeatureSpec


def build_feature_matrix(
    rows: list[dict], st_map: dict[str, str], spec: FeatureSpec | None = None,
) -> FeatureMatrix:
    """从 rows 构建特征矩阵。

    rows:某 species×drug 的(建议去重后)记录,每行含 ncbi_amr_genotypes/resistant_phenotype/genome_id。
    st_map:genome_id(asm_acc)→ST。spec=None 则从 rows 冻结词表(train 折用),否则复用(test 折用)。
    """
    if spec is None:
        vocab: set[str] = set()
        for row in rows:
            vocab |= parse_genotypes(row.get("ncbi_amr_genotypes", ""))
        spec = FeatureSpec(sorted(vocab))

    X = FeatureSpec.transform(spec, rows)
    group = np.array([
        st_map.get((r.get("genome_id") or "").strip(), "unknown") for r in rows
    ])
    y_sir = np.array([
        _SIR_BIN.get(str(r.get("resistant_phenotype", "")).strip().upper(), -1) for r in rows
    ], dtype=int)
    y_sir3 = np.array([
        _SIR3.get(str(r.get("resistant_phenotype", "")).strip().upper(), -1) for r in rows
    ], dtype=int)
    strain_ids = np.array([(r.get("genome_id") or "").strip() for r in rows])
    return FeatureMatrix(X, group, y_sir, y_sir3, strain_ids, spec)
