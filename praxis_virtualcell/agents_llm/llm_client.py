"""DeepSeek client using httpx and the OpenAI-compatible /chat/completions API. No OpenAI/Anthropic SDK is
required. Missing credentials disable the client; complete() returns an error record rather than raising on
provider failures.
"""
from __future__ import annotations

from typing import Any

import httpx

from praxis_virtualcell.core.config import LLM_MODES, RuntimeConfig


class LLMClient:
    def __init__(self, *, enabled: bool, api_key: str = "",
                 base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-chat", timeout: float = 60.0) -> None:
        self.enabled = enabled
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, messages: list[dict], *, json_mode: bool = False,
                 max_tokens: int = 1024) -> dict[str, Any]:
        if not self.enabled:
            return {"disabled": True, "content": None, "error": None}
        body: dict[str, Any] = {"model": self.model, "messages": messages,
                                "temperature": 0, "max_tokens": max_tokens}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json=body, timeout=self.timeout)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return {"disabled": False, "content": content, "error": None}
        except Exception as e:
            return {"disabled": False, "content": None, "error": str(e)}


def make_llm_client(config: RuntimeConfig) -> LLMClient:

    enabled = config.mode in LLM_MODES and bool(config.deepseek_api_key)
    return LLMClient(enabled=enabled, api_key=config.deepseek_api_key,
                     base_url=config.deepseek_base_url, model=config.deepseek_model)
