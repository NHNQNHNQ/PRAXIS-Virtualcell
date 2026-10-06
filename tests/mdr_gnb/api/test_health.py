"""9.1 /health:存活探针,报告支持物种数。"""


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "praxis-mdr-gnb"
    # 5 有模型物种 / 10 物种框架
    assert body["n_species_supported"] == 5
    assert body["n_species_total"] == 10
