from praxis_virtualcell.workflows.predict_delta_expression import run_request

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_human_request_predicts_no_abstain():
    report = run_request(_HUMAN)
    assert report["abstain"] is False
    assert "MockCPA" in report["models_used"]
    assert report["prediction"] is not None
    assert report["critic_violations"] == []


def test_bacteria_request_abstains_no_applicable_model():
    bact = dict(_HUMAN, species="bacteria", request_id="r2")
    report = run_request(bact)
    assert report["abstain"] is True
    assert report["models_used"] == []
