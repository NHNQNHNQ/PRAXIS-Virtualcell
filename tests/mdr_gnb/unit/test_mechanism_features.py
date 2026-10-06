"""机制聚合特征的生物学不变量(G2R 特征工程)。"""
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import (
    mechanism_tokens, augmented_features,
)
from praxis_virtualcell.mdr_gnb.predictors.features import parse_genotypes


def test_carbapenemase_fires_pathway():
    t = mechanism_tokens("blaKPC-2,oqxA")
    assert "mech=carbapenemase" in t
    assert "mech=carbapenem_R_pathway" in t


def test_esbl_plus_porin_fires_pathway_without_carbapenemase():
    # 规则法漏判的核心场景:无碳青霉烯酶,但 ESBL + porin 失活 → 碳青霉烯耐药通路
    g = "blaSHV-12,blaCTX-M-15,ompK36_D135DGD=POINT,ompK35_E42RfsTer47=POINT"
    t = mechanism_tokens(g)
    assert "mech=carbapenemase" not in t          # 确无碳青霉烯酶
    assert "mech=esbl" in t
    assert "mech=porin_loss_any" in t
    assert "mech=carbapenem_R_pathway" in t        # 交互项命中(规则法没有)


def test_narrow_shv_not_esbl():
    # SHV-1/11 是窄谱,不得误判 ESBL
    assert "mech=esbl" not in mechanism_tokens("blaSHV-1")
    assert "mech=esbl" not in mechanism_tokens("blaSHV-11,oqxA")


def test_porin_needs_specific_mutation():
    # 光有 ompK36 基名不带具体突变后缀不算失活(需 _<突变>)
    assert "mech=porin_ompK36_loss" not in mechanism_tokens("ompK36")
    assert "mech=porin_ompK36_loss" in mechanism_tokens("ompK36_D135DGD=POINT")


def test_augmented_superset_of_baseline():
    g = "blaKPC-2,ompK36_D135DGD=POINT,gyrA_S83I=POINT"
    aug = augmented_features(g)
    assert parse_genotypes(g) <= aug              # 叠加不替换
    assert any(x.startswith("mech=") for x in aug)


def test_deterministic():
    g = "blaCTX-M-15,ompC_X=POINT"
    assert mechanism_tokens(g) == mechanism_tokens(g)
