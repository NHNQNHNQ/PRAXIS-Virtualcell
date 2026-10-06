"""小分子特征化(Morgan 指纹),供 SmallMoleculeModel 使用。

B1(线B 注册进核心)实现:先只上 Morgan 指纹 baseline(与 B0.1 qsar_baseline 同款,
radius=2/2048bit),不上理化描述符 / GNN(留 B0.2+)。rdkit 仅在此惰性 import——
53 等无 rdkit 环境 import 本模块不崩,只在真调用特征化时才需要 rdkit。
"""
from __future__ import annotations

from functools import cache

import numpy as np

N_BITS = 2048       # Morgan 指纹默认位数(与 B0.1 baseline 对齐)
RADIUS = 2          # Morgan 默认半径


@cache
def _morgan_generator(n_bits: int, radius: int):
    """返回与历史 Morgan bit-vector API 等价的、按形状缓存的 generator。

    这是运行时可复现性维护，不改变已冻结 artifact 的特征定义。参数显式保留
    ``GetMorganFingerprintAsBitVect(..., radius, nBits=...)`` 的默认语义；特别是
    使用连接性不变量（``atomInvariantsGenerator=None``）而不是 feature invariants。
    保持 RDKit 惰性 import，故无 RDKit 的部署环境只会在实际请求特征时 fail-closed。
    """
    from rdkit.Chem import rdFingerprintGenerator

    return rdFingerprintGenerator.GetMorganGenerator(
        radius=radius,
        countSimulation=False,
        includeChirality=False,
        useBondTypes=True,
        onlyNonzeroInvariants=False,
        includeRingMembership=True,
        fpSize=n_bits,
        includeRedundantEnvironments=False,
    )


def morgan_bitvect(smiles: str, n_bits: int = N_BITS, radius: int = RADIUS):
    """SMILES → RDKit ExplicitBitVect；invalid SMILES 返回 None。

    ``morgan_bits`` 和科学基线共用此单一特征定义，以防训练/推理因 RDKit API
    迁移而漂移。generator 按 ``(n_bits, radius)`` 缓存，因测试/小模型会使用
    非默认 512 位指纹。
    """
    from rdkit import Chem

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return None
    return _morgan_generator(n_bits, radius).GetFingerprint(molecule)


def morgan_bits(smiles: str, n_bits: int = N_BITS, radius: int = RADIUS):
    """SMILES → Morgan 指纹 uint8 数组(n_bits,)取值 {0,1}。invalid SMILES 返回 None。

    rdkit 惰性 import。与 qsar_baseline.morgan_fp 同款(radius/nBits 一致)。
    """
    from rdkit.DataStructs import ConvertToNumpyArray

    bv = morgan_bitvect(smiles, n_bits=n_bits, radius=radius)
    if bv is None:
        return None
    arr = np.zeros((n_bits,), dtype=np.uint8)
    ConvertToNumpyArray(bv, arr)
    return arr


def structural_stats(smiles: str) -> dict | None:
    """SMILES → 规模敏感结构统计:{"heavy_atom_count", "n_fragments"}。invalid SMILES 返回 None。

    Phase 12 加法方向 sanity gate 用:重原子数(HAC)/组分数是**规模敏感**判据,补 Morgan 位集
    Tanimoto 对"加原子/加组分"的单调失明。rdkit 惰性 import。与 morgan_bits 同款 MolFromSmiles
    解析(同 SMILES 同结果),故 bits 非 None ⟹ stats 非 None。
    """
    from rdkit import Chem

    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return {
        "heavy_atom_count": m.GetNumHeavyAtoms(),      # 重原子数(超长同聚物在此暴露)
        "n_fragments": len(Chem.GetMolFrags(m)),       # 组分数(混合物洗白在此暴露)
    }


def build_small_molecule_features(smiles: str, n_bits: int = N_BITS,
                                  radius: int = RADIUS) -> dict:
    """从 SMILES 构建分子特征。返回 {"morgan": uint8(n_bits,), "n_bits", "radius"}。

    invalid SMILES → ValueError(诚实报错,不伪造特征;上游据此 abstain)。
    """
    bits = morgan_bits(smiles, n_bits, radius)
    if bits is None:
        raise ValueError(f"invalid SMILES,无法特征化:{smiles!r}")
    return {"morgan": bits, "n_bits": n_bits, "radius": radius}
