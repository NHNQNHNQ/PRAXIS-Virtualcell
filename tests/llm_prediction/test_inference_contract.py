import json

import pytest
from pydantic import ValidationError

from praxis_virtualcell.llm_prediction import analyze_with_agents, workflow
from praxis_virtualcell.llm_prediction.schemas import Assessment, MICConditions, empty_assessment
from tests.llm_prediction.test_orchestrator import Client, Profile, assessment, plan, response, review, tool_response


async def test_assay_conditions_and_smiles_only_cross_real_roles_with_separate_analysis_route(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda *_: Profile())
    selected = ["transcriptome"]
    base = Client([response(plan(selected)), response(review())])
    qwen = Client([tool_response(selected), response(assessment(selected))])
    conditions = {"medium": "CAMHB", "medium_supplements": ["10% serum"], "temperature_c": 37.0,
                  "exposure_hours": 20.0, "method": "broth_microdilution", "inoculum": "5e5 CFU/mL"}
    result = await analyze_with_agents("OCC", "test-strain", client=base, model="base-reviewer",
                                       analysis_client=qwen, analysis_model="qwen-adapter", analysis_provider="qwen",
                                       conditions=conditions, candidate_id="PRIVATE_DRUG_NAME_CHEMBL999",
                                       modalities=selected, max_turns=2, analysis_max_output_tokens=4096, include_cell_structure=False)
    assert result["status"] == "completed"
    assert result["candidate"]["id"] == "PRIVATE_DRUG_NAME_CHEMBL999"
    assert result["conditions"] == conditions
    for request in base.requests + qwen.requests:
        user = json.loads(request["messages"][0]["content"])
        assert user["candidate"] == {"smiles": "CCO"}
        assert user["conditions"] == conditions
        assert "PRIVATE_DRUG_NAME_CHEMBL999" not in json.dumps(request)
    assert all(request["model"] == "base-reviewer" for request in base.requests)
    assert all(request["model"] == "qwen-adapter" and request["thinking"] == {"type": "disabled"}
               and "reasoning_effort" not in request and request["max_tokens"] == 4096 for request in qwen.requests)
    assert [stage["model"] for stage in result["agent_trace"]["stages"]] == ["base-reviewer", "qwen-adapter", "base-reviewer"]


async def test_conditional_observations_still_require_observed_omics_references(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda *_: Profile(["transcriptome"]))
    value = assessment(["transcriptome"])
    value["mic_estimate"]["evidence_refs"] = []
    value["mic_observations"] = [{"relation": ">", "value": 64, "lower": 64, "upper": None,
                                   "lower_closed": False, "upper_closed": True}]
    client = Client([tool_response(["transcriptome"]), response(value)])
    result = await workflow.analyze_candidate("CCO", "test-strain", client=client, _profile=Profile(["transcriptome"]), max_turns=2)
    assert result["status"] == "unsupported"
    assert "mic_observations_require_verified_gene_evidence" in result["evidence_validation"]["issues"]
    request = json.loads(client.requests[0]["messages"][0]["content"])
    assert request["conditions"] == MICConditions().model_dump()


def test_censored_and_repeated_mic_contract_preserves_bounds_without_averaging():
    value = empty_assessment("Heterogeneous conditional estimates")
    value["mic_observations"] = [
        {"relation": "=", "value": 4, "lower": 4, "upper": 4, "lower_closed": True, "upper_closed": True},
        {"relation": ">", "value": 64, "lower": 64, "upper": None, "lower_closed": False, "upper_closed": True},
    ]
    validated = Assessment.model_validate(value)
    assert validated.mic_estimate.value is None
    assert validated.mic_observations[1].lower == 64 and not validated.mic_observations[1].lower_closed
    value["mic_estimate"]["value"] = 34
    with pytest.raises(ValidationError, match="exact and equal"):
        Assessment.model_validate(value)
    value["mic_estimate"]["value"] = None
    value["mic_observations"][1]["lower_closed"] = True
    with pytest.raises(ValidationError, match="open/closed"):
        Assessment.model_validate(value)


@pytest.mark.parametrize("conditions", [{"exposure_hours": -1}, {"temperature_c": True},
                                          {"temperature_c": float("inf")}, {"MIC": 4}])
def test_invalid_assay_conditions_rejected(conditions):
    with pytest.raises(ValidationError):
        MICConditions.model_validate(conditions)
