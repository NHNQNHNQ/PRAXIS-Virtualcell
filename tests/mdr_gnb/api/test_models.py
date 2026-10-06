"""9.1 /models:registry 能力摘要 + evidence_tiers 证据面摘要。只暴露,不重算。"""

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def test_models_registry_summary(client):
    r = client.get("/models")
    assert r.status_code == 200
    reg = r.json()["registry"]
    assert reg["n_specs"] == 20          # +1 sm_activity(B1)+1 peptide_activity(B5)
    # 五类 output_kind 都在
    assert reg["by_output_kind"]["sir_class"] == 10
    assert "mic_scalar" in reg["by_output_kind"]
    assert "mechanism_state" in reg["by_output_kind"]
    assert "sm_activity" in reg["by_output_kind"]        # 线B 化合物活性
    assert "peptide_activity" in reg["by_output_kind"]   # 线B B5 肽活性


def test_models_evidence_tiers_summary(client):
    ev = client.get("/models").json()["evidence_tiers"]
    assert ev["total"] == 132
    # tier 分布(G2R 证据面 sweep 冻结结果)
    assert ev["by_tier"] == {"strong": 26, "practical": 24, "no_baseline": 67, "unevaluated": 15}
    # evidence_level 分布
    assert ev["by_evidence_level"]["E4"] == 26


def test_models_strong_combos_have_stats(client):
    ev = client.get("/models").json()["evidence_tiers"]
    combos = ev["strong_combos"]
    assert len(combos) == 26
    c = combos[0]
    # baseline 对比字段(前端要展示 ΔVME / p / AUC)
    for k in ("species", "drug", "delta_vme", "p_value", "auc_R", "evidence_level"):
        assert k in c
    assert c["evidence_level"] == "E4"


def test_models_deterministic(client):
    a = client.get("/models").json()
    b = client.get("/models").json()
    assert a == b
