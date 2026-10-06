"""版本冻结规则基线 RuleBaselineSIR 测试(G2 对照方)。"""
import pytest

from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR


def test_resistant_on_family_hit():
    clf = RuleBaselineSIR(db_version="2025-07-16.1")
    assert clf.predict_one("meropenem", ["blaKPC-3"]) == "R"
    assert clf.predict_one("meropenem", ["blaTEM-1"]) == "S"  # blaTEM 非碳青霉烯酶


def test_ceftriaxone_esbl():
    clf = RuleBaselineSIR(db_version="2025-07-16.1")
    assert clf.predict_one("ceftriaxone", ["blaCTX-M-15"]) == "R"


def test_snapshot_recorded():
    clf = RuleBaselineSIR(db_version="2025-07-16.1")
    assert clf.snapshot()["amrfinder_db_version"] == "2025-07-16.1"
    assert clf.snapshot()["rules_schema_version"] == 1


def test_unknown_drug_abstains():
    clf = RuleBaselineSIR(db_version="2025-07-16.1")
    with pytest.raises(KeyError):
        clf.predict_one("colistin", ["mcr-1"])  # 未收录药物显式失败,不静默判 S


def test_predict_from_ncbi_genotype_string():
    # 便捷:直接吃 NCBI ncbi_amr_genotypes 串(含 =POINT/=MISTRANSLATION 修饰)
    clf = RuleBaselineSIR(db_version="2025-07-16.1")
    geno = "aac(6')-Ib,blaKPC-2,blaSHV-12,gyrA_S83I=POINT,oqxA"
    assert clf.predict_one_genotype("meropenem", geno) == "R"   # blaKPC-2 命中
    assert clf.predict_one_genotype("meropenem", "blaTEM-1,fosA") == "S"
