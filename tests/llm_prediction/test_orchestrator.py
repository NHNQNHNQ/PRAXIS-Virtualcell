"""Agent protocol, modality ablation and bounded scientific-review behavior."""
from copy import deepcopy
import itertools
import json
from pathlib import Path

import pytest

from praxis_virtualcell.llm_prediction import analyze_with_agents, workflow
from praxis_virtualcell.llm_prediction.schemas import empty_assessment
from praxis_virtualcell.llm_prediction.trajectories import export_trajectories


MODALITIES = ["genome", "transcriptome", "proteome"]
FEATURES = {
    "genome": {"feature_id": "gene-1", "gene_id": "ABUW_0001", "protein_id": "P1", "presence": True},
    "transcriptome": {"feature_id": "RNA-1", "gene_id": "ABUW_0001", "protein_id": "P1", "expression_value": 0.0},
    "proteome": {"feature_id": "P1", "gene_id": None, "protein_id": "P1", "abundance_value": 7.5},
}
FIELDS = {"genome": "presence", "transcriptome": "expression_value", "proteome": "abundance_value"}


class Profile:
    def __init__(self, selected=None):
        self.selected = list(selected or MODALITIES)

    def select_modalities(self, selected=None):
        if selected is not None and (not selected or set(selected) - set(MODALITIES)):
            raise ValueError("unavailable modality")
        return Profile(selected)

    def overview(self):
        return {"profile_id": "test-strain", "source_id": "omics:test-strain:profile",
                "species": {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"}, "strain": "test",
                "available_modalities": MODALITIES, "selected_modalities": self.selected,
                "modalities": {name: {"unit": "test native unit"} for name in self.selected}}

    def query_features(self, modality, feature_ids, limit=30):
        if modality not in self.selected:
            raise ValueError("unselected")
        row = {**FEATURES[modality], "modality": modality, "unit": "test native unit",
               "source_id": f"omics:test-strain:{modality}:feature:{FEATURES[modality]['feature_id']}",
               "source_locator": {"row": 1}}
        return {"profile_id": "test-strain", "modality": modality,
                "features": [row] if row["feature_id"] in feature_ids else [],
                "missing_feature_ids": [], "truncated": False}


class Client:
    def __init__(self, responses):
        self.responses = deepcopy(responses)
        self.requests = []

    async def messages(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        return self.responses.pop(0)


def response(value, **message_fields):
    return {"choices": [{"message": {"content": json.dumps(value), "reasoning_content": "PRIVATE_REASONING",
                                      **message_fields}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def plan(selected):
    return {"selected_modalities": selected, "questions": ["这些观察对药效判断有什么支持和缺口？"],
            "search_terms": ["membrane"], "limitations": ["没有靶点结合实验。"]}


def tool_response(selected):
    calls = [{"id": f"read-{name}", "type": "function", "function": {
        "name": "query_features", "arguments": json.dumps({"modality": name, "feature_ids": [FEATURES[name]["feature_id"]]})
    }} for name in selected]
    return response(None, content=None, tool_calls=calls)


def assessment(selected, mic=None):
    value = empty_assessment("这是基于已提供观察的未校准假说。")
    observations = []
    for name in selected:
        row = FEATURES[name]
        field = FIELDS[name]
        ref = {"tool_call_id": f"read-{name}", "pointer": f"/features/0/{field}",
               "source_id": f"omics:test-strain:{name}:feature:{row['feature_id']}", "value": row[field]}
        observations.append({"gene_id": row["gene_id"], "field": field, "value": row[field], "evidence_ref": ref})
    value["supporting_evidence"] = [{"claim": "各项观测保留原始单位，尚不能证明药物结合。", "observations": observations}]
    value["mic_estimate"]["value"] = mic
    value["mic_estimate"]["evidence_refs"] = [observations[0]["evidence_ref"]]
    return value


def review(decision="accept"):
    return {"decision": decision, "summary": "观察引用一致，药效仍需实验验证。",
            "issues": [] if decision == "accept" else [{"code": "certainty", "severity": "blocking",
                                                         "finding": "缺少直接药效证据，应降低数值判断的确定性。"}],
            "recommended_changes": [] if decision == "accept" else ["MIC 保持未知。"]}


@pytest.fixture(autouse=True)
def loaded_profile(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda profile_id, data_root: Profile())


COMBINATIONS = [list(combo) for n in range(1, 4) for combo in itertools.combinations(MODALITIES, n)]


@pytest.mark.parametrize("selected", COMBINATIONS)
async def test_direct_analysis_uses_the_loaded_view_when_modalities_are_omitted(selected):
    client = Client([tool_response(selected), response(assessment(selected))])
    result = await workflow.analyze_candidate("CCO", "test-strain", client=client,
                                              _profile=Profile(selected), max_turns=2)
    assert result["status"] == "completed"
    assert result["profile"]["selected_modalities"] == selected
    assert "query_features" in {item["function"]["name"] for item in client.requests[0]["tools"]}
    assert "EVERY selected modality" in client.requests[0]["system"]


async def test_direct_analysis_cannot_skip_other_loaded_modalities_without_a_selection_argument():
    client = Client([tool_response(["transcriptome"]), response(assessment(["transcriptome"]))])
    result = await workflow.analyze_candidate("CCO", "test-strain", client=client,
                                              _profile=Profile(), max_turns=2)
    assert result["status"] == "unsupported"
    assert result["assessment"]["mic_estimate"]["value"] is None
    assert "selected_modality_not_observed:genome" in result["evidence_validation"]["issues"]
    assert "selected_modality_not_cited:proteome" in result["evidence_validation"]["issues"]


@pytest.mark.parametrize("selected", COMBINATIONS)
async def test_seven_views_run_review_and_export_without_hidden_reasoning(selected):
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected)), response(review())])
    events = []
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected,
                                       max_turns=2, on_progress=events.append)
    assert result["status"] == "completed"
    assert result["review_resolution"] == "accepted"
    assert result["profile"]["selected_modalities"] == selected
    assert [stage["stage"] for stage in result["agent_trace"]["stages"]] == ["planning", "analysis", "review"]
    assert result["execution_trace"]["token_usage"]["total_tokens"] == 60
    assert result["agent_trace"]["token_usage"] == result["execution_trace"]["token_usage"]
    assert "PRIVATE_REASONING" not in json.dumps(result)
    assert all(call["data"].get("modality") in selected for call in result["execution_trace"]["tool_calls"]
               if call["name"] == "query_features")
    assert client.requests[0]["tools"] is None
    assert client.requests[-1]["tools"] is None
    assert events[-1]["stage"] == "report_completed"
    exported = export_trajectories(result)
    assert not exported["skipped"]
    assert [row["stage"] for row in exported["records"]] == ["planning", "analysis", "review"]
    assert all(row["supervision"]["prediction_is_gold"] is False for row in exported["records"])


