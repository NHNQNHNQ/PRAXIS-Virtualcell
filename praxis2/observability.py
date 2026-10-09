from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftAlert:
    drifted: bool
    metric: float
    message: str = ""


class DriftMonitor:
    def __init__(self, *, threshold: float) -> None:
        self._threshold = threshold
        self._counts: dict[str, dict[str, int]] = {}

    def record(self, category: str, outcome: str) -> None:
        self._counts.setdefault(category, {})
        self._counts[category][outcome] = self._counts[category].get(outcome, 0) + 1

    def distribution(self, category: str) -> dict[str, float]:
        c = self._counts.get(category, {})
        total = sum(c.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in c.items()}

    def check_drift(self, category: str, *, baseline: dict[str, float]) -> DriftAlert:
        cur = self.distribution(category)
        keys = set(cur) | set(baseline)

        tv = 0.5 * sum(abs(cur.get(k, 0.0) - baseline.get(k, 0.0)) for k in keys)
        drifted = tv > self._threshold
        msg = (
            (
                "Output distribution drift: category "
                f"{category!r}"
                "shift "
                f"{tv:.3f}"
                "> threshold "
                f"{self._threshold}"
                "(review tool descriptions, prompts, and schema c"
                "onstraints)"
            )
            if drifted
            else ""
        )
        return DriftAlert(drifted=drifted, metric=tv, message=msg)


@dataclass
class ObservabilitySnapshot:
    prompt_hash: str
    dump_path: str
    chain_id: str
    depth: int
    tokens: dict[str, int]
    cost_usd: float
    cost_is_known: bool
    cache_read_tokens: int
    agent_route: dict[str, Any] = field(default_factory=dict)
    env_choice: dict[str, Any] = field(default_factory=dict)
    review_audit: list[dict] = field(default_factory=list)
    drift: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "prompt_hash": self.prompt_hash,
            "dump_path": self.dump_path,
            "chain_id": self.chain_id,
            "depth": self.depth,
            "tokens": self.tokens,
            "cost_usd": self.cost_usd,
            "cost_is_known": self.cost_is_known,
            "cache_read_tokens": self.cache_read_tokens,
            "agent_route": self.agent_route,
            "env_choice": self.env_choice,
            "review_audit": self.review_audit,
            "drift": self.drift,
        }


def _first(events: list[dict], etype: str) -> dict:
    for e in events:
        if e.get("type") == etype:
            return {k: v for k, v in e.items() if k != "type"}
    return {}


def collect_snapshot(
    *,
    state: Any,
    usage: Any,
    transcript_events: list[dict],
    dump_path: str,
    drift: "dict | None" = None,
) -> ObservabilitySnapshot:

    ctx = getattr(state, "tool_use_context", {})
    tracking = getattr(state, "tracking", None)
    totals = usage.total()
    audits = [{k: v for k, v in e.items() if k != "type"} for e in transcript_events if e.get("type") == "review_audit"]
    return ObservabilitySnapshot(
        prompt_hash=ctx.get("system_prompt_hash", ""),
        dump_path=dump_path,
        chain_id=getattr(tracking, "chain_id", ""),
        depth=getattr(tracking, "depth", 0),
        tokens=totals,
        cost_usd=usage.cost_usd(),
        cost_is_known=usage.cost_is_known(),
        cache_read_tokens=totals.get("cache_read_input_tokens", 0),
        agent_route=_first(transcript_events, "agent_route"),
        env_choice=_first(transcript_events, "env_choice"),
        review_audit=audits,
        drift=drift or {},
    )
