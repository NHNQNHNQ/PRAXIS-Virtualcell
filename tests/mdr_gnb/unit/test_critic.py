"""GNB critic 七类不变量:各一违例 + 一条全清白 trace。"""
from praxis_virtualcell.mdr_gnb.critic import check_invariants, CriticInput


def _clean(**kw):
    base = dict(
        trace_types=["brain_retrieved", "predictor_result", "ensemble_done"],
        abstain=False, reasons=[], models_used=["mic_regressor"],
        ensemble={"mic_scalar": 2.0}, rules_referenced=["…/rules.yaml"],
        breakpoint_sources={"meropenem": "EUCAST v14.0"},
        request_breakpoint_version="EUCAST v14.0",
        genotype={"blaNDM-5": True}, conclusion_sir={"meropenem": "R"},
        provenance={
            "route": "accept",
            "capability": {"catalog_digest": "a" * 64},
            "governance_snapshot": {"governance_digest": "b" * 64},
            "trace_schema_version": "mdr-trace-v1",
            "critic_policy_version": "mdr-critic-v2-final-fusion",
        },
        mechanism_claimed=False, g3_passed=False,
    )
    base.update(kw)
    return CriticInput(**base)


def test_clean_trace_no_violations():
    assert check_invariants(_clean()).violations == []


def test_predict_before_retrieve():
    v = check_invariants(_clean(
        trace_types=["predictor_result", "brain_retrieved"])).violations
    assert "predict_before_retrieve" in v


def test_prediction_without_abstain_or_models():
    v = check_invariants(_clean(models_used=[], abstain=False,
                                ensemble={"mic_scalar": 2.0})).violations
    assert "prediction_without_predictor" in v


def test_abstain_but_prediction_present():
    v = check_invariants(_clean(abstain=True, ensemble={"mic_scalar": 2.0})).violations
    assert "abstain_inconsistent_with_prediction" in v


def test_breakpoint_version_mismatch():
    v = check_invariants(_clean(
        breakpoint_sources={"meropenem": "EUCAST v13.0"},
        request_breakpoint_version="EUCAST v14.0")).violations
    assert "breakpoint_version_mismatch" in v


def test_genotype_conclusion_contradiction():
    # 声明 R 但基因型无任何耐药机制 → 结论与基因型不一致
    v = check_invariants(_clean(genotype={}, conclusion_sir={"meropenem": "R"})).violations
    assert "genotype_conclusion_contradiction" in v


def test_missing_provenance():
    v = check_invariants(_clean(provenance={}, rules_referenced=[])).violations
    assert "missing_provenance" in v


def test_mechanism_claim_without_g3():
    v = check_invariants(_clean(mechanism_claimed=True, g3_passed=False)).violations
    assert "mechanism_claim_without_g3" in v


def test_mechanism_claim_with_g3_ok():
    assert "mechanism_claim_without_g3" not in \
        check_invariants(_clean(mechanism_claimed=True, g3_passed=True)).violations
