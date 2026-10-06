"""P18 advisory provenance must be replayable without changing core science."""
from __future__ import annotations

import hashlib
import json

import fakeredis
from fastapi.testclient import TestClient

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.app import _trace_metadata_from_events, create_app
from praxis_virtualcell.mdr_gnb.api.cache import PredictionCache

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


EC_CEFTRIAXONE = {
    "species": "escherichia_coli",
    "drug_panel": [{"drug": "ceftriaxone", "drug_class": "cephalosporin"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaCTX-M-15": True},
}
MORGANELLA = {
    "species": "morganella_morganii",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC": True},
}


def _canonical_sha256(value: object) -> str:
    blob = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _event(trace: list[dict], message_type: str) -> dict:
    return next(event for event in trace if event["message_type"] == message_type)


def _expected_payload(response: dict) -> dict:
    return {
        "schema_version": "mdr-response-advisory-v1",
        "advisory_policy_version": service.ADVISORY_POLICY_VERSION,
        "advisory_only": True,
        "runtime_evidence_level": response["runtime_evidence_level"],
        "active_learning": response["active_learning"],
    }


def test_response_advisory_is_append_only_hashed_trace_event():
    """The API layer makes its public advisory replayable after core report_built."""
    result = service.predict(EC_CEFTRIAXONE)
    response = result["response"]
    record = result["trace_record"]
    trace = record["trace"]
    report_event = _event(trace, "report_built")
    advisory_event = _event(trace, "response_advisory_built")
    payload = _expected_payload(response)

    assert trace[-1] == advisory_event
    assert advisory_event["parent_message_id"] == report_event["message_id"]
    assert advisory_event["payload"] == {
        **payload,
        "payload_sha256": _canonical_sha256(payload),
    }
    assert report_event["payload"]["report_sha256"] == _canonical_sha256(response["report"])
    assert "blaCTX-M-15" not in json.dumps(advisory_event, sort_keys=True)
    assert "amr_profile" not in json.dumps(advisory_event, sort_keys=True)

    metadata = record["trace_metadata"]["response_advisory"]
    assert metadata == {
        "schema_version": "mdr-response-advisory-v1",
        "advisory_policy_version": service.ADVISORY_POLICY_VERSION,
        "message_id": advisory_event["message_id"],
        "parent_message_id": report_event["message_id"],
        "payload_sha256": advisory_event["payload"]["payload_sha256"],
    }


def test_no_model_advisory_replays_null_runtime_level_without_claiming_prediction():
    result = service.predict(MORGANELLA)
    response = result["response"]
    advisory_event = _event(result["trace_record"]["trace"], "response_advisory_built")

    assert response["prediction_available"] is False
    assert response["runtime_evidence_level"] is None
    assert advisory_event["payload"]["runtime_evidence_level"] is None
    assert advisory_event["payload"]["advisory_only"] is True


def test_persisted_restart_and_event_fallback_recover_response_advisory(tmp_path):
    """The persisted trace, restart replay and no-migration fallback agree."""
    url = f"sqlite:///{tmp_path}/mdr.db"
    first = TestClient(create_app(db_url=url))
    response = first.post("/predict", json=EC_CEFTRIAXONE).json()
    task_id = response["task_id"]

    restarted = TestClient(create_app(db_url=url))
    trace_record = restarted.get(f"/trace/{task_id}").json()
    advisory_event = _event(trace_record["trace"], "response_advisory_built")
    metadata = trace_record["trace_metadata"]
    assert _trace_metadata_from_events(trace_record["trace"])["response_advisory"] == metadata[
        "response_advisory"
    ]

    rows = restarted.get(f"/executions/{task_id}").json()["executions"]
    replay = restarted.get(f"/execution/{rows[0]['execution_record_id']}").json()
    replay_event = _event(replay["trace"], "response_advisory_built")
    assert replay_event == advisory_event
    assert replay["trace_metadata"]["response_advisory"] == metadata["response_advisory"]


def test_advisory_policy_change_invalidates_cache_and_replays_the_new_binding(
    tmp_path, monkeypatch
):
    """Response-only advisory policy changes must not replay an old cached queue.

    The core scientific report remains byte-identical.  The API must instead
    create a new execution identity and persist a trace event that identifies
    the advisory policy which produced the public queue.
    """
    url = f"sqlite:///{tmp_path}/mdr.db"
    cache = PredictionCache(fakeredis.FakeStrictRedis())
    client = TestClient(create_app(db_url=url, cache=cache))
    initial_policy_version = service.ADVISORY_POLICY_VERSION

    first_http = client.post("/predict", json=EC_CEFTRIAXONE)
    assert first_http.headers["x-mdr-cache"] == "miss"
    first = first_http.json()

    class ChangedQueue:
        def to_dict(self):
            return {
                "items": [{"candidate": "changed_after_policy_release"}],
                "notes": ["simulated_new_advisory_policy"],
            }

    changed_policy_version = "mdr-response-advisory-policy-test-v2"
    monkeypatch.setattr(service, "ADVISORY_POLICY_VERSION", changed_policy_version)
    monkeypatch.setattr(
        service,
        "build_amr_learning_queue",
        lambda *args, **kwargs: ChangedQueue(),
    )

    second_http = client.post("/predict", json=EC_CEFTRIAXONE)
    assert second_http.headers["x-mdr-cache"] == "miss"
    second = second_http.json()

    assert second["task_id"] == first["task_id"]
    assert second["execution_id"] != first["execution_id"]
    assert second["report"] == first["report"]
    assert second["active_learning"]["items"] == [
        {"candidate": "changed_after_policy_release"}
    ]

    rows = client.get(f"/executions/{first['task_id']}").json()["executions"]
    assert len(rows) == 2
    first_replay = client.get(f"/execution/{rows[0]['execution_record_id']}").json()
    second_replay = client.get(f"/execution/{rows[1]['execution_record_id']}").json()

    first_event = _event(first_replay["trace"], "response_advisory_built")
    second_event = _event(second_replay["trace"], "response_advisory_built")
    assert first_event["payload"]["advisory_policy_version"] == initial_policy_version
    assert second_event["payload"]["advisory_policy_version"] == changed_policy_version
    assert first_replay["trace_metadata"]["response_advisory"][
        "advisory_policy_version"
    ] == initial_policy_version
    assert second_replay["trace_metadata"]["response_advisory"][
        "advisory_policy_version"
    ] == changed_policy_version
    assert _event(first_replay["trace"], "report_built")["payload"][
        "report_sha256"
    ] == _event(second_replay["trace"], "report_built")["payload"]["report_sha256"]
