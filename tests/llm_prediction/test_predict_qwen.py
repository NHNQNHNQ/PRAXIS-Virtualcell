import json
import asyncio
from types import SimpleNamespace

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


async def test_without_omics_keeps_profile_but_never_reads_omics_or_claims_platform_eligibility(monkeypatch):
    from praxis_virtualcell.cell_structure import cell_structure_overview
    from praxis_virtualcell.llm_prediction.workflow import CELL_STRUCTURE_TOOLS

    monkeypatch.setattr(predict_qwen, "_load_organism", lambda *_: Profile(["genome"]))
    record = public_record()
    record["messages"] = record["messages"][:2]
    request = json.loads(record["messages"][1]["content"])
    request["available_modalities"] = []
    record["messages"][1]["content"] = json.dumps(request)
    data = cell_structure_overview(Profile(["genome"]).overview())
    source = data["structures"][0]
    record["tools"] += CELL_STRUCTURE_TOOLS
    record["messages"].extend([
        {"role": "assistant", "content": "", "tool_calls": [{"id": "read-structure", "type": "function",
            "function": {"name": "cell_structure_overview", "arguments": {}}}]},
        {"role": "tool", "tool_call_id": "read-structure", "content": json.dumps({
            "tool_call_id": "read-structure", "name": "cell_structure_overview", "ok": True, "data": data})}])
    value = empty_assessment("No omics evidence was requested.")
    value["structure_analysis"] = {"compartment_hypotheses": [{
        "structure_id": source["structure_id"], "compartment": source["compartment"],
        "evidence_scope": source["evidence_scope"], "evidence_type": source["evidence_type"],
        "hypothesis": "This source is a species prior; transport remains unknown.", "evidence_refs": [{
            "tool_call_id": "read-structure", "pointer": "/structures/0/compartment",
            "source_id": source["source_id"], "value": source["compartment"]}]}], "limitations": data["gaps"]}
    client = Client([response(value)])
    result = await predict_qwen.predict_record(record, client, model="qwen", data_root="unused")
    assert result["status"] == "completed" and result["platform_eligible"] is False
    assert result["evidence_validation"]["status"] == "not_applicable_omics_withheld"
    assert result["evidence_validation"]["issues"] == ["no_gene_observations_loaded"]
    assert result["evidence_validation"]["selected_modalities"] == []
    assert {tool["function"]["name"] for tool in client.requests[0]["tools"]} == {
        "cell_structure_overview", "query_cell_structure"}
    numeric = json.loads(json.dumps(value))
    numeric["mic_estimate"]["value"] = 8
    numeric["mic_observations"] = [{"relation": "=", "value": 8, "lower": 8, "upper": 8}]
    client = Client([response(numeric)])
    result = await predict_qwen.predict_record(record, client, model="qwen", data_root="unused")
    assert result["status"] == "completed" and result["assessment"]["mic_estimate"]["value"] == 8
    assert result["platform_eligible"] is False
    assert result["evidence_validation"] == {"status": "not_applicable_omics_withheld", "selected_modalities": [],
        "issues": ["mic_observations_require_verified_gene_evidence", "no_gene_observations_loaded",
                   "numeric_mic_requires_verified_gene_evidence"]}
    ordinary = json.loads(json.dumps(record))
    ordinary_request = json.loads(ordinary["messages"][1]["content"])
    ordinary_request.pop("available_modalities")
    ordinary["messages"][1]["content"] = json.dumps(ordinary_request)
    result = await predict_qwen.predict_record(ordinary, Client([response(numeric)]), model="qwen", data_root="unused")
    assert result["status"] == "unsupported" and result["evidence_validation"]["status"] == "failed"
    forged = json.loads(json.dumps(numeric))
    forged["structure_analysis"]["compartment_hypotheses"][0]["evidence_refs"][0]["source_id"] = "invented"
    result = await predict_qwen.predict_record(record, Client([response(forged)]), model="qwen", data_root="unused")
    assert result["status"] == "unsupported" and result["evidence_validation"]["status"] == "failed"
    assert "source_id_does_not_match_tool" in result["evidence_validation"]["issues"]
    forged = json.loads(json.dumps(numeric))
    forged["mic_estimate"]["evidence_refs"] = [{"tool_call_id": "invented", "pointer": "/features/0/presence",
                                               "source_id": "invented", "value": True}]
    result = await predict_qwen.predict_record(record, Client([response(forged)]), model="qwen", data_root="unused")
    assert result["status"] == "unsupported" and result["evidence_validation"]["status"] == "failed"
    assert "unknown_or_failed_tool_call" in result["evidence_validation"]["issues"]
    client = Client([tool_response(["genome"])])
    result = await predict_qwen.predict_record(record, client, model="qwen", data_root="unused")
    assert result["reason"] == "unapproved_or_duplicate_tool_call"


