"""统一 LLM 接口。Week 2 只实现 disabled / mock;真 OpenAI/Anthropic 留 W3。
无 key 时 enabled=False,complete() 返回 {disabled: True} 不抛 — 保证 offline 永不依赖 API。"""
from __future__ import annotations

from typing import Any

from praxis_virtualcell.core.config import Mode, RuntimeConfig


class LLMClient:
    def __init__(self, *, enabled: bool, backend: str = "disabled") -> None:
        self.enabled = enabled
        self.backend = backend

    def complete(self, messages: list[dict], schema: dict | None = None) -> dict[str, Any]:
        if not self.enabled:
            return {"disabled": True, "content": None}
        # W3 接真 backend;Week 2 mock:回显
        return {"disabled": False, "content": {"echo": messages[-1].get("content")}}


def make_llm_client(config: RuntimeConfig) -> LLMClient:
    enabled = config.mode is Mode.LLM_ASSISTED and config.llm_enabled
    return LLMClient(enabled=enabled, backend="mock" if enabled else "disabled")
