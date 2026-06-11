"""M9 config 扩字段单元测试(§6⑤ fail-fast)。"""

from __future__ import annotations

import dataclasses

import pytest

from praxis2.config import ConfigError, Settings, load_from_env

# M8 基线必填(沿用 M0-M8 已有,本测试仅覆盖 M9 新增)
_M8_BASE = {
    "PRAXIS_ANTHROPIC_API_KEY": "sk-test",
    "PRAXIS_ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "PRAXIS_MODEL": "claude-3-5-sonnet-20241022",
    "PRAXIS_MAX_TOKENS": "4096",
    "PRAXIS_MAX_TURNS": "30",
    "PRAXIS_RECOVERY_BUDGET": "3",
    "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
    "PRAXIS_HOST": "0.0.0.0",
    "PRAXIS_PORT": "8001",
    "PRAXIS_WORKERS": "2",
    "PRAXIS_MAX_CONCURRENT_PER_USER": "5",
    "PRAXIS_USER_QPS": "10.0",
    "PRAXIS_GLOBAL_LLM_INFLIGHT": "100",
    "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "200",
}

_M9_NEW_REQUIRED = {
    "PRAXIS_DB_URL": "postgresql://praxis2:pw@127.0.0.1:5432/praxis2",
    "PRAXIS_REDIS_URL": "redis://127.0.0.1:6379/1",
    "PRAXIS_PASSWORD_PEPPER": "test-pepper-secret",
}


def test_m9_required_db_url_fail_fast():
    env = {**_M8_BASE, **_M9_NEW_REQUIRED}
    env.pop("PRAXIS_DB_URL")
    with pytest.raises(ConfigError, match="PRAXIS_DB_URL"):
        load_from_env(env)


def test_m9_required_redis_url_fail_fast():
    env = {**_M8_BASE, **_M9_NEW_REQUIRED}
    env.pop("PRAXIS_REDIS_URL")
    with pytest.raises(ConfigError, match="PRAXIS_REDIS_URL"):
        load_from_env(env)


def test_m9_required_password_pepper_fail_fast():
    env = {**_M8_BASE, **_M9_NEW_REQUIRED}
    env.pop("PRAXIS_PASSWORD_PEPPER")
    with pytest.raises(ConfigError, match="PRAXIS_PASSWORD_PEPPER"):
        load_from_env(env)


def test_m9_optional_defaults_when_missing():
    s = load_from_env({**_M8_BASE, **_M9_NEW_REQUIRED})
    assert s.cookie_secure is False
    assert s.cookie_samesite == "Lax"
    assert s.session_ttl_days == 30
    assert s.allow_self_signup is True
    assert s.smtp_host == ""
    assert s.smtp_port == 0
    assert s.smtp_user == ""
    assert s.smtp_password == ""
    assert s.smtp_from == ""
    assert s.env_label == "dev"


def test_m9_optional_overridable():
    env = {
        **_M8_BASE,
        **_M9_NEW_REQUIRED,
        "PRAXIS_COOKIE_SECURE": "true",
        "PRAXIS_COOKIE_SAMESITE": "Strict",
        "PRAXIS_SESSION_TTL_DAYS": "7",
        "PRAXIS_ALLOW_SELF_SIGNUP": "false",
        "PRAXIS_SMTP_HOST": "smtp.example.com",
        "PRAXIS_SMTP_PORT": "465",
        "PRAXIS_SMTP_USER": "admin@example.com",
        "PRAXIS_SMTP_PASSWORD": "smtp-pw",
        "PRAXIS_SMTP_FROM": "PRAXIS <admin@example.com>",
        "PRAXIS_ENV_LABEL": "staging",
    }
    s = load_from_env(env)
    assert s.cookie_secure is True
    assert s.cookie_samesite == "Strict"
    assert s.session_ttl_days == 7
    assert s.allow_self_signup is False
    assert s.smtp_host == "smtp.example.com"
    assert s.smtp_port == 465
    assert s.smtp_user == "admin@example.com"
    assert s.smtp_password == "smtp-pw"
    assert s.smtp_from == "PRAXIS <admin@example.com>"
    assert s.env_label == "staging"


def test_settings_post_init_rejects_prod_without_smtp():
    """§6⑤ fail-fast:Settings(env_label='prod', smtp_host='') 构造即崩(boot 时崩,
    不允许 lazy 到首次发邮件才崩)。"""
    env = {**_M8_BASE, **_M9_NEW_REQUIRED, "PRAXIS_ENV_LABEL": "prod"}
    with pytest.raises(ConfigError, match="prod.*PRAXIS_SMTP_HOST"):
        load_from_env(env)


def test_settings_prod_with_smtp_host_ok():
    """prod + 有 smtp_host → 构造成功(正常路径)。"""
    env = {
        **_M8_BASE,
        **_M9_NEW_REQUIRED,
        "PRAXIS_ENV_LABEL": "prod",
        "PRAXIS_SMTP_HOST": "smtp.example.com",
        "PRAXIS_SMTP_PORT": "465",
        "PRAXIS_SMTP_USER": "admin@example.com",
        "PRAXIS_SMTP_PASSWORD": "pw",
        "PRAXIS_SMTP_FROM": "noreply@example.com",
    }
    s = load_from_env(env)
    assert s.env_label == "prod"
    assert s.smtp_host == "smtp.example.com"


def test_settings_dataclass_has_m9_fields():
    fields = {f.name for f in dataclasses.fields(Settings)}
    for required in {"db_url", "redis_url", "password_pepper"}:
        assert required in fields, f"Settings 缺必填 {required}"
    for optional in {
        "cookie_secure",
        "cookie_samesite",
        "session_ttl_days",
        "allow_self_signup",
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "smtp_from",
        "env_label",
    }:
        assert optional in fields, f"Settings 缺可选 {optional}"