@pytest.mark.parametrize("content", ['{"broken":', '{"activity":"not-a-valid-activity"}'])
async def test_invalid_final_json_or_schema_preserves_raw_response(content):
    client = Client([{"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}])
    result = await predict_qwen.predict_record(public_record(None), client, model="qwen", data_root="unused")
    assert result["status"] == "error" and result["reason"] == "invalid_final_assessment"
    assert result["raw_response"] == content


async def test_length_failure_records_actual_reduced_budget_and_partial_text():
    budget = {"requested_max_tokens": 12288, "max_new_tokens": 12, "reduced": True, "input_truncated": False}
    client = Client([{"choices": [{"message": {"content": '{"partial":'}, "finish_reason": "length"}],
                      "generation_budget": budget}])
    result = await predict_qwen.predict_record(public_record(None), client, model="qwen", data_root="unused")
    assert result["status"] == "incomplete" and result["reason"] == "output_truncated"
    assert result["generation_steps"][0]["generation_budget"] == budget
    assert result["raw_response"] == '{"partial":'


def run_fixture(tmp_path):
    rows = [public_record(None), public_record(None)]
    rows[0]["record_id"], rows[1]["record_id"] = "validation:first", "validation:second"
    inputs = tmp_path / "pilot.inputs.jsonl"
    inputs.write_text("".join(json.dumps(row) + "\n" for row in rows))
    args = SimpleNamespace(inputs=str(inputs), output=str(tmp_path / "predictions.jsonl"), base_url="http://local",
        model="qwen", data_root="unused", limit=0, max_turns=4, max_tokens=12288, resume=False,
        run_id="baseline-pilot", record_timeout_seconds=900, max_seconds=0)
    health = {"status": "ok", "model": "qwen", "enable_thinking": False, "model_identity": "base-sha",
              "adapter_loaded": False, "max_context": 32768, "generation": "greedy_remaining_context.v1"}
    return args, rows, health


class RunClient(Client):
    def __init__(self, responses, health, *, clock=None, before_reply=None):
        super().__init__(responses)
        self.health, self.clock, self.before_reply = health, clock, before_reply
        self.closed = False
        async def get(_path, **_kwargs):
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: self.health.copy())
        self._http = SimpleNamespace(get=get)
    async def messages(self, **kwargs):
        if self.before_reply:
            self.before_reply()
        if self.clock:
            self.clock.now += 1
        return await super().messages(**kwargs)
    async def aclose(self):
        self.closed = True


async def test_segment_resume_keeps_error_coverage_skips_attempted_ids_and_allows_new_soft_limit(tmp_path, monkeypatch):
    args, rows, health = run_fixture(tmp_path)
    clock = SimpleNamespace(now=0)
    monkeypatch.setattr(predict_qwen.time, "monotonic", lambda: clock.now)
    first = RunClient([{"choices": [{"message": {"content": "not JSON"}, "finish_reason": "stop"}]}],
                      health, clock=clock)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: first)
    args.max_seconds = .5
    await predict_qwen.run(args)
    output = tmp_path / "predictions.jsonl"
    manifest_path = tmp_path / "predictions.jsonl.run.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["coverage"] == {"processed": 1, "expected": 2}
    assert manifest["segments"][0]["status"] == "soft_limit_reached"
    assert manifest["processed_record_ids"] == [rows[0]["record_id"]] and manifest["completed_record_ids"] == []
    assert json.loads(output.read_text())["raw_response"] == "not JSON"
    second = RunClient([response(empty_assessment("No omics."))], health, clock=clock)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: second)
    args.resume, args.max_seconds = True, 0
    await predict_qwen.run(args)
    results = [json.loads(line) for line in output.read_text().splitlines()]
    assert [row["record_id"] for row in results] == [row["record_id"] for row in rows]
    assert [row["status"] for row in results] == ["error", "completed"]
    manifest = json.loads(manifest_path.read_text())
    assert manifest["coverage"] == {"processed": 2, "expected": 2}
    assert manifest["status_counts"] == {"error": 1, "completed": 1}
    assert len(second.requests) == 1 and first.closed and second.closed
    untouched = output.read_bytes()
    third = RunClient([], health)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: third)
    await predict_qwen.run(args)
    assert not third.requests and output.read_bytes() == untouched


