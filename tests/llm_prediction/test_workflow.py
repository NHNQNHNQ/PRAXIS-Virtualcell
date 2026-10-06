"""Pure-LLM tool execution, evidence binding and unsupported result contracts."""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from praxis_virtualcell.llm_prediction import analyze_candidate, analyze_candidates, render_report
from praxis_virtualcell.llm_prediction import workflow


GENE = {
    "gene_id": "ABUW_0001", "expression_value": 3.5, "unit": "normalized_mean_intensity",
    "scale": "source_normalized", "gene_symbol": "example", "product": "example membrane protein",
    "protein_id": "P-example", "source_id": "omics:AB5075-AZI000:gene:ABUW_0001",
    "source_locator": {"expression_file": "expression.tsv", "row": 1},
}


class Profile:
    def overview(self):
        return {"profile_id": "AB5075-AZI000", "species": "Acinetobacter baumannii", "strain": "AB5075",
                "condition": "AZI_000", "source_id": "omics:AB5075-AZI000:profile",
                "unknown_fields": ["protein abundance", "drug response"]}

    def query_genes(self, gene_ids, limit=30):
        return {"profile_id": "AB5075-AZI000", "genes": [deepcopy(GENE)] if GENE["gene_id"] in gene_ids else [],
                "missing_gene_ids": [g for g in gene_ids if g != GENE["gene_id"]], "truncated": False}

    def search_annotations(self, query, limit=30):
        return {"profile_id": "AB5075-AZI000", "genes": [deepcopy(GENE)],
                "query": query, "match_count": 1, "truncated": False}


