"""P18:接活运行时证据层 + 主动学习到 /predict 响应(顶层键,不碰 report)。

契约(预注册,见 docs/superpowers/plans/2026-07-17-phase18-wire-evidence-active-learning.md):
- response 顶层新增 runtime_evidence_level(运行时 E0-E5)+ active_learning(该测什么队列)。
- 守卫①两套别混:runtime_evidence_level(有 level)与验证层 evidence(有 tier)是不同 dict。
- 守卫②no-prediction 不显自信运行时级:prediction_available=False → runtime_evidence_level=None;
  但 active_learning 仍暴露(无模型物种的 bootstrap 建议正是主动学习价值)。
- advisory 红线:接线后 response["report"] 与 run_mdr_query 原始 report **逐字节相等**(只加顶层键,
  裁决字段一字不改)。
- 确定性:同 raw 两次 predict → 整个 response 逐字节相等。
"""
import json

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

EC_CEFTRIAXONE = {
    "species": "escherichia_coli",
    "drug_panel": [{"drug": "ceftriaxone", "drug_class": "cephalosporin"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaCTX-M-15": True},
}
MORGANELLA = {   # 无模型物种:核心 hard abstain → 守卫②
    "species": "morganella_morganii",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC": True},
}
METHANE = {      # OOD 弃权
    "species": "escherichia_coli",
    "smiles": "C",
    "drug_panel": [{"drug": "C", "drug_class": "novel_compound"}],
    "requested_outputs": ["activity"],
}


def _dumps(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False)


def test_runtime_evidence_present_for_prediction():
    """有预测(accept)→ runtime_evidence_level 非 None 且 level ∈ E0-E5;active_learning 有 items。"""
    resp = service.predict(EC_CEFTRIAXONE)["response"]
    assert resp["prediction_available"] is True
    rev = resp["runtime_evidence_level"]
    assert rev is not None
    assert rev["level"] in {"E0", "E1", "E2", "E3", "E4", "E5"}
    assert "active_learning" in resp
    assert isinstance(resp["active_learning"]["items"], list)


def test_two_evidence_systems_not_conflated():
    """守卫①:运行时(有 level)与验证层 evidence(有 tier)是两套不同 dict,不互冒充。"""
    resp = service.predict(EC_CEFTRIAXONE)["response"]
    assert "level" in resp["runtime_evidence_level"]      # 运行时:E 级
    assert "tier" in resp["evidence"]                     # 验证层:strong/practical…
    assert resp["runtime_evidence_level"] is not resp["evidence"]
    assert "tier" not in resp["runtime_evidence_level"]   # 运行时不带 tier(不冒充验证层)


def test_no_model_species_no_confident_runtime_level():
    """无模型物种在核心层弃权，且对外不显示自信运行时级。"""
    resp = service.predict(MORGANELLA)["response"]
    assert resp["prediction_available"] is False
    assert resp["report"]["abstained"] is True
    assert "no_successful_predictor" in resp["report"]["abstain_reasons"]
    assert resp["runtime_evidence_level"] is None
    cands = " ".join(it["candidate"] for it in resp["active_learning"]["items"])
    assert "bootstrap_isolates" in cands


def test_ood_abstain_no_confident_runtime_level():
    """OOD 弃权 → runtime_evidence_level=None(不显自信级)。"""
    resp = service.predict(METHANE)["response"]
    assert resp["prediction_available"] is False
    assert resp["runtime_evidence_level"] is None


def test_advisory_does_not_touch_report():
    """advisory 红线:接线后 response.report 与 run_mdr_query 原始 report 逐字节相等。"""
    for raw in (EC_CEFTRIAXONE, MORGANELLA, METHANE):
        task_id = service.canonical_task_id(raw)
        base_report = run_mdr_query(raw, seed_task_id=task_id)["report"]
        resp = service.predict(raw)["response"]
        assert _dumps(resp["report"]) == _dumps(base_report)


def test_determinism_full_response():
    """同 raw 两次 predict → 整个 response 逐字节相等(含新键)。"""
    for raw in (EC_CEFTRIAXONE, MORGANELLA, METHANE):
        a = service.predict(raw)["response"]
        b = service.predict(raw)["response"]
        assert _dumps(a) == _dumps(b)
