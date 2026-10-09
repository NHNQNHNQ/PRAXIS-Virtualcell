import os

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env


def _cfg():
    load_env()
    return RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""))


@pytest.mark.llm
def test_deepseek_real_completion_roundtrip():
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(_cfg())
    assert client.enabled is True
    res = client.complete([{"role": "user", "content": "reply with exactly: pong"}], max_tokens=5)
    assert res["disabled"] is False
    assert res.get("error") is None, res
    assert "pong" in (res["content"] or "").lower()


@pytest.mark.llm
def test_deepseek_json_mode_returns_parseable():
    import json

    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(_cfg())
    res = client.complete(
        [{"role": "system", "content": "Output JSON only"},
         {"role": "user", "content": 'Return {"ok": true}'}], json_mode=True)
    assert json.loads(res["content"])["ok"] is True
