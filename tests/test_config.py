"""§6⑤ Settings 单一源 + fail-fast 缺必填项。"""

import pytest

from praxis2.config import ConfigError, Settings, load_from_env


def test_settings_required_fields_no_default():
    # 必填项无默认值:缺即 TypeError(Python dataclass 强约束)
    with pytest.raises(TypeError):
        Settings()  # 全缺


def test_settings_minimal_construction_succeeds():
    # 全必填项给齐 → 构造成功
    s = Settings(
        anthropic_api_key="sk-x",
        anthropic_base_url="https://api.anthropic.com",
        model="claude-3",
        max_tokens=4096,
        max_turns=20,
        recovery_budget=3,
        max_output_recovery=2,
        host="0.0.0.0",
        port=8000,
        workers=2,
        max_concurrent_per_user=5,
        user_qps=10.0,
        global_llm_inflight=100,
        quota_global_max_queued=100,
    )
    assert s.model == "claude-3"
    assert s.workers == 2


def test_settings_optional_fields_have_zero_value_default():
    # 「零值即关闭」语义:dump_prompts="" 即关、max_heavy_jobs_per_user=0 即关 channel B
    s = Settings(
        anthropic_api_key="sk",
        anthropic_base_url="u",
        model="m",
        max_tokens=64,
        max_turns=20,
        recovery_budget=3,
        max_output_recovery=2,
        host="h",
        port=1,
        workers=1,
        max_concurrent_per_user=1,
        user_qps=1.0,
        global_llm_inflight=1,
        quota_global_max_queued=1,
    )
    assert s.dump_prompts == ""
    assert s.max_heavy_jobs_per_user == 0