@pytest.fixture(autouse=True)
def profile(monkeypatch):
    def load(profile_id, data_root):
        if profile_id != "AB5075-AZI000":
            raise KeyError("unknown profile")
        return Profile()
    monkeypatch.setattr(workflow, "_load_organism", load)


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.last_response = None

    async def messages(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        if self.responses:
            self.last_response = self.responses.pop(0)
        if self.last_response is None:
            raise AssertionError("No mock responses supplied")
        return deepcopy(self.last_response)


def tool_response(name="query_genes", arguments=None, call_id="genes-1", reasoning="PRIVATE_REASONING"):
    return {"choices": [{"message": {"role": "assistant", "content": None, "reasoning_content": reasoning,
                                      "tool_calls": [{"id": call_id, "type": "function", "function": {
                                          "name": name, "arguments": json.dumps(arguments or {"gene_ids": ["ABUW_0001"]})}}]},
                         "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def ref(field="expression_value", value=3.5):
    return {"tool_call_id": "genes-1", "pointer": f"/genes/0/{field}",
            "source_id": GENE["source_id"], "value": value}


def assessment(mic=8.0):
    evidence = ref()
    return {
        "activity": "uncertain", "mic_estimate": {"value": mic, "unit": "ug/mL", "basis": "llm_estimate",
                                                    "reason": "An uncalibrated hypothesis using observed omics.",
                                                    "evidence_refs": [evidence]},
        "confidence": {"level": "low", "calibrated": False}, "killing_effect": "unknown",
        "targets": [{"name": "example membrane protein", "target_id": "ABUW_0001",
                     "hypothesis": "Possible target, not established by baseline expression.", "status": "hypothesis",
                     "evidence_refs": [ref("gene_id", "ABUW_0001")], "counterevidence_refs": []}],
        "mechanism_hypotheses": [{"hypothesis": "Potential envelope effect requiring experiments.",
                                  "status": "hypothesis", "evidence_refs": [evidence], "counterevidence_refs": []}],
        "supporting_evidence": [{"claim": "A source annotation and basal observation are available.",
                                 "observations": [{"gene_id": "ABUW_0001", "field": "expression_value", "value": 3.5,
                                                   "evidence_ref": evidence}], "evidence_refs": [evidence]}],
        "counterevidence": [], "gaps": ["No binding or bactericidal data."],
        "rationale_summary": "The candidate remains an experimental hypothesis.",
    }


def final_response(value):
    return {"choices": [{"message": {"role": "assistant", "content": json.dumps(value),
                                      "reasoning_content": "PRIVATE_FINAL_REASONING"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}}


async def test_real_tool_loop_and_reasoning_are_not_persisted():
    client = Client([tool_response(), final_response(assessment())])
    result = await analyze_candidate("CCO", client=client, candidate_id="C1")
    assert result["status"] == "completed"
    assert result["assessment"]["mic_estimate"]["value"] == 8
    assert result["assessment"]["confidence"]["calibrated"] is False
    assert result["assessment"]["targets"][0]["causality_verified"] is False
    assert result["execution_trace"]["token_usage"]["total_tokens"] == 45
    assert result["execution_trace"]["tool_calls"][-1]["data"]["genes"][0] == GENE
    second_messages = client.requests[1]["messages"]
    assert second_messages[-2]["reasoning_content"] == "PRIVATE_REASONING"
    assert second_messages[-1]["role"] == "tool"
    assert second_messages[-1]["tool_call_id"] == "genes-1"
    assert "PRIVATE_REASONING" not in json.dumps(result)
    assert "PRIVATE_FINAL_REASONING" not in render_report(result)
    assert client.requests[0]["max_tokens"] == 10000
    assert client.requests[0]["thinking"] == {"type": "enabled"}
    assert client.requests[0]["reasoning_effort"] == "high"


async def test_unknown_mic_remains_null():
    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(assessment(None))]))
    assert result["status"] == "completed"
    assert result["assessment"]["mic_estimate"]["value"] is None
    assert "未知（未给出数值）" in render_report(result)


async def test_profile_and_structure_errors_do_not_call_llm():
    client = Client([])
    result = await analyze_candidate("CCO", profile_id="missing", client=client)
    assert result["status"] == "error"
    assert result["assessment"]["gaps"] == ["profile_unavailable"]
    result = await analyze_candidate("invalid molecule", client=client)
    assert result["assessment"]["gaps"] == ["invalid_smiles"]
    assert not client.requests


@pytest.mark.parametrize("change,issue", [
    ("value", "quoted_value_does_not_match_tool"),
    ("source", "source_id_does_not_match_tool"),
    ("pointer", "unresolved_evidence_pointer"),
    ("call", "unknown_or_failed_tool_call"),
    ("gene", "target_identity_not_observed"),
    ("text_gene", "gene_in_text_not_observed"),
    ("observation", "observation_value_does_not_match_tool"),
    ("text_expression", "expression_quantity_in_text_not_observed"),
    ("text_source", "source_in_text_not_observed"),
])
async def test_fabricated_evidence_is_rejected(change, issue):
    value = assessment()
    evidence = value["mic_estimate"]["evidence_refs"][0]
    if change == "value": evidence["value"] = 999
    if change == "source": evidence["source_id"] = "invented-paper"
    if change == "pointer": evidence["pointer"] = "/genes/999/expression_value"
    if change == "call": evidence["tool_call_id"] = "not-called"
    if change == "gene": value["targets"][0]["target_id"] = "ABUW_9999"
    if change == "text_gene": value["rationale_summary"] = "ABUW_9999 is expressed."
    if change == "observation": value["supporting_evidence"][0]["observations"][0]["value"] = 999
    if change == "text_expression": value["rationale_summary"] = "ABUW_0001 expression_value = 999."
    if change == "text_source": value["rationale_summary"] = "According to omics:AB5075-AZI000:invented."
    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(value)]))
    assert result["status"] == "unsupported"
    assert issue in result["evidence_validation"]["issues"]
    assert result["assessment"]["mic_estimate"]["value"] is None


@pytest.mark.parametrize("mic", [0, -1, "8", True, float("nan"), float("inf")])
async def test_invalid_numbers_are_not_predictions(mic):
    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(assessment(mic))]))
    assert result["status"] == "unsupported"
    assert result["assessment"]["mic_estimate"]["value"] is None


@pytest.mark.parametrize("change", ["unit", "calibration", "killing", "confirmed_target"])
async def test_units_and_estimate_boundaries_are_enforced(change):
    value = assessment()
    if change == "unit": value["mic_estimate"]["unit"] = "uM"
    if change == "calibration": value["confidence"]["calibrated"] = True
    if change == "killing": value["killing_effect"] = "90%"
    if change == "confirmed_target": value["targets"][0]["status"] = "confirmed"
    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(value)]))
    assert result["status"] == "unsupported"
    assert result["evidence_validation"]["issues"] == ["invalid_assessment_schema"]


