"""Phase 4:LLM_ORCHESTRATED 模式开关。测枚举新增不破坏、from_env 识别、make_llm_client enabled 扩展、
三 flag 仍恒 False(红线 2)、无 key 时 orchestrated 仍不 enabled(红线 1/6)。"""
import os

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.core.config import Mode, RuntimeConfig, assert_llm_boundaries


def test_new_enum_values_exist_and_are_strings():
    assert Mode.LLM_ORCHESTRATED.value == "llm_orchestrated"
    assert Mode.LLM_ORCHESTRATED_STRICT.value == "llm_orchestrated_strict"
    # 现有枚举不变
    assert Mode.OFFLINE.value == "offline"
    assert Mode.LLM_ASSISTED.value == "llm_assisted"


def test_from_env_recognizes_orchestrated(monkeypatch):
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "llm_orchestrated")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")
    c = RuntimeConfig.from_env(env_path="/nonexistent.env")
    assert c.mode is Mode.LLM_ORCHESTRATED
    assert c.llm_enabled is True         # orchestrated + key → enabled


def test_from_env_orchestrated_strict(monkeypatch):
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "llm_orchestrated_strict")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")
    c = RuntimeConfig.from_env(env_path="/nonexistent.env")
    assert c.mode is Mode.LLM_ORCHESTRATED_STRICT
    assert c.llm_enabled is True


def test_orchestrated_without_key_not_enabled(monkeypatch):
    """红线 1/6:无 key 时 orchestrated 不 enabled(client 不真调,回退)。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="")
    assert make_llm_client(c).enabled is False


def test_make_llm_client_enabled_for_orchestrated_with_key():
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="sk-fake")
    assert make_llm_client(c).enabled is True
    c2 = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED_STRICT, deepseek_api_key="sk-fake")
    assert make_llm_client(c2).enabled is True


def test_offline_still_not_enabled():
    """红线 1:OFFLINE 恒不 enabled。"""
    assert make_llm_client(RuntimeConfig(mode=Mode.OFFLINE)).enabled is False


def test_three_flags_stay_false_under_orchestrated():
    """红线 2:新模式下三 flag 仍恒 False,assert_llm_boundaries 不抛。"""
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="sk-fake")
    assert c.allow_llm_to_modify_core_decision is False
    assert c.allow_llm_to_modify_prediction is False
    assert c.allow_llm_to_override_hard_rules is False
    assert_llm_boundaries(c)             # 不抛