@pytest.mark.parametrize("changed", ["max_tokens", "max_turns", "record_timeout_seconds", "run_id", "input", "service"])
async def test_resume_refuses_changed_input_model_asset_or_generation_settings(tmp_path, monkeypatch, changed):
    args, rows, health = run_fixture(tmp_path)
    client = RunClient([response(empty_assessment("No omics.")) for _ in rows], health)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    await predict_qwen.run(args)
    original = (tmp_path / "predictions.jsonl").read_bytes()
    args.resume = True
    if changed == "input":
        path = tmp_path / "pilot.inputs.jsonl"
        path.write_text(path.read_text() + "\n")
    elif changed == "service":
        health.update(model_identity="different-adapter-sha", adapter_loaded=True)
    elif changed == "run_id":
        args.run_id = "another-experiment"
    else:
        setattr(args, changed, getattr(args, changed) + 1)
    client = RunClient([], health)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    with pytest.raises(ValueError, match="resume_identity_mismatch"):
        await predict_qwen.run(args)
    assert not client.requests and (tmp_path / "predictions.jsonl").read_bytes() == original
    assert client.closed


async def test_record_timeout_is_written_as_failure_and_never_retried_on_resume(tmp_path, monkeypatch):
    args, rows, health = run_fixture(tmp_path)
    args.limit, args.record_timeout_seconds = 1, .01
    client = RunClient([], health)
    async def hanging(**_kwargs):
        await asyncio.sleep(1)
    client.messages = hanging
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    await predict_qwen.run(args)
    result = json.loads((tmp_path / "predictions.jsonl").read_text())
    assert result["status"] == "error" and result["reason"] == "record_timeout"
    manifest = json.loads((tmp_path / "predictions.jsonl.run.json").read_text())
    assert manifest["coverage"] == {"processed": 1, "expected": 1}
    args.resume = True
    client = RunClient([], health)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    await predict_qwen.run(args)
    assert not client.requests


async def test_prediction_preserves_service_cuda_oom_signal_for_pipeline_stop(tmp_path, monkeypatch):
    args, rows, health = run_fixture(tmp_path)
    args.limit = 1
    client = RunClient([], health)
    async def failed(**_kwargs):
        error = RuntimeError("HTTP 500")
        error.response = SimpleNamespace(json=lambda: {"error": "cuda_out_of_memory",
                                                       "exception_type": "OutOfMemoryError"})
        raise error
    client.messages = failed
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    await predict_qwen.run(args)
    result = json.loads((tmp_path / "predictions.jsonl").read_text())
    assert result["status"] == "error" and result["service_error"]["error"] == "cuda_out_of_memory"


async def test_each_prediction_is_flushed_before_next_generation(tmp_path, monkeypatch):
    args, rows, health = run_fixture(tmp_path)
    checks = []
    def inspect_previous():
        if checks:
            previous = [json.loads(line) for line in (tmp_path / "predictions.jsonl").read_text().splitlines()]
            assert len(previous) == 1 and previous[0]["record_id"] == rows[0]["record_id"]
        checks.append(True)
    client = RunClient([response(empty_assessment("No omics.")) for _ in rows], health, before_reply=inspect_previous)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    await predict_qwen.run(args)
    assert len(checks) == 2


@pytest.mark.parametrize("corruption", ["different_run", "duplicate", "partial_line"])
async def test_resume_refuses_mixed_duplicate_or_partial_output_instead_of_hiding_it(tmp_path, monkeypatch, corruption):
    args, rows, health = run_fixture(tmp_path)
    client = RunClient([response(empty_assessment("No omics.")) for _ in rows], health)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    await predict_qwen.run(args)
    path = tmp_path / "predictions.jsonl"
    content = path.read_text()
    if corruption == "different_run":
        first, second = map(json.loads, content.splitlines())
        first["run_identity"] = "another-run"
        content = json.dumps(first) + "\n" + json.dumps(second) + "\n"
    elif corruption == "duplicate":
        content += content.splitlines()[0] + "\n"
    else:
        content = content.rstrip("\n")
    path.write_text(content)
    client = RunClient([], health)
    monkeypatch.setattr(predict_qwen, "QwenAnalysisClient", lambda *a, **k: client)
    args.resume = True
    with pytest.raises(ValueError):
        await predict_qwen.run(args)
    assert not client.requests and path.read_text() == content
