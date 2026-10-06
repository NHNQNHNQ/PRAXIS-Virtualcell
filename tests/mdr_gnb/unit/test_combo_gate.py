"""逐组合 go/no-go 归类 combo_gate 测试。"""
from praxis_virtualcell.mdr_gnb.evaluators.combo_gate import evaluate_combo_gate, GatePrereg

_PRE = GatePrereg(min_effect_size=0.05, alpha=0.05, min_st_with_R=8, min_strains=50)


def test_excluded_when_too_few():
    r = evaluate_combo_gate(
        "proteus_mirabilis", "meropenem",
        n_strains=10, n_st_with_R=2, vme_model=None, vme_rule=None,
        effect_size=None, p_value=None, prereg=_PRE,
    )
    assert r.status == "excluded"


def test_pass_when_significant():
    r = evaluate_combo_gate(
        "escherichia_coli", "ceftriaxone",
        n_strains=800, n_st_with_R=30, vme_model=0.05, vme_rule=0.15,
        effect_size=-0.10, p_value=0.001, prereg=_PRE,
    )
    assert r.status == "pass"


def test_degrade_when_not_better():
    r = evaluate_combo_gate(
        "enterobacter_cloacae", "meropenem",
        n_strains=300, n_st_with_R=15, vme_model=0.14, vme_rule=0.15,
        effect_size=-0.01, p_value=0.4, prereg=_PRE,
    )
    assert r.status == "degrade_classification"


def test_abstain_only_when_marginal_data():
    r = evaluate_combo_gate(
        "serratia_marcescens", "meropenem",
        n_strains=70, n_st_with_R=4, vme_model=None, vme_rule=None,
        effect_size=None, p_value=None, prereg=_PRE,
    )
    assert r.status == "abstain_only"


def test_kp_anchor_degrades():
    # 本项目真实 KP×meropenem 结果:ML 未显著优于规则 → degrade_classification
    r = evaluate_combo_gate(
        "klebsiella_pneumoniae", "meropenem",
        n_strains=717, n_st_with_R=68, vme_model=0.255, vme_rule=0.266,
        effect_size=-0.011, p_value=0.418, prereg=_PRE,
    )
    assert r.status == "degrade_classification"
