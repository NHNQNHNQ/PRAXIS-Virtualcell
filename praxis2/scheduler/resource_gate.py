"""§7.3.9 ResourceGate 五分支提交闸 + 决策回喂模型(§4④)。

5 分支:submit_now / enqueue(返 ETA) / downscale(给降配建议) /
cpu_fallback(GPU→CPU 退) / reject(全局队列满+无可降配/退回)。

**绝不阻塞 worker**:Gate 是**同步决策函数**,真正提交在 hpc_submit.py
异步进行。决策回喂模型:to_tool_result_payload() 折叠成 is_error 文本,
模型按 §4④ 自主选(等 vs 改参 vs 换工具 vs 放弃),受 recovery_budget 约束。"""

from dataclasses import dataclass
from enum import StrEnum

from praxis2.scheduler.quota import Quota
from praxis2.tools.base import ResourceCost


class GateBehavior(StrEnum):
    SUBMIT_NOW = "submit_now"     # 配额未满 + 资源足
    ENQUEUE = "enqueue"           # 配额满或资源不足但全局队列未满
    DOWNSCALE = "downscale"       # 给降配建议(模型决策)
    CPU_FALLBACK = "cpu_fallback" # GPU 全占退 CPU 节点
    REJECT = "reject"             # 全局队列满 + 不可降配/退回


@dataclass
class AvailableResources:
    """当前可用资源快照(M7 由 SchedulerRegistry.snapshot 提供;M8 接真集群监控)。"""

    gpu_count_free: int
    cpu_cores_free: int
    mem_gb_free: float


@dataclass
class GateDecision:
    """§4④ 决策回喂模型:behavior + reason + eta(排队)+ alt_cost(降配)+
    queue_position(排队位次)。to_tool_result_payload 折叠为 is_error 文本。"""

    behavior: GateBehavior
    reason: str = ""
    eta_s: float | None = None
    alt_cost: ResourceCost | None = None
    queue_position: int = 0

    def to_tool_result_payload(self) -> dict:
        """折叠为模型可读 tool_result(§4④ 自救):is_error=True 除非 SUBMIT_NOW。"""
        is_err = self.behavior is not GateBehavior.SUBMIT_NOW
        parts = [f"[ResourceGate 决策] {self.behavior.name}:{self.reason}"]
        if self.eta_s is not None:
            parts.append(f"预计等待 {self.eta_s:.0f}s")
        if self.queue_position > 0:
            parts.append(f"排队位次:{self.queue_position}")
        if self.alt_cost is not None:
            parts.append(
                f"降配建议:cpu={self.alt_cost.cpu_cores} "
                f"mem={self.alt_cost.mem_gb}GB "
                f"gpu={self.alt_cost.gpu_count} "
                f"queue_hint={self.alt_cost.queue_hint!r}"
            )
        return {
            "type": "tool_result",
            "is_error": is_err,
            "content": "\n".join(parts),
        }


class ResourceGate:
    """五分支提交闸(§7.3.9)。同步决策,绝不阻塞 worker;真实异步提交在
    hpc_submit.py。决策由 SerialToolRunner 包成 tool_result 回喂模型。"""

    def __init__(self, *, quota: Quota) -> None:
        self._quota = quota

    def decide(
        self,
        *,
        cost: ResourceCost,
        user_id: str,
        available: AvailableResources,
        allow_downscale: bool = False,
        allow_cpu_fallback: bool = False,
    ) -> GateDecision:
        # 1. 资源足吗?
        gpu_ok = cost.gpu_count <= available.gpu_count_free
        cpu_ok = cost.cpu_cores <= available.cpu_cores_free
        mem_ok = cost.mem_gb <= available.mem_gb_free
        resource_ok = gpu_ok and cpu_ok and mem_ok

        # 2. 用户配额能拿吗?
        if resource_ok and self._quota.try_acquire(user_id):
            return GateDecision(
                behavior=GateBehavior.SUBMIT_NOW,
                reason="配额可得 + 资源足,立即提交",
            )

        # 3. 不能立即跑 → 看降配/回退/排队/拒绝
        if not gpu_ok and cost.gpu_count > 0 and allow_downscale:
            # 降配:去 GPU 走 CPU(若 CPU 资源足)
            alt = ResourceCost(
                cpu_cores=max(cost.cpu_cores, 4),
                mem_gb=cost.mem_gb,
                wall_time_s=cost.wall_time_s * 2,  # CPU 跑通常慢 2x
                gpu_count=0,
                gpu_mem_gb=0.0,
                queue_hint="cpu",
            )
            return GateDecision(
                behavior=GateBehavior.DOWNSCALE,
                reason="GPU 不可得;建议降到 CPU 配置(模型自决是否接受,§4④)",
                alt_cost=alt,
            )

        if not gpu_ok and cost.gpu_count > 0 and allow_cpu_fallback:
            alt = ResourceCost(
                cpu_cores=cost.cpu_cores * 2,  # CPU 多核补 GPU
                mem_gb=cost.mem_gb,
                wall_time_s=cost.wall_time_s * 3,
                gpu_count=0,
                gpu_mem_gb=0.0,
                queue_hint="cpu",
            )
            return GateDecision(
                behavior=GateBehavior.CPU_FALLBACK,
                reason="GPU 全占,退回 CPU 节点(CPUX/scw6chb)",
                alt_cost=alt,
            )

        # 4. 排队 or 拒绝
        if self._quota.try_enqueue(user_id):
            return GateDecision(
                behavior=GateBehavior.ENQUEUE,
                reason="资源/配额不足,已入队等待(背压不雪崩,§11.2)",
                eta_s=self._estimate_eta(cost),
                queue_position=self._quota.global_queued(),
            )

        return GateDecision(
            behavior=GateBehavior.REJECT,
            reason="全局队列已满,无降配/回退路径;请稍后重试或换工具(§4④)",
        )

    def _estimate_eta(self, cost: ResourceCost) -> float:
        """简单 ETA:wall_time_s × 排队位次系数(M7 第一版近似;M8 接真实
        前序作业时长统计)。"""
        n = max(1, self._quota.global_queued())
        return float(cost.wall_time_s * n / 2)
