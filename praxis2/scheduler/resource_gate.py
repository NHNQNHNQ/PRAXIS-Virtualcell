from dataclasses import dataclass
from enum import StrEnum

from praxis2.scheduler.quota import Quota
from praxis2.tools.base import ResourceCost


class GateBehavior(StrEnum):
    SUBMIT_NOW = "submit_now"
    ENQUEUE = "enqueue"
    DOWNSCALE = "downscale"
    CPU_FALLBACK = "cpu_fallback"
    REJECT = "reject"


@dataclass
class AvailableResources:
    gpu_count_free: int
    cpu_cores_free: int
    mem_gb_free: float


@dataclass
class GateDecision:
    behavior: GateBehavior
    reason: str = ""
    eta_s: float | None = None
    alt_cost: ResourceCost | None = None
    queue_position: int = 0

    def to_tool_result_payload(self) -> dict:

        is_err = self.behavior is not GateBehavior.SUBMIT_NOW
        parts = [f"[ResourceGate decision] {self.behavior.name}:{self.reason}"]
        if self.eta_s is not None:
            parts.append(f"Expected wait {self.eta_s:.0f}s")
        if self.queue_position > 0:
            parts.append(f"Queue position:{self.queue_position}")
        if self.alt_cost is not None:
            parts.append(
                f"Suggested reduced resources: cpu={self.alt_cost.cpu_cores} "
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

        gpu_ok = cost.gpu_count <= available.gpu_count_free
        cpu_ok = cost.cpu_cores <= available.cpu_cores_free
        mem_ok = cost.mem_gb <= available.mem_gb_free
        resource_ok = gpu_ok and cpu_ok and mem_ok

        if resource_ok and self._quota.try_acquire(user_id):
            return GateDecision(
                behavior=GateBehavior.SUBMIT_NOW,
                reason="Quota and resources are available; submit now",
            )

        if not gpu_ok and cost.gpu_count > 0 and allow_downscale:
            alt = ResourceCost(
                cpu_cores=max(cost.cpu_cores, 4),
                mem_gb=cost.mem_gb,
                wall_time_s=cost.wall_time_s * 2,
                gpu_count=0,
                gpu_mem_gb=0.0,
                queue_hint="cpu",
            )
            return GateDecision(
                behavior=GateBehavior.DOWNSCALE,
                reason="GPU unavailable; consider a CPU configuration",
                alt_cost=alt,
            )

        if not gpu_ok and cost.gpu_count > 0 and allow_cpu_fallback:
            alt = ResourceCost(
                cpu_cores=cost.cpu_cores * 2,
                mem_gb=cost.mem_gb,
                wall_time_s=cost.wall_time_s * 3,
                gpu_count=0,
                gpu_mem_gb=0.0,
                queue_hint="cpu",
            )
            return GateDecision(
                behavior=GateBehavior.CPU_FALLBACK,
                reason="GPUs busy; fall back to a CPU worker",
                alt_cost=alt,
            )

        if self._quota.try_enqueue(user_id):
            return GateDecision(
                behavior=GateBehavior.ENQUEUE,
                reason="Resources or quota unavailable; queued to limit overload",
                eta_s=self._estimate_eta(cost),
                queue_position=self._quota.global_queued(),
            )

        return GateDecision(
            behavior=GateBehavior.REJECT,
            reason="The global queue is full with no available fallback. Retry later or choose another tool.",
        )

    def _estimate_eta(self, cost: ResourceCost) -> float:

        n = max(1, self._quota.global_queued())
        return float(cost.wall_time_s * n / 2)
