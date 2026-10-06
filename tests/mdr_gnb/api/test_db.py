"""9.2 持久化层(SQLite 兜底)。存 job metadata/input manifest/prediction output/
trace hash/model version/registry version/db_version;跨连接持久化;幂等 upsert。
SQLite 内建 → 常规套件跑(不需外部 DB)。PG 集成测另见 test_db_pg.py。"""
from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.db import (
    DB_VERSION, PredictionRepo, init_db, make_engine, trace_hash,
)

KP = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}


def _predict():
    result = service.predict(KP)
    return result["response"], result["trace_record"]


def test_save_and_get_roundtrip(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/mdr.db")
    init_db(engine)
    repo = PredictionRepo(engine)
    resp, tr = _predict()
    repo.save_prediction(resp, tr, registry_version="rv-abc")

    row = repo.get(resp["task_id"])
    assert row is not None
    assert row["task_id"] == resp["task_id"]
    assert row["species"] == "klebsiella_pneumoniae"
    assert row["drug"] == "meropenem"
    assert row["sir"] == "R"
    assert row["abstained"] is False
    assert row["registry_version"] == "rv-abc"
    assert row["db_version"] == DB_VERSION
    # trace hash 可复算(供跨系统校验)
    assert row["trace_hash"] == trace_hash(tr["trace"])
    # 完整 report/input manifest 落库(可回放)
    assert row["report"]["sir"] == "R"
    assert row["input_manifest"]["species"] == "klebsiella_pneumoniae"


def test_persistence_across_connections(tmp_path):
    """一个 engine 写,另一个新 engine 读同一文件 → 真持久化。"""
    url = f"sqlite:///{tmp_path}/mdr.db"
    resp, tr = _predict()
    e1 = make_engine(url); init_db(e1)
    PredictionRepo(e1).save_prediction(resp, tr, registry_version="rv1")

    e2 = make_engine(url)   # 全新连接
    row = PredictionRepo(e2).get(resp["task_id"])
    assert row is not None and row["sir"] == "R"


def test_upsert_idempotent(tmp_path):
    """同 task_id 存两次不重复(内容寻址,确定性)。"""
    engine = make_engine(f"sqlite:///{tmp_path}/mdr.db"); init_db(engine)
    repo = PredictionRepo(engine)
    resp, tr = _predict()
    repo.save_prediction(resp, tr, registry_version="rv1")
    repo.save_prediction(resp, tr, registry_version="rv1")
    assert len(repo.list_ids()) == 1


def test_get_missing_returns_none(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/mdr.db"); init_db(engine)
    assert PredictionRepo(engine).get("nope") is None
