"""Trajectory review queues, tool history integrity and out-of-band labels."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from praxis_virtualcell.llm_prediction.trajectories import (
    export_trajectories,
    write_trajectories_jsonl,
)


def assessment(mic=None):
    return {
        "activity": "uncertain",
        "mic_estimate": {"value": mic, "unit": "ug/mL", "basis": "llm_estimate",
                         "reason": "Insufficient activity evidence.", "evidence_refs": []},
        "confidence": {"level": "low", "calibrated": False}, "killing_effect": "unknown",
        "targets": [], "mechanism_hypotheses": [], "supporting_evidence": [],
        "counterevidence": [], "gaps": ["No paired drug response."],
        "rationale_summary": "A model hypothesis requiring independent evaluation.",
    }


def run():
    call = {"tool_call_id": "gene-1", "name": "query_genes", "arguments": {"gene_ids": ["ABUW_0001"]},
            "ok": True, "data": {"genes": [{"gene_id": "ABUW_0001", "expression_value": 3.5,
                                            "source_id": "omics:sample:gene:ABUW_0001"}]}}
    tools = [{"type": "function", "function": {"name": "query_genes", "parameters": {
        "type": "object", "properties": {"gene_ids": {"type": "array"}}, "required": ["gene_ids"]}}}]
    analysis = {
        "stage": "analysis", "status": "completed", "tools": tools,
        "messages": [
            {"role": "system", "content": "Use only the available observations."},
            {"role": "user", "content": '{"candidate":"CCO","profile_id":"sample"}'},
            {"role": "assistant", "content": None, "reasoning_content": "PRIVATE_THOUGHTS",
             "tool_calls": [{"id": "gene-1", "type": "function", "function": {
                 "name": "query_genes", "arguments": '{"gene_ids":["ABUW_0001"]}'}}]},
            {"role": "tool", "tool_call_id": "gene-1", "content": json.dumps(call)},
            {"role": "assistant", "content": json.dumps(assessment()),
             "reasoning_content": "PRIVATE_FINAL_THOUGHTS"},
        ],
    }
    return {"schema_version": "llm-antibacterial-v1", "status": "completed",
            "candidate": {"id": "C1"}, "profile": {"profile_id": "sample"},
            "assessment": assessment(), "evidence_validation": {"status": "passed"},
            "execution_trace": {"model": "test-model", "tool_calls": [call]},
            "agent_trace": {"schema_version": "praxis.agent-trace.v1", "stages": [analysis]}}


def approval(**overrides):
    return {"approved": True, "curator": "expert-1", "label_source_ids": ["curation:review-1"], **overrides}


def test_default_export_is_reviewable_evidence_workflow_never_gold():
    source = run()
    original = deepcopy(source)
    exported = export_trajectories(source)
    assert source == original
    assert exported["skipped"] == []
    record = exported["records"][0]
    assert record["task"] == {"type": "analyze_candidate", "candidate_id": "C1", "profile_id": "sample"}
    assert record["stage"] == "analysis"
    assert record["provenance"]["origin"] == "model_generated"
    assert record["provenance"]["model"] == "test-model"
    assert record["supervision"]["review_status"] == "needs_review"
    assert record["supervision"]["prediction_is_gold"] is False
    assert "PRIVATE" not in json.dumps(exported)
    assert record["messages"][2]["tool_calls"][0]["id"] == "gene-1"
    assert record["messages"][3]["tool_call_id"] == "gene-1"


def test_export_strips_credentials_nested_json_thinking_and_raw_api_fields():
    source = run()
    stage = source["agent_trace"]["stages"][0]
    stage["messages"][0].update(api_key="SENSITIVE_KEY_123", raw_api_response={"secret": "RAW_SECRET"})
    stage["messages"][0]["content"] += " DEEPSEEK_API_KEY=SENSITIVE_KEY_123 Bearer HEADER_TOKEN"
    reply = json.loads(stage["messages"][3]["content"])
    reply["data"]["api_key"] = "NESTED_KEY_456"
    reply["data"]["reasoning_content"] = "NESTED_THOUGHTS"
    stage["messages"][3]["content"] = json.dumps(reply)
    stage["messages"][-1]["content"] = "<think>INLINE_PRIVATE</think>" + stage["messages"][-1]["content"]
    exported = export_trajectories(source)
    text = json.dumps(exported)
    for private in ("SENSITIVE_KEY_123", "RAW_SECRET", "HEADER_TOKEN", "NESTED_KEY_456", "NESTED_THOUGHTS", "INLINE_PRIVATE"):
        assert private not in text
    assert exported["records"]
    assert "api_key" not in exported["records"][0]["messages"][0]
    assert json.loads(exported["records"][0]["messages"][-1]["content"]) == assessment()


@pytest.mark.parametrize("status", ["error", "unsupported", "incomplete"])
def test_unaccepted_runs_are_not_supervised_even_with_curator_approval(status):
    source = run()
    source["status"] = status
    exported = export_trajectories(source, approval())
    assert exported == {"records": [], "skipped": [{"stage": "run", "reason": "run_not_accepted"}]}


def test_failed_evidence_missing_trace_and_failed_stage_are_audited():
    source = run()
    source["evidence_validation"]["status"] = "failed"
    assert not export_trajectories(source)["records"]
    source = run()
    del source["agent_trace"]
    assert export_trajectories(source)["skipped"][0]["reason"] == "missing_agent_trace"
    source = run()
    source["agent_trace"]["stages"][0]["status"] = "failed"
    assert export_trajectories(source)["skipped"][0]["reason"] == "stage_not_completed"


def test_rejected_stage_requires_explicit_stage_curation():
    source = run()
    source["agent_trace"]["stages"][0]["rejected"] = True
    for supervision in (None, approval()):
        exported = export_trajectories(source, supervision)
        assert not exported["records"]
        assert exported["skipped"][0]["reason"] == "rejected_stage_not_curated"
    record = export_trajectories(source, approval(curated_stage_indices=[0]))["records"][0]
    assert record["supervision"]["kind"] == "workflow_supervision"
    assert record["supervision"]["prediction_is_gold"] is False
    assert record["supervision"]["rejected_output_curated"] is True


@pytest.mark.parametrize("change,reason", [
    ("unknown_reply", "unmatched_or_duplicate_tool_result"),
    ("duplicate_reply", "unmatched_or_duplicate_tool_result"),
    ("missing_reply", "tool_results_out_of_order"),
    ("duplicate_call", "duplicate_or_missing_tool_call_id"),
    ("bad_arguments", "invalid_tool_arguments"),
    ("unknown_tool", "tool_not_in_schema"),
    ("wrong_name", "tool_result_name_mismatch"),
    ("no_final", "missing_final_assistant_output"),
])
def test_tool_protocol_failures_skip_stage(change, reason):
    source = run()
    messages = source["agent_trace"]["stages"][0]["messages"]
    call = messages[2]["tool_calls"][0]
    if change == "unknown_reply":
        messages[3]["tool_call_id"] = "not-called"
    elif change == "duplicate_reply":
        messages.insert(4, deepcopy(messages[3]))
    elif change == "missing_reply":
        del messages[3]
    elif change == "duplicate_call":
        messages[2]["tool_calls"].append(deepcopy(call))
    elif change == "bad_arguments":
        call["function"]["arguments"] = "[]"
    elif change == "unknown_tool":
        call["function"]["name"] = "predict_mic"
    elif change == "wrong_name":
        messages[3]["name"] = "another_tool"
    elif change == "no_final":
        messages.pop()
    exported = export_trajectories(source)
    assert not exported["records"]
    assert exported["skipped"][0]["reason"] == reason


@pytest.mark.parametrize("supervision", [
    {}, {"approved": False}, {"approved": 1},
    approval(curator=" "), approval(curator=None),
    approval(label_source_ids=[]), approval(label_source_ids=[""]),
    approval(label_source_ids="curation:x"), approval(curated_stage_indices=[True]),
    approval(gold_assessment={"activity": "certain"}),
])
def test_supervision_requires_explicit_approval_curator_sources_and_contract(supervision):
    with pytest.raises(ValueError):
        export_trajectories(run(), supervision)


def test_workflow_approval_without_gold_never_creates_numeric_label():
    source = run()
    source["assessment"]["mic_estimate"]["value"] = 8.0
    source["agent_trace"]["stages"][0]["messages"][-1]["content"] = json.dumps(source["assessment"])
    record = export_trajectories(source, approval())["records"][0]
    assert record["supervision"]["kind"] == "workflow_supervision"
    assert record["supervision"]["prediction_is_gold"] is False
    assert json.loads(record["messages"][-1]["content"])["mic_estimate"]["value"] == 8


def test_gold_target_is_separate_from_model_visible_inputs_and_original_run():
    source = run()
    original = deepcopy(source)
    gold = assessment(16.0)
    gold["mic_estimate"]["evidence_refs"] = [{
        "tool_call_id": "gene-1", "pointer": "/genes/0/expression_value",
        "source_id": "omics:sample:gene:ABUW_0001", "value": 3.5,
    }]
    record = export_trajectories(source, approval(gold_assessment=gold))["records"][0]
    assert source == original
    assert json.loads(record["messages"][-1]["content"])["mic_estimate"]["value"] == 16
    assert record["messages"][:-1] == export_trajectories(source)["records"][0]["messages"][:-1]
    assert "expert-1" not in json.dumps(record["messages"])
    assert "curation:review-1" not in json.dumps(record["messages"])
    assert record["supervision"]["prediction_is_gold"] is True
    assert record["supervision"]["target_origin"] == "curator_supplied"
    assert record["provenance"]["origin"] == "model_generated"


def test_invalid_gold_citations_do_not_become_targets():
    gold = assessment(16.0)
    gold["mic_estimate"]["evidence_refs"] = [{
        "tool_call_id": "gene-1", "pointer": "/genes/0/expression_value",
        "source_id": "omics:sample:gene:ABUW_0001", "value": 99.0,
    }]
    with pytest.raises(ValueError, match="invalid_gold_assessment_evidence"):
        export_trajectories(run(), approval(gold_assessment=gold))
    with pytest.raises(ValueError, match="invalid_gold_assessment_evidence"):
        export_trajectories(run(), approval(gold_assessment=assessment(16.0)))


def test_gold_preserves_selected_modality_coverage_even_when_mic_is_unknown():
    source = run()
    source["profile"]["selected_modalities"] = ["transcriptome", "proteome"]
    transcriptome = source["execution_trace"]["tool_calls"][0]
    transcriptome["data"]["modality"] = "transcriptome"
    protein = {"tool_call_id": "protein-1", "name": "query_features", "ok": True,
               "data": {"modality": "proteome", "features": [{
                   "modality": "proteome", "feature_id": "protein-1", "protein_id": "P1",
                   "abundance_value": 7.5, "source_id": "omics:sample:protein:P1",
               }]}}
    source["execution_trace"]["tool_calls"].append(protein)
    gold = assessment()
    gold["supporting_evidence"] = [{"claim": "RNA observation.", "observations": [{
        "gene_id": "ABUW_0001", "field": "expression_value", "value": 3.5,
        "evidence_ref": {"tool_call_id": "gene-1", "pointer": "/genes/0/expression_value",
                         "source_id": "omics:sample:gene:ABUW_0001", "value": 3.5},
    }]}]
    accepted = deepcopy(gold)
    accepted["supporting_evidence"][0]["observations"].append({
        "gene_id": None, "field": "abundance_value", "value": 7.5,
        "evidence_ref": {"tool_call_id": "protein-1", "pointer": "/features/0/abundance_value",
                         "source_id": "omics:sample:protein:P1", "value": 7.5},
    })
    source["assessment"] = accepted
    stage = source["agent_trace"]["stages"][0]
    stage["tools"].append({"type": "function", "function": {"name": "query_features", "parameters": {}}})
    stage["messages"][2]["tool_calls"].append({"id": "protein-1", "type": "function", "function": {
        "name": "query_features", "arguments": '{"modality":"proteome","feature_ids":["protein-1"]}',
    }})
    stage["messages"][3]["content"] = json.dumps(transcriptome)
    stage["messages"].insert(4, {"role": "tool", "tool_call_id": "protein-1", "content": json.dumps(protein)})
    stage["messages"][-1]["content"] = json.dumps(accepted)
    with pytest.raises(ValueError, match="invalid_gold_assessment_evidence"):
        export_trajectories(source, approval(gold_assessment=gold))
    exported = export_trajectories(source, approval(gold_assessment=accepted))
    assert exported["records"][0]["supervision"]["prediction_is_gold"] is True


def test_only_final_accepted_analysis_or_revision_receives_gold():
    source = run()
    analysis = source["agent_trace"]["stages"][0]
    review = {"stage": "review", "status": "completed", "messages": [
        {"role": "user", "content": "Review the candidate assessment."},
        {"role": "assistant", "content": '{"decision":"accept"}'},
    ]}
    revision = deepcopy(analysis)
    revision["stage"] = "revision"
    source["agent_trace"]["stages"] = [analysis, review, revision]
    gold = assessment()
    gold["rationale_summary"] = "Curator revised this target."
    records = export_trajectories(source, approval(gold_assessment=gold))["records"]
    assert [record["supervision"]["prediction_is_gold"] for record in records] == [False, False, True]
    source["agent_trace"]["stages"] = [review]
    with pytest.raises(ValueError, match="gold_requires_final_accepted_assessment_message"):
        export_trajectories(source, approval(gold_assessment=gold))


def test_display_annotations_do_not_prevent_accepted_target_matching():
    source = run()
    source["assessment"]["targets"] = [{"name": "unknown", "target_id": None,
                                        "hypothesis": "Unverified.", "status": "hypothesis",
                                        "evidence_refs": [], "counterevidence_refs": []}]
    source["agent_trace"]["stages"][0]["messages"][-1]["content"] = json.dumps(source["assessment"])
    source["assessment"]["targets"][0].update(causality_verified=False, identity_observed=False)
    exported = export_trajectories(source, approval(gold_assessment=assessment()))
    assert exported["records"][0]["supervision"]["prediction_is_gold"] is True


def test_jsonl_writer_preserves_records_without_skip_entries(tmp_path):
    exported = export_trajectories(run())
    exported["skipped"].append({"stage": "review", "reason": "stage_not_completed"})
    path = tmp_path / "exports" / "trajectories.jsonl"
    assert write_trajectories_jsonl(path, exported) == 1
    assert [json.loads(line) for line in path.read_text().splitlines()] == exported["records"]
    assert write_trajectories_jsonl(path, {"records": [], "skipped": []}) == 0
    assert path.read_text() == ""
