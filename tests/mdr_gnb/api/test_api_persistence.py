"""9.2 API↔DB 集成(SQLite,常规套件跑)。create_app(db_url=) 时 /predict 落库,
/trace 可从 DB 回放(跨 app 实例即跨重启),provenance 版本入库。"""
import json

from fastapi.testclient import TestClient

from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.db import DB_VERSION, PredictionRepo, make_engine

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

KP = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}


def test_predict_persists_row(tmp_path):
    url = f"sqlite:///{tmp_path}/mdr.db"
    c = TestClient(create_app(db_url=url))
    task_id = c.post("/predict", json=KP).json()["task_id"]
    # DB 里能查到,且 provenance 版本齐全
    row = PredictionRepo(make_engine(url)).get(task_id)
    assert row is not None
    assert row["sir"] == "R"
    assert row["registry_version"]           # 非空
    assert row["trace_hash"]
    assert row["db_version"] == DB_VERSION


def test_trace_survives_restart(tmp_path):
    """新 app(空内存 store)+ 同 db_url → /trace 从 DB 回放(模拟重启)。"""
    url = f"sqlite:///{tmp_path}/mdr.db"
    c1 = TestClient(create_app(db_url=url))
    task_id = c1.post("/predict", json=KP).json()["task_id"]

    c2 = TestClient(create_app(db_url=url))   # 全新进程语义:内存 store 为空
    r = c2.get(f"/trace/{task_id}")
    assert r.status_code == 200
    assert r.json()["task_id"] == task_id
    assert len(r.json()["trace"]) >= 1
    metadata = r.json()["trace_metadata"]
    assert metadata["schema_version"] == "mdr-trace-v1"
    assert len(metadata["input_sha256"]) == 64
    assert len(metadata["report_sha256"]) == 64
    assert metadata["critic_policy_version"] == "mdr-critic-v2-final-fusion"


def test_persisted_public_trace_redacts_raw_biological_inputs_after_restart(tmp_path):
    """The DB fallback must not bypass the in-memory public trace projection."""
    url = f"sqlite:///{tmp_path}/mdr.db"
    raw = {
        **KP,
        "amr_profile": {
            "blaKPC-2": True,
            "private_marker_gene_123": True,
        },
    }
    first = TestClient(create_app(db_url=url))
    task_id = first.post("/predict", json=raw).json()["task_id"]

    body = TestClient(create_app(db_url=url)).get(f"/trace/{task_id}").json()

    assert body["trace_redacted"] is True
    assert body["trace_hash_scope"] == "stored_full_trace"
    assert "input_manifest" not in body
    assert "private_marker_gene_123" not in json.dumps(body, sort_keys=True)


def test_no_db_still_works(tmp_path):
    """不给 db_url → 纯内存,/predict /trace 仍工作(9.1 行为不变)。"""
    c = TestClient(create_app())
    task_id = c.post("/predict", json=KP).json()["task_id"]
    assert c.get(f"/trace/{task_id}").status_code == 200
