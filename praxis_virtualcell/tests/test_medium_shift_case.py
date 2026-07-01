"""W5.1(v0.4,Phase II):微生物 培养基/碳源切换 → growth case(环境扰动,真跑 GEM)。

激活 schema 里的 `medium` 扰动对象(此前未用于 case);证明 agent 能处理**gene 以外的
环境扰动**(碳源改变)并受治理产出。无 cobra 时 skip。断言真实 FBA:acetate << glucose
(乙醛酸支路,弱碳源);碳源不在模型 exchange → abstain 不虚构。
"""
import pytest

pytest.importorskip("cobra")

from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM
from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case, CARBON_EXCHANGES
from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route


@pytest.fixture(scope="module")
def gem():
    return EcoliGEM()


def test_route_medium_growth_to_gem():
    d = route(normalize_request({"species": "bacteria", "perturbation_object": "medium",
                                 "perturbation_targets": ["acetate"], "target_output": "growth"}))
    assert d.engine == "gem_fba"


def test_acetate_much_worse_than_glucose(gem):
    from praxis_virtualcell.predictors.mechanistic.medium_shift import carbon_growth
    glc = carbon_growth(gem, "glucose")
    ac = carbon_growth(gem, "acetate")
    assert glc > 0.8 and ac < glc * 0.5      # 真实 FBA:acetate 远弱于 glucose


def test_full_case_7parts_real_numbers(gem):
    report, dec = run_medium_shift_case({
        "case_id": "S_ecoli_carbon", "species": "bacteria", "cell_type": "E. coli",
        "perturbation_object": "medium", "perturbation_targets": ["acetate", "succinate", "glucose"],
        "target_output": "growth",
    }, gem=gem)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "gem_fba"
    rows = {r["carbon"]: r for r in d["raw_output"]["carbon_sources"]}
    assert rows["acetate"]["growth"] < rows["glucose"]["growth"]   # 真实数值,非 mock
    assert rows["acetate"]["ratio_vs_glucose"] < 0.5
    assert d["reliability_decision"]["disposition"] == "accept"    # 全部碳源在模型内


def test_unknown_carbon_abstains(gem):
    report, _ = run_medium_shift_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "medium",
        "perturbation_targets": ["unobtainium"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"


def test_partial_unknown_carbon_caution(gem):
    report, _ = run_medium_shift_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "medium",
        "perturbation_targets": ["glucose", "unobtainium"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "caution"


def test_carbon_map_covers_common_sources():
    assert {"glucose", "acetate", "succinate", "fructose", "lactate"} <= set(CARBON_EXCHANGES)
