"""9.4 后端放行 Vite dev(5173)CORS,使 MDR 前端 dev 可跨源直连。
前端只读展示,不影响后端科学决策。"""


def test_cors_allows_vite_dev(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_preflight_predict(client):
    r = client.options(
        "/predict",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
