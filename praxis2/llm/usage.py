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

        return any(m in self._price for m in self._by_model)

    def cost_usd(self) -> float:

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

    if api_count is not None:
        try:
            return int(api_count()), False
        except Exception:  # noqa: BLE001
            pass
    blob = json.dumps(messages, ensure_ascii=False)
    if tools:
        blob += json.dumps(tools, ensure_ascii=False)
    return max(1, len(blob.encode()) // 4), True


def should_auto_compact(*, used: int, window: int, buffer: int) -> bool:

    return used >= (window - buffer)
