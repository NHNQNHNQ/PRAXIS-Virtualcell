import json
import argparse
import asyncio

import pytest
from fastapi.testclient import TestClient

from praxis_virtualcell.cli import read_candidates
from praxis_virtualcell.settings import LLMSettings


def test_settings_reuse_one_local_key_without_exposing_it(tmp_path):
    path = tmp_path / ".env"
    path.write_text("DEEPSEEK_API_KEY='private-test-credential'\nPRAXIS_MODEL=deepseek-v4-pro\n", encoding="utf-8")
    settings = LLMSettings.load(path, environ={})
    assert settings.api_key == "private-test-credential"
    assert "private-test-credential" not in repr(settings)
    assert LLMSettings.load(path, environ={"PRAXIS_MODEL": "deepseek-flash"}).model == "deepseek-flash"


def test_candidate_import_excludes_old_prediction_scores(tmp_path):
    path = tmp_path / "candidates.csv"
    path.write_text("smiles,score,mic\nCCO,0.99,1\nCCN,0.05,500\n", encoding="utf-8")
    assert read_candidates(path) == [{"id": "candidate-001", "smiles": "CCO"},
                                     {"id": "candidate-002", "smiles": "CCN"}]


@pytest.mark.asyncio
async def test_batch_bounds_concurrency_and_preserves_input_order(tmp_path, monkeypatch):
    import praxis_virtualcell.llm_prediction as prediction
    import praxis2.llm.client as llm
    from praxis_virtualcell.cli import run_analysis
    env = tmp_path / ".env"
    env.write_text("DEEPSEEK_API_KEY=private-test-credential\n", encoding="utf-8")
    source = tmp_path / "candidates.csv"
    source.write_text("id,SMILES,score\nfirst,CCO,0.99\nsecond,CCN,0.01\nthird,CCC,0.5\n", encoding="utf-8")
    active = peak = 0
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def aclose(self):
            pass
    async def analyze(smiles, profile_id, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        await asyncio.sleep(0.03 if kwargs["candidate_id"] == "first" else 0.001)
        active -= 1
        return {"status": "completed", "candidate": {"id": kwargs["candidate_id"]},
                "assessment": {"activity": "uncertain", "mic_estimate": {"value": None}}}
    monkeypatch.setattr(llm, "LLMClient", Client)
    monkeypatch.setattr(prediction, "analyze_candidate", analyze)
    monkeypatch.setattr(prediction, "render_report", lambda result: result["candidate"]["id"])
    args = argparse.Namespace(command="batch", env_file=env, model=None, input=source,
                              limit=None, output=tmp_path / "reports", concurrency=2,
                              profile="chosen-strain", data_root=None, max_turns=8)
    assert await run_analysis(args) == 0
    assert peak == 2
    summary = json.loads((args.output / "summary.json").read_text())
    assert [item["candidate_id"] for item in summary] == ["first", "second", "third"]
    assert (args.output / "001.md").read_text() == "first"


@pytest.fixture
def web_profiles(monkeypatch):
    import praxis_virtualcell.omics as omics
    class Profile:
        def overview(self):
            return {"profile_id": "AB5075-AZI000", "strain": "AB5075", "condition": "untreated"}
        def query_genes(self, gene_ids):
            return {"missing": gene_ids}
        def search_annotations(self, query):
            return {"query": query, "matches": []}
    def load(profile_id, data_root=None):
        if profile_id != "AB5075-AZI000":
            raise KeyError(profile_id)
        return Profile()
    monkeypatch.setattr(omics, "load_profile", load)
    monkeypatch.setattr(omics, "list_profiles", lambda data_root=None: [Profile().overview()])


def test_web_profile_selection_and_no_key_failure(tmp_path, web_profiles):
    from praxis_virtualcell.web.app import create_app
    env = tmp_path / ".env"
    env.write_text("DEEPSEEK_API_KEY=\n", encoding="utf-8")
    with TestClient(create_app(env_file=env, report_root=tmp_path / "reports")) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/profiles").json()["profiles"][0]["strain"] == "AB5075"
        assert client.get("/api/profiles/wrong-strain").status_code == 404
        response = client.post("/api/analyze", json={"smiles": "CCO"})
        assert response.status_code == 503


def test_web_runs_selected_profile_and_keeps_credentials_private(tmp_path, web_profiles, monkeypatch):
    import praxis_virtualcell.llm_prediction as prediction
    from praxis_virtualcell.web.app import create_app
    env = tmp_path / ".env"
    secret = "private-test-credential"
    env.write_text("DEEPSEEK_API_KEY=" + secret + "\n", encoding="utf-8")
    calls = []
    async def analyze(smiles, profile_id, **kwargs):
        calls.append((smiles, profile_id, kwargs["model"]))
        return {"status": "completed", "assessment": {"activity": "uncertain"}, "execution_trace": {"tool_calls": []}}
    monkeypatch.setattr(prediction, "render_report", lambda result: "LLM estimate; historical untreated sample")
    with TestClient(create_app(env_file=env, report_root=tmp_path / "reports", analyzer=analyze)) as client:
        response = client.post("/api/analyze", json={"smiles": "CCO", "profile_id": "AB5075-AZI000"})
        assert response.status_code == 200
        result = response.json()
        assert calls == [("CCO", "AB5075-AZI000", "deepseek-v4-pro")]
        assert secret not in json.dumps(result)
        assert secret not in client.get("/api/health").text
        assert client.get("/api/reports/" + result["report_id"]).json()["status"] == "completed"
        assert "historical untreated" in client.get("/api/reports/" + result["report_id"] + "?format=md").text
