import pytest  # noqa

from praxis2.core.state import State
from praxis2.scheduler.quota import Quota, QuotaConfig
from praxis2.scheduler.resource_gate import AvailableResources, ResourceGate
from praxis2.tools.base import ResourceCost, Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner


class _LightEcho(Tool):
    name = "echo"

    def input_schema(self) -> dict:
        return {"type": "object"}

    async def run(self, payload):  # noqa: ARG002
        return ToolResult(ok=True, value="echo_ok")


class _HeavyAF3(Tool):
    name = "af3"

    def input_schema(self) -> dict:
        return {"type": "object"}

    async def run(self, payload):  # noqa: ARG002
        return ToolResult(ok=True, value="af3_ok")

    def estimated_resource_cost(self, *, payload: dict) -> ResourceCost:  # noqa: ARG002
        return ResourceCost(
            cpu_cores=8,
            mem_gb=32.0,
            gpu_count=1,
            gpu_mem_gb=24.0,
            wall_time_s=600,
            queue_hint="gpu",
        )


def _gate_with_resources(gpu_free: int) -> ResourceGate:  # noqa: ARG001  # spec verbatim
    return ResourceGate(
        quota=Quota(QuotaConfig(max_concurrent_per_user=2, global_max_queued=10)),
    )


async def test_light_tool_bypasses_gate_no_regression():

    reg = ToolRegistry()
    reg.register(_LightEcho())
    gate = _gate_with_resources(gpu_free=0)
    available = AvailableResources(gpu_count_free=0, cpu_cores_free=0, mem_gb_free=0.0)
    runner = SerialToolRunner(
        reg,
        recovery_budget=3,
        resource_gate=gate,
        resource_available=available,
    )
    state = State()
    state.tool_use_context["user_id"] = "u1"
    blk = {"type": "tool_use", "id": "t1", "name": "echo", "input": {}}
    results = []
    async for r in runner.run_blocks([blk], state=state):
        results.append(r)
    assert len(results) == 1
    assert "echo_ok" in results[0]["content"]


async def test_heavy_tool_passes_gate_submit_now():

    reg = ToolRegistry()
    reg.register(_HeavyAF3())
    gate = ResourceGate(quota=Quota(QuotaConfig(2, 10)))
    available = AvailableResources(gpu_count_free=2, cpu_cores_free=48, mem_gb_free=512.0)
    runner = SerialToolRunner(
        reg,
        recovery_budget=3,
        resource_gate=gate,
        resource_available=available,
    )
    state = State()
    state.tool_use_context["user_id"] = "u1"
    blk = {"type": "tool_use", "id": "t2", "name": "af3", "input": {}}
    results = []
    async for r in runner.run_blocks([blk], state=state):
        results.append(r)
    assert len(results) == 1
    assert "af3_ok" in results[0]["content"]


async def test_heavy_tool_rejected_by_gate_replaces_with_decision_payload():

    reg = ToolRegistry()
    reg.register(_HeavyAF3())
    gate = ResourceGate(quota=Quota(QuotaConfig(max_concurrent_per_user=0, global_max_queued=0)))
    available = AvailableResources(gpu_count_free=0, cpu_cores_free=0, mem_gb_free=0.0)
    runner = SerialToolRunner(
        reg,
        recovery_budget=3,
        resource_gate=gate,
        resource_available=available,
    )
    state = State()
    state.tool_use_context["user_id"] = "u1"
    blk = {"type": "tool_use", "id": "t3", "name": "af3", "input": {}}
    results = []
    async for r in runner.run_blocks([blk], state=state):
        results.append(r)
    assert len(results) == 1

    assert results[0]["is_error"] is True
    assert "REJECT" in results[0]["content"] or "\u62d2\u7edd" in results[0]["content"]


async def test_runtools_no_gate_kwargs_still_works_zero_regression():

    reg = ToolRegistry()
    reg.register(_LightEcho())
    runner = SerialToolRunner(reg, recovery_budget=3)
    state = State()
    state.tool_use_context["user_id"] = "u1"
    blk = {"type": "tool_use", "id": "t4", "name": "echo", "input": {}}
    results = []
    async for r in runner.run_blocks([blk], state=state):
        results.append(r)
    assert "echo_ok" in results[0]["content"]
