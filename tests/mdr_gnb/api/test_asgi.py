"""9.4 生产 ASGI 入口:uvicorn praxis_virtualcell.mdr_gnb.api.asgi:app。
env 接线(MDR_DB_URL/MDR_REDIS_URL);未设则纯内存,/health 可达。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def test_asgi_app_is_fastapi():
    from praxis_virtualcell.mdr_gnb.api.asgi import app
    assert isinstance(app, FastAPI)


def test_asgi_health_reachable():
    from praxis_virtualcell.mdr_gnb.api.asgi import app
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "praxis-mdr-gnb"


def test_build_app_memory_default(monkeypatch):
    monkeypatch.delenv("MDR_DB_URL", raising=False)
    monkeypatch.delenv("MDR_REDIS_URL", raising=False)
    from praxis_virtualcell.mdr_gnb.api.asgi import build_app
    app = build_app()
    assert TestClient(app).get("/health").json()["persistence"] == "memory"


@pytest.mark.parametrize("blank_url", ["", "   "])
def test_build_app_blank_db_url_stays_in_memory_and_creates_no_default_database(
    monkeypatch, tmp_path, blank_url
):
    """An unset-like environment value must not silently retain biological input."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MDR_DB_URL", blank_url)
    monkeypatch.delenv("MDR_REDIS_URL", raising=False)
    from praxis_virtualcell.mdr_gnb.api.asgi import build_app

    app = build_app()
    assert TestClient(app).get("/health").json()["persistence"] == "memory"
    assert not (tmp_path / "data" / "mdr_gnb" / "mdr_api.db").exists()


def test_build_app_explicit_sqlite_url_enables_persistence(monkeypatch, tmp_path):
    """Persistence is opt-in and needs a nonblank, explicit database URL."""
    db_path = tmp_path / "audit.sqlite"
    monkeypatch.setenv("MDR_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("MDR_REDIS_URL", raising=False)
    from praxis_virtualcell.mdr_gnb.api.asgi import build_app

    app = build_app()
    assert TestClient(app).get("/health").json()["persistence"] == "on"
    assert db_path.is_file()
