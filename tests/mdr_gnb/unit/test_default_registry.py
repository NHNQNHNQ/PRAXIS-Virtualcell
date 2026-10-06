"""默认注册装配:M2 模型 + M3 机理层包成 PredictorSpec,按能力可发现。"""
from praxis_virtualcell.mdr_gnb.predictors.default_registry import build_default_registry


def test_anchor_combinations_discoverable():
    reg = build_default_registry()
    # 锚点 1:E. coli × carbapenems 应能发现 MIC 回归 + 规则基线
    mic = reg.discover(species="escherichia_coli", drug_class="carbapenems",
                       output_kind="mic_scalar")
    assert any(s.name == "mic_regressor" for s in mic)
    rule = reg.discover(species="escherichia_coli", drug_class="carbapenems",
                        output_kind="sir_class")
    names = {s.name for s in rule}
    assert {"rule_baseline_sir", "genotype_to_sir"} <= names


def test_rule_baseline_is_wildcard_fallback():
    reg = build_default_registry()
    # 固有耐药物种也必须至少有规则基线兜底(SIR)
    hit = reg.discover(species="stenotrophomonas_maltophilia",
                       drug_class="fluoroquinolones", output_kind="sir_class")
    assert any(s.name == "rule_baseline_sir" for s in hit)


def test_mechanism_layer_registered_with_g3_flag():
    reg = build_default_registry()
    mech = reg.discover(species="klebsiella_pneumoniae", drug_class="carbapenems",
                        output_kind="mechanism_state")
    assert mech, "机理状态模型必须注册"
    # G3 门:每个机理 spec 的 requires 必含 g3_passed 声明
    assert all("g3_passed" in s.requires for s in mech)
