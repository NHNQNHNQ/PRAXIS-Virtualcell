"""P1.1(v0.6):LLM 决策边界安全 flag —— 三个 allow_llm_* 必须永远 False,不可配置为 True。

铁律:LLM 绝不碰 prediction / hard-rule / learned reliability 终决。这些 flag 是代码级守卫。
"""
import pytest

from praxis_virtualcell.core.config import RuntimeConfig, assert_llm_boundaries


def test_flags_default_false():
    c = RuntimeConfig()
    assert c.allow_llm_to_modify_core_decision is False
    assert c.allow_llm_to_modify_prediction is False
    assert c.allow_llm_to_override_hard_rules is False


def test_from_env_flags_false():
    c = RuntimeConfig.from_env(env_path="/nonexistent.env")
    assert c.allow_llm_to_modify_core_decision is False
    assert c.allow_llm_to_modify_prediction is False
    assert c.allow_llm_to_override_hard_rules is False


def test_assert_boundaries_passes_when_false():
    assert_llm_boundaries(RuntimeConfig())          # 不抛


@pytest.mark.parametrize("flag", [
    "allow_llm_to_modify_core_decision",
    "allow_llm_to_modify_prediction",
    "allow_llm_to_override_hard_rules",
])
def test_assert_boundaries_raises_if_any_true(flag):
    c = RuntimeConfig()
    object.__setattr__(c, flag, True)               # 强行改也要被守卫拦下
    with pytest.raises(Exception):
        assert_llm_boundaries(c)
