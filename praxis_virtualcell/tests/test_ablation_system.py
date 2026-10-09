"""Tests for ablation system."""
from praxis_virtualcell.benchmarks.ablation import SEED_REQUESTS, run_ablation, run_group_A, run_group_D


def test_ablation_A_vs_D_two_poles():
    r = run_ablation()
    a, d = r["A_ML_only"], r["D_Full"]

    assert a["OOD_rejection_rate"] == 0.0 and d["OOD_rejection_rate"] == 1.0
    assert a["wrong_model_use_rate"] == 1.0 and d["wrong_model_use_rate"] == 0.0
    assert a["provenance_completeness"] == 0.0 and d["provenance_completeness"] >= 0.9
    assert a["abstain_correctness"] == 0.0 and d["abstain_correctness"] == 1.0
    assert a["trace_completeness"] == 0.0 and d["trace_completeness"] == 1.0


def test_group_A_hard_predicts_ood():

    out = run_group_A(SEED_REQUESTS[1])  # bacteria_ood
    assert out["abstain"] is False and out["models_used"]
    assert out["trace"] is None and out["provenance"] is None


def test_group_D_abstains_ood():

    out = run_group_D(SEED_REQUESTS[1])  # bacteria_ood
    assert out["abstain"] is True and out["models_used"] == []
    assert out["trace"] is not None


def test_group_D_indist_predicts():

    out = run_group_D(SEED_REQUESTS[0])  # human_indist
    assert out["abstain"] is False and "MockCPA" in out["models_used"]
