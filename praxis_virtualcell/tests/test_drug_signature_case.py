"""W3.1(v0.4):Human drug response case —— LINCS L1000 药物签名 MOA 一致性(真跑,非 mock)。

用 Enrichr 的 LINCS_L1000_Chem_Pert 签名(curated 子集 data/drug_signatures/curated_subset.json)。
核心分析:drug → 签名 → 与同 MOA 药物签名相似度 vs 跨 MOA 基线(富集)。
治理(防过度承诺,R6 主题):
  - 富集 ≥ 阈值(同 MOA 明显更像)→ accept(MOA-consistent);
  - 富集 < 阈值(信号弱,如 HDAC 对) → downgrade(不硬说 MOA 匹配);
  - 无同 MOA 参考(单例药) → downgrade;
  - 药不在库 → abstain(不虚构签名)。
断言基于**实测数字**:HSP90 对(geldanamycin/tanespimycin)富集 >1.5 → accept;
HDAC 对(vorinostat/entinostat)富集 <1.5 → downgrade。
"""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.embedding.drug_signature import (
    _DEFAULT_SUBSET,
    DrugSignatureDB,
    run_drug_response_case,
)

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"curated_subset.json 缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return DrugSignatureDB()


def test_db_loads_curated_drugs(db):
    assert db.has("geldanamycin") and db.moa("geldanamycin") == "HSP90_inhibitor"
    assert db.has("vorinostat") and db.moa("vorinostat") == "HDAC_inhibitor"
    assert not db.has("aspirin")               # 不在库


def test_same_moa_more_similar_for_hsp90(db):
    # HSP90 对:同 MOA 相似度 > 跨 MOA(可检验的真实信号)
    same = db.similarity("geldanamycin", "tanespimycin")
    cross = db.similarity("geldanamycin", "vorinostat")
    assert same > cross


def test_geldanamycin_accept_moa_consistent(db):
    report, dec = run_drug_response_case({
        "case_id": "C6_drug", "species": "human", "cell_type": "A549",
        "perturbation_object": "drug", "perturbation_targets": ["geldanamycin"],
        "target_output": "expression",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "embedding"
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["raw_output"]["per_drug"][0]["moa_enrichment"] > 1.5


def test_vorinostat_downgrade_weak_signal(db):
    # HDAC 对信号弱(实测富集 0.10)→ 不硬说 MOA 匹配,downgrade
    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["vorinostat"], "target_output": "expression",
    }, db=db)
    d = report.to_dict()
    assert d["reliability_decision"]["disposition"] == "downgrade"
    assert d["raw_output"]["per_drug"][0]["moa_enrichment"] < 1.5


def test_singleton_drug_downgrade_no_reference(db):
    # sirolimus 在库但无同 MOA 伙伴 → 无法验证 MOA 一致性 → downgrade
    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["sirolimus"], "target_output": "expression",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "downgrade"


def test_unknown_drug_abstains(db):
    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["notadrug123"], "target_output": "expression",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"


def test_case_has_provenance_and_boundary(db):
    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["geldanamycin"], "target_output": "expression",
    }, db=db)
    pb = report.to_dict()["provenance_boundary"]
    assert "LINCS" in str(pb) and "boundary" in pb
