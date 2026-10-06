"""mdr_router:声明式 presence-absence 四档路由(accept/caution/downgrade/abstain)。"""
from praxis_virtualcell.mdr_gnb.coordinator.mdr_router import route_mdr
from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry


def _req(species, drug, drug_class, outputs=("MIC_range", "SIR")):
    return {"species": species, "drug": drug, "drug_class": drug_class,
            "requested_outputs": list(outputs), "amr_profile": {}}


def test_mic_request_downgrades_to_exact_ready_sir_when_mic_is_declared_only():
    reg = build_default_registry()
    d = route_mdr(_req("escherichia_coli", "meropenem", "carbapenems"), reg)
    assert d.disposition == "downgrade"
    assert "genotype_to_sir" in {s.name for s in d.candidates}
    assert "mic_regressor" not in {s.name for s in d.candidates}
    assert {item["reason_code"] for item in d.unready_candidates} >= {
        "quantitative_mic_model_unavailable"
    }


def test_abstain_when_only_declared_rule_fallback_exists():
    reg = build_default_registry()
    # rule baseline 是显式 fail-closed stub，不能再被路由误当作可执行降级模型。
    d = route_mdr(_req("proteus_mirabilis", "ciprofloxacin", "fluoroquinolones"), reg)
    assert d.disposition == "abstain"
    assert d.reason == "no_ready_capability"
    assert d.candidates == []
    assert {item["reason_code"] for item in d.unready_candidates} >= {
        "rule_baseline_not_runtime_predictor"
    }


def test_abstain_when_no_capability():
    reg = build_default_registry()
    d = route_mdr(_req("", "unknown_drug", "unknown_class"), reg)
    assert d.disposition == "abstain"
    assert d.candidates == []


def test_mechanism_requested_but_g3_not_passed_is_caution():
    reg = build_default_registry()
    # P. aeruginosa 未在 _G3_PASSED_SPECIES → 请求 mechanism 只能降级为仅代谢靶/规则
    d = route_mdr(_req("pseudomonas_aeruginosa", "meropenem", "carbapenems",
                       outputs=("SIR", "mechanism")), reg)
    assert d.disposition in ("caution", "downgrade")
    assert "mechanism_g3_not_passed" in d.caution_flags


def test_intrinsic_resistance_species_flagged():
    reg = build_default_registry()
    d = route_mdr(_req("stenotrophomonas_maltophilia", "meropenem", "carbapenems"), reg)
    assert "intrinsic_resistance_species" in d.caution_flags
