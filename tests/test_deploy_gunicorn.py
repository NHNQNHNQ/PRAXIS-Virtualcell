"""§11.1 gunicorn 配置 + make_app_default 工厂 + 本地多 worker smoke。"""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest


def _deploy_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "deploy"


def test_gunicorn_conf_exists_and_reads_from_settings():
    f = _deploy_dir() / "gunicorn.conf.py"
    assert f.is_file()
    text = f.read_text()
    # 必须从 praxis2.config 读(单一源,§6⑤)
    assert "from praxis2.config import" in text
    assert "load_from_env" in text
    # worker_class uvicorn(总纲 §11.1)
    assert "uvicorn" in text
    # bind / workers 字段
    assert "bind" in text
    assert "workers" in text


def test_make_app_default_factory_exists(monkeypatch):
    # gunicorn CMD `praxis2.server.app:make_app_default` 工厂存在
    for k in [
        "PRAXIS_ANTHROPIC_API_KEY",
        "PRAXIS_ANTHROPIC_BASE_URL",
        "PRAXIS_MODEL",
        "PRAXIS_MAX_TOKENS",
        "PRAXIS_MAX_TURNS",
        "PRAXIS_RECOVERY_BUDGET",
        "PRAXIS_MAX_OUTPUT_RECOVERY",
        "PRAXIS_HOST",
        "PRAXIS_PORT",
        "PRAXIS_WORKERS",
        "PRAXIS_MAX_CONCURRENT_PER_USER",
        "PRAXIS_USER_QPS",
        "PRAXIS_GLOBAL_LLM_INFLIGHT",
        "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED",
    ]:
        monkeypatch.setenv(
            k,
            "1"
            if k.endswith(
                (
                    "PORT",
                    "TOKENS",
                    "TURNS",
                    "BUDGET",
                    "RECOVERY",
                    "WORKERS",
                    "USER",
                    "INFLIGHT",
                    "QUEUED",
                )
            )
            else "x",
        )
    monkeypatch.setenv("PRAXIS_USER_QPS", "1.0")
    # M9 新增必填(§6⑤ 校准)
    monkeypatch.setenv("PRAXIS_DB_URL", "postgresql://x")
    monkeypatch.setenv("PRAXIS_REDIS_URL", "redis://x")
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "p")

    # M9:make_app_default 真连 PG/Redis,本测仅验工厂存在,monkeypatch 重 IO 函数
    import praxis2.server.app as appmod
    from praxis2.auth.repository import FakeAuthRepository

    async def _fake_pool(_url, **_kw):
        return object()  # 占位:不会真用

    monkeypatch.setattr("praxis2.store.pg.make_pg_pool", _fake_pool)
    monkeypatch.setattr("praxis2.store.redis.make_redis_client", lambda _url, **_kw: object())
    monkeypatch.setattr(
        "praxis2.auth.repository_pg.PgAuthRepository", lambda _pool: FakeAuthRepository()
    )
    # PgStore 也 stub(__init__ 只存 pool,不连)
    monkeypatch.setattr("praxis2.store.pg.PgStore", lambda _pool: object())

    app = appmod.make_app_default()
    # v0.9.1 hotfix:make_app_default 返 _LifespanApp(lifespan.startup 时才 init)。
    # permission_registry 等内层属性在 _ensure_init 后才可访问;此处只验工厂签名。
    assert isinstance(app, appmod._LifespanApp)
    assert callable(app)  # ASGI app(callable scope, receive, send)


@pytest.mark.integration
def test_local_multi_worker_smoke():
    """本地真起 gunicorn 多 worker:N=2,curl /chat/stream(M8 校准 SLO 真路径数值)。
    本机若无 gunicorn 装(pip install gunicorn 即可)→ skip。"""
    if shutil.which("gunicorn") is None:
        pytest.skip("gunicorn 未装,跳过本地 multi-worker smoke")
    # 找空闲端口
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    env = os.environ.copy()
    env.update(
        {
            "PRAXIS_ANTHROPIC_API_KEY": "sk-test",
            "PRAXIS_ANTHROPIC_BASE_URL": "https://example.invalid",
            "PRAXIS_MODEL": "test-model",
            "PRAXIS_MAX_TOKENS": "64",
            "PRAXIS_MAX_TURNS": "20",
            "PRAXIS_RECOVERY_BUDGET": "3",
            "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
            "PRAXIS_HOST": "127.0.0.1",
            "PRAXIS_PORT": str(port),
            "PRAXIS_WORKERS": "2",
            "PRAXIS_MAX_CONCURRENT_PER_USER": "5",
            "PRAXIS_USER_QPS": "10.0",
            "PRAXIS_GLOBAL_LLM_INFLIGHT": "100",
            "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "100",
            # M9 新增必填(§6⑤ 校准)
            "PRAXIS_DB_URL": "postgresql://x",
            "PRAXIS_REDIS_URL": "redis://x",
            "PRAXIS_PASSWORD_PEPPER": "p",
        }
    )

    cwd = Path(__file__).resolve().parent.parent
    proc = subprocess.Popen(
        [
            "gunicorn",
            "-c",
            str(_deploy_dir() / "gunicorn.conf.py"),
            "-w",
            "2",
            "-k",
            "uvicorn.workers.UvicornWorker",
            "-b",
            f"127.0.0.1:{port}",
            "--access-logfile",
            "-",
            "praxis2.server.app:make_app_default",
        ],
        env=env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        # 等 gunicorn 起来(轮询健康端口)
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), 0.5):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("gunicorn 8s 内未起")

        # 打 /nope 验证 404(/chat/stream 需 cassette 上游,smoke 用 404 验路由活)
        r = httpx.get(f"http://127.0.0.1:{port}/nope", timeout=3.0)
        assert r.status_code == 404
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
