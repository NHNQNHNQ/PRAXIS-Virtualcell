from praxis2.scheduler.quota import Quota, QuotaConfig
from praxis2.scheduler.resource_gate import (
    AvailableResources,
    GateBehavior,
    GateDecision,
    ResourceGate,
)
from praxis2.tools.base import ResourceCost


def _gate(*, max_per_user=2, max_queued=10) -> ResourceGate:
    return ResourceGate(
        quota=Quota(
            QuotaConfig(
                max_concurrent_per_user=max_per_user,
                global_max_queued=max_queued,
            )
        ),
    )


def _gpu_cost() -> ResourceCost:
    return ResourceCost(
        cpu_cores=8,
        mem_gb=32.0,
        gpu_count=1,
        gpu_mem_gb=24.0,
        wall_time_s=600,
        queue_hint="gpu",
    )


def _avail(*, gpu_free=2, cpu_free=48) -> AvailableResources:
    return AvailableResources(
        gpu_count_free=gpu_free,
        cpu_cores_free=cpu_free,
        mem_gb_free=512.0,
    )


def test_submit_now_when_quota_and_resources_available():

    g = _gate()
    d = g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())
    assert isinstance(d, GateDecision)
    assert d.behavior is GateBehavior.SUBMIT_NOW
    assert "\u7acb\u5373" in d.reason or "submit" in d.reason.lower()


def test_enqueue_when_user_quota_full_but_global_queue_open():
    g = _gate(max_per_user=1)

    g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())

    d = g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())
    assert d.behavior is GateBehavior.ENQUEUE
    assert d.eta_s is not None and d.eta_s > 0
    assert d.queue_position >= 1


def test_enqueue_when_resources_busy_but_user_quota_ok():
    g = _gate()

    d = g.decide(
        cost=_gpu_cost(),
        user_id="u1",
        available=_avail(gpu_free=0),
    )
    assert d.behavior is GateBehavior.ENQUEUE
    assert "GPU" in d.reason or "Resources" in d.reason


def test_downscale_when_gpu_busy_and_cost_allows_lower_config():

    g = _gate()
    cost = ResourceCost(
        cpu_cores=8,
        mem_gb=64.0,
        gpu_count=1,
        gpu_mem_gb=24.0,
        wall_time_s=600,
        queue_hint="gpu",
    )
    d = g.decide(
        cost=cost,
        user_id="u1",
        available=_avail(gpu_free=0, cpu_free=48),
        allow_downscale=True,
    )

    assert d.behavior is GateBehavior.DOWNSCALE
    assert d.alt_cost is not None
    assert d.alt_cost.gpu_count == 0


def test_cpu_fallback_when_gpu_only_and_disallow_downscale():

    g = _gate()
    d = g.decide(
        cost=_gpu_cost(),
        user_id="u1",
        available=_avail(gpu_free=0, cpu_free=48),
        allow_cpu_fallback=True,
    )
    assert d.behavior is GateBehavior.CPU_FALLBACK
    assert d.alt_cost is not None and d.alt_cost.queue_hint == "cpu"


def test_reject_when_global_queue_full_and_no_fallback():

    g = _gate(max_per_user=1, max_queued=1)
    g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())
    g.decide(cost=_gpu_cost(), user_id="u2", available=_avail(gpu_free=0))

    d = g.decide(cost=_gpu_cost(), user_id="u3", available=_avail(gpu_free=0))
    assert d.behavior is GateBehavior.REJECT
    assert "queue" in d.reason or "full" in d.reason


def test_decision_to_tool_result_payload_for_model_self_recovery():

    d = GateDecision(
        behavior=GateBehavior.ENQUEUE,
        reason="\u914d\u989d\u5df2\u6ee1,\u6392\u961f\u7b49\u5f85",
        eta_s=120.0,
        queue_position=3,
    )
    payload = d.to_tool_result_payload()
    assert payload["type"] == "tool_result"
    assert payload["is_error"] is True
    assert "ENQUEUE" in payload["content"] or "queued" in payload["content"]
    assert "120" in payload["content"]
    assert "3" in payload["content"]


def test_submit_now_decision_payload_is_not_error():

    d = GateDecision(behavior=GateBehavior.SUBMIT_NOW, reason="\u7acb\u5373\u63d0\u4ea4")
    payload = d.to_tool_result_payload()
    assert payload["is_error"] is False
