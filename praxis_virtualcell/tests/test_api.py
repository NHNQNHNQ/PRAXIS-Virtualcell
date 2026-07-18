"""v0.6 P2:FastAPI 本地服务 —— offline 全链(health/parse/jobs/reports/trace/provenance)。

无 fastapi 或无法 import praxis_vc_api(不在 path)时 skip。offline 不调 LLM。
"""

import json
from pathlib import Path

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


def test_health(client, monkeypatch):
    from praxis_virtualcell import __version__

    monkeypatch.setenv("GIT_SHA", "abcdef1234567890")
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "mode": "offline",
        "llm_enabled": False,
        "product_version": __version__,
        "api_protocol_version": "vc.api.v1",
        "runtime_protocol_version": "vc.runtime.v1",
        "runtime_version": "v0.3",
        "git_sha": "abcdef1234567890",
    }


def test_parse_offline(client):
    r = client.post("/api/parse", json={"text": "在 human 细胞敲 AHR", "mode": "offline"})
    assert r.status_code == 200
    d = r.json()
    assert d["llm_used"] is False and d["candidate_request"]["species"] == "human"


def test_parse_surrogate_in_structured_input_returns_safe_clarification(client):
    text = (
        "human AHR knockout\n结构化描述:"
        '{"species":"human","perturbation_type":"gene",'
        '"perturbation_targets":["AHR"],"output_modality":"\ud800"}'
    )
    body = json.dumps({"text": text, "mode": "offline"}, ensure_ascii=True)
    r = client.post(
        "/api/parse",
        content=body.encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["schema_valid"] is False
    assert d["clarification_required"] is True
    assert d["errors"] == ["query_not_utf8_safe"]


@pytest.mark.parametrize(
    ("assumptions", "llm_error"),
    [
        (["\ud800"], None),
        (["safe"], "\ud800"),
        (["safe"], {"nested": "\ud800"}),
    ],
)
def test_parse_llm_metadata_and_assumptions_are_response_safe(
    client, monkeypatch, assumptions, llm_error
):
    import praxis_vc_api.services.runtime_service as rs
    import praxis_virtualcell.agents_llm.llm_client as llm_client
    from praxis_virtualcell.core.config import Mode, RuntimeConfig

    config = RuntimeConfig(
        mode=Mode.LLM_ASSISTED,
        llm_enabled=True,
        deepseek_api_key="stub-not-a-real-key",
    )
    monkeypatch.setattr(rs, "config_for", lambda mode: config)

    class StubClient:
        def complete(self, messages, **kwargs):
            return {
                "content": json.dumps({
                    "species": "human",
                    "perturbation_type": "gene",
                    "perturbation_targets": ["AHR"],
                    "task_type": "predict_delta_expression",
                    "assumptions": assumptions,
                }, ensure_ascii=True),
                "error": llm_error,
            }

    monkeypatch.setattr(llm_client, "make_llm_client", lambda config: StubClient())
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post(
        "/api/parse",
        json={"text": "human AHR knockout", "mode": "llm_assisted"},
    )
    assert response.status_code == 200
    payload = response.json()
    json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    assert all("\ud800" not in value for value in payload["assumptions"])


def test_parse_deep_structured_candidate_is_response_safe(client):
    nested: object = []
    for _ in range(400):
        nested = [nested]
    structured = json.dumps({
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": nested,
        "output_modality": "delta_expression",
    })
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post(
        "/api/parse",
        json={
            "text": f"请核对深层输入\n结构化描述:{structured}",
            "mode": "offline",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_valid"] is False
    assert payload["candidate_request"] == {"perturbation_targets": []}
    json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")


def test_parse_llm_huge_integer_dose_returns_safe_clarification(client, monkeypatch):
    import praxis_vc_api.services.runtime_service as rs
    import praxis_virtualcell.agents_llm.llm_client as llm_client
    from praxis_virtualcell.core.config import Mode, RuntimeConfig

    config = RuntimeConfig(
        mode=Mode.LLM_ASSISTED,
        llm_enabled=True,
        deepseek_api_key="stub-not-a-real-key",
    )
    monkeypatch.setattr(rs, "config_for", lambda mode: config)

    class StubClient:
        def complete(self, messages, **kwargs):
            return {
                "content": json.dumps({
                    "species": "human",
                    "perturbation_type": "drug",
                    "perturbation_targets": ["geldanamycin"],
                    "task_type": "predict_delta_expression",
                    "perturbation_dose": 10**400,
                }),
                "error": None,
            }

    monkeypatch.setattr(llm_client, "make_llm_client", lambda config: StubClient())
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post(
        "/api/parse",
        json={"text": "human drug response", "mode": "llm_assisted"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_valid"] is False
    assert payload["errors"] == ["invalid_perturbation_dose"]


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


def test_job_endpoint_revalidates_confirmed_request(client):
    invalid = {"species": "human", "perturbation_type": "gene",
               "perturbation_targets": ["AHR"], "input_modality": "scRNA",
               "output_modality": "invented_output", "task_type": "predict_delta_expression"}
    r = client.post("/api/jobs", json={"request": invalid, "mode": "offline"})
    assert r.status_code == 400
    assert r.json()["detail"] == "invalid_request"


def test_job_endpoint_normalizes_metadata_routing_controls(client):
    import praxis_vc_api.services.runtime_service as rs

    req = {
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
        "metadata": {
            "requested_outputs": {"growth": True},
            "assumptions": ["safe", {"not": "text"}],
            "note": "preserve me",
        },
    }
    response = client.post("/api/jobs", json={"request": req, "mode": "offline"})
    assert response.status_code == 200
    saved = rs.get_job(response.json()["job_id"])["request"]
    assert saved["metadata"] == {
        "requested_outputs": [],
        "assumptions": ["safe"],
        "note": "preserve me",
    }


@pytest.mark.parametrize("bad_dose", [{}, "not-a-number", True, 10**400])
def test_job_endpoint_rejects_invalid_perturbation_dose(client, bad_dose):
    req = {
        "species": "human",
        "perturbation_type": "drug",
        "perturbation_targets": ["geldanamycin"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
        "perturbation_dose": bad_dose,
    }
    response = client.post("/api/jobs", json={"request": req, "mode": "offline"})
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_request"


def test_job_endpoint_normalizes_finite_perturbation_dose(client):
    import praxis_vc_api.services.runtime_service as rs

    req = {
        "species": "human",
        "perturbation_type": "drug",
        "perturbation_targets": ["geldanamycin"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
        "perturbation_dose": 10,
    }
    response = client.post("/api/jobs", json={"request": req, "mode": "offline"})
    assert response.status_code == 200
    saved = rs.get_job(response.json()["job_id"])["request"]
    assert saved["perturbation_dose"] == 10.0


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


def test_module_plan_endpoint(client):
    # 可路由请求(human + 有 targets)→ 应产 module_plan
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    jid = client.post("/api/jobs", json={"request": req, "mode": "offline"}).json()["job_id"]
    r = client.get(f"/api/reports/{jid}/module-plan")
    assert r.status_code == 200
    mp = r.json()["module_plan"]
    assert mp.get("primary") and "entries" in mp and "overall_verdict" in mp


def test_job_endpoint_rejects_missing_targets_before_module_plan(client):
    # 已确认请求仍须经过后端最终校验，不能绕过 Review 直接执行空 targets。
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": [],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    r = client.post("/api/jobs", json={"request": req, "mode": "offline"})
    assert r.status_code == 400
    assert r.json()["detail"] == "invalid_request"


def test_job_endpoint_does_not_expose_internal_exception(client, monkeypatch):
    import praxis_vc_api.main as api_main

    sentinel = "secret-path-/srv/private/checkpoint.bin"

    def fail_job(*args, **kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(api_main.svc, "run_job", fail_job)
    req = {
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    }
    response = client.post("/api/jobs", json={"request": req, "mode": "offline"})
    assert response.status_code == 500
    assert response.json()["detail"] == "job_execution_failed"
    assert sentinel not in response.text


def test_legacy_module_plan_missing_is_empty_not_500(client):
    import praxis_vc_api.services.runtime_service as rs

    job_id = "legacy_without_module_plan"
    job_dir = Path(rs.RUNS_DIR) / job_id
    job_dir.mkdir(parents=True)
    (job_dir / "status").write_text("done", encoding="utf-8")
    (job_dir / "report.json").write_text("{}", encoding="utf-8")

    response = client.get(f"/api/reports/{job_id}/module-plan")
    assert response.status_code == 200
    assert response.json()["module_plan"] == {}


def test_module_plan_404(client):
    assert client.get("/api/reports/nope/module-plan").status_code == 404
