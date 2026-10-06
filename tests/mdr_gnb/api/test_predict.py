"""9.1 /predict:包 run_mdr_query,暴露 report + fusion/evidence 摘要。
红线:确定性(同 raw 逐字相等)、fail-closed(unsupported 不伪造)、LLM 不裁决。"""
from tests.mdr_gnb.mic_invariant import assert_report_mic_matches_log10

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

EC_CEFTRIAXONE = {
    "species": "escherichia_coli",
    "drug_panel": [{"drug": "ceftriaxone", "drug_class": "cephalosporin"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaCTX-M-15": True},
}
KP_MEROPENEM = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}
STENO = {
    "species": "stenotrophomonas_maltophilia",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {},
}


def test_predict_ec(client):
    """EC×ceftriaxone + blaCTX-M-15(ESBL)→ 真实 R,strong tier,融合摘要齐备。"""
    r = client.post("/predict", json=EC_CEFTRIAXONE)
    assert r.status_code == 200
    body = r.json()
    rep = body["report"]
    assert rep["abstained"] is False
    assert rep["sir"] == "R"
    assert rep["output_kind"] == "sir_class"
    assert body["prediction_available"] is True
    assert body["supported_species"] is True
    # 融合摘要(rule_pred vs ml_sir + method)
    assert body["fusion"]["method"] == "rule_first_fusion"
    assert body["fusion"]["rule_pred"] == "R"
    assert body["fusion"]["evidence_tier"] == "strong"
    # evidence 摘要(baseline 对比:ΔVME/p/AUC)
    assert body["evidence"]["tier"] == "strong"
    assert body["evidence"]["evidence_level"] == "E4"
    assert "delta_vme" in body["evidence"]


def test_predict_kp(client):
    """KP×meropenem + blaKPC-2(碳青霉烯酶)→ 真实 R;rule=R 永不翻 S。"""
    r = client.post("/predict", json=KP_MEROPENEM)
    body = r.json()
    rep = body["report"]
    assert rep["sir"] == "R"
    assert rep["abstained"] is False
    assert body["fusion"]["rule_pred"] == "R"
    assert body["fusion"]["evidence_tier"] == "strong"


def test_unsupported_species_abstain(client):
    """stenotrophomonas(5 fail-closed 物种之一)→ 不伪造预测:sir=None,警示。"""
    r = client.post("/predict", json=STENO)
    assert r.status_code == 200
    body = r.json()
    assert body["report"]["sir"] is None            # 不伪造
    assert body["prediction_available"] is False
    assert body["supported_species"] is False
    assert any("unsupported" in w or "species" in w for w in body["warnings"])


def test_predict_llm_not_adjudicating(client):
    """LLM 不裁决:三 flag 恒 False(offline 默认也须显式钉住)。"""
    body = client.post("/predict", json=KP_MEROPENEM).json()
    llm = body["llm"]
    assert llm["modify_disposition"] is False
    assert llm["override_abstain"] is False
    assert llm["change_breakpoint"] is False


def test_predict_deterministic_byte_identical(client):
    """同 raw 两次 /predict → report 逐字相等 + task_id 相等(fusion 确定性)。"""
    a = client.post("/predict", json=KP_MEROPENEM).json()
    b = client.post("/predict", json=KP_MEROPENEM).json()
    assert a["task_id"] == b["task_id"]
    assert a["report"] == b["report"]
    assert a == b


def test_task_id_content_addressed(client):
    """task_id 由 raw 内容决定:不同 raw → 不同 task_id。"""
    a = client.post("/predict", json=KP_MEROPENEM).json()["task_id"]
    b = client.post("/predict", json=EC_CEFTRIAXONE).json()["task_id"]
    assert a != b


# --- 线B:小分子结构(SMILES)→ 活性 MIC(需本地 sm_activity artifact + rdkit)---
EC_CIPRO_SMILES = {
    "species": "escherichia_coli",
    "smiles": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O",
    "drug_panel": [{"drug": "ciprofloxacin", "drug_class": "novel_compound"}],
    "requested_outputs": ["activity"],
}
# 甲烷:落在训练化学空间外 → OOD fail-closed 弃权(不伪造 MIC)
EC_METHANE_OOD = {
    "species": "escherichia_coli",
    "smiles": "C",
    "drug_panel": [{"drug": "methane", "drug_class": "novel_compound"}],
    "requested_outputs": ["activity"],
}
# 肽 Magainin-2 → 活性 MIC(µM)(需本地 peptide_activity artifact)
EC_MAGAININ = {
    "species": "escherichia_coli",
    "sequence": "GIGKFLHSAKKFGKAFVGEIMNS",
    "drug_panel": [{"drug": "magainin-2", "drug_class": "antimicrobial_peptide"}],
    "requested_outputs": ["peptide_activity"],
}


def test_predict_small_molecule_activity(client):
    """SMILES 经 HTTP 到达后端(不被 schema 剥离)→ 真 QSAR 活性,mechanism 分栏。"""
    body = client.post("/predict", json=EC_CIPRO_SMILES).json()
    rep = body["report"]
    assert rep["abstained"] is False
    assert rep["output_kind"] == "sm_activity"
    act = rep["activity"]
    assert act is not None
    # 活性字段齐备(MIC + 不确定度 + 化学近邻度 + OOD)
    for k in ("log10_mic", "mic_ug_ml", "uncertainty_std", "max_tanimoto", "is_ood"):
        assert k in act
    # 值一致性:上面只查字段名在不在,查不出值对不对。验证层只验 log10_mic,
    # 网站展示的却是 mic_ug_ml——本断言是**第一处在真 artifact 路径(真 app + 真 HTTP)
    # 上做的值断言**,此前该数的值覆盖全是合成桩。实测:ens/rb 任一处改错 1000 倍,
    # 本断言真红(详见 mic_invariant 模块 docstring 的变异矩阵结论)。
    assert_report_mic_matches_log10(act, "mic_ug_ml")
    assert body["prediction_available"] is True
    # 机制与活性分栏,互不冒充:activity 无 growth_inhibition,mechanism 无 MIC
    assert "growth_inhibition" not in act
    assert rep["mechanism"] is not None


def test_predict_small_molecule_ood_abstain(client):
    """OOD 化合物(甲烷)→ fail-closed 弃权,不伪造 MIC,activity=None。"""
    body = client.post("/predict", json=EC_METHANE_OOD).json()
    rep = body["report"]
    assert rep["abstained"] is True
    assert rep["activity"] is None
    assert body["prediction_available"] is False


def test_predict_peptide_activity(client):
    """肽序列经 HTTP 到达后端 → 真 QSAR 活性(µM);prediction_available 认 peptide_activity。"""
    body = client.post("/predict", json=EC_MAGAININ).json()
    rep = body["report"]
    assert rep["abstained"] is False
    assert rep["output_kind"] == "peptide_activity"
    pep = rep["peptide_activity"]
    assert pep is not None
    for k in ("log10_mic", "mic_um", "uncertainty_std", "max_jaccard", "is_ood"):
        assert k in pep
    # 值一致性:同 test_predict_small_molecule_activity——展示给用户的 mic_um 必须与
    # 验证层唯一验的 log10_mic 自洽;真 artifact 路径上的值断言。
    assert_report_mic_matches_log10(pep, "mic_um")
    # 红线:peptide_activity 也须被 prediction_available 认作有效预测(否则 UI 误判无结果)
    assert body["prediction_available"] is True


def test_predict_line_b_deterministic(client):
    """线B 小分子/肽预测确定性:同 raw 两次逐字相等。"""
    a = client.post("/predict", json=EC_CIPRO_SMILES).json()
    b = client.post("/predict", json=EC_CIPRO_SMILES).json()
    assert a == b
    c = client.post("/predict", json=EC_MAGAININ).json()
    d = client.post("/predict", json=EC_MAGAININ).json()
    assert c == d
