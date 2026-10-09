from praxis2.core.state import State
from praxis2.llm.usage import UsageTracker
from praxis2.observability import (
    DriftMonitor,
    ObservabilitySnapshot,
    collect_snapshot,
)


def test_snapshot_aggregates_all_facets_in_one_place():
    # §12.4 一处汇总(不散落):六个面汇成一个 snapshot
    st = State()
    st.tool_use_context["system_prompt_hash"] = "abc123"
    st.tracking.chain_id = "chain-1"
    st.tracking.depth = 2
    tracker = UsageTracker(price_per_mtok={"m": (1.0, 2.0)})
    tracker.add("m", {"input_tokens": 1000, "output_tokens": 500,
                      "cache_read_input_tokens": 200})
    transcript_events = [
        {"type": "agent_route", "chosen": "Cryo", "score": 3},
        {"type": "env_choice", "env": "conda:cryo"},
        {"type": "review_audit", "action": "approve", "cand": "c1"},
    ]
    snap = collect_snapshot(
        state=st, usage=tracker, transcript_events=transcript_events,
        dump_path="/tmp/p.jsonl",
    )
    assert isinstance(snap, ObservabilitySnapshot)
    assert snap.prompt_hash == "abc123"
    assert snap.dump_path == "/tmp/p.jsonl"
    assert snap.chain_id == "chain-1" and snap.depth == 2
    assert snap.tokens["input_tokens"] == 1000
    assert snap.cost_usd > 0 and snap.cost_is_known is True
    assert snap.cache_read_tokens == 200
    assert snap.agent_route == {"chosen": "Cryo", "score": 3}
    assert snap.env_choice == {"env": "conda:cryo"}
    assert snap.review_audit == [{"action": "approve", "cand": "c1"}]


def test_snapshot_to_dict_is_single_panel_payload():
    # §12.4 目标:一个 payload 能回答"今天是否正常/为什么这么选"
    snap = collect_snapshot(state=State(), usage=UsageTracker(),
                            transcript_events=[], dump_path="")
    d = snap.to_dict()
    assert set(d.keys()) == {
        "prompt_hash", "dump_path", "chain_id", "depth",
        "tokens", "cost_usd", "cost_is_known", "cache_read_tokens",
        "agent_route", "env_choice", "review_audit", "drift",
    }


def test_drift_monitor_basic_distribution_and_threshold_alert():
    # §12.2 基础版:按意图类别落点分布 + 偏移超阈值告警
    dm = DriftMonitor(threshold=0.3)
    # 滚动基线:工具选择分布
    for _ in range(8):
        dm.record("tool_choice", "retrieve")
    for _ in range(2):
        dm.record("tool_choice", "call_skill")
    base = dm.distribution("tool_choice")
    assert abs(base["retrieve"] - 0.8) < 1e-9
    # 与基线比:今天 call_skill 占比飙升 → 偏移超阈值告警
    dm2 = DriftMonitor(threshold=0.3)
    for _ in range(5):
        dm2.record("tool_choice", "call_skill")
    alert = dm2.check_drift("tool_choice", baseline=base)
    assert alert.drifted is True
    assert alert.metric > 0.3
    assert "tool_choice" in alert.message


def test_drift_no_alert_within_threshold():
    dm = DriftMonitor(threshold=0.5)
    dm.record("phase_transition", "retrieve")
    dm.record("phase_transition", "execute")
    alert = dm.check_drift("phase_transition",
                           baseline={"retrieve": 0.5, "execute": 0.5})
    assert alert.drifted is False


def test_drift_monitor_unknown_category_empty_distribution():
    dm = DriftMonitor(threshold=0.3)
    assert dm.distribution("never_seen") == {}
