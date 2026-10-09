"""共享 fixture — 一次启 PG+Redis testcontainers + alembic upgrade,
所有 integration test 复用。"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from dataclasses import dataclass

import pytest
import pytest_asyncio


@dataclass
class _TestSettings:
    anthropic_api_key: str = "sk-test"
    anthropic_base_url: str = "https://api.anthropic.com"
    model: str = "deepseek-v4-pro"
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
    permission_ask_timeout_s: float = 60.0
    static_root: str = ""
    files_root: str = "/tmp/praxis2-files-test"
    files_quota_bytes: int = 100 * 1024**3
    files_max_per_file_bytes: int = 100 * 1024**2
    # M11.1 spawn 默认(覆盖 Settings dataclass 默认)
    spawn_max_concurrent_per_user: int = 2
    spawn_keep_last_per_user: int = 100
    spawn_partial_flush_chunks: int = 20
    llm_price_in_per_m_li: int = 1500
    llm_price_out_per_m_li: int = 6000
    signup_gift_li: int = 10000
    # M11.2 MD
    hpc_ssh_host: str = "10.102.106.53"
    hpc_ssh_user: str = "zkyd"
    hpc_ssh_key_path: str = "/tmp/fake-key"
    hpc_ssh_timeout_s: float = 15.0
    md_hpc_account: str = "SCW6CHB"
    md_price_gpu_per_h_li: int = 10000
    md_price_cpu_per_h_li: int = 500
    md_free_cpu_hours_per_job: float = 1.0
    md_max_concurrent_per_user: int = 2
    md_poll_interval_s: int = 30
    md_check_gpus_script_path: str = "~/check_gpus.sh"
    md_gromacs_load_cmd: str = "conda activate praxis-md-cuda"
    # M12 admin + proposals 配额
    admin_reconcile_max_users: int = 1000
    proposals_per_user_per_day: int = 20


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def app_with_real_backends():
    """启 PG+Redis containers,跑 alembic,装 ASGI app。session-scope,整个测试 session 共享一套容器。"""
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
        pg_url = pg_container.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql",
        )
        redis_url = (
            f"redis://{redis_container.get_container_host_ip()}:"
            f"{redis_container.get_exposed_port(6379)}/0"
        )
        env = {**os.environ, "PRAXIS_DB_URL": pg_url}
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env, check=True, timeout=60,
        )

        pool = await make_pg_pool(pg_url)
        redis_client = make_redis_client(redis_url)

        settings = _TestSettings()
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


@pytest_asyncio.fixture(loop_scope="session")
async def pg_pool(app_with_real_backends):
    """方便 fixture — 仅给 unit-y 测试拿 pool,不需要 app。"""
    _, pool, _ = app_with_real_backends
    yield pool


@pytest_asyncio.fixture(loop_scope="session")
async def fake_user_id(pg_pool):
    """临时建一个用户(余额 100000 li),测试结束 cascade 清空 spawn_tasks。"""
    uid = uuid.uuid4()
    async with pg_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, role, balance_li) "
            "VALUES ($1, $2, '', 'user', 100000)",
            uid, f"spawn-test-{uid}@x.x",
        )
    yield str(uid)
    async with pg_pool.acquire() as conn:
        # ledger FK 无 CASCADE,需手动先清
        await conn.execute("DELETE FROM ledger WHERE user_id=$1", uid)
        await conn.execute("DELETE FROM spawn_tasks WHERE user_id=$1", uid)
        await conn.execute("DELETE FROM users WHERE id=$1", uid)
