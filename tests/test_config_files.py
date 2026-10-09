"""M10 config:PRAXIS_FILES_ROOT + QUOTA_BYTES + MAX_PER_FILE_BYTES。"""
from __future__ import annotations

from praxis2.config import Settings, load_from_env


def test_default_files_root():
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
    assert s.files_root == "/home/zkyd/data1/praxis2-files"


def test_default_files_quota_100gb():
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
    assert s.files_quota_bytes == 100 * 1024**3  # 107374182400


def test_default_files_max_per_file_20gb():
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
    assert s.files_max_per_file_bytes == 20 * 1024**3  # 21474836480


def test_env_override_files_root(monkeypatch):
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
    monkeypatch.setenv("PRAXIS_FILES_ROOT", "/tmp/custom")
    s = load_from_env()
    assert s.files_root == "/tmp/custom"


def test_env_override_quota(monkeypatch):
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
    monkeypatch.setenv("PRAXIS_FILES_QUOTA_BYTES", "1073741824")  # 1 GB
    s = load_from_env()
    assert s.files_quota_bytes == 1073741824


def test_default_model_is_deepseek_v4_pro():
    """M10.5:默认模型改为 deepseek-v4-pro。"""
    from praxis2.config import Settings
    s = Settings(
        password_pepper="x",
        smtp_host="",
        # 必填字段给最小化值
        anthropic_api_key="key",
        anthropic_base_url="url",
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
    assert s.model == "deepseek-v4-pro"
