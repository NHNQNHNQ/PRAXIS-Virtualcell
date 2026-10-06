"""P2: persisted MDR executions must be append-only and replayable."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.db import (
    DB_VERSION,
    Prediction,
    PredictionRepo,
    init_db,
    make_engine,
)


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


KP = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True, "private_marker_gene_123": True},
}


def _prediction():
    result = service.predict(KP)
    return result["response"], result["trace_record"]


def test_repo_keeps_append_only_records_while_latest_snapshot_stays_compatible(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/mdr.db")
    init_db(engine)
    repo = PredictionRepo(engine)
    response, trace_record = _prediction()

    first_id = repo.save_prediction(
        response,
        trace_record,
        registry_version="registry-before",
        now=datetime(2026, 7, 18, 0, 0, tzinfo=timezone.utc),
    )
    second_id = repo.save_prediction(
        response,
        trace_record,
        registry_version="registry-after",
        now=datetime(2026, 7, 18, 0, 1, tzinfo=timezone.utc),
    )

    assert first_id != second_id
    history = repo.list_execution_summaries(response["task_id"])
    assert [item["execution_record_id"] for item in history] == [first_id, second_id]
    assert [item["registry_version"] for item in history] == [
        "registry-before",
        "registry-after",
    ]
    assert all(item["execution_id"] == response["execution_id"] for item in history)
    assert repo.get(response["task_id"])["registry_version"] == "registry-after"

    first = repo.get_execution(first_id)
    assert first is not None
    assert first["trace"] == trace_record["trace"]
    assert first["trace_metadata"] == trace_record["trace_metadata"]
    assert first["db_version"] == DB_VERSION


def test_sqlite_execution_history_rejects_raw_dml_and_survives_reopen(tmp_path):
    """The SQLite audit table must not rely only on repository discipline."""
    url = f"sqlite:///{tmp_path}/guarded-history.db"
    engine = make_engine(url)
    init_db(engine)
    repo = PredictionRepo(engine)
    response, trace_record = _prediction()
    record_id = repo.save_prediction(
        response,
        trace_record,
        registry_version="registry-original",
        now=datetime(2026, 7, 19, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(IntegrityError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE prediction_executions "
                    "SET registry_version = :registry_version "
                    "WHERE execution_record_id = :record_id"
                ),
                {"registry_version": "tampered", "record_id": record_id},
            )
    with pytest.raises(IntegrityError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM prediction_executions "
                    "WHERE execution_record_id = :record_id"
                ),
                {"record_id": record_id},
            )
    # SQLite REPLACE does not provide a normal UPDATE path.  Guard it explicitly
    # so a raw same-primary-key replacement cannot erase the original record.
    with pytest.raises(IntegrityError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR REPLACE INTO prediction_executions "
                    "SELECT * FROM prediction_executions "
                    "WHERE execution_record_id = :record_id"
                ),
                {"record_id": record_id},
            )

    original = repo.get_execution(record_id)
    assert original is not None
    assert original["registry_version"] == "registry-original"

    # File-backed SQLite must retain the guards after a fresh engine/connection.
    engine.dispose()
    reopened = make_engine(url)
    with reopened.connect() as connection:
        trigger_names = set(
            connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'trigger' AND tbl_name = 'prediction_executions'"
                )
            ).scalars()
        )
    assert trigger_names == {
        "prediction_executions_no_delete",
        "prediction_executions_no_replace",
        "prediction_executions_no_update",
    }
    with pytest.raises(IntegrityError, match="append-only"):
        with reopened.begin() as connection:
            connection.execute(
                text(
                    "UPDATE prediction_executions "
                    "SET registry_version = :registry_version "
                    "WHERE execution_record_id = :record_id"
                ),
                {"registry_version": "tampered-after-reopen", "record_id": record_id},
            )
    assert PredictionRepo(reopened).get_execution(record_id)["registry_version"] == (
        "registry-original"
    )


def test_additive_schema_upgrade_preserves_v1_latest_row_without_inventing_history(tmp_path):
    """A pre-history database must remain readable; it gets no fabricated past events."""
    engine = make_engine(f"sqlite:///{tmp_path}/legacy.db")
    Prediction.__table__.create(engine)
    with Session(engine) as session:
        session.add(
            Prediction(
                task_id="legacy-task",
                species="escherichia_coli",
                drug="meropenem",
                sir="R",
                abstained=False,
                output_kind="sir_class",
                trace_hash="a" * 64,
                registry_version="legacy-registry",
                db_version="1",
                input_manifest={"legacy": True},
                report={"task_id": "legacy-task", "sir": "R"},
                trace=[],
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()

    init_db(engine)
    repo = PredictionRepo(engine)
    assert repo.get("legacy-task")["registry_version"] == "legacy-registry"
    assert repo.list_execution_summaries("legacy-task") == []


def test_persistent_api_exposes_each_execution_and_its_replay_trace(tmp_path):
    client = TestClient(create_app(db_url=f"sqlite:///{tmp_path}/mdr.db"))
    task_id = client.post("/predict", json=KP).json()["task_id"]
    assert client.post("/predict", json=KP).json()["task_id"] == task_id

    history = client.get(f"/executions/{task_id}")
    assert history.status_code == 200
    rows = history.json()["executions"]
    assert len(rows) == 2
    assert rows[0]["execution_record_id"] != rows[1]["execution_record_id"]
    assert rows[0]["execution_id"] == rows[1]["execution_id"]
    assert all(len(row["trace_hash"]) == 64 for row in rows)

    replay = client.get(f"/execution/{rows[0]['execution_record_id']}")
    assert replay.status_code == 200
    assert replay.json()["task_id"] == task_id
    assert replay.json()["execution_record_id"] == rows[0]["execution_record_id"]
    assert replay.json()["trace"]
    assert "input_manifest" not in replay.json()
    assert replay.json()["trace_redacted"] is True
    assert replay.json()["trace_hash_scope"] == "stored_full_trace"
    assert "private_marker_gene_123" not in json.dumps(replay.json())


def test_execution_history_endpoints_fail_closed_without_persistence():
    client = TestClient(create_app())
    assert client.get("/executions/missing").status_code == 404
    assert client.get("/execution/1").status_code == 404
