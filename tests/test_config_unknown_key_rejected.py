"""C.1(reviewer M0/M8 C1):load_from_env 拒未知 PRAXIS_* key,§6⑤ fail-fast。

防 typo 如 PRAXIS_WROKERS=4 静默吞掉用默认值。`_KNOWN_KEYS` 白名单显式列举所有
合法 key;`PRAXIS_CFG_TEST_*` 前缀旁路给测试覆盖用。"""

import pytest

from praxis2.config import ConfigError, load_from_env


def _base_env() -> dict:
    """构造 minimal 通过 load_from_env 的 env 字典(沿用 tests/test_config.py 体例)。"""
    return {
        "PRAXIS_ANTHROPIC_API_KEY": "sk",
        "PRAXIS_ANTHROPIC_BASE_URL": "https://up",
        "PRAXIS_MODEL": "m",
        "PRAXIS_MAX_TOKENS": "64",
        "PRAXIS_MAX_TURNS": "20",
        "PRAXIS_RECOVERY_BUDGET": "3",
        "PRAXIS_MAX_OUTPUT_RECOVERY": "2",
        "PRAXIS_HOST": "0.0.0.0",
        "PRAXIS_PORT": "8001",
        "PRAXIS_WORKERS": "1",
        "PRAXIS_MAX_CONCURRENT_PER_USER": "2",
        "PRAXIS_USER_QPS": "1000.0",
        "PRAXIS_GLOBAL_LLM_INFLIGHT": "100",
        "PRAXIS_QUOTA_GLOBAL_MAX_QUEUED": "200",
        "PRAXIS_DB_URL": "postgresql://x",
        "PRAXIS_REDIS_URL": "redis://x",
        "PRAXIS_PASSWORD_PEPPER": "p",
    }


def test_unknown_praxis_key_raises():
    """typo 形如 PRAXIS_WROKERS 应被拒,不静默用默认值。"""
    env = _base_env() | {"PRAXIS_WROKERS": "4"}
    with pytest.raises(ConfigError, match="未知配置"):
        load_from_env(env)


def test_unknown_non_praxis_key_ignored():
    """非 PRAXIS_ 前缀键(如 PATH/HOME)忽略,不影响。"""
    env = _base_env() | {"PATH": "/usr/bin", "HOME": "/root"}
    cfg = load_from_env(env)
    assert cfg.workers == 1


def test_praxis_cfg_test_prefix_bypass():
    """PRAXIS_CFG_TEST_* 旁路前缀放行(测试覆盖用,不影响 fail-fast 主路径)。"""
    env = _base_env() | {"PRAXIS_CFG_TEST_FOO": "bar"}
    cfg = load_from_env(env)
    assert cfg.workers == 1


def test_unknown_keys_sorted_in_error():
    """多 unknown key 错误消息应稳定排序(便于 grep / CI 比对)。"""
    env = _base_env() | {"PRAXIS_ZZZ": "1", "PRAXIS_AAA": "2"}
    with pytest.raises(ConfigError) as exc:
        load_from_env(env)
    msg = str(exc.value)
    # AAA 应在 ZZZ 之前(sorted)
    assert msg.index("PRAXIS_AAA") < msg.index("PRAXIS_ZZZ")
