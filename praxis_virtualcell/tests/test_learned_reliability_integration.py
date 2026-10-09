"""Tests for learned reliability integration."""
import json

from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _rel(payload, **kw):
    bus = MessageBus()
    ReliabilityAgent(**kw).handle(AgentMessage("m", "X", "Reliability", "assess", payload, "t"), bus)
    return bus.latest("reliability_decided").payload


def _base(dis=0.4, used=("MockCPA", "MockGEARS")):
    return {"request": {"perturbation_targets": ["AHR"]}, "models_used": list(used),
            "ensemble": {"delta": [0.1]}, "disagreement": {"score": dis, "n_zero_vector_pairs": 0},
            "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": []}}}}



def test_learned_mode_runs_and_emits_provenance():
    out = _rel(_base(dis=0.8), mode="learned")
    lr = out["learned_reliability"]
    assert lr["reliability_mode"] == "learned" and lr["fallback"] is False
    assert "reliability_score" in lr and lr["abstain_decision"] in ("accept", "downgrade", "abstain")
    assert lr["model_version"] == "reliability_v0.3.0"
    assert set(lr["features_used"]) == {"disagreement_score", "seen_in_train", "disagreement_n_zero_pairs"}



def test_missing_artifact_falls_back_to_rule():
    out = _rel(_base(), mode="learned_with_rule_fallback", art_dir="/nonexistent_dir")
    lr = out["learned_reliability"]
    assert lr["fallback"] is True and lr["reason"] == "artifact_missing"

    assert out["reliability_decision"]["reliability"] in ("high", "medium", "low")



def test_schema_mismatch_falls_back(tmp_path):
    (tmp_path / "reliability_model_v0_3.json").write_text(json.dumps(
        {"feature_schema_version": "WRONG", "features": [], "mean": [], "std": [], "weights": [0]}))
    (tmp_path / "abstain_head_v0_3.json").write_text(json.dumps(
        {"abstain_threshold_dp": 0.4, "downgrade_threshold_dp": 0.5}))
    out = _rel(_base(), mode="learned", art_dir=str(tmp_path))
    lr = out["learned_reliability"]
    assert lr["fallback"] is True and lr["reason"] == "schema_mismatch"



def test_no_leakage_label_rejected():
    import pytest

    from praxis_virtualcell.governance import learned_reliability as L
    with pytest.raises(AssertionError):
        L.score({"disagreement_score": 0.4, "delta_pearson": 0.7})



def test_hard_abstain_not_overridden_by_learned():
    p = {"request": {"perturbation_targets": ["recA"]}, "models_used": [],
         "brain_context": {"species_supported": True,
                           "generic": {"default_abstain_rules": {"abstain_if": ["all_predictors_rejected"]}}}}
    out = _rel(p, mode="learned")
    assert out["reliability_decision"]["abstain"] is True
    assert "all_predictors_rejected" in out["reliability_decision"]["reasons"]



def test_reproduce_risk_coverage_finding():
    from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
    from praxis_virtualcell.governance import abstain_head as ah
    led = EvalLedger.from_jsonl("docs/findings/m1_ledger_151.jsonl")
    res = ah.evaluate_abstain(led.entries, k=5)
    assert abs(res["learned"]["auc"] - 0.746) < 0.01
    assert res["learned"]["auc"] > res["disagreement_only"]["auc"]



def test_e2e_report_carries_learned_decision():
    from praxis_virtualcell.workflows.predict_delta_expression import run_request
    r = run_request({"request_id": "r", "species": "human", "perturbation_type": "gene",
                     "perturbation_targets": ["AHR"], "input_modality": "scRNA",
                     "output_modality": "delta_expression", "task_type": "predict_delta_expression"})
    lr = r["learned_reliability"]
    assert lr is not None and lr["reliability_mode"] == "learned_with_rule_fallback"
    assert lr["fallback"] is False and "reliability_score" in lr and lr["model_version"] == "reliability_v0.3.0"

    assert len(lr["artifact_sha256"]) == 64 and len(lr["abstain_artifact_sha256"]) == 64



def test_artifact_tamper_falls_back(tmp_path):
    import json
    import os
    import shutil

    from praxis_virtualcell.governance import learned_reliability as L
    art = "praxis_virtualcell/governance/artifacts"
    for f in os.listdir(art):
        if f.endswith(".json"):
            shutil.copy(f"{art}/{f}", tmp_path / f)
    rel = json.loads((tmp_path / "reliability_model_v0_3.json").read_text())
    rel["weights"][1] += 99.0
    (tmp_path / "reliability_model_v0_3.json").write_text(json.dumps(rel))
    r = L.score({"disagreement_score": 0.4}, art_dir=str(tmp_path))
    assert r["fallback"] is True and r["reason"] == "integrity_mismatch"
    (tmp_path / "reliability_model_v0_3.json").write_text(json.dumps({"feature_schema_version": "v0.3.0"}))
    r2 = L.score({"disagreement_score": 0.4}, art_dir=str(tmp_path))
    assert r2["fallback"] is True and r2["reason"] == "incomplete_artifact"



def test_mode_compare_learned_improves_soft_risk():
    from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
    from praxis_virtualcell.governance import mode_compare as mc
    r = mc.compare(EvalLedger.from_jsonl("docs/findings/m1_ledger_151.jsonl").entries)
    assert r["hard_rule_override"] == 0 and r["provenance_complete"] is True
    learned = r["modes"]["learned_with_rule_fallback"]
    rule = r["modes"]["rule_only"]
    assert learned["wrong_accept"] < rule["wrong_accept"] - 0.3
    assert learned["risk_coverage"] > rule["risk_coverage"] + 0.3
