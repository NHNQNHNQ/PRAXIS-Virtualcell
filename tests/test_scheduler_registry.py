import pytest

from praxis2.scheduler.registry import (
    ResourceReservation,
    SchedulerRegistry,
)
from praxis2.scheduler.resource_gate import AvailableResources
from praxis2.tools.base import ResourceCost


def _initial() -> AvailableResources:
    return AvailableResources(gpu_count_free=2, cpu_cores_free=48, mem_gb_free=512.0)


def test_reserve_decrements_available_resources():
    reg = SchedulerRegistry(initial=_initial())
    before = reg.snapshot()
    cost = ResourceCost(cpu_cores=8, mem_gb=32.0, gpu_count=1, gpu_mem_gb=24.0, wall_time_s=600)
    res = reg.reserve(cost=cost, user_id="u1")
    assert isinstance(res, ResourceReservation)
    after = reg.snapshot()
    assert after.gpu_count_free == before.gpu_count_free - 1
    assert after.cpu_cores_free == before.cpu_cores_free - 8
    assert after.mem_gb_free == before.mem_gb_free - 32.0


def test_release_restores_available_resources():
    reg = SchedulerRegistry(initial=_initial())
    cost = ResourceCost(cpu_cores=8, mem_gb=32.0, gpu_count=1, gpu_mem_gb=24.0, wall_time_s=600)
    res = reg.reserve(cost=cost, user_id="u1")
    before_release = reg.snapshot()
    reg.release(res)
    after_release = reg.snapshot()
    assert after_release.gpu_count_free == before_release.gpu_count_free + 1
    assert after_release.cpu_cores_free == before_release.cpu_cores_free + 8


def test_reserve_raises_when_resources_insufficient():

    reg = SchedulerRegistry(initial=AvailableResources(0, 0, 0.0))
    with pytest.raises(ValueError, match="Insufficient resources"):
        reg.reserve(
            cost=ResourceCost(cpu_cores=1, mem_gb=1.0, wall_time_s=60),
            user_id="u1",
        )


def test_release_idempotent_on_unknown_reservation():

    reg = SchedulerRegistry(initial=_initial())
    res = reg.reserve(
        cost=ResourceCost(cpu_cores=1, mem_gb=1.0, wall_time_s=60),
        user_id="u1",
    )
    reg.release(res)
    reg.release(res)


def test_reservation_owner_user_id_tracked():

    reg = SchedulerRegistry(initial=_initial())
    res = reg.reserve(
        cost=ResourceCost(cpu_cores=1, mem_gb=1.0, wall_time_s=60),
        user_id="u1",
    )
    assert res.user_id == "u1"