def test_load_from_env_full(monkeypatch):
    # load_from_env 从 os.environ 装载;读完整必填集
    env = {
        "PRAXIS_ANTHROPIC_API_KEY": "sk-env",
        "PRAXIS_ANTHROPIC_BASE_URL": "https://up",
        "PRAXIS_MODEL": "claude-3-5-sonnet",
        "PRAXIS_MAX_TOKENS": "4096",
        "PRAXIS_MAX_TURNS": "30",
        "PRAXIS_RECOVERY_BUDGET": "3",
        "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
        "PRAXIS_HOST": "0.0.0.0",
        "PRAXIS_PORT": "8080",
        "PRAXIS_WORKERS": "4",
        "PRAXIS_MAX_CONCURRENT_PER_USER": "5",
        "PRAXIS_USER_QPS": "10.0",
        "PRAXIS_GLOBAL_LLM_INFLIGHT": "100",
        "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "200",
        # M9 新增必填(§6⑤ 校准)
        "PRAXIS_DB_URL": "postgresql://praxis2:pw@127.0.0.1:5432/praxis2",
        "PRAXIS_REDIS_URL": "redis://127.0.0.1:6379/1",
        "PRAXIS_PASSWORD_PEPPER": "test-pepper-secret",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = load_from_env()
    assert s.anthropic_api_key == "sk-env"
    assert s.model == "claude-3-5-sonnet"
    assert s.workers == 4
    assert s.user_qps == 10.0


def test_permission_ask_timeout_default(monkeypatch):
    """A.6 fixup I2:permission_ask_timeout_s 默认 60.0(§7.6.2 ASK 超时安全默认)。

    锁字段存在 + 默认值;PRAXIS_PERMISSION_ASK_TIMEOUT_S 不显式给则 60.0。
    """
    env = {
        "PRAXIS_ANTHROPIC_API_KEY": "sk",
        "PRAXIS_ANTHROPIC_BASE_URL": "u",
        "PRAXIS_MODEL": "m",
        "PRAXIS_MAX_TOKENS": "4096",
        "PRAXIS_MAX_TURNS": "20",
        "PRAXIS_RECOVERY_BUDGET": "3",
        "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
        "PRAXIS_HOST": "h",
        "PRAXIS_PORT": "8080",
        "PRAXIS_WORKERS": "1",
        "PRAXIS_MAX_CONCURRENT_PER_USER": "1",
        "PRAXIS_USER_QPS": "1.0",
        "PRAXIS_GLOBAL_LLM_INFLIGHT": "1",
        "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "1",
        "PRAXIS_DB_URL": "postgresql://x",
        "PRAXIS_REDIS_URL": "redis://x",
        "PRAXIS_PASSWORD_PEPPER": "p",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("PRAXIS_PERMISSION_ASK_TIMEOUT_S", raising=False)
    s = load_from_env()
    assert s.permission_ask_timeout_s == 60.0


def test_permission_ask_timeout_override(monkeypatch):
    """显式给 PRAXIS_PERMISSION_ASK_TIMEOUT_S → 解析为 float。"""
    env = {
        "PRAXIS_ANTHROPIC_API_KEY": "sk",
        "PRAXIS_ANTHROPIC_BASE_URL": "u",
        "PRAXIS_MODEL": "m",
        "PRAXIS_MAX_TOKENS": "4096",
        "PRAXIS_MAX_TURNS": "20",
        "PRAXIS_RECOVERY_BUDGET": "3",
        "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
        "PRAXIS_HOST": "h",
        "PRAXIS_PORT": "8080",
        "PRAXIS_WORKERS": "1",
        "PRAXIS_MAX_CONCURRENT_PER_USER": "1",
        "PRAXIS_USER_QPS": "1.0",
        "PRAXIS_GLOBAL_LLM_INFLIGHT": "1",
        "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "1",
        "PRAXIS_DB_URL": "postgresql://x",
        "PRAXIS_REDIS_URL": "redis://x",
        "PRAXIS_PASSWORD_PEPPER": "p",
        "PRAXIS_PERMISSION_ASK_TIMEOUT_S": "12.5",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = load_from_env()
    assert s.permission_ask_timeout_s == 12.5


def test_load_from_env_missing_required_raises_config_error(monkeypatch):
    # 缺必填项 → ConfigError 含 key 名(治 v1 默认值骗人)
    monkeypatch.delenv("PRAXIS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="PRAXIS_ANTHROPIC_API_KEY"):
        load_from_env()


def test_load_from_env_invalid_int_raises_config_error(monkeypatch):
    # 类型错误也 fail-fast(int 字段给非数字字符串)
    # 全字段给合法值,仅 PRAXIS_PORT 故意给非数字 → 锁定 PORT 抛错路径
    base = {
        "PRAXIS_ANTHROPIC_API_KEY": "sk",
        "PRAXIS_ANTHROPIC_BASE_URL": "u",
        "PRAXIS_MODEL": "m",
        "PRAXIS_MAX_TOKENS": "4096",
        "PRAXIS_MAX_TURNS": "20",
        "PRAXIS_RECOVERY_BUDGET": "3",
        "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
        "PRAXIS_HOST": "h",
        "PRAXIS_PORT": "not-a-port",  # ← 唯一非法值
        "PRAXIS_WORKERS": "1",
        "PRAXIS_MAX_CONCURRENT_PER_USER": "1",
        "PRAXIS_USER_QPS": "1.0",
        "PRAXIS_GLOBAL_LLM_INFLIGHT": "1",
        "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "1",
        # M9 新增必填(§6⑤ 校准)
        "PRAXIS_DB_URL": "postgresql://x",
        "PRAXIS_REDIS_URL": "redis://x",
        "PRAXIS_PASSWORD_PEPPER": "p",
    }
    for k, v in base.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ConfigError, match="PRAXIS_PORT"):
        load_from_env()


# --- v0.17 MCP client:mcp_servers_json 接入 Settings ---
# 复用本文件既有「inline 最小必填 env dict + monkeypatch.setenv + load_from_env()」风格
_MCP_MIN_ENV = {
    "PRAXIS_ANTHROPIC_API_KEY": "sk",
    "PRAXIS_ANTHROPIC_BASE_URL": "u",
    "PRAXIS_MODEL": "m",
    "PRAXIS_MAX_TOKENS": "4096",
    "PRAXIS_MAX_TURNS": "20",
    "PRAXIS_RECOVERY_BUDGET": "3",
    "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
    "PRAXIS_HOST": "h",
    "PRAXIS_PORT": "8080",
    "PRAXIS_WORKERS": "1",
    "PRAXIS_MAX_CONCURRENT_PER_USER": "1",
    "PRAXIS_USER_QPS": "1.0",
    "PRAXIS_GLOBAL_LLM_INFLIGHT": "1",
    "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "1",
    "PRAXIS_DB_URL": "postgresql://x",
    "PRAXIS_REDIS_URL": "redis://x",
    "PRAXIS_PASSWORD_PEPPER": "p",
}


def test_mcp_servers_json_defaults_empty(monkeypatch):
    """不配 PRAXIS_MCP_SERVERS_JSON → 默认空串(零值即关)。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("PRAXIS_MCP_SERVERS_JSON", raising=False)
    s = load_from_env()
    assert s.mcp_servers_json == ""


def test_mcp_servers_json_loaded(monkeypatch):
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv(
        "PRAXIS_MCP_SERVERS_JSON",
        '[{"name":"echo","command":"python","args":[]}]',
    )
    s = load_from_env()
    assert "echo" in s.mcp_servers_json


def test_mcp_servers_json_in_known_keys():
    """PRAXIS_MCP_SERVERS_JSON 在白名单(否则 load_from_env 会 fail-fast 拒)。"""
    from praxis2.config import _KNOWN_KEYS
    assert "PRAXIS_MCP_SERVERS_JSON" in _KNOWN_KEYS


def test_bash_tool_enabled_defaults_false(monkeypatch):
    """不配 PRAXIS_BASH_TOOL_ENABLED → 默认关(软沙盒 opt-in)。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("PRAXIS_BASH_TOOL_ENABLED", raising=False)
    s = load_from_env()
    assert s.bash_tool_enabled is False


def test_bash_tool_enabled_loaded(monkeypatch):
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("PRAXIS_BASH_TOOL_ENABLED", "true")
    s = load_from_env()
    assert s.bash_tool_enabled is True


def test_bash_tool_enabled_in_known_keys():
    """PRAXIS_BASH_TOOL_ENABLED 在白名单(否则 load_from_env 会 fail-fast 拒)。"""
    from praxis2.config import _KNOWN_KEYS
    assert "PRAXIS_BASH_TOOL_ENABLED" in _KNOWN_KEYS


# --- v0.18 子项目1:bash_isolation + bash_isolation_mask 配置 ---

def test_bash_isolation_defaults_false(monkeypatch):
    """不配 PRAXIS_BASH_ISOLATION → 默认关(真隔离 opt-in)。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("PRAXIS_BASH_ISOLATION", raising=False)
    monkeypatch.delenv("PRAXIS_BASH_ISOLATION_MASK", raising=False)
    s = load_from_env()
    assert s.bash_isolation is False
    assert s.bash_isolation_mask == ""


def test_bash_isolation_from_env(monkeypatch):
    """PRAXIS_BASH_ISOLATION=true + PRAXIS_BASH_ISOLATION_MASK → 正确读入。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("PRAXIS_BASH_ISOLATION", "true")
    monkeypatch.setenv("PRAXIS_BASH_ISOLATION_MASK", "/home/zkyd/secret,/etc/foo")
    s = load_from_env()
    assert s.bash_isolation is True
    assert s.bash_isolation_mask == "/home/zkyd/secret,/etc/foo"


def test_bash_isolation_in_known_keys():
    """两个新 key 都在白名单(否则 load_from_env 会 fail-fast 拒)。"""
    from praxis2.config import _KNOWN_KEYS
    assert "PRAXIS_BASH_ISOLATION" in _KNOWN_KEYS
    assert "PRAXIS_BASH_ISOLATION_MASK" in _KNOWN_KEYS


# --- v0.18 子项目2:bash_cgroup + bash_cgroup_mem_mb + bash_cgroup_cpu_pct 配置 ---

def test_bash_cgroup_defaults(monkeypatch):
    """不配三个 cgroup key → 使用默认值(cgroup 默认关,mem=1024,cpu=100)。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    for k in ("PRAXIS_BASH_CGROUP", "PRAXIS_BASH_CGROUP_MEM_MB", "PRAXIS_BASH_CGROUP_CPU_PCT"):
        monkeypatch.delenv(k, raising=False)
    s = load_from_env()
    assert s.bash_cgroup is False
    assert s.bash_cgroup_mem_mb == 1024
    assert s.bash_cgroup_cpu_pct == 100


def test_bash_cgroup_from_env(monkeypatch):
    """PRAXIS_BASH_CGROUP=true + MEM_MB/CPU_PCT 自定义 → 正确读入。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("PRAXIS_BASH_CGROUP", "true")
    monkeypatch.setenv("PRAXIS_BASH_CGROUP_MEM_MB", "512")
    monkeypatch.setenv("PRAXIS_BASH_CGROUP_CPU_PCT", "200")
    s = load_from_env()
    assert s.bash_cgroup is True
    assert s.bash_cgroup_mem_mb == 512
    assert s.bash_cgroup_cpu_pct == 200


def test_bash_cgroup_in_known_keys():
    """三个新 key 都在白名单(否则 load_from_env 会 fail-fast 拒)。"""
    from praxis2.config import _KNOWN_KEYS
    assert "PRAXIS_BASH_CGROUP" in _KNOWN_KEYS
    assert "PRAXIS_BASH_CGROUP_MEM_MB" in _KNOWN_KEYS
    assert "PRAXIS_BASH_CGROUP_CPU_PCT" in _KNOWN_KEYS


# --- v0.18 子项目3:bash_netns 网络隔离配置 ---

def test_bash_netns_default(monkeypatch):
    """不配 PRAXIS_BASH_NETNS → 默认关(网络隔离 opt-in)。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("PRAXIS_BASH_NETNS", raising=False)
    s = load_from_env()
    assert s.bash_netns is False


def test_bash_netns_from_env(monkeypatch):
    """PRAXIS_BASH_NETNS=true → 正确读入。"""
    for k, v in _MCP_MIN_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("PRAXIS_BASH_NETNS", "true")
    s = load_from_env()
    assert s.bash_netns is True


def test_bash_netns_in_known_keys():
    """PRAXIS_BASH_NETNS 在白名单(否则 load_from_env 会 fail-fast 拒)。"""
    from praxis2.config import _KNOWN_KEYS
    assert "PRAXIS_BASH_NETNS" in _KNOWN_KEYS
