import os

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env


def test_load_env_injects_without_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("FOO_K1=v1\n# comment\nFOO_K2=v2\n", encoding="utf-8")
    monkeypatch.delenv("FOO_K1", raising=False)
    monkeypatch.setenv("FOO_K2", "preset")
    load_env(str(env))
    assert os.environ["FOO_K1"] == "v1"
    assert os.environ["FOO_K2"] == "preset"


def test_config_has_deepseek_fields_defaults():
    cfg = RuntimeConfig()
    assert cfg.deepseek_base_url == "https://api.deepseek.com"
    assert cfg.deepseek_model == "deepseek-chat"
    assert cfg.deepseek_api_key == ""


def test_make_llm_client_disabled_without_key():
    assert make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED)).enabled is False
    assert make_llm_client(RuntimeConfig(mode=Mode.OFFLINE)).enabled is False
