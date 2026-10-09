"""Tests for llm boundary flags."""
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
    assert_llm_boundaries(RuntimeConfig())


@pytest.mark.parametrize("flag", [
    "allow_llm_to_modify_core_decision",
    "allow_llm_to_modify_prediction",
    "allow_llm_to_override_hard_rules",
])
def test_assert_boundaries_raises_if_any_true(flag):
    c = RuntimeConfig()
    object.__setattr__(c, flag, True)
    with pytest.raises(Exception):  # noqa: B017
        assert_llm_boundaries(c)
