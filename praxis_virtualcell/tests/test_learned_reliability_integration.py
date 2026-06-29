"""M2.1 Step6:learned reliability/abstain 接回 runtime 的验收测试(7 gates)。Mac 可跑。"""
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


# gate2:learned mode 能运行;gate6:report/payload 含 learned 决策 + provenance
def test_learned_mode_runs_and_emits_provenance():
    out = _rel(_base(dis=0.8), mode="learned")
    lr = out["learned_reliability"]
    assert lr["reliability_mode"] == "learned" and lr["fallback"] is False
    assert "reliability_score" in lr and lr["abstain_decision"] in ("accept", "downgrade", "abstain")
    assert lr["model_version"] == "reliability_v0.3.0"
    assert set(lr["features_used"]) == {"disagreement_score", "seen_in_train", "disagreement_n_zero_pairs"}


# gate3:无 artifact → fail-closed 退回 rule
def test_missing_artifact_falls_back_to_rule():
    out = _rel(_base(), mode="learned_with_rule_fallback", art_dir="/nonexistent_dir")
    lr = out["learned_reliability"]
    assert lr["fallback"] is True and lr["reason"] == "artifact_missing"
    # 决策仍由 rule 给出(不崩)
    assert out["reliability_decision"]["reliability"] in ("high", "medium", "low")


# gate4:schema 不匹配 → 退回 rule,reason 记录
def test_schema_mismatch_falls_back(tmp_path):
    (tmp_path / "reliability_model_v0_3.json").write_text(json.dumps(
        {"feature_schema_version": "WRONG", "features": [], "mean": [], "std": [], "weights": [0]}))
    (tmp_path / "abstain_head_v0_3.json").write_text(json.dumps(
        {"abstain_threshold_dp": 0.4, "downgrade_threshold_dp": 0.5}))
    out = _rel(_base(), mode="learned", art_dir=str(tmp_path))
    lr = out["learned_reliability"]
    assert lr["fallback"] is True and lr["reason"] == "schema_mismatch"


# gate5:禁止泄漏字段(label 进 runtime 特征 → 断言失败)
def test_no_leakage_label_rejected():
    from praxis_virtualcell.governance import learned_reliability as L
    import pytest
    with pytest.raises(AssertionError):
        L.score({"disagreement_score": 0.4, "delta_pearson": 0.7})  # delta_pearson 是 label


# 硬 abstain(全拒)即便 learned mode 也不被覆盖
def test_hard_abstain_not_overridden_by_learned():
    p = {"request": {"perturbation_targets": ["recA"]}, "models_used": [],
         "brain_context": {"species_supported": True,
                           "generic": {"default_abstain_rules": {"abstain_if": ["all_predictors_rejected"]}}}}
    out = _rel(p, mode="learned")
    assert out["reliability_decision"]["abstain"] is True
    assert "all_predictors_rejected" in out["reliability_decision"]["reasons"]


# gate7:复现 Step3 risk-coverage finding(用 ledger,不需 runtime 重训)
def test_reproduce_risk_coverage_finding():
    from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
    from praxis_virtualcell.governance import abstain_head as ah
    led = EvalLedger.from_jsonl("docs/findings/m1_ledger_151.jsonl")
    res = ah.evaluate_abstain(led.entries, k=5)
    assert abs(res["learned"]["auc"] - 0.746) < 0.01       # finding 记录值
    assert res["learned"]["auc"] > res["disagreement_only"]["auc"]


# gate6 e2e:默认 workflow report 携带 learned 决策(runtime 真的在用 learned)
def test_e2e_report_carries_learned_decision():
    from praxis_virtualcell.workflows.predict_delta_expression import run_request
    r = run_request({"request_id": "r", "species": "human", "perturbation_type": "gene",
                     "perturbation_targets": ["AHR"], "input_modality": "scRNA",
                     "output_modality": "delta_expression", "task_type": "predict_delta_expression"})
    lr = r["learned_reliability"]
    assert lr is not None and lr["reliability_mode"] == "learned_with_rule_fallback"
    assert lr["fallback"] is False and "reliability_score" in lr and lr["model_version"] == "reliability_v0.3.0"
    # 冻结治理证据:决策可追溯到 artifact 内容哈希(64 hex)
    assert len(lr["artifact_sha256"]) == 64 and len(lr["abstain_artifact_sha256"]) == 64
