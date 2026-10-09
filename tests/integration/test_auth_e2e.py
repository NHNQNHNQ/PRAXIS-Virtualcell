"""M9 端到端 integration:testcontainers PG+Redis + alembic + full auth flow。"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

import httpx
import pytest
import pytest_asyncio

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def app_with_real_backends():
    pytest.importorskip("testcontainers.postgres")
    pytest.importorskip("testcontainers.redis")
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

    from praxis2.auth.email import DevEmailGateway
    from praxis2.auth.repository_pg import PgAuthRepository
    from praxis2.server.app import AppDeps, make_app
    from praxis2.store.pg import PgStore, make_pg_pool
    from praxis2.store.redis import make_redis_client

    pg_container = PostgresContainer("postgres:16")
    redis_container = RedisContainer("redis:7-alpine")
    pg_container.start()
    redis_container.start()
    try:
        pg_url = pg_container.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        redis_url = (
            f"redis://{redis_container.get_container_host_ip()}:"
            f"{redis_container.get_exposed_port(6379)}/0"
        )
        env = {**os.environ, "PRAXIS_DB_URL": pg_url}
        # 用 sys.executable 跑 alembic 模块,避免 PATH 不含 venv/bin 的子进程问题
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            check=True,
            timeout=60,
        )

        pool = await make_pg_pool(pg_url)
        redis_client = make_redis_client(redis_url)

        @dataclass
        class _S:
            anthropic_api_key: str = "sk-test"
            anthropic_base_url: str = "https://api.anthropic.com"
            model: str = "claude-3-5-sonnet-20241022"
            max_tokens: int = 4096
            max_turns: int = 30
            recovery_budget: int = 3
            max_output_recovery: int = 2
            host: str = "0.0.0.0"
            port: int = 8001
            workers: int = 1
            max_concurrent_per_user: int = 5
            user_qps: float = 10.0
            global_llm_inflight: int = 100
            quota_global_max_queued: int = 200
            dump_prompts: str = ""
            max_heavy_jobs_per_user: int = 0
            db_url: str = ""
            redis_url: str = ""
            password_pepper: str = "integration-pepper"
            cookie_secure: bool = False
            cookie_samesite: str = "Lax"
            session_ttl_days: int = 30
            allow_self_signup: bool = True
            smtp_host: str = ""
            smtp_port: int = 0
            smtp_user: str = ""
            smtp_password: str = ""
            smtp_from: str = ""
            env_label: str = "integration"

        settings = _S()
        # 闭包变量赋值给 dataclass 字段(class body 不能直接引用闭包变量)
        settings.__dict__["db_url"] = pg_url
        settings.__dict__["redis_url"] = redis_url
        deps = AppDeps(
            settings=settings,
            store=PgStore(pool),
            api_key="sk-test",
            base_url="https://api.anthropic.com",
            repo=PgAuthRepository(pool),
            redis=redis_client,
            email_gateway=DevEmailGateway(),
        )
        app = make_app(deps)
        yield app, pool, redis_client
        await pool.close()
        await redis_client.aclose()
    finally:
        pg_container.stop()
        redis_container.stop()


@pytest.mark.asyncio
async def test_full_auth_flow_register_login_me_logout(app_with_real_backends):
    app, _, _ = app_with_real_backends
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # /api/info 白名单
        r = await client.get("/api/info")
        assert r.status_code == 200
        assert r.json()["service"] == "PRAXIS-2"

        # send-code
        r = await client.post(
            "/api/auth/email/send-code",
            json={"email": "e2e@test.com", "purpose": "register"},
        )
        assert r.status_code == 200
        code = r.json()["dev_code"]

        # register
        r = await client.post(
            "/api/auth/register",
            json={
                "email": "e2e@test.com",
                "code": code,
                "password": "e2e-strong-pw",
                "display_name": "E2E",
            },
        )
        assert r.status_code == 200
        sc = r.headers.get("set-cookie")
        assert sc and "praxis_session=" in sc
        token = sc.split("praxis_session=")[1].split(";")[0]

        # me
        r = await client.get("/api/me", headers={"Cookie": f"praxis_session={token}"})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == "e2e@test.com"

        # me/balance
        r = await client.get("/api/me/balance", headers={"Cookie": f"praxis_session={token}"})
        assert r.status_code == 200
        assert r.json() == {"balance_li": 0, "currency": "li"}

        # logout
        r = await client.post("/api/auth/logout", headers={"Cookie": f"praxis_session={token}"})
        assert r.status_code == 200

        # logout 后 me 401
        r = await client.get("/api/me", headers={"Cookie": f"praxis_session={token}"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_soft_delete_then_reregister_same_email(app_with_real_backends):
    app, _, redis_client = app_with_real_backends
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # register #1
        r = await client.post(
            "/api/auth/email/send-code",
            json={"email": "del@test.com", "purpose": "register"},
        )
        c1 = r.json()["dev_code"]
        r = await client.post(
            "/api/auth/register",
            json={
                "email": "del@test.com",
                "code": c1,
                "password": "pw12345",
                "display_name": "A",
            },
        )
        assert r.status_code == 200
        token = r.headers["set-cookie"].split("praxis_session=")[1].split(";")[0]

        # delete account(软删)
        r = await client.request(
            "DELETE",
            "/api/me/account",
            headers={"Cookie": f"praxis_session={token}"},
        )
        assert r.status_code == 200

        # register #2(同邮箱)— 软删后 partial unique 允许
        await redis_client.delete("email_throttle:del@test.com")
        r = await client.post(
            "/api/auth/email/send-code",
            json={"email": "del@test.com", "purpose": "register"},
        )
        c2 = r.json()["dev_code"]
        r = await client.post(
            "/api/auth/register",
            json={
                "email": "del@test.com",
                "code": c2,
                "password": "pw2",
                "display_name": "A2",
            },
        )
        assert r.status_code == 200, f"软删后同邮箱重注失败:{r.json()}"
