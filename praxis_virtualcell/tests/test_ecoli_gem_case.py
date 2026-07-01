"""W2.1(v0.4):E. coli KO growth case —— 真跑 cobrapy GEM(机制模型),非 mock。

无 cobra 时整文件 skip(机制模型为可选依赖 `pip install '.[mechanistic]'`)。
断言真实生物学:gltA(b0720)/ icd(b1136)essential;WT growth ≈ 0.874(textbook 已知值)。
治理:不在 GEM 的基因 → downgrade/abstain,不虚构生长。
"""
import pytest

cobra = pytest.importorskip("cobra")   # 无 cobra → skip

from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM, run_ecoli_growth_case
from praxis_virtualcell.agents.case_report import validate_case_report


@pytest.fixture(scope="module")
def gem():
    return EcoliGEM()


def test_wt_growth_known_value(gem):
    assert gem.wt_growth == pytest.approx(0.8739, abs=1e-3)   # textbook e_coli_core WT


def test_gltA_essential(gem):
    r = gem.knockout("b0720")          # gltA 柠檬酸合酶
    assert r.in_model and r.essential and r.growth == pytest.approx(0.0, abs=1e-6)


def test_nonessential_gene_grows(gem):
    r = gem.knockout("b0356")          # 非必需 → 生长基本不变
    assert r.in_model and not r.essential and r.ratio > 0.5


def test_gene_not_in_model_flagged(gem):
    r = gem.knockout("ZZZ_notagene")
    assert r.in_model is False and r.growth is None and r.essential is None


def test_full_case_7parts_real_numbers(gem):
    report, dec = run_ecoli_growth_case({
        "case_id": "C4_ecoli_ko_growth", "species": "bacteria", "cell_type": "E. coli",
        "perturbation_object": "gene", "perturbation_targets": ["b0720", "b1136", "b0356"],
        "target_output": "growth", "medium": "glucose_minimal",
    }, gem=gem)
    validate_case_report(report)               # 7 部分齐全
    d = report.to_dict()
    assert dec.engine == "gem_fba"
    assert d["models_tools_selected"]["method"].startswith("FBA")
    kos = {k["gene"]: k for k in d["raw_output"]["knockouts"]}
    assert kos["b0720"]["essential"] is True   # 真实数值,非 mock
    assert kos["b1136"]["essential"] is True   # icd 也 essential
    assert d["reliability_decision"]["disposition"] == "accept"   # 全在模型内
    assert d["baseline_comparison"]["essential_count"] >= 2


def test_case_downgrades_when_gene_missing(gem):
    report, _ = run_ecoli_growth_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "gene",
        "perturbation_targets": ["b0720", "ZZZ_notagene"], "target_output": "growth",
    }, gem=gem)
    # 部分基因不在 GEM → caution(不虚构缺失基因的生长)
    assert report.to_dict()["reliability_decision"]["disposition"] == "caution"


def test_all_missing_abstains(gem):
    report, _ = run_ecoli_growth_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "gene",
        "perturbation_targets": ["ZZZ1", "ZZZ2"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
