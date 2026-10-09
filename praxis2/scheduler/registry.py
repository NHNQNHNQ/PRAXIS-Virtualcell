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
                f"Insufficient resources: required gpu={cost.gpu_count} cpu={cost.cpu_cores} "
                f"mem={cost.mem_gb}GB; available gpu={self._avail.gpu_count_free} "
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

        rec = self._reservations.get(reservation.reservation_id)
        if rec is None or rec.released:
            return
        cost = rec.cost
        self._avail.gpu_count_free += cost.gpu_count
        self._avail.cpu_cores_free += cost.cpu_cores
        self._avail.mem_gb_free += cost.mem_gb
        rec.released = True
        reservation.released = True
