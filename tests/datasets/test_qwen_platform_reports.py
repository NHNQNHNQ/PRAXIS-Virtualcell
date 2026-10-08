from copy import deepcopy

import pytest

from praxis_virtualcell.datasets.qwen_evaluation import _prediction
from praxis_virtualcell.llm_prediction.orchestrator import _assessment_output
from praxis_virtualcell.llm_prediction.schemas import Assessment, empty_assessment


def test_qwen_scorer_accepts_real_workflow_display_metadata_without_mutating_it():
    target = empty_assessment("Uncalibrated estimate")
    target["mic_estimate"]["value"] = 8.0
    target["targets"] = [{"name": "A hypothetical target", "target_id": None, "hypothesis": "Not established"}]
    target["mechanism_hypotheses"] = [{"hypothesis": "Not established"}]
    displayed = _assessment_output(Assessment.model_validate(target))
    original = deepcopy(displayed)
    parsed, error = _prediction({"status": "completed", "assessment": displayed})
    assert error is None and parsed["mic_estimate"]["value"] == 8.0
    assert displayed == original
    assert "causality_verified" not in parsed["targets"][0] and "identity_observed" not in parsed["targets"][0]
    assert "causality_verified" not in parsed["mechanism_hypotheses"][0]


def test_qwen_scorer_still_rejects_unknown_nested_contract_fields():
    target = empty_assessment("Unknown estimate")
    target["targets"] = [{"name": "A target", "hypothesis": "Not established", "unexpected_private_field": "bad"}]
    parsed, error = _prediction({"status": "completed", "assessment": target})
    assert parsed is None and error == "invalid_assessment_contract"


@pytest.mark.parametrize("section,item", [("targets", "malformed"), ("mechanism_hypotheses", 7)])
def test_malformed_model_list_items_are_invalid_reports_without_crashing_the_scorer(section, item):
    target = empty_assessment("Malformed model report")
    target[section] = [item]
    parsed, error = _prediction({"status": "completed", "assessment": target})
    assert parsed is None and error == "invalid_assessment_contract"
