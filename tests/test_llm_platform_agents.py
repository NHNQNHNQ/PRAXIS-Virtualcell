"""Platform wiring, explicit modality choices, and local trajectory export."""
import json

import pytest
from fastapi.testclient import TestClient

from praxis_virtualcell.cli import main
from praxis_virtualcell.llm_prediction.report import render_report


class Profile:
    def __init__(self, available=("genome", "transcriptome", "proteome"), selected=None):
        self.available = list(available)
        self.selected = list(selected) if selected is not None else list(available)

    def select_modalities(self, modalities=None):
        if modalities is None:
            return self
        if not modalities or len(set(modalities)) != len(modalities) or set(modalities) - set(self.available):
            raise ValueError("Unavailable modalities")
        return Profile(self.available, modalities)

    def overview(self):
        return {"profile_id": "test-profile", "species": {"scientific_name": "Test bacterium"},
                "strain": "test-strain", "available_modalities": self.available, "selected_modalities": self.selected}

    def query_genes(self, gene_ids):
        return {"selected_modalities": self.selected, "gene_ids": gene_ids}

    def search_annotations(self, query):
        return {"selected_modalities": self.selected, "query": query}

    def query_features(self, modality, feature_ids):
        return {"modality": modality, "feature_ids": feature_ids, "selected_modalities": self.selected}

    def search_features(self, modality, query):
        return {"modality": modality, "query": query, "selected_modalities": self.selected}


@pytest.fixture
def platform(monkeypatch, tmp_path):
    import praxis_virtualcell.omics as omics
    import praxis_virtualcell.llm_prediction as prediction
    import praxis2.llm.client as llm
    profile = Profile()
    monkeypatch.setattr(omics, "load_profile", lambda profile_id, data_root=None: profile)
    monkeypatch.setattr(omics, "list_profiles", lambda data_root=None: [profile.overview()])
    monkeypatch.setattr(prediction, "render_report", lambda result: "Public agent report")
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def aclose(self):
            pass
    monkeypatch.setattr(llm, "LLMClient", Client)
    env = tmp_path / ".env"
    env.write_text("DEEPSEEK_API_KEY=dummy-local-test-key\n", encoding="utf-8")
    return profile, env


def test_web_default_uses_agents_and_forwards_explicit_combination(platform, monkeypatch, tmp_path):
    from praxis_virtualcell.web.app import create_app
    import praxis_virtualcell.llm_prediction as prediction
    calls = []
    async def agents(smiles, profile_id, **kwargs):
        calls.append(kwargs)
        return {"status": "completed", "agent_review": {"decision": "accept", "summary": "checked"}}
    monkeypatch.setattr(prediction, "analyze_with_agents", agents)
    with TestClient(create_app(env_file=platform[1], report_root=tmp_path / "reports")) as client:
        response = client.post("/api/analyze", json={"smiles": "CCO", "modalities": ["genome", "proteome"]})
        assert response.status_code == 200
        assert calls[0]["modalities"] == ["genome", "proteome"]
        assert response.json()["agent_review"]["summary"] == "checked"
        assert client.get("/api/health").json()["workflow"] == "planning_analysis_review_revision"


def test_web_injected_legacy_analyzer_receives_no_implicit_modalities(platform, tmp_path):
    from praxis_virtualcell.web.app import create_app
    async def legacy(smiles, profile_id, *, client, model, data_root, max_turns, candidate_id,
                     on_progress, max_output_tokens, reasoning_effort):
        return {"status": "completed"}
    with TestClient(create_app(env_file=platform[1], report_root=tmp_path / "reports", analyzer=legacy)) as client:
        assert client.post("/api/analyze", json={"smiles": "CCO"}).status_code == 200


