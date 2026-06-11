"""§7.3.2 Tool.estimated_resource_cost() 协议测试。"""

from praxis2.tools.base import ResourceCost, Tool, ToolResult


def test_resource_cost_dataclass_fields():
    # §7.3.2 6 字段最小集(§11.7 节点维度对应)
    rc = ResourceCost(
        cpu_cores=8, mem_gb=32.0, gpu_count=1, gpu_mem_gb=24.0,
        wall_time_s=600, queue_hint="gpu",
    )
    assert rc.cpu_cores == 8 and rc.mem_gb == 32.0
    assert rc.gpu_count == 1 and rc.gpu_mem_gb == 24.0
    assert rc.wall_time_s == 600 and rc.queue_hint == "gpu"


def test_resource_cost_defaults_zero_no_gpu_no_hint():
    rc = ResourceCost(cpu_cores=1, mem_gb=1.0, wall_time_s=60)
    assert rc.gpu_count == 0
    assert rc.gpu_mem_gb == 0.0
    assert rc.queue_hint is None


def test_tool_default_estimated_resource_cost_is_none():
    # 默认 None = 轻量工具,worker 内 async 跑,不走 ResourceGate(向后兼容)
    class LightTool(Tool):
        name = "light"

        def input_schema(self) -> dict:
            return {"type": "object"}

        async def run(self, payload):  # noqa: ARG002
            return ToolResult(ok=True, value="ok")

    t = LightTool()
    assert t.estimated_resource_cost(payload={}) is None


def test_tool_override_returns_resource_cost():
    # 重算力工具:子类覆盖返回 ResourceCost
    class HeavyTool(Tool):
        name = "af3"

        def input_schema(self) -> dict:
            return {"type": "object"}

        async def run(self, payload):  # noqa: ARG002
            return ToolResult(ok=True, value="ok")

        def estimated_resource_cost(self, *, payload: dict) -> ResourceCost:
            return ResourceCost(
                cpu_cores=8, mem_gb=64.0, gpu_count=1, gpu_mem_gb=24.0,
                wall_time_s=1800, queue_hint="gpu",
            )

    t = HeavyTool()
    rc = t.estimated_resource_cost(payload={"seq": "MKK"})
    assert rc is not None
    assert rc.queue_hint == "gpu" and rc.gpu_count == 1


def test_tool_estimated_cost_payload_aware():
    # 资源代价应允许按 payload 动态计算(短序列 vs 长序列)
    class DynamicTool(Tool):
        name = "dyn"

        def input_schema(self) -> dict:
            return {"type": "object"}

        async def run(self, payload):  # noqa: ARG002
            return ToolResult(ok=True)

        def estimated_resource_cost(self, *, payload: dict) -> ResourceCost:
            n = len(payload.get("seq", ""))
            return ResourceCost(
                cpu_cores=1, mem_gb=2.0,
                wall_time_s=max(60, n * 2),  # 按长度线性
            )

    t = DynamicTool()
    short = t.estimated_resource_cost(payload={"seq": "MK"})
    long_ = t.estimated_resource_cost(payload={"seq": "M" * 500})
    assert short.wall_time_s == 60   # 兜底下限
    assert long_.wall_time_s == 1000  # 500*2
