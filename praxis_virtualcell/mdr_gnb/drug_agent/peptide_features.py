"""抗菌肽序列特征化(氨基酸组成 + 理化描述符),供 PeptideActivityModel 使用(线B B5,数据源 DBAASP)。

肽不用小分子的 Morgan 指纹;用**序列级**特征:20 维氨基酸组成(频率)+ 6 维理化(长度/净电荷/
正电荷占比/平均疏水性/芳香度/**疏水矩=两亲性**)。疏水矩(Eisenberg,α-螺旋 100°周期)是抗菌肽
机制最相关特征。纯序列→特征,确定性,无网、无 rdkit(stdlib + numpy)。
invalid 序列(空/含非标准氨基酸字母/小写)→ ValueError 诚实报错,不静默"修正"、不伪造特征。
注:仅校验字母属 20 标准 AA 单字母码,**无法区分恰好由 ACGT 等合法码组成的 DNA/乱码**——
真管线序列来自 DBAASP 肽字段,此风险低;此校验只挡非法字母/小写/空。防泄漏在 baseline 分组,不在此。
"""
from __future__ import annotations

import math

import numpy as np

# 20 标准氨基酸(单字母,固定顺序 → 特征向量确定性)
CANONICAL_AA = tuple("ACDEFGHIKLMNPQRSTVWY")
_AA_SET = frozenset(CANONICAL_AA)

# Kyte-Doolittle 疏水性标度
_KD_HYDRO = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}
_AROMATIC = frozenset("FWY")
_HELIX_DELTA = 100.0 * math.pi / 180.0      # α-螺旋每残基 100°(疏水矩相位步长)


def _validate(sequence: str) -> str:
    """校验为非空、全大写标准氨基酸的序列;否则 ValueError(不静默修正)。"""
    if not sequence or not isinstance(sequence, str):
        raise ValueError(f"空/非法肽序列:{sequence!r}")
    if any(c not in _AA_SET for c in sequence):
        bad = sorted(set(c for c in sequence if c not in _AA_SET))
        raise ValueError(f"含非标准氨基酸 {bad}(须大写 20 标准 AA):{sequence!r}")
    return sequence


def build_peptide_features(sequence: str) -> dict:
    """序列 → 特征 dict:aa_composition(20 维频率)+ 理化(length/net_charge/
    fraction_positive/mean_hydrophobicity/aromaticity)。invalid → ValueError。"""
    seq = _validate(sequence)
    n = len(seq)
    counts = {aa: seq.count(aa) for aa in CANONICAL_AA}
    comp = {aa: counts[aa] / n for aa in CANONICAL_AA}
    pos = counts["K"] + counts["R"]                 # 正电荷残基
    neg = counts["D"] + counts["E"]                 # 负电荷残基
    net_charge = float(pos - neg)
    mean_hydro = float(sum(_KD_HYDRO[c] for c in seq) / n)
    aromaticity = float(sum(1 for c in seq if c in _AROMATIC) / n)
    # 疏水矩(Eisenberg):把各残基疏水值按 α-螺旋 100°/残基排布,取向量和的模,归一化长度=两亲性
    sx = sum(_KD_HYDRO[c] * math.cos(_HELIX_DELTA * i) for i, c in enumerate(seq))
    sy = sum(_KD_HYDRO[c] * math.sin(_HELIX_DELTA * i) for i, c in enumerate(seq))
    hydrophobic_moment = float(math.hypot(sx, sy) / n)
    return {
        "aa_composition": comp,
        "length": n,
        "net_charge": net_charge,
        "fraction_positive": float(pos / n),
        "mean_hydrophobicity": mean_hydro,
        "aromaticity": aromaticity,
        "hydrophobic_moment": hydrophobic_moment,
    }


def peptide_vector(sequence: str) -> np.ndarray:
    """序列 → 定长 float64 特征向量(20 组成 + 6 理化),供 RF 训练。invalid → ValueError。"""
    f = build_peptide_features(sequence)
    comp = [f["aa_composition"][aa] for aa in CANONICAL_AA]
    physico = [float(f["length"]), f["net_charge"], f["fraction_positive"],
               f["mean_hydrophobicity"], f["aromaticity"], f["hydrophobic_moment"]]
    return np.asarray(comp + physico, dtype=np.float64)
