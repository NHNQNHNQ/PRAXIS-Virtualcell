"""ensembler:按 output_kind 分派聚合(MIC log2 几何均值 / SIR 概率均值 / synergy FIC),弃 delta。"""
from praxis_virtualcell.mdr_gnb.ensembler import aggregate, MDRPredictorResult


def _r(name, kind, pred, sigma=0.5, status="success"):
    return MDRPredictorResult(agent_name=name, status=status, output_kind=kind,
                              prediction=pred, uncertainty={"sigma": sigma},
                              evidence=[], provenance={"src": name})


def test_mic_scalar_geometric_mean_log2():
    # MIC 在 log2 尺度聚合:2 与 8 → 4(几何均值)
    res = aggregate([_r("a", "mic_scalar", {"mic_scalar": 2.0}),
                     _r("b", "mic_scalar", {"mic_scalar": 8.0})])
    assert abs(res.ensemble["mic_scalar"] - 4.0) < 1e-9
    assert res.output_kind == "mic_scalar"
    # 分歧 = log2 极差 = |log2(8)-log2(2)| = 2
    assert abs(res.disagreement["log2_range"] - 2.0) < 1e-9


def test_sir_class_probability_mean():
    res = aggregate([_r("a", "sir_class", {"sir_prob": {"S": 0.8, "I": 0.1, "R": 0.1}}),
                     _r("b", "sir_class", {"sir_prob": {"S": 0.2, "I": 0.1, "R": 0.7}})])
    assert abs(res.ensemble["sir_prob"]["S"] - 0.5) < 1e-9
    assert res.ensemble["sir"] in ("S", "R")  # argmax
    assert res.disagreement["metric"] == "mean_class_entropy"


def test_synergy_fic_mean():
    res = aggregate([_r("a", "synergy", {"fic_index": 0.4}),
                     _r("b", "synergy", {"fic_index": 0.6})])
    assert abs(res.ensemble["fic_index"] - 0.5) < 1e-9


def test_rejected_not_aggregated():
    res = aggregate([_r("a", "mic_scalar", {"mic_scalar": 2.0}),
                     _r("bad", "mic_scalar", {"mic_scalar": 99.0}, status="rejected")])
    assert res.models_used == ["a"] and res.models_rejected == ["bad"]
    assert abs(res.ensemble["mic_scalar"] - 2.0) < 1e-9


def test_empty_has_defined_semantics():
    res = aggregate([])
    assert res.ensemble is None and res.output_kind is None
    assert res.disagreement["reason"] == "no_models"


def test_mixed_output_kind_rejected():
    import pytest
    with pytest.raises(ValueError):
        aggregate([_r("a", "mic_scalar", {"mic_scalar": 2.0}),
                   _r("b", "sir_class", {"sir_prob": {"S": 1.0}})])
