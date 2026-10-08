import json

import pytest

from praxis_virtualcell.llm_prediction.schemas import MICConditions, empty_assessment
from praxis_virtualcell.llm_prediction.workflow import MULTIOMICS_TOOLS
from scripts.finetuning import predict_qwen
from tests.llm_prediction.test_orchestrator import Client, Profile, assessment, response, tool_response


def public_record(profile_id="test-strain"):
    tools = [tool for tool in MULTIOMICS_TOOLS if tool["function"]["name"] in {
        "overview", "query_features", "search_features"}]
    messages = [{"role": "system", "content": "Use actual observed omics; return Assessment JSON."},
                {"role": "user", "content": json.dumps({"candidate": {"smiles": "CCO"}, "profile_id": profile_id,
                                                         "conditions": MICConditions().model_dump()})}]
    if profile_id:
        messages.extend([
            {"role": "assistant", "content": "", "tool_calls": [{"id": "initial-overview", "type": "function",
                "function": {"name": "overview", "arguments": {}}}]},
            {"role": "tool", "tool_call_id": "initial-overview", "content": json.dumps({
                "tool_call_id": "initial-overview", "name": "overview", "arguments": {}, "ok": True,
                "data": Profile(["genome"]).overview()})},
        ])
    return {"record_id": "validation:fixture", "messages": messages, "tools": tools if profile_id else []}


async def test_generator_executes_real_profile_tool_and_cleans_paths_before_next_request(monkeypatch):
    read = []
    class SourceProfile(Profile):
        def query_features(self, modality, feature_ids, limit=30):
            read.append((modality, feature_ids))
            data = super().query_features(modality, feature_ids, limit)
            data["features"][0]["source_locator"]["path"] = "/home/private/observed_genome.tsv"
            return data
    monkeypatch.setattr(predict_qwen, "_load_organism", lambda *_: SourceProfile(["genome"]))
    client = Client([tool_response(["genome"]), response(assessment(["genome"]))])
    result = await predict_qwen.predict_record(public_record(), client, model="qwen", data_root="unused", max_turns=2)
    assert read == [("genome", ["gene-1"])]
    assert result["status"] == "completed" and result["evidence_validation"]["status"] == "passed"
    path = result["tool_calls"][0]["data"]["features"][0]["source_locator"]["path"]
    assert path.startswith("asset:")
    assert "/home/private/observed_genome.tsv" not in json.dumps(client.requests)


async def test_generator_does_not_release_forged_omics_observation(monkeypatch):
    monkeypatch.setattr(predict_qwen, "_load_organism", lambda *_: Profile(["genome"]))
    value = assessment(["genome"])
    value["supporting_evidence"][0]["observations"][0]["value"] = False
    client = Client([tool_response(["genome"]), response(value)])
    result = await predict_qwen.predict_record(public_record(), client, model="qwen", data_root="unused", max_turns=2)
    assert result["status"] == "unsupported"
    assert result["evidence_validation"]["status"] == "failed"


async def test_generator_rejects_a_real_tool_reply_for_the_wrong_profile(monkeypatch):
    class WrongProfile(Profile):
        def query_features(self, modality, feature_ids, limit=30):
            data = super().query_features(modality, feature_ids, limit)
            data["profile_id"] = "another-strain"
            return data
    monkeypatch.setattr(predict_qwen, "_load_organism", lambda *_: WrongProfile(["genome"]))
    client = Client([tool_response(["genome"])])
    with pytest.raises(ValueError, match="profile_identity_mismatch"):
        await predict_qwen.predict_record(public_record(), client, model="qwen", data_root="unused", max_turns=2)


@pytest.mark.parametrize("candidate", [{"name": "aspirin"}, {"id": "CHEMBL1"}, {"smiles": "CCO", "name": "aspirin"}])
async def test_generator_rejects_names_and_identifiers_as_public_candidate_inputs(candidate):
    record = public_record(None)
    request = json.loads(record["messages"][1]["content"])
    request["candidate"] = candidate
    record["messages"][1]["content"] = json.dumps(request)
    with pytest.raises(ValueError, match="SMILES_only"):
        await predict_qwen.predict_record(record, Client([]), model="qwen", data_root="unused")


async def test_auxiliary_generation_cannot_claim_platform_evidence_validation(monkeypatch):
    client = Client([response(empty_assessment("No omics profile is available."))])
    result = await predict_qwen.predict_record(public_record(None), client, model="qwen", data_root="unused")
    assert result["status"] == "completed"
    assert result["platform_eligible"] is False
    assert result["evidence_validation"]["status"] == "not_applicable_auxiliary"
