"""M9 config:PRAXIS_SIGNUP_GIFT_LI 默认 10000(=100元)"""
from __future__ import annotations

from praxis2.config import Settings, load_from_env


def test_default_signup_gift_li_is_10000():
    s = Settings(
        password_pepper="x",
        smtp_host="",
        # 必填字段给最小化值
        anthropic_api_key="key",
        anthropic_base_url="url",
        model="model",
        max_tokens=1,
        max_turns=1,
        recovery_budget=1,
        max_output_recovery=1,
        host="localhost",
        port=8000,
        workers=1,
        max_concurrent_per_user=1,
        user_qps=1.0,
        global_llm_inflight=1,
        quota_global_max_queued=1,
        db_url="",
        redis_url="",
    )
    assert s.signup_gift_li == 10000


def test_env_override_sets_value(monkeypatch):
    monkeypatch.setenv("PRAXIS_ANTHROPIC_API_KEY", "key")
    monkeypatch.setenv("PRAXIS_ANTHROPIC_BASE_URL", "url")
    monkeypatch.setenv("PRAXIS_MODEL", "model")
    monkeypatch.setenv("PRAXIS_MAX_TOKENS", "1")
    monkeypatch.setenv("PRAXIS_MAX_TURNS", "1")
    monkeypatch.setenv("PRAXIS_RECOVERY_BUDGET", "1")
    monkeypatch.setenv("PRAXIS_MAX_OUTPUT_RECOVERY", "1")
    monkeypatch.setenv("PRAXIS_HOST", "localhost")
    monkeypatch.setenv("PRAXIS_PORT", "8000")
    monkeypatch.setenv("PRAXIS_WORKERS", "1")
    monkeypatch.setenv("PRAXIS_MAX_CONCURRENT_PER_USER", "1")
    monkeypatch.setenv("PRAXIS_USER_QPS", "1.0")
    monkeypatch.setenv("PRAXIS_GLOBAL_LLM_INFLIGHT", "1")
    monkeypatch.setenv("PRAXIS_QUOTA_GLOBAL_MAX_QUEUED", "1")
    monkeypatch.setenv("PRAXIS_DB_URL", "db")
    monkeypatch.setenv("PRAXIS_REDIS_URL", "redis")
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "x")
    monkeypatch.setenv("PRAXIS_SIGNUP_GIFT_LI", "20000")
    s = load_from_env()
    assert s.signup_gift_li == 20000


def test_env_0_means_no_gift(monkeypatch):
    monkeypatch.setenv("PRAXIS_ANTHROPIC_API_KEY", "key")
    monkeypatch.setenv("PRAXIS_ANTHROPIC_BASE_URL", "url")
    monkeypatch.setenv("PRAXIS_MODEL", "model")
    monkeypatch.setenv("PRAXIS_MAX_TOKENS", "1")
    monkeypatch.setenv("PRAXIS_MAX_TURNS", "1")
    monkeypatch.setenv("PRAXIS_RECOVERY_BUDGET", "1")
    monkeypatch.setenv("PRAXIS_MAX_OUTPUT_RECOVERY", "1")
    monkeypatch.setenv("PRAXIS_HOST", "localhost")
    monkeypatch.setenv("PRAXIS_PORT", "8000")
    monkeypatch.setenv("PRAXIS_WORKERS", "1")
    monkeypatch.setenv("PRAXIS_MAX_CONCURRENT_PER_USER", "1")
    monkeypatch.setenv("PRAXIS_USER_QPS", "1.0")
    monkeypatch.setenv("PRAXIS_GLOBAL_LLM_INFLIGHT", "1")
    monkeypatch.setenv("PRAXIS_QUOTA_GLOBAL_MAX_QUEUED", "1")
    monkeypatch.setenv("PRAXIS_DB_URL", "db")
    monkeypatch.setenv("PRAXIS_REDIS_URL", "redis")
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "x")
    monkeypatch.setenv("PRAXIS_SIGNUP_GIFT_LI", "0")
    s = load_from_env()
    assert s.signup_gift_li == 0