async def test_omics_must_actually_be_queried():
    result = await analyze_candidate("CCO", client=Client([final_response(assessment(None))]))
    assert result["status"] == "unsupported"
    assert "no_gene_observations_loaded" in result["evidence_validation"]["issues"]


async def test_missing_expression_is_not_imputed(monkeypatch):
    unknown = deepcopy(GENE)
    unknown["expression_value"] = None
    monkeypatch.setattr(Profile, "query_genes", lambda self, gene_ids, limit=30: {
        "profile_id": "AB5075-AZI000", "genes": [unknown], "missing_gene_ids": [], "truncated": False})
    value = assessment(None)
    value["mic_estimate"]["evidence_refs"] = [ref(value=None)]
    value["supporting_evidence"][0]["observations"][0].update(value=None, evidence_ref=ref(value=None))
    value["supporting_evidence"][0]["evidence_refs"] = [ref(value=None)]
    value["mechanism_hypotheses"] = []
    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(value)]))
    assert result["status"] == "completed"
    assert result["assessment"]["supporting_evidence"][0]["observations"][0]["value"] is None


async def test_search_annotations_uses_the_same_verifiable_rows():
    result = await analyze_candidate("CCO", client=Client([
        tool_response("search_annotations", {"query": "membrane", "limit": 5}), final_response(assessment(None))]))
    assert result["status"] == "completed"
    assert result["execution_trace"]["tool_calls"][-1]["name"] == "search_annotations"


async def test_normalizer_cannot_substitute_a_different_candidate():
    result = await analyze_candidate("CCO", client=Client([
        tool_response("normalize_molecule", {"smiles": "CCC"})]), max_turns=1)
    assert result["execution_trace"]["tool_calls"][-1]["error"] == "molecule_does_not_match_candidate"


async def test_truncated_model_output_is_not_a_completed_estimate():
    response = final_response(assessment(None))
    response["choices"][0]["finish_reason"] = "length"
    result = await analyze_candidate("CCO", client=Client([response]))
    assert result["status"] == "incomplete"
    assert result["assessment"]["mic_estimate"]["value"] is None


async def test_only_allowed_tools_can_execute_and_loop_is_bounded():
    response = tool_response("predict_mic", {"smiles": "CCO"})
    result = await analyze_candidate("CCO", client=Client([response]), max_turns=1)
    assert result["status"] == "incomplete"
    assert result["execution_trace"]["tool_calls"][-1]["error"] == "tool_not_allowed"
    assert result["assessment"]["mic_estimate"]["value"] is None


async def test_batch_order_and_error_are_preserved():
    client = Client([tool_response(), final_response(assessment(None))])
    result = await analyze_candidates([{"id": "bad", "smiles": "bad molecule"}, {"id": "ok", "smiles": "CCO"}], client=client)
    assert [r["candidate"]["id"] for r in result["results"]] == ["bad", "ok"]
    assert result["counts"]["error"] == result["counts"]["completed"] == 1


def test_forbidden_predictor_imports_are_absent():
    package = Path(workflow.__file__).parent
    imports = []
    for file in package.glob("*.py"):
        if file.name.startswith("._"):
            continue
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    forbidden = ("praxis_virtualcell.mdr_gnb", "abwm", "sklearn", "torch", "joblib")
    assert not [name for name in imports if name.startswith(forbidden)]
    assert {tool["function"]["name"] for tool in workflow.TOOLS} == {
        "overview", "query_genes", "search_annotations", "normalize_molecule"}


async def test_one_final_repair_preserves_public_draft_and_checks_again():
    invalid = assessment()
    invalid["supporting_evidence"][0]["observations"][0]["field"] = "basal_expression"
    client = Client([tool_response(), final_response(invalid), final_response(assessment())])
    result = await analyze_candidate("CCO", client=client, max_turns=3)
    assert result["status"] == "completed"
    assert result["assessment"]["mic_estimate"]["value"] == 8
    rejected = result["rejected_output"]
    assert rejected["is_prediction"] is False
    assert rejected["parsed_draft"]["mic_estimate"]["value"] == 8
    assert rejected["evidence_errors"][0]["location"] == ["supporting_evidence", 0, "observations", 0, "field"]
    assert rejected["evidence_errors"][0]["code"] == "observation_field_does_not_match_pointer"
    feedback = json.loads(client.requests[2]["messages"][-1]["content"])
    assert feedback["task"] == "correct_rejected_assessment"
    assert "/condition/medium -> medium" in feedback["instruction"]
    assert client.requests[2]["messages"][-2]["reasoning_content"] == "PRIVATE_FINAL_REASONING"
    assert "PRIVATE" not in json.dumps(result)
    assert result["evidence_validation"]["status"] == "passed"


