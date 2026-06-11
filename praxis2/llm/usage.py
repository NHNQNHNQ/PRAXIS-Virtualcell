"""用量追踪 + token 估算(总纲 §7.4.7)。缺它会导致 compact 盲目 + PTL 连锁。"""

import json
from collections.abc import Callable
from typing import Any

_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


class UsageTracker:
    def __init__(self, price_per_mtok: dict[str, tuple[float, float]] | None = None):
        # model -> (USD/1M input, USD/1M output)
        self._price = price_per_mtok or {}
        self._by_model: dict[str, dict[str, int]] = {}

    def add(self, model: str, usage: dict[str, Any]) -> None:
        acc = self._by_model.setdefault(model, dict.fromkeys(_KEYS, 0))
        for k in _KEYS:
            acc[k] += int(usage.get(k, 0) or 0)

    def total(self) -> dict[str, int]:
        out = dict.fromkeys(_KEYS, 0)
        for acc in self._by_model.values():
            for k in _KEYS:
                out[k] += acc[k]
        return out

    def cost_is_known(self) -> bool:
        # 语义:**至少一个**已用模型有价即 True。混用有价/无价模型时
        # cost_usd() 会静默跳过无价模型 → 返回值是"不完整真实成本";
        # M1+ failover 混模型时勿据此做完整成本判断(需更严格则改 all())。
        return any(m in self._price for m in self._by_model)

    def cost_usd(self) -> float:
        # M0 简化:仅按 input/output 计价;cache_read(Anthropic ~0.1x)与
        # cache_creation(~1.25x)有独立价位,暂未接入——M1+ 接真实计价时
        # 必须扩展此方法,否则成本会偏低且难定位根因。
        cost = 0.0
        for model, acc in self._by_model.items():
            if model not in self._price:
                continue
            pin, pout = self._price[model]
            cost += acc["input_tokens"] / 1e6 * pin
            cost += acc["output_tokens"] / 1e6 * pout
        return cost


def estimate_tokens(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    api_count: Callable[[], int] | None,
) -> tuple[int, bool]:
    """优先用 API count_tokens;不可用则降级粗估(~4 字节/token)。
    返回 (tokens, is_estimate)。"""
    if api_count is not None:
        try:
            return int(api_count()), False
        except Exception:  # noqa: BLE001 - 降级粗估
            pass
    blob = json.dumps(messages, ensure_ascii=False)
    if tools:
        blob += json.dumps(tools, ensure_ascii=False)
    return max(1, len(blob.encode()) // 4), True


def should_auto_compact(*, used: int, window: int, buffer: int) -> bool:
    """已用 token 逼近上下文窗口(留 buffer)即触发(总纲 §7.4.5 触发条件之一)。

    调用方需保证 buffer < window;buffer >= window 时阈值为负,任意 used 均触发
    (有意语义:配置错误下宁可频繁 compact 也不越界)。
    """
    return used >= (window - buffer)