async def test_once_revised_answer_requires_second_review_and_rejected_draft_is_not_exported():
    selected = ["transcriptome"]
    revised = assessment(selected)
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected, 8)),
                     response(review("revise")), response(revised), response(review())])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "completed"
    assert result["review_resolution"] == "revised"
    assert result["assessment"]["mic_estimate"]["value"] is None
    stages = result["agent_trace"]["stages"]
    assert [stage["stage"] for stage in stages] == ["planning", "analysis", "review", "revision", "review"]
    assert stages[1]["rejected"] is True
    exported = export_trajectories(result)
    assert "analysis" not in [record["stage"] for record in exported["records"]]
    assert "revision" in [record["stage"] for record in exported["records"]]
    assert len(client.requests) == 6


@pytest.mark.parametrize("decision", ["revise", "abstain"])
async def test_second_review_cannot_trigger_another_revision_or_release_numeric_draft(decision):
    selected = ["transcriptome"]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected, 8)),
                     response(review("revise")), response(assessment(selected, 4)), response(review(decision))])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert result["assessment"]["mic_estimate"]["value"] is None
    assert len(client.requests) == 6
    assert not export_trajectories(result)["records"]


async def test_review_abstention_does_not_release_an_analysis_draft():
    selected = ["proteome"]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected, 8)), response(review("abstain"))])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert result["review_resolution"] == "abstained"
    assert result["assessment"]["targets"] == []
    assert result["assessment"]["mic_estimate"]["value"] is None
    assert result["agent_rejected_assessment"]["mic_estimate"]["value"] == 8


@pytest.mark.parametrize("bad_plan", [{"selected_modalities": ["transcriptome"], "questions": []}, plan(["genome"])])
async def test_invalid_plan_stops_before_analysis(bad_plan):
    client = Client([response(bad_plan)])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=["transcriptome"])
    assert result["status"] == "unsupported"
    assert len(client.requests) == 1
    assert result["agent_trace"]["stages"][0]["rejected"] is True


@pytest.mark.parametrize("review_value", [{"decision": "accept", "summary": "ok", "issues": review("revise")["issues"]},
                                         {"decision": "revise", "summary": "ok", "issues": [], "recommended_changes": []}])
