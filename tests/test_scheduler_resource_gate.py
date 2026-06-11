"""§7.3.9 ResourceGate 五分支提交闸 + 决策回喂模型(§4④)。"""

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
        quota=Quota(QuotaConfig(
            max_concurrent_per_user=max_per_user,
            global_max_queued=max_queued,
        )),
    )


def _gpu_cost() -> ResourceCost:
    return ResourceCost(
        cpu_cores=8, mem_gb=32.0, gpu_count=1, gpu_mem_gb=24.0,
        wall_time_s=600, queue_hint="gpu",
    )


def _avail(*, gpu_free=2, cpu_free=48) -> AvailableResources:
    return AvailableResources(
        gpu_count_free=gpu_free, cpu_cores_free=cpu_free, mem_gb_free=512.0,
    )


def test_submit_now_when_quota_and_resources_available():
    # 配额未满 + 资源足 → 立即提交
    g = _gate()
    d = g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())
    assert isinstance(d, GateDecision)
    assert d.behavior is GateBehavior.SUBMIT_NOW
    assert "立即" in d.reason or "submit" in d.reason.lower()


def test_enqueue_when_user_quota_full_but_global_queue_open():
    g = _gate(max_per_user=1)
    # 先用满 u1 配额
    g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())
    # 第二次同用户:配额满 → 排队
    d = g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())
    assert d.behavior is GateBehavior.ENQUEUE
    assert d.eta_s is not None and d.eta_s > 0
    assert d.queue_position >= 1


def test_enqueue_when_resources_busy_but_user_quota_ok():
    g = _gate()
    # GPU 全占(资源不足)
    d = g.decide(
        cost=_gpu_cost(), user_id="u1",
        available=_avail(gpu_free=0),
    )
    assert d.behavior is GateBehavior.ENQUEUE
    assert "GPU" in d.reason or "资源" in d.reason


def test_downscale_when_gpu_busy_and_cost_allows_lower_config():
    # 请求 1×GPU + 64GB 内存,GPU 全占;ResourceGate 提议降到 0×GPU + 32GB CPU 路径
    g = _gate()
    cost = ResourceCost(
        cpu_cores=8, mem_gb=64.0, gpu_count=1, gpu_mem_gb=24.0,
        wall_time_s=600, queue_hint="gpu",
    )
    d = g.decide(
        cost=cost, user_id="u1",
        available=_avail(gpu_free=0, cpu_free=48),
        allow_downscale=True,
    )
    # GPU 不可得 + 允许降配 → 给出 alt_cost(模型决定接不接受)
    assert d.behavior is GateBehavior.DOWNSCALE
    assert d.alt_cost is not None
    assert d.alt_cost.gpu_count == 0  # 降到 CPU


def test_cpu_fallback_when_gpu_only_and_disallow_downscale():
    # queue_hint=gpu 但 GPU 全占 + 不允许降配 → CPU_FALLBACK(转 CPU 节点)
    g = _gate()
    d = g.decide(
        cost=_gpu_cost(), user_id="u1",
        available=_avail(gpu_free=0, cpu_free=48),
        allow_cpu_fallback=True,
    )
    assert d.behavior is GateBehavior.CPU_FALLBACK
    assert d.alt_cost is not None and d.alt_cost.queue_hint == "cpu"


def test_reject_when_global_queue_full_and_no_fallback():
    # 全局队列满 + 不可降配/退回 → 拒绝
    g = _gate(max_per_user=1, max_queued=1)
    g.decide(cost=_gpu_cost(), user_id="u1", available=_avail())  # u1 占 1 槽
    g.decide(cost=_gpu_cost(), user_id="u2", available=_avail(gpu_free=0))  # u2 入队(满)
    # 第三个:全局队列已满 + 配额已满 → 拒绝
    d = g.decide(cost=_gpu_cost(), user_id="u3", available=_avail(gpu_free=0))
    assert d.behavior is GateBehavior.REJECT
    assert "队列" in d.reason or "满" in d.reason


def test_decision_to_tool_result_payload_for_model_self_recovery():
    # §4④ 决策回喂模型:behavior/reason/eta/queue_position/alt_cost 折叠成可读文本
    d = GateDecision(
        behavior=GateBehavior.ENQUEUE,
        reason="配额已满,排队等待",
        eta_s=120.0,
        queue_position=3,
    )
    payload = d.to_tool_result_payload()
    assert payload["type"] == "tool_result"
    assert payload["is_error"] is True  # 非 submit_now 即非成功
    assert "ENQUEUE" in payload["content"] or "排队" in payload["content"]
    assert "120" in payload["content"]  # eta 显示
    assert "3" in payload["content"]    # queue_position 显示


def test_submit_now_decision_payload_is_not_error():
    # SUBMIT_NOW 是成功决策(将异步提交);to_tool_result_payload is_error=False
    d = GateDecision(behavior=GateBehavior.SUBMIT_NOW, reason="立即提交")
    payload = d.to_tool_result_payload()
    assert payload["is_error"] is False
