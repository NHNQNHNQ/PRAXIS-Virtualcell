"""同源托管:static_root 给定则 serve SPA;API 路由不受影响;不给定则无 static。"""
from pathlib import Path

from fastapi.testclient import TestClient

from praxis_virtualcell.mdr_gnb.api.app import create_app


def _make_dist(tmp_path: Path) -> Path:
    (tmp_path / "mdr.html").write_text("<!doctype html><title>MDR</title>OK", encoding="utf-8")
    (tmp_path / "index.html").write_text("<!doctype html>root", encoding="utf-8")
    return tmp_path


def test_static_root_serves_spa(tmp_path):
    dist = _make_dist(tmp_path)
    client = TestClient(create_app(static_root=str(dist)))
    # API 仍在
    assert client.get("/health").json()["service"] == "praxis-mdr-gnb"
    assert isinstance(client.get("/species").json()["species"], list)
    # 根路径 serve SPA
    r = client.get("/")
    assert r.status_code == 200
    assert "root" in r.text or "OK" in r.text


def test_no_static_root_keeps_api_only(tmp_path):
    client = TestClient(create_app())          # 不给 static_root
    assert client.get("/health").status_code == 200
    # 根路径无 static → 404(仅 API,行为不变)
    assert client.get("/").status_code == 404
