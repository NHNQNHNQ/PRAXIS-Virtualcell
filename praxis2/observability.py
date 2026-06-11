"""§12.4 统一可观测面板一处汇总(不散落)。

汇总六面:prompt dump/hash(§7.2.8)、token&cost&cache(§7.4.7/§7.6.4)、
chain/depth 调用链(§7.1.7)、输出分布漂移(§12.2)、agent 路由依据/env
选择(§7.5.0/§7.3.10)、管理员审核审计(§7.4.2)。目标:任何时候能回答
"今天 agent 是否还正常工作、为什么这么选"。

**只读聚合**:复用 M0 usage.UsageTracker / M2 prompt_debug / M5
transcript_sink 产物,不复制其计算(DRY)。§12.5:漂移监控第一版
基础版(落点统计+阈值告警),统一面板 M6 建基线、随模块增量接入。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftAlert:
    drifted: bool
    metric: float
    message: str = ""


class DriftMonitor:
    """§12.2 基础版:按意图类别(tool_choice/phase_transition/answer_shape
    /tool_error_rate 等)记落点 → 与滚动基线比,偏移超阈值告警。
    偏移度量 = 分布的 L1 距离半值(总变差距离,0~1,确定性可测)。
    关联根因的高级分析作 v2(§12.2 原文)。"""

    def __init__(self, *, threshold: float) -> None:
        self._threshold = threshold
        self._counts: dict[str, dict[str, int]] = {}

    def record(self, category: str, outcome: str) -> None:
        self._counts.setdefault(category, {})
        self._counts[category][outcome] = (
            self._counts[category].get(outcome, 0) + 1
        )

    def distribution(self, category: str) -> dict[str, float]:
        c = self._counts.get(category, {})
        total = sum(c.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in c.items()}

    def check_drift(
        self, category: str, *, baseline: dict[str, float]
    ) -> DriftAlert:
        cur = self.distribution(category)
        keys = set(cur) | set(baseline)
        # 总变差距离 = 0.5 * Σ|p_i - q_i|(0~1)
        tv = 0.5 * sum(
            abs(cur.get(k, 0.0) - baseline.get(k, 0.0)) for k in keys
        )
        drifted = tv > self._threshold
        msg = (
            f"输出分布漂移告警:类别 {category!r} 偏移 {tv:.3f} "
            f"> 阈值 {self._threshold}(人工核查:改工具描述/prompt/收紧 schema)"
            if drifted else ""
        )
        return DriftAlert(drifted=drifted, metric=tv, message=msg)


@dataclass
class ObservabilitySnapshot:
    """§12.4 一个 payload 汇齐六面(回答"今天是否正常/为什么这么选")。"""

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
    """只读聚合(不复制各模块计算,DRY):从 state(prompt_hash/chain/depth)
    + UsageTracker(token/cost/cache)+ transcript 事件(路由/env/审核审计)
    汇成单一面板 payload(§12.4 一处汇总)。"""
    ctx = getattr(state, "tool_use_context", {})
    tracking = getattr(state, "tracking", None)
    totals = usage.total()
    audits = [
        {k: v for k, v in e.items() if k != "type"}
        for e in transcript_events
        if e.get("type") == "review_audit"
    ]
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
