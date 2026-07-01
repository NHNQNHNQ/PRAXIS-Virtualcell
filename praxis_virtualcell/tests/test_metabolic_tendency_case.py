"""W5.3(v0.4,Phase II):Human 代谢通路 tendency case —— 表达→糖酵解/OXPHOS(真跑,治理对照)。

核心是 R6 治理对照:同一 IFN-β 扰动,ISG 激活强(accept),但代谢通路表达层信号弱 → **downgrade**
(不硬报代谢重编程)。断言实测:max |d| < 0.8 → 非 accept。
"""
import pytest

from praxis_virtualcell.predictors.state.metabolic_tendency import (
    MetabolicDB, run_metabolic_tendency_case, _DEFAULT_SUBSET,
)
from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"代谢子集缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return MetabolicDB()


def test_route_human_flux_to_pathway_scoring():
    d = route(normalize_request({"species": "human", "perturbation_object": "ligand",
                                 "perturbation_targets": ["IFNB1"], "target_output": "flux"}))
    assert d.engine == "pathway_scoring"


def test_metabolic_signal_is_weak(db):
    # 实测:IFN 在表达层对糖酵解/OXPHOS 影响弱(|d| 小)
    shifts = {s["panel"]: s for s in [db.pathway_shift(p) for p in db.panels()]}
    assert abs(shifts["glycolysis"]["cohens_d"]) < 0.8


def test_full_case_downgrades_weak_metabolic(db):
    report, dec = run_metabolic_tendency_case({
        "case_id": "S_ifn_metab", "species": "human", "cell_type": "PBMC",
        "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"],
        "target_output": "flux",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "pathway_scoring"
    # 弱信号 → 不 accept(downgrade 或 caution),体现治理对照
    assert d["reliability_decision"]["disposition"] in ("downgrade", "caution")
    assert d["raw_output"]["max_abs_cohens_d"] < 0.8


def test_pathways_covered(db):
    assert {"glycolysis", "oxphos"} <= set(db.panels())
