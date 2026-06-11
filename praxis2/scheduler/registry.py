"""§11.5 SchedulerRegistry.reserve 资源预留。

提交前对调度器声明资源占用,防重复扣减。三者职责切分:
- `ResourceGate.decide` 决定能否提交(读但不改资源)
- `SchedulerRegistry.reserve` 实际扣资源(返句柄)
- `hpc_submit.submit` 投递作业

reserve 失败抛 ValueError(资源不足);release 幂等(防多 worker 重投。"""

import uuid
from dataclasses import dataclass, field

from praxis2.scheduler.resource_gate import AvailableResources
from praxis2.tools.base import ResourceCost


@dataclass
class ResourceReservation:
    reservation_id: str
    user_id: str
    cost: ResourceCost
    released: bool = field(default=False)


class SchedulerRegistry:
    """资源占用登记表 + reserve/release/snapshot。"""

    def __init__(self, *, initial: AvailableResources) -> None:
        self._avail = AvailableResources(
            gpu_count_free=initial.gpu_count_free,
            cpu_cores_free=initial.cpu_cores_free,
            mem_gb_free=initial.mem_gb_free,
        )
        self._reservations: dict[str, ResourceReservation] = {}

    def snapshot(self) -> AvailableResources:
        return AvailableResources(
            gpu_count_free=self._avail.gpu_count_free,
            cpu_cores_free=self._avail.cpu_cores_free,
            mem_gb_free=self._avail.mem_gb_free,
        )

    def reserve(self, *, cost: ResourceCost, user_id: str) -> ResourceReservation:
        if (
            cost.gpu_count > self._avail.gpu_count_free
            or cost.cpu_cores > self._avail.cpu_cores_free
            or cost.mem_gb > self._avail.mem_gb_free
        ):
            raise ValueError(
                f"资源不足:需 gpu={cost.gpu_count} cpu={cost.cpu_cores} "
                f"mem={cost.mem_gb}GB,可得 gpu={self._avail.gpu_count_free} "
                f"cpu={self._avail.cpu_cores_free} mem={self._avail.mem_gb_free}GB"
            )
        self._avail.gpu_count_free -= cost.gpu_count
        self._avail.cpu_cores_free -= cost.cpu_cores
        self._avail.mem_gb_free -= cost.mem_gb
        res = ResourceReservation(
            reservation_id="res-" + uuid.uuid4().hex,
            user_id=user_id,
            cost=cost,
        )
        self._reservations[res.reservation_id] = res
        return res

    def release(self, reservation: ResourceReservation) -> None:
        """幂等:已 release 的 reservation 不再扣减;未知 reservation_id 不抛。"""
        rec = self._reservations.get(reservation.reservation_id)
        if rec is None or rec.released:
            return
        cost = rec.cost
        self._avail.gpu_count_free += cost.gpu_count
        self._avail.cpu_cores_free += cost.cpu_cores
        self._avail.mem_gb_free += cost.mem_gb
        rec.released = True
        reservation.released = True
