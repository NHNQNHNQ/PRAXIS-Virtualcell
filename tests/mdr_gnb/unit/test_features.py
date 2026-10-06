"""特征矩阵测试(NCBI-only 适配):基因型串解析、冻结词表防泄漏、SIR 标签。"""
from praxis_virtualcell.mdr_gnb.predictors.features import (
    build_feature_matrix,
    FeatureSpec,
    parse_genotypes,
)


def _rows():
    return [
        {"genome_id": "s1", "ncbi_amr_genotypes": "blaCTX-M-15,gyrA_S83L=POINT",
         "resistant_phenotype": "R"},
        {"genome_id": "s2", "ncbi_amr_genotypes": "blaCTX-M-15,blaTEM-1,blaOXA=MISTRANSLATION",
         "resistant_phenotype": "R"},
        {"genome_id": "s3", "ncbi_amr_genotypes": "", "resistant_phenotype": "S"},
    ]


def _st():
    return {"s1": "ST131", "s2": "ST131", "s3": "ST69"}


def test_parse_genotypes_gene_vs_mut():
    toks = parse_genotypes("blaKPC-2,gyrA_S83I=POINT,blaOXA=MISTRANSLATION")
    # =POINT → mut=基名;其余(含 =MISTRANSLATION 修饰)→ gene=基名
    assert toks == {"gene=blaKPC-2", "mut=gyrA_S83I", "gene=blaOXA"}


def test_vocab_frozen_from_train():
    fm = build_feature_matrix(_rows(), _st())
    assert set(fm.spec.feature_names) == {
        "gene=blaCTX-M-15", "gene=blaTEM-1", "gene=blaOXA", "mut=gyrA_S83L",
    }
    assert fm.X.shape == (3, 4)
    assert list(fm.group) == ["ST131", "ST131", "ST69"]


def test_transform_ignores_unseen_features():
    fm = build_feature_matrix(_rows(), _st())
    test = [
        {"genome_id": "t1", "ncbi_amr_genotypes": "blaNDM-1", "resistant_phenotype": "R"},  # 未见特征
        {"genome_id": "t2", "ncbi_amr_genotypes": "blaCTX-M-15", "resistant_phenotype": "R"},
        {"genome_id": "t3", "ncbi_amr_genotypes": "", "resistant_phenotype": "S"},
    ]
    Xt = FeatureSpec.transform(fm.spec, test)
    assert Xt.shape == (3, 4)  # 列数随 train 词表冻结不变
    j = fm.spec.feature_names.index("gene=blaCTX-M-15")
    assert Xt[:, j].tolist() == [0.0, 1.0, 0.0]


def test_y_sir_binary_and_three():
    fm = build_feature_matrix(_rows(), _st())
    assert fm.y_sir.tolist() == [1, 1, 0]   # R,R,S → R=1 vs 非R=0
    assert fm.y_sir3.tolist() == [2, 2, 0]  # R=2,S=0
