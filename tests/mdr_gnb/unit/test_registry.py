"""PredictorRegistry:能力声明式注册/发现,替代硬编码候选表。"""
import pytest

from praxis_virtualcell.mdr_gnb.predictors.registry import (
    PredictorRegistry, PredictorSpec,
)


def _spec(name, species, drug_class, output_kind, version="v1"):
    return PredictorSpec(
        name=name, version=version, species=list(species),
        drug_class=list(drug_class), output_kind=output_kind,
        artifact_path=f"data/mdr_gnb/models/{name}.joblib",
        requires=[], predict=lambda ctx: {"stub": name},
    )


def test_discover_by_capability():
    reg = PredictorRegistry()
    reg.register(_spec("ecoli_mic", ["escherichia_coli"], ["carbapenems"], "mic_scalar"))
    reg.register(_spec("kpn_sir", ["klebsiella_pneumoniae"], ["carbapenems"], "sir_class"))

    hit = reg.discover(species="escherichia_coli", drug_class="carbapenems",
                       output_kind="mic_scalar")
    assert [s.name for s in hit] == ["ecoli_mic"]
    # 物种不匹配 → 空
    assert reg.discover(species="klebsiella_pneumoniae", drug_class="carbapenems",
                        output_kind="mic_scalar") == []
    # output_kind 不匹配 → 空(kpn 只注册了 sir_class)
    assert reg.discover(species="klebsiella_pneumoniae", drug_class="carbapenems",
                        output_kind="mic_scalar") == []


def test_wildcard_species_and_drug_class():
    reg = PredictorRegistry()
    reg.register(_spec("rule_sir", ["*"], ["*"], "sir_class"))
    hit = reg.discover(species="proteus_mirabilis", drug_class="fluoroquinolones",
                       output_kind="sir_class")
    assert [s.name for s in hit] == ["rule_sir"]


def test_version_query_and_duplicate_rejected():
    reg = PredictorRegistry()
    reg.register(_spec("ecoli_mic", ["escherichia_coli"], ["carbapenems"], "mic_scalar", "v3"))
    assert reg.get("ecoli_mic").version == "v3"
    with pytest.raises(ValueError):
        reg.register(_spec("ecoli_mic", ["escherichia_coli"], ["carbapenems"], "mic_scalar", "v3"))


def test_deterministic_order():
    reg = PredictorRegistry()
    reg.register(_spec("b_model", ["escherichia_coli"], ["carbapenems"], "mic_scalar"))
    reg.register(_spec("a_model", ["escherichia_coli"], ["carbapenems"], "mic_scalar"))
    hit = reg.discover(species="escherichia_coli", drug_class="carbapenems",
                       output_kind="mic_scalar")
    assert [s.name for s in hit] == ["a_model", "b_model"]  # 名字排序,replay 稳定
