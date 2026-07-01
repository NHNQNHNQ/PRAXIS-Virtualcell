"""W2.2(v0.4):Yeast KO growth case —— 真跑 iMM904 GEM(机制模型),非 mock。

无 cobra 或 iMM904 SBML 缺失时整文件 skip。断言真实生物学:ERG1(YGR175C,葡萄糖基础培养必需)
essential;WT growth ≈ 0.288(iMM904 已知值)。治理:不在 GEM 的基因 → downgrade/abstain。
"""
import pytest

pytest.importorskip("cobra")

from praxis_virtualcell.predictors.mechanistic.yeast_gem import (
    YeastGEM, run_yeast_growth_case, _DEFAULT_YEAST_SBML,
)
from praxis_virtualcell.agents.case_report import validate_case_report

if not _DEFAULT_YEAST_SBML.is_file():
    pytest.skip(f"iMM904 SBML 缺失({_DEFAULT_YEAST_SBML})", allow_module_level=True)


@pytest.fixture(scope="module")
def gem():
    return YeastGEM()


def test_wt_growth_known_value(gem):
    assert gem.wt_growth == pytest.approx(0.2879, abs=1e-3)   # iMM904 WT(葡萄糖基础培养)


def test_erg1_essential(gem):
    r = gem.knockout("YGR175C")        # ERG1 角鲨烯环氧酶
    assert r.in_model and r.essential and r.growth == pytest.approx(0.0, abs=1e-6)


def test_nonessential_gene_grows(gem):
    r = gem.knockout("YOR375C")        # GDH1 → 非必需(葡萄糖基础)
    assert r.in_model and not r.essential and r.ratio > 0.9


def test_gene_not_in_model_flagged(gem):
    r = gem.knockout("ZZZ_notagene")
    assert r.in_model is False and r.growth is None


def test_full_case_7parts_real_numbers(gem):
    report, dec = run_yeast_growth_case({
        "case_id": "C5_yeast_deletion_growth", "species": "yeast", "cell_type": "S. cerevisiae",
        "perturbation_object": "gene", "perturbation_targets": ["YGR175C", "YOR375C"],
        "target_output": "growth", "medium": "glucose_minimal",
    }, gem=gem)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "gem_fba"
    assert "iMM904" in d["models_tools_selected"]["tool"]
    kos = {k["gene"]: k for k in d["raw_output"]["knockouts"]}
    assert kos["YGR175C"]["essential"] is True     # 真实数值,非 mock
    assert d["reliability_decision"]["disposition"] == "accept"


def test_case_abstains_when_all_missing(gem):
    report, _ = run_yeast_growth_case({
        "species": "yeast", "cell_type": "S. cerevisiae", "perturbation_object": "gene",
        "perturbation_targets": ["ZZZ1", "ZZZ2"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