async def test_second_invalid_final_is_rejected_without_third_repair():
    invalid = assessment()
    invalid["mic_estimate"]["evidence_refs"][0]["value"] = 999
    client = Client([tool_response(), final_response(invalid), final_response(invalid), final_response(assessment())])
    result = await analyze_candidate("CCO", client=client, max_turns=8)
    assert result["status"] == "unsupported"
    assert result["assessment"]["mic_estimate"]["value"] is None
    assert len(client.requests) == 3
    assert len(result["rejected_output"]["previous_drafts"]) == 1
    assert result["rejected_output"]["evidence_errors"]


async def test_repair_does_not_extend_original_turn_budget():
    invalid = assessment()
    invalid["mic_estimate"]["unit"] = "uM"
    client = Client([tool_response(), final_response(invalid), final_response(assessment())])
    result = await analyze_candidate("CCO", client=client, max_turns=2)
    assert result["status"] == "unsupported"
    assert len(client.requests) == 2
    assert result["rejected_output"]["schema_errors"][0]["location"] == ["mic_estimate", "unit"]
    assert set(result["rejected_output"]["schema_errors"][0]) == {"location", "code", "message"}
    assert "input" not in result["rejected_output"]["schema_errors"][0]


async def test_invalid_json_public_answer_is_retained_without_thoughts():
    response = final_response(assessment())
    response["choices"][0]["message"]["content"] = '<think>PRIVATE_EMBEDDED_THOUGHT</think>{"activity":"uncertain",'
    result = await analyze_candidate("CCO", client=Client([response]), max_turns=1)
    assert result["status"] == "unsupported"
    assert result["rejected_output"]["public_answer"] == '{"activity":"uncertain",'
    assert result["rejected_output"]["schema_errors"][0]["code"] == "invalid_json"
    assert "PRIVATE" not in json.dumps(result)


async def test_private_extra_fields_do_not_survive_rejection_diagnostics():
    invalid = assessment()
    invalid["reasoning_content"] = "PRIVATE_EMBEDDED_REASONING"
    invalid["api_key"] = "PRIVATE_EMBEDDED_KEY"
    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(invalid)]), max_turns=2)
    assert result["status"] == "unsupported"
    assert "PRIVATE" not in json.dumps(result)
    assert "api_key" not in result["rejected_output"]["parsed_draft"]
    assert "reasoning_content" not in result["rejected_output"]["parsed_draft"]


async def test_safe_sync_and_async_progress_are_optional():
    events = []
    client = Client([tool_response(), final_response(assessment(None))])
    result = await analyze_candidate("CCO", client=client, on_progress=events.append)
    assert result["status"] == "completed"
    assert {event["stage"] for event in events} >= {"profile_loaded", "turn_started", "tool_started", "tool_completed", "assessment_completed"}
    assert all(set(event) <= {"stage", "candidate_id", "profile_id", "turn", "tool_name", "status"} for event in events)
    assert "PRIVATE" not in json.dumps(events)

    async def callback(event):
        events.append(event)

    result = await analyze_candidate("CCO", client=Client([tool_response(), final_response(assessment(None))]), on_progress=callback)
    assert result["status"] == "completed"


async def test_error_bodies_and_callback_errors_are_not_persisted():
    class FailingClient:
        async def messages(self, **kwargs):
            raise RuntimeError("PRIVATE_API_BODY")

    def callback(event):
        raise RuntimeError("PRIVATE_CALLBACK_BODY")

    result = await analyze_candidate("CCO", client=FailingClient(), on_progress=callback)
    assert result["status"] == "error"
    assert "PRIVATE" not in json.dumps(result)
