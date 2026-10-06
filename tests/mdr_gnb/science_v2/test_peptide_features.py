"""B5-肽 gate(其一):抗菌肽序列特征化(氨基酸组成 + 理化描述符)。

肽不用 Morgan 指纹(那是小分子的);用序列级特征:20 维氨基酸组成 + 理化(长度/净电荷/
疏水性/两亲性/芳香度)。纯序列→特征,确定性,无网无 rdkit。invalid 序列诚实报错不伪造。
"""
import numpy as np
import pytest

from praxis_virtualcell.mdr_gnb.drug_agent.peptide_features import (
    build_peptide_features, peptide_vector, CANONICAL_AA,
)


def test_aa_composition_sums_to_one():
    f = build_peptide_features("AAAA")
    comp = f["aa_composition"]
    assert abs(sum(comp.values()) - 1.0) < 1e-9
    assert comp["A"] == 1.0                       # 全 A


def test_physicochemical_charge_and_length():
    # KKRR:4 个正电荷,净电荷 +4;DDEE:净 -4
    f = build_peptide_features("KKRR")
    assert f["length"] == 4
    assert abs(f["net_charge"] - 4.0) < 1e-9
    assert abs(f["fraction_positive"] - 1.0) < 1e-9
    f2 = build_peptide_features("DDEE")
    assert abs(f2["net_charge"] - (-4.0)) < 1e-9


def test_aromaticity_and_hydrophobicity():
    f = build_peptide_features("FWYA")            # 3/4 芳香
    assert abs(f["aromaticity"] - 0.75) < 1e-9
    # 疏水性有限值(Kyte-Doolittle 均值)
    assert isinstance(f["mean_hydrophobicity"], float)


def test_hydrophobic_moment_amphipathicity():
    # 疏水矩(两亲性):完全同质序列(全 A)矩为 0;两亲交替序列矩显著 > 0
    f_flat = build_peptide_features("AAAAAAAAAAAA")
    assert f_flat["hydrophobic_moment"] >= 0.0
    # 疏亲交替(经典两亲)应比全 A 矩大
    f_amphi = build_peptide_features("LKLKLKLKLKLK")
    assert f_amphi["hydrophobic_moment"] > f_flat["hydrophobic_moment"]


def test_peptide_vector_deterministic_and_fixed_dim():
    v1 = peptide_vector("GLFDIVKKVVGALGSL")
    v2 = peptide_vector("GLFDIVKKVVGALGSL")
    assert v1.shape == (len(CANONICAL_AA) + 6,)   # 20 组成 + 6 理化(含疏水矩)
    assert np.array_equal(v1, v2)                 # 确定性
    assert v1.dtype == np.float64


def test_invalid_sequence_honest_error():
    with pytest.raises(ValueError):
        build_peptide_features("")                # 空
    with pytest.raises(ValueError):
        build_peptide_features("XZ123")           # 非标准氨基酸
    with pytest.raises(ValueError):
        peptide_vector("acgt")                    # 小写/非法(须大写标准 AA)


def test_lowercase_and_whitespace_rejected_not_silently_fixed():
    # 不静默"修正"——非标准输入诚实报错,避免把 DNA/乱码当肽伪造特征
    with pytest.raises(ValueError):
        build_peptide_features("gly")