def test_selected_overview_and_native_feature_endpoints(platform):
    from praxis_virtualcell.web.app import create_app
    with TestClient(create_app(env_file=platform[1])) as client:
        view = client.get("/api/profiles/test-profile", params=[("modalities", "genome"), ("modalities", "proteome")])
        assert view.json()["selected_modalities"] == ["genome", "proteome"]
        features = client.post("/api/profiles/test-profile/features", json={"feature_ids": ["protein-7"], "modality": "proteome"})
        assert features.json() == {"modality": "proteome", "feature_ids": ["protein-7"], "selected_modalities": ["proteome"]}
        search = client.get("/api/profiles/test-profile/features", params={"query": "efflux", "modality": "genome"})
        assert search.json()["selected_modalities"] == ["genome"]
        assert client.post("/api/profiles/test-profile/genes", json={"gene_ids": ["g1"], "modality": "transcriptome"}).json()["selected_modalities"] == ["transcriptome"]


def test_web_prefers_loadable_exact_strain_collection_for_omitted_profile(tmp_path, monkeypatch):
    from praxis_virtualcell.web.app import create_app
    from tests.omics.test_strain_reference import REFERENCE_ID, _strain_references
    from praxis_virtualcell.omics import load_profile
    import praxis_virtualcell.llm_prediction as prediction
    import praxis2.llm.client as llm

    root = tmp_path / "profiles"
    root.mkdir()
    _strain_references(root)
    env = tmp_path / ".env"
    env.write_text("DEEPSEEK_API_KEY=dummy-local-test-key\n")
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def aclose(self):
            pass
    monkeypatch.setattr(llm, "LLMClient", Client)
    monkeypatch.setattr(prediction, "render_report", lambda result: "Public strain report")
    seen = []
    async def analyze(smiles, profile_id, **kwargs):
        seen.append((profile_id, kwargs.get("modalities")))
        return {"status": "completed", "profile": load_profile(profile_id, root).overview()}
    with TestClient(create_app(data_root=root, env_file=env, report_root=tmp_path / "reports", analyzer=analyze)) as client:
        data = client.get("/api/profiles").json()
        assert data["default_profile_id"] == data["profiles"][0]["profile_id"] == REFERENCE_ID
        assert data["profiles"][0]["strain"] == "AB5075"
        assert all(item.get("input_role") != "species_reference" for item in data["profiles"])
        legacy = client.get("/api/profiles/synthetic-species-reference")
        assert legacy.status_code == 200 and legacy.json()["input_role"] == "species_reference"
        assert client.get("/api/health").json()["default_profile_id"] == REFERENCE_ID
        view = client.get(f"/api/profiles/{REFERENCE_ID}", params={"modalities": "proteome"}).json()
        assert view["prediction_scope"] == "strain_reference" and view["strain"] == "AB5075"
        assert view["selected_modalities"] == ["proteome"]
        assert client.post("/api/analyze", json={"smiles": "CCO", "modalities": ["genome"]}).status_code == 200
        assert seen == [(REFERENCE_ID, ["genome"])]
        assert client.post("/api/analyze", json={"smiles": "CCO", "profile_id": "synthetic-species-reference"}).status_code == 422
        assert seen == [(REFERENCE_ID, ["genome"])]


def test_web_never_defaults_to_a_species_only_background(tmp_path, monkeypatch):
    from praxis_virtualcell.web.app import create_app
    import praxis_virtualcell.omics as omics

    monkeypatch.setattr(omics, "list_profiles", lambda data_root=None: [{
        "profile_id": "species-only", "label": "Species background", "strain": None,
        "input_role": "species_reference", "prediction_scope": "species_reference",
    }])
    env = tmp_path / ".env"
    env.write_text("DEEPSEEK_API_KEY=\n")
    with TestClient(create_app(env_file=env)) as client:
        assert client.get("/api/profiles").json()["default_profile_id"] is None
        response = client.post("/api/analyze", json={"smiles": "CCO"})
        assert response.status_code == 422 and "explicit strain" in response.json()["detail"]


@pytest.mark.parametrize("modalities", [[], ["metabolome"], ["genome", "genome"]])
def test_invalid_modality_requests_do_not_start_analyzer(platform, tmp_path, modalities):
    from praxis_virtualcell.web.app import create_app
    async def prohibited(*args, **kwargs):
        raise AssertionError("Invalid request must not reach the model")
    with TestClient(create_app(env_file=platform[1], analyzer=prohibited, report_root=tmp_path / "reports")) as client:
        assert client.post("/api/analyze", json={"smiles": "CCO", "modalities": modalities}).status_code == 422


