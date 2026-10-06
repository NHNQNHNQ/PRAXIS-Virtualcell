"""生产融合层:rule-first + 证据分层门控。安全保证/fail-closed/确定性。"""
from praxis_virtualcell.mdr_gnb.coordinator.fusion import fuse_sir, load_evidence_tiers


def _ml(sir, p_r):
    return {"output_kind": "sir_class", "abstained": False,
            "sir": sir, "sir_prob": {"S": 1 - p_r, "I": 0.0, "R": p_r}}


def test_rule_R_never_flipped_to_S():
    # blaKPC-2(碳青霉烯酶)→ 规则判 meropenem R;即便 ML 判 S(p 低),融合必 R(安全保证)
    out = fuse_sir(_ml("S", 0.05), species="klebsiella_pneumoniae", drug="meropenem",
                   amr_profile={"blaKPC-2": True})
    assert out["sir"] == "R"
    assert out["fusion"]["rule_pred"] == "R"
    assert out["fusion"]["ml_sir"] == "S"


def test_rule_S_ml_R_gives_R():
    # 无碳青霉烯酶但 ML 判 R(p 高)→ 融合 R(ML 补规则漏判)
    out = fuse_sir(_ml("R", 0.9), species="klebsiella_pneumoniae", drug="meropenem",
                   amr_profile={"blaSHV-1": True})
    assert out["sir"] == "R"


def test_rule_S_ml_S_gives_S():
    out = fuse_sir(_ml("S", 0.1), species="klebsiella_pneumoniae", drug="meropenem",
                   amr_profile={"blaSHV-1": True})
    assert out["sir"] == "S"
    assert out["fusion"]["method"] == "rule_first_fusion"


def test_no_baseline_drug_ml_only():
    # 冻结规则表未收录的药 → no_baseline,ML-only + warning
    out = fuse_sir(_ml("R", 0.8), species="klebsiella_pneumoniae", drug="__not_a_real_drug__",
                   amr_profile={"blaKPC-2": True})
    assert out["fusion"]["method"] == "ml_only_no_baseline"
    assert out["fusion"]["evidence_tier"] == "no_baseline"
    assert out["fusion"]["warning"] is not None


def test_abstained_unchanged():
    r = {"output_kind": "sir_class", "abstained": True, "abstain_reason": "x"}
    out = fuse_sir(r, species="klebsiella_pneumoniae", drug="meropenem", amr_profile={})
    assert out.get("sir") is None and "fusion" not in out    # fail-closed 保留,不融合


def test_non_sir_unchanged():
    r = {"output_kind": "mic_scalar", "abstained": False, "mic": 8}
    out = fuse_sir(r, species="escherichia_coli", drug="meropenem", amr_profile={})
    assert "fusion" not in out


def test_tier_attached_from_config():
    # KP×meropenem 在 evidence_tiers.yaml 里是 strong
    tiers = load_evidence_tiers()
    if ("klebsiella_pneumoniae", "meropenem") in tiers:
        out = fuse_sir(_ml("R", 0.7), species="klebsiella_pneumoniae", drug="meropenem",
                       amr_profile={"blaKPC-2": True})
        assert out["fusion"]["evidence_tier"] == "strong"


def test_deterministic():
    a = fuse_sir(_ml("S", 0.3), species="klebsiella_pneumoniae", drug="meropenem",
                 amr_profile={"blaKPC-2": True})
    b = fuse_sir(_ml("S", 0.3), species="klebsiella_pneumoniae", drug="meropenem",
                 amr_profile={"blaKPC-2": True})
    assert a == b
