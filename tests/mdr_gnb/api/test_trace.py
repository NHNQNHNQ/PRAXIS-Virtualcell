"""9.1 /trace/{task_id}:取回确定性 trace(replay)。缺 job → 404。"""

import json

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

KP_MEROPENEM = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}


def test_trace_after_predict(client):
    task_id = client.post("/predict", json=KP_MEROPENEM).json()["task_id"]
    r = client.get(f"/trace/{task_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["task_id"] == task_id
    assert len(body["trace"]) >= 1
    # trace 项是序列化的 AgentMessage
    m = body["trace"][0]
    for k in ("message_id", "sender", "receiver", "message_type", "timestamp"):
        assert k in m


def test_trace_replay_identical(client):
    """两次 predict 同 raw → trace 逐字相等(确定性 replay)。"""
    t1 = client.post("/predict", json=KP_MEROPENEM).json()["task_id"]
    tr1 = client.get(f"/trace/{t1}").json()["trace"]
    # 新 client(新内存 store)重跑,trace 仍相等
    from fastapi.testclient import TestClient
    from praxis_virtualcell.mdr_gnb.api.app import create_app
    c2 = TestClient(create_app())
    t2 = c2.post("/predict", json=KP_MEROPENEM).json()["task_id"]
    tr2 = c2.get(f"/trace/{t2}").json()["trace"]
    assert t1 == t2
    assert tr1 == tr2


def test_trace_exposes_schema_input_and_report_bindings(client):
    """P1 trace spine: API 回放记录必须说明 schema、输入和最终报告的哈希绑定。"""
    task_id = client.post("/predict", json=KP_MEROPENEM).json()["task_id"]
    body = client.get(f"/trace/{task_id}").json()
    metadata = body["trace_metadata"]

    assert metadata["schema_version"] == "mdr-trace-v1"
    assert len(metadata["input_sha256"]) == 64
    assert len(metadata["report_sha256"]) == 64
    assert metadata["critic_policy_version"] == "mdr-critic-v2-final-fusion"
    assert len(metadata["governance_snapshot_digest"]) == 64
    snapshot_event = next(
        event for event in body["trace"]
        if event["message_type"] == "governance_snapshot_bound"
    )
    assert snapshot_event["payload"]["governance_digest"] == metadata[
        "governance_snapshot_digest"
    ]
    events = {event["message_type"]: event for event in body["trace"]}
    final_decision = events["final_decision_resolved"]
    assert final_decision["payload"]["schema_version"] == "mdr-final-decision-v1"
    assert final_decision["parent_message_id"] == events["critic_checked"]["message_id"]
    assert events["report_built"]["parent_message_id"] == final_decision["message_id"]


def test_public_trace_redacts_raw_biological_request_inputs(client):
    """Unauthenticated replay must retain the trace spine without exposing AMR calls."""
    raw = {
        **KP_MEROPENEM,
        "amr_profile": {
            "blaKPC-2": True,
            "private_marker_gene_123": True,
        },
    }
    task_id = client.post("/predict", json=raw).json()["task_id"]

    body = client.get(f"/trace/{task_id}").json()

    assert body["trace_redacted"] is True
    assert body["trace_hash_scope"] == "stored_full_trace"
    assert "input_manifest" not in body
    assert "private_marker_gene_123" not in json.dumps(body, sort_keys=True)
    task_event = next(
        event for event in body["trace"] if event["message_type"] == "mdr_task"
    )
    assert task_event["payload"]["request"] == {"redacted": True}


def test_trace_missing_404(client):
    r = client.get("/trace/does-not-exist")
    assert r.status_code == 404