def test_unavailable_modalities_rejected_before_inference(platform, monkeypatch, tmp_path):
    from praxis_virtualcell.web.app import create_app
    import praxis_virtualcell.omics as omics
    monkeypatch.setattr(omics, "load_profile", lambda *args, **kwargs: Profile(("transcriptome",)))
    async def prohibited(*args, **kwargs):
        raise AssertionError("Unavailable modality must not reach the model")
    with TestClient(create_app(env_file=platform[1], analyzer=prohibited, report_root=tmp_path / "reports")) as client:
        assert client.post("/api/analyze", json={"smiles": "CCO", "modalities": ["proteome"]}).status_code == 422


def test_cli_agents_receive_selected_modalities(platform, monkeypatch, tmp_path):
    import praxis_virtualcell.llm_prediction as prediction
    calls = []
    async def agents(smiles, profile_id, **kwargs):
        calls.append(kwargs)
        return {"status": "completed"}
    monkeypatch.setattr(prediction, "analyze_with_agents", agents)
    output = tmp_path / "result.json"
    assert main(["--env-file", str(platform[1]), "analyze", "--smiles", "CCO", "--modalities", "genome", "proteome", "--output", str(output)]) == 0
    assert calls[0]["modalities"] == ["genome", "proteome"]
    assert output.with_suffix(".md").read_text() == "Public agent report"


def test_web_conditions_and_qwen_route_reach_analyzer_with_validated_smiles(platform, monkeypatch, tmp_path):
    from praxis_virtualcell.web.app import create_app
    import praxis_virtualcell.llm_prediction as prediction
    import praxis_virtualcell.llm_prediction.qwen_serving as serving
    env = platform[1]
    env.write_text(env.read_text() + "PRAXIS_ANALYSIS_MODEL=qwen-adapter\nPRAXIS_ANALYSIS_BASE_URL=http://127.0.0.1:8790\n")
    seen = []
    class LocalClient:
        closed = False
        async def aclose(self):
            self.closed = True
    local = LocalClient()
    monkeypatch.setattr(serving, "analysis_client", lambda settings: local)
    async def agents(smiles, profile_id, **kwargs):
        seen.append((smiles, kwargs))
        return {"status": "completed"}
    monkeypatch.setattr(prediction, "analyze_with_agents", agents)
    with TestClient(create_app(env_file=env, report_root=tmp_path / "reports")) as client:
        result = client.post("/api/analyze", json={"smiles": "OCC", "conditions": {
            "medium": "CAMHB", "medium_supplements": ["serum"], "temperature_c": 37,
            "exposure_hours": 24, "method": "broth_microdilution", "inoculum": "5e5 CFU/mL"}})
        assert result.status_code == 200
        assert client.post("/api/analyze", json={"smiles": "aspirin"}).status_code == 422
        assert client.post("/api/analyze", json={"candidate_id": "aspirin"}).status_code == 422
    smiles, kwargs = seen[0]
    assert len(seen) == 1 and smiles == "CCO"
    assert kwargs["conditions"]["exposure_hours"] == 24 and kwargs["conditions"]["medium_supplements"] == ["serum"]
    assert kwargs["analysis_model"] == "qwen-adapter" and kwargs["analysis_provider"] == "qwen"
    assert kwargs["analysis_client"] is local and local.closed


def test_cli_all_assay_fields_reach_analyzer(platform, monkeypatch, tmp_path):
    import praxis_virtualcell.llm_prediction as prediction
    seen = []
    async def agents(smiles, profile_id, **kwargs):
        seen.append((smiles, kwargs["conditions"]))
        return {"status": "completed"}
    monkeypatch.setattr(prediction, "analyze_with_agents", agents)
    args = ["--env-file", str(platform[1]), "analyze", "--smiles", "OCC", "--medium", "CAMHB",
            "--medium-supplement", "serum", "--medium-supplement", "NaCl", "--temperature-c", "37",
            "--exposure-hours", "20", "--method", "broth_microdilution", "--inoculum", "5e5 CFU/mL",
            "--output", str(tmp_path / "conditions.json")]
    assert main(args) == 0
    assert seen == [("CCO", {"medium": "CAMHB", "medium_supplements": ["serum", "NaCl"], "temperature_c": 37,
                              "exposure_hours": 20, "method": "broth_microdilution", "inoculum": "5e5 CFU/mL"})]


