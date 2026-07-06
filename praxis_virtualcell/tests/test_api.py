"""v0.6 P2:FastAPI 本地服务 —— offline 全链(health/parse/jobs/reports/trace/provenance)。

无 fastapi 或无法 import praxis_vc_api(不在 path)时 skip。offline 不调 LLM。
"""

import pytest

pytest.importorskip("fastapi")
try:
    from fastapi.testclient import TestClient

    from praxis_vc_api.main import app
except Exception:  # noqa: BLE001
    pytest.skip("praxis_vc_api 不可导入(需 repo root 在 PYTHONPATH)", allow_module_level=True)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_VC_RUNS", str(tmp_path / "runs"))
    # 强制 offline
    monkeypatch.delenv("PRAXIS_VIRTUALCELL_MODE", raising=False)
    import importlib

    import praxis_vc_api.services.runtime_service as rs
    importlib.reload(rs)
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and "mode" in r.json()


def test_parse_offline(client):
    r = client.post("/api/parse", json={"text": "在 human 细胞敲 AHR", "mode": "offline"})
    assert r.status_code == 200
    d = r.json()
    assert d["llm_used"] is False and d["candidate_request"]["species"] == "human"


def test_job_flow_offline(client):
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    j = client.post("/api/jobs", json={"request": req, "mode": "offline"})
    assert j.status_code == 200
    jid = j.json()["job_id"]
    assert j.json()["status"] == "done"
    rep = client.get(f"/api/reports/{jid}")
    assert rep.status_code == 200
    assert rep.json()["llm_used_for_prediction"] is False
    assert "structured_report" in rep.json()
    tr = client.get(f"/api/reports/{jid}/trace")
    assert tr.status_code == 200 and tr.json()["trace"]
    pv = client.get(f"/api/reports/{jid}/provenance")
    assert pv.status_code == 200 and "provenance" in pv.json()


def test_list_jobs(client):
    # 空 → []
    assert client.get("/api/jobs").json()["jobs"] == []
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    client.post("/api/jobs", json={"request": req, "mode": "offline"})
    jobs = client.get("/api/jobs").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["species"] == "human" and jobs[0]["status"] == "done"


def test_options(client):
    d = client.get("/api/options").json()
    assert "human" in d["species"] and "mouse" in d["species"]
    assert "gene" in d["perturbation_type"]
    assert d["cell_type_free_text"] is True and len(d["cell_type_examples"]) > 0
    presets = d["cell_presets"]
    assert len(presets) >= 10
    p0 = presets[0]
    assert p0["species"] in d["species"] and p0["cell_type"] and p0["label"]


def test_report_markdown(client):
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    jid = client.post("/api/jobs", json={"request": req, "mode": "offline"}).json()["job_id"]
    r = client.get(f"/api/reports/{jid}/markdown")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert "# PRAXIS-VirtualCell Report" in r.text
    assert "## 5. Governance Verdict" in r.text


def test_report_markdown_404(client):
    assert client.get("/api/reports/nope/markdown").status_code == 404


def test_missing_job_404(client):
    assert client.get("/api/reports/nope").status_code == 404


def test_modules_catalog(client):
    d = client.get("/api/modules").json()
    mods = d["modules"]
    assert len(mods) == 8
    codes = [m["code"] for m in mods]
    assert codes == ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]  # MODULE_ORDER 顺序
    m2 = next(m for m in mods if m["code"] == "M2")
    assert m2["id"] == "genetic_hub" and m2["display_name"] == "Genetic Hub"
    assert "donor_predictor" in m2["engines"]
    assert "pillars" in m2 and isinstance(m2["pillars"], list)
