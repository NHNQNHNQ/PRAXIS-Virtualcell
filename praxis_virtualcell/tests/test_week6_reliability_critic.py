"""Tests for week6 reliability critic."""
from praxis_virtualcell.agents.critic import CriticAgent
from praxis_virtualcell.agents.ensemble import _disagreement
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _result(name, status, delta=None, sigma=0.2):
    return {"agent_name": name, "status": status,
            "prediction": {"delta": delta} if status == "success" else None,
            "uncertainty": {"sigma": sigma} if status == "success" else None,
            "applicability_score": 1.0, "evidence": [], "rejection_reason": None, "provenance": {}}


# --- model disagreement (§8.3) ---

def test_disagreement_score_direction_sensitive():
    assert _disagreement([[0.5], [0.5]])["score"] == 0.0
    assert _disagreement([[0.5], [-0.5]])["score"] == 1.0
    assert _disagreement([[0.5]])["score"] is None


def test_disagreement_zero_vector_audited():
    d = _disagreement([[0.0], [0.5]])
    assert d["n_zero_vector_pairs"] == 1


def _rel(payload):
    bus = MessageBus()
    ReliabilityAgent().handle(AgentMessage("m", "X", "Reliability", "assess", payload, "t"), bus)
    return bus.latest("reliability_decided").payload["reliability_decision"]


def test_disagreement_high_abstains_when_rule_present():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockCPA", "MockGEARS"],
               "ensemble": {"delta": [0.05]}, "disagreement": {"score": 0.9},
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["model_disagreement_too_high"]}}}})  # noqa: E501
    assert rd["abstain"] is True and "model_disagreement_too_high" in rd["reasons"]
    assert rd["model_disagreement"]["triggered"] is True


def test_disagreement_high_downgrades_when_no_abstain_rule():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockCPA", "MockGEARS"],
               "ensemble": {"delta": [0.05]}, "disagreement": {"score": 0.9},
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": []}}}})
    assert rd["abstain"] is False and rd["reliability"] == "medium"
    assert "downgrade:model_disagreement_too_high" in rd["reasons"]


# --- core_predictor_failed (§8.2) ---

def test_core_predictor_failed_abstains():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockGEARS"],
               "ensemble": {"delta": [0.1]},
               "results": [_result("MockCPA", "failed"), _result("MockGEARS", "success", [0.1])],
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["core_predictor_failed"]},
                                             "core_predictors": {"core": ["MockCPA"]}}}})
    assert rd["abstain"] is True and "core_predictor_failed" in rd["reasons"]


def test_non_core_failed_does_not_abstain():
    rd = _rel({"request": {"perturbation_targets": ["A"]}, "models_used": ["MockGEARS"],
               "ensemble": {"delta": [0.1]},
               "results": [_result("MockCPA", "failed"), _result("MockGEARS", "success", [0.1])],
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["core_predictor_failed"]},
                                             "core_predictors": {"core": []}}}})
    assert rd["abstain"] is False




def test_cell_type_unsupported_lowers_reliability():
    rd = _rel({"request": {"perturbation_targets": ["A"], "cell_type": "Jurkat"},
               "models_used": ["MockCPA", "MockGEARS"], "ensemble": {"delta": [0.1]},
               "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": []}},
                                 "model_applicability": {"MockCPA": {"supported_cell_types": ["K562"]},
                                                         "MockGEARS": {"supported_cell_types": ["K562"]}}}})
    assert rd["abstain"] is False and rd["reliability"] == "medium"
    assert "downgrade:cell_type_not_supported" in rd["reasons"]




def _crit(payload, trace_types=("brain_retrieved", "predictor_result")):
    bus = MessageBus()
    for i, t in enumerate(trace_types):
        bus.send(AgentMessage(f"b{i}", "X", "Y", t, {}, "t"))
    CriticAgent().handle(AgentMessage("m", "X", "Critic", "review", payload, "t"), bus)
    return bus.latest("critic_done").payload["critic_violations"]


def test_critic_missing_provenance():
    v = _crit({"brain_context": {"rules_referenced": []}, "request": {"species": "human"},
               "reliability_decision": {"abstain": False}, "models_used": ["MockCPA"],
               "results": [_result("MockCPA", "success", [0.1])]})
    assert "missing_provenance" in v


def test_critic_missing_uncertainty():
    bad = _result("MockCPA", "success", [0.1])
    bad["uncertainty"] = None
    v = _crit({"brain_context": {"rules_referenced": ["x.yaml"]}, "request": {"species": "human"},
               "reliability_decision": {"abstain": False}, "models_used": ["MockCPA"], "results": [bad]})
    assert any(x.startswith("missing_uncertainty") for x in v)


def test_critic_abstain_inconsistent_with_prediction():
    v = _crit({"brain_context": {"rules_referenced": ["x.yaml"]}, "request": {"species": "human"},
               "reliability_decision": {"abstain": True}, "models_used": [], "ensemble": {"delta": [0.1]},
               "results": []})
    assert "abstain_inconsistent_with_prediction" in v


def test_critic_happy_no_violations():
    v = _crit({"brain_context": {"rules_referenced": ["x.yaml"],
                                 "model_applicability": {"MockCPA": {"supported_species": ["human"]}}},
               "request": {"species": "human"}, "reliability_decision": {"abstain": False},
               "models_used": ["MockCPA"], "ensemble": {"delta": [0.1]},
               "results": [_result("MockCPA", "success", [0.1])]})
    assert v == []




def test_report_cell_type_out_of_domain_abstains_e2e():
    from praxis_virtualcell.workflows.predict_delta_expression import run_request



    r = run_request({"request_id": "r", "species": "human", "perturbation_type": "gene",
                     "perturbation_targets": ["AHR"], "input_modality": "scRNA",
                     "output_modality": "delta_expression", "task_type": "predict_delta_expression",
                     "cell_type": "Jurkat"})
    assert r["abstain"] is True
    assert "cell_type_out_of_domain" in r["abstain_reasons"]
    assert "downgrade:cell_type_not_supported" in r["downgrade_reasons"]
    assert r["provenance"]["cell_type_gate"]["reliability_original_abstain"] is False
    assert "models_failed" in r and "model_disagreement" in r
