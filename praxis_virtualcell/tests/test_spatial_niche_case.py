"""R5(v0.5):Spatial niche 依赖状态 case —— squidpy imc(真跑,填应用 5 例 5B)。

断言实测:间质邻接肿瘤细胞 EMT 评分 > 间质贫瘠(niche 依赖,Cohen's d ~0.7)。治理:niche 效应中等→caution。
"""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.spatial.niche import (
    _DEFAULT_SUBSET,
    SpatialNicheDB,
    run_spatial_niche_case,
)

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"imc niche 子集缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return SpatialNicheDB()


def test_route_medium_state_to_spatial_niche():
    d = route(normalize_request({"species": "human", "perturbation_object": "medium",
                                 "perturbation_targets": ["stromal_niche"], "target_output": "state"}))
    assert d.engine == "spatial_niche"


def test_stroma_adjacent_more_mesenchymal(db):
    res = db.emt_by_niche()
    assert res["mean_a"] > res["mean_b"]       # 间质邻接 EMT 评分 > 间质贫瘠
    assert abs(res["cohens_d"]) > 0.3          # 真实 niche 效应(实测 ~0.74)


def test_full_case_7parts(db):
    report, dec = run_spatial_niche_case({
        "case_id": "S_niche", "species": "human", "cell_type": "breast tumor",
        "perturbation_object": "medium", "perturbation_targets": ["stromal_niche"],
        "target_output": "state",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "spatial_niche"
    # niche 效应中等(实测 d~0.74)→ caution/accept,不是 downgrade
    assert d["reliability_decision"]["disposition"] in ("accept", "caution")
    assert d["raw_output"]["niche_emt_shift"]["cohens_d"] > 0.3


def test_boundary_notes_niche(db):
    report, _ = run_spatial_niche_case({
        "species": "human", "cell_type": "breast tumor", "perturbation_object": "medium",
        "perturbation_targets": ["stromal_niche"], "target_output": "state",
    }, db=db)
    assert "niche" in str(report.to_dict()["provenance_boundary"]).lower()
