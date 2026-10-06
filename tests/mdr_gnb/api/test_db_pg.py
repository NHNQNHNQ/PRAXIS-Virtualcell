"""9.2 PostgreSQL 集成测(PG 走 53)。@pytest.mark.integration;缺 MDR_PG_URL 则 skip。
本地无 PG 不阻塞常规套件;53 上设 MDR_PG_URL 后跑真 PG。"""
import os

import pytest

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.db import PredictionRepo, init_db, make_engine

pytestmark = pytest.mark.integration

KP = {
    "species": "klebsiella_pneumoniae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}


@pytest.fixture()
def pg_engine():
    url = os.environ.get("MDR_PG_URL")
    if not url:
        pytest.skip("MDR_PG_URL 未设:无本地 PostgreSQL,跳过 PG 集成测")
    engine = make_engine(url)
    init_db(engine)
    return engine


def test_pg_roundtrip(pg_engine):
    repo = PredictionRepo(pg_engine)
    result = service.predict(KP)
    repo.save_prediction(result["response"], result["trace_record"], registry_version="rv-pg")
    row = repo.get(result["response"]["task_id"])
    assert row is not None and row["sir"] == "R"
    assert row["registry_version"] == "rv-pg"
