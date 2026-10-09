"""v2.0.1 — 本地 dev 单进程启动:in-memory store + fakeredis + DevEmailGateway。

无需 docker PG/Redis,无需真 Anthropic key 也能起(chat 会 5xx 但 /api/agents
/api/info / 注册登录链路都走通,够 FE 开起来核对 UI)。

跑法:
    uvicorn --factory scripts.dev_server:make_dev_app --host 127.0.0.1 --port 8001
或直接:
    python scripts/dev_server.py
"""

from __future__ import annotations

import os

import fakeredis.aioredis

from praxis2.auth.email import DevEmailGateway
from praxis2.auth.repository import FakeAuthRepository
from praxis2.server.app import AppDeps, make_app
from praxis2.store.memory import InMemoryStore


class _DevSettings:
    anthropic_api_key = os.environ.get("PRAXIS_ANTHROPIC_API_KEY", "sk-dev")
    anthropic_base_url = os.environ.get(
        "PRAXIS_ANTHROPIC_BASE_URL", "https://api.anthropic.com"
    )
    model = os.environ.get("PRAXIS_MODEL", "AWS-GPT-5.4")
    max_tokens = 1024
    max_turns = 20
    recovery_budget = 3
    max_output_recovery = 2
    host = "127.0.0.1"
    port = 8001
    workers = 1
    max_concurrent_per_user = 2
    user_qps = 1000.0
    global_llm_inflight = 100
    quota_global_max_queued = 200
    dump_prompts = ""
    max_heavy_jobs_per_user = 0
    permission_ask_timeout_s = 60.0
    db_url = ""
    redis_url = ""
    password_pepper = "dev-pepper-only"
    cookie_secure = False
    cookie_samesite = "Lax"
    session_ttl_days = 30
    allow_self_signup = True
    smtp_host = ""
    smtp_port = 0
    smtp_user = ""
    smtp_password = ""
    smtp_from = ""
    env_label = "dev"
    # vite dev 端口默认 5173;也加 4173 (preview)
    allowed_origins = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:4173,http://localhost:4173"
    )
    static_root = ""


def make_dev_app():
    deps = AppDeps(
        settings=_DevSettings(),
        store=InMemoryStore(),
        api_key=_DevSettings.anthropic_api_key,
        base_url=_DevSettings.anthropic_base_url,
        repo=FakeAuthRepository(),
        redis=fakeredis.aioredis.FakeRedis(decode_responses=True),
        email_gateway=DevEmailGateway(),
    )
    return make_app(deps)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "scripts.dev_server:make_dev_app",
        host="127.0.0.1",
        port=8001,
        factory=True,
        reload=False,
    )