async def test_inconsistent_review_fails_closed(review_value):
    selected = ["transcriptome"]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected, 8)), response(review_value)])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert result["evidence_validation"]["issues"] == ["review_failed"]
    assert result["assessment"]["mic_estimate"]["value"] is None


async def test_reviewer_cannot_invent_a_citation():
    selected = ["transcriptome"]
    value = review()
    value["issues"] = [{"code": "warning", "severity": "warning", "finding": "数据不足。",
                        "evidence_refs": [{"tool_call_id": "nonexistent", "pointer": "/value", "source_id": "fake", "value": 1}]}]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected)), response(value)])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert result["agent_trace"]["stages"][-1]["error"] == "invalid_review_reference"


async def test_reading_modalities_without_citing_each_one_is_rejected():
    selected = MODALITIES
    value = assessment(["transcriptome"])
    client = Client([response(plan(selected)), tool_response(selected), response(value)])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert "selected_modality_not_cited:genome" in result["evidence_validation"]["issues"]
    assert "selected_modality_not_cited:proteome" in result["evidence_validation"]["issues"]
    assert len(client.requests) == 3


async def test_unselected_modality_tool_cannot_read_its_data():
    selected = ["transcriptome"]
    client = Client([response(plan(selected)), tool_response(["proteome"]), response(assessment(["proteome"]))])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    call = result["execution_trace"]["tool_calls"][-1]
    assert call["ok"] is False
    assert call["error"] == "modality_not_selected"
    assert "data" not in call


async def test_revision_with_forged_measurement_stops_before_second_review():
    selected = ["transcriptome"]
    invalid = assessment(selected)
    invalid["supporting_evidence"][0]["observations"][0]["value"] = 99
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected)),
                     response(review("revise")), response(invalid)])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert result["evidence_validation"]["issues"] == ["revision_evidence_failed"]
    assert len(client.requests) == 5


async def test_missing_client_or_invalid_selection_never_calls_an_llm():
    client = Client([])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=["unknown"])
    assert result["status"] == "error"
    assert result["evidence_validation"]["issues"] == ["profile_or_modalities_unavailable"]
    assert not client.requests
    result = await analyze_with_agents("CCO", "test-strain")
    assert result["evidence_validation"]["issues"] == ["llm_client_required"]


async def test_callback_failure_does_not_break_valid_analysis():
    selected = ["transcriptome"]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected)), response(review())])
    async def progress(event):
        raise RuntimeError("callback failed")
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected,
                                       max_turns=2, on_progress=progress)
    assert result["status"] == "completed"
    assert result["agent_trace"]["events"][0]["event"] == "progress_callback_failed"


async def test_existing_measured_v1_profile_runs_through_new_roles_and_export(monkeypatch):
    from praxis_virtualcell.omics import load_profile
    root = Path(__file__).parents[2] / "data" / "organisms"
    if not (root / "AB5075-AZI000" / "manifest.json").exists():
        pytest.skip("The real local profile is not redistributed with Git")
    monkeypatch.setattr(workflow, "_load_organism", lambda profile_id, data_root: load_profile(profile_id, root))
    profile = load_profile("AB5075-AZI000", root)
    gene = profile.query_features("transcriptome", ["ABUW_0001"])["features"][0]
    tool = response(None, content=None, tool_calls=[{"id": "read-native", "type": "function", "function": {
        "name": "query_features", "arguments": json.dumps({"modality": "transcriptome", "feature_ids": ["ABUW_0001"]})}}])
    ref = {"tool_call_id": "read-native", "pointer": "/features/0/expression_value",
           "source_id": gene["source_id"], "value": gene["expression_value"]}
    value = empty_assessment("真实 RNA 背景不能证明直接靶点结合。")
    value["supporting_evidence"] = [{"claim": "读取该参考背景的原生表达观察。", "observations": [
        {"gene_id": "ABUW_0001", "field": "expression_value", "value": gene["expression_value"], "evidence_ref": ref}]}]
    client = Client([response(plan(["transcriptome"])), tool, response(value), response(review())])
    result = await analyze_with_agents("CCO", "AB5075-AZI000", client=client, max_turns=2)
    assert result["status"] == "completed"
    assert result["profile"]["selected_modalities"] == ["transcriptome"]
    assert result["execution_trace"]["tool_calls"][-1]["data"]["features"][0]["expression_value"] == gene["expression_value"]
    assert len(export_trajectories(result)["records"]) == 3
