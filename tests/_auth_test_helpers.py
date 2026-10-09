"""M9 共享测试辅助:统一构 AppDeps + 预置 session,给 M6/M7 既有测试用。

cookie session 来源 = `AuthMiddleware(_App, redis)` 解出 scope["user"];测试方式:
1. `make_test_app_deps(...)`  → AppDeps 含 FakeAuthRepository + fakeredis + DevEmailGateway
2. `await preseed_session(deps, user_id, ...)` → 返回 cookie 头值
3. httpx 请求带 `headers={"Cookie": cookie}` 即可命中 scope["user"]
"""

from __future__ import annotations

from dataclasses import dataclass

import fakeredis.aioredis

from praxis2.auth.email import DevEmailGateway
from praxis2.auth.repository import FakeAuthRepository
from praxis2.server.app import AppDeps
from praxis2.store.memory import InMemoryStore
from praxis2.store.redis import auth_session_set


@dataclass
class _TestSettings:
    """M9 默认测试 settings:含 M0-M8 既有字段 + M9 新增 8 字段。"""

    anthropic_api_key: str = "sk"
    anthropic_base_url: str = "https://up.example"
    model: str = "m"
    max_tokens: int = 64
    max_turns: int = 20
    recovery_budget: int = 3
    max_output_recovery: int = 2
    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1
    max_concurrent_per_user: int = 2
    user_qps: float = 1000.0
    global_llm_inflight: int = 100
    quota_global_max_queued: int = 200
    dump_prompts: str = ""
    max_heavy_jobs_per_user: int = 0
    permission_ask_timeout_s: float = 60.0
    db_url: str = ""
    redis_url: str = ""
    password_pepper: str = "test-pepper"
    cookie_secure: bool = False
    cookie_samesite: str = "Lax"
    session_ttl_days: int = 30
    allow_self_signup: bool = True
    smtp_host: str = ""
    smtp_port: int = 0
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    signup_gift_li: int = 10000
    env_label: str = "dev"
    allowed_origins: str = ""
    static_root: str = ""
    files_root: str = "/tmp/praxis2-test-files"
    files_quota_bytes: int = 100 * 1024**3
    files_max_per_file_bytes: int = 20 * 1024**3
    # M11.1 spawn
    spawn_max_concurrent_per_user: int = 2
    spawn_keep_last_per_user: int = 100
    spawn_partial_flush_chunks: int = 20
    llm_price_in_per_m_li: int = 1500
    llm_price_out_per_m_li: int = 6000
    # M11.2 MD + HPC SSH
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
    # M12 admin v2 + proposals
    admin_reconcile_max_users: int = 1000
    proposals_per_user_per_day: int = 20
    # v0.17 子项目2 + v0.18 子项目1:BashTool
    bash_tool_enabled: bool = False
    bash_isolation: bool = False
    bash_isolation_mask: str = ""
    # v0.18 子项目2:cgroup 资源隔离(fail-open)
    bash_cgroup: bool = False
    bash_cgroup_mem_mb: int = 1024
    bash_cgroup_cpu_pct: int = 100
    # v0.18 子项目3:网络隔离(fail-closed)
    bash_netns: bool = False


def make_test_app_deps(*, store=None, settings=None) -> AppDeps:
    """构造测试 AppDeps:store 可注入,默认 InMemoryStore + FakeAuthRepo + fakeredis。"""
    return AppDeps(
        settings=settings or _TestSettings(),
        store=store or InMemoryStore(),
        api_key="sk",
        base_url="https://up.example",
        repo=FakeAuthRepository(),
        redis=fakeredis.aioredis.FakeRedis(decode_responses=True),
        email_gateway=DevEmailGateway(),
    )


async def preseed_session(
    deps: AppDeps,
    *,
    user_id: str = "u1",
    email: str = "u1@t.com",
    role: str = "user",
    ttl_s: int = 3600,
) -> str:
    """在 deps.redis 预置一个 valid session,返回 Cookie 头值。"""
    token = f"test-token-{user_id}"
    await auth_session_set(
        deps.redis,
        token,
        {"user_id": user_id, "email": email, "role": role},
        ttl_s=ttl_s,
        pepper=deps.settings.password_pepper,
    )
    return f"praxis_session={token}"


async def make_admin_user_in_db(
    pg_pool, balance_li: int = 0,
) -> tuple[str, str, str]:
    """直接 PG insert 一个 admin user;绕过 register flow。返 (user_id, email, password)。

    pepper 必须跟 tests/integration/conftest.py 的 _TestSettings.password_pepper
    一致 ("integration-pepper"),否则 login verify 会挂。
    """
    import uuid

    from praxis2.auth.service import hash_password

    email = f"admin-{uuid.uuid4().hex[:8]}@test.local"
    password = "AdminTest12345!"
    pw_hash = hash_password(password, pepper="integration-pepper")
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash, display_name, role, balance_li) "
            "VALUES ($1, $2, $3, 'admin', $4) RETURNING id",
            email, pw_hash, "Test Admin", balance_li,
        )
    return str(row["id"]), email, password


async def make_normal_user_in_db(
    pg_pool, balance_li: int = 0,
) -> tuple[str, str, str]:
    """跟 make_admin_user_in_db 但 role='user'。"""
    import uuid

    from praxis2.auth.service import hash_password

    email = f"user-{uuid.uuid4().hex[:8]}@test.local"
    password = "UserTest12345!"
    pw_hash = hash_password(password, pepper="integration-pepper")
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash, display_name, role, balance_li) "
            "VALUES ($1, $2, $3, 'user', $4) RETURNING id",
            email, pw_hash, "Test User", balance_li,
        )
    return str(row["id"]), email, password