def test_cli_inspect_selected_view_without_credentials(platform, capsys):
    assert main(["inspect", "--profile", "test-profile", "--modalities", "proteome"]) == 0
    assert json.loads(capsys.readouterr().out)["selected_modalities"] == ["proteome"]


def _trajectory_report():
    return {"status": "completed", "evidence_validation": {"status": "passed"},
            "candidate": {"id": "candidate-1"}, "profile": {"profile_id": "test-profile"},
            "agent_trace": {"schema_version": "praxis.agent-trace.v1", "stages": [
                {"stage": "planning", "status": "completed", "model": "mock-model", "tools": [],
                 "messages": [{"role": "system", "content": "Plan an evidence search"},
                              {"role": "user", "content": "Use the selected organism context"},
                              {"role": "assistant", "content": '{"questions":["native expression"]}',
                               "reasoning_content": "PRIVATE_REASONING"}]}]}}


def test_export_sft_is_local_and_keeps_generated_predictions_out_of_gold(tmp_path, capsys):
    source = tmp_path / "report.json"
    source.write_text(json.dumps(_trajectory_report()), encoding="utf-8")
    output = tmp_path / "nested" / "trajectory.jsonl"
    assert main(["export-sft", "--input", str(source), "--output", str(output)]) == 0
    record = json.loads(output.read_text())
    assert record["stage"] == "planning"
    assert record["supervision"]["prediction_is_gold"] is False
    assert record["supervision"]["review_status"] == "needs_review"
    assert "PRIVATE_REASONING" not in output.read_text()
    assert json.loads(capsys.readouterr().out)["records"] == 1


def test_bad_explicit_supervision_does_not_write_sft(tmp_path):
    source = tmp_path / "report.json"
    source.write_text(json.dumps(_trajectory_report()), encoding="utf-8")
    supervision = tmp_path / "supervision.json"
    supervision.write_text('{"approved":false}', encoding="utf-8")
    output = tmp_path / "trajectory.jsonl"
    assert main(["export-sft", "--input", str(source), "--output", str(output), "--supervision", str(supervision)]) == 1
    assert not output.exists()


def _legacy_report():
    return {"status": "completed", "candidate": {"id": "C1", "smiles": "CCO"},
            "profile": {"profile_id": "P1", "species": "Test bacterium", "strain": "S1"},
            "assessment": {"activity": "uncertain", "mic_estimate": {"value": None, "reason": "Unknown", "evidence_refs": []},
                           "confidence": {"level": "low"}, "rationale_summary": "Evidence remains incomplete.",
                           "supporting_evidence": [], "counterevidence": [], "targets": [], "mechanism_hypotheses": [], "gaps": []},
            "evidence_validation": {"status": "passed"}, "execution_trace": {"model": "mock-model"}}


def test_report_keeps_legacy_results_and_renders_public_agent_review():
    legacy = _legacy_report()
    assert "MIC：未知" in render_report(legacy)
    assert "智能体阶段" not in render_report(legacy)
    legacy["profile"]["selected_modalities"] = ["genome", "proteome"]
    legacy["agent_trace"] = {"stages": [{"stage": "planning", "status": "completed", "model": "planner"},
                                         {"stage": "revision", "status": "completed", "model": "writer"}]}
    legacy["agent_review"] = {"decision": "revise", "summary": "Fix unsupported binding claim", "issues": [
        {"severity": "blocking", "code": "unsupported_causality", "finding": "Binding has not been measured", "evidence_refs": []}],
        "recommended_changes": ["Preserve the target as a hypothesis"]}
    legacy["review_resolution"] = "revised"
    text = render_report(legacy)
    assert "本次组学输入：genome、proteome" in text
    assert "规划：completed" in text and "修订：completed" in text
    assert "处理结果：revised" in text and "unsupported_causality" in text
