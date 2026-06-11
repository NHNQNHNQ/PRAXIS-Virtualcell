"""Tool 契约最小子集(总纲 §7.3.1)+ 结构化结果(§4①)。

M1 只取闭环必需字段;is_destructive/is_idempotent/checkpoint/estimated_resource_cost
/diagnose_error 等扩展字段在 M3(Permission)/M4(回滚)/M7(资源)按需补。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ResourceCost:
    """§7.3.2 工具资源代价声明(M7 落地)。
    6 字段最小集对应 §11.7 节点维度:cpu_cores/mem_gb/gpu_count/gpu_mem_gb/
    wall_time_s(超时阈值)/queue_hint("gpu"|"cpu"|"big_mem"|None 候选)。
    `Tool.estimated_resource_cost()` 默认 None = 轻量工具(worker 内 async 跑);
    非 None = 重算力,必须经 `scheduler/resource_gate.py` 决策(§7.3.9)。"""

    cpu_cores: int
    mem_gb: float
    wall_time_s: int
    gpu_count: int = 0
    gpu_mem_gb: float = 0.0
    queue_hint: str | None = None  # "gpu" | "cpu" | "big_mem" | None


@dataclass
class ToolResult:
    """§4①:所有工具返回 {ok, value|error}。不变式约定:ok=True → error 应为 None;
    ok=False → error 必填(runtools 包成 tool_result(is_error),error 是模型读的可执行文本)。
    M1 不做 __post_init__ 强校验(个人开发,最小 overhead);runtools 对 error 缺失有兜底。"""

    ok: bool
    value: Any = None
    error: str | None = None  # 失败类别 + 已知诱因 + 建议下一步
    recovery_hint: str | None = None  # 建议的下一步(§7.3.7 recovery_hint)


class Tool(ABC):
    """工具契约最小子集(§7.3.1)。子类必须定义类属性 name(str),可选 description(str),
    并实现 input_schema() 与 async run();validate_input() 可选覆盖。"""

    name: str
    description: str = ""
    # §7.3.7 RMCP 操作类(call_skill 等);None=工具类不受相位约束。
    # ⚠ execute/写类工具子类必须显式声明 rmcp_op,漏声明(或误置 None)= 相位门静默绕过
    # = 科学严谨失守(M5 接 call_skill 类工具时务必声明,T8 端到端测试网兜底)
    rmcp_op: str | None = None

    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """Anthropic tools[].input_schema(JSON schema dict)。"""

    def validate_input(self, payload: dict[str, Any]) -> None:
        """schema 之外的语义校验;M3 RMCP 相位检查挂这。默认放行。"""
        return  # noqa: B027 — 意图明确:子类可选择性覆盖,默认放行

    def is_concurrency_safe(self, payload: dict[str, Any]) -> bool:
        """按 payload 判断是否可与他者并发执行。默认保守 False(§7.3.1)。"""
        return False

    def estimated_resource_cost(
        self, *, payload: dict[str, Any]
    ) -> "ResourceCost | None":
        """§7.3.2 工具资源代价(M7)。默认 None = 轻量工具(worker 内 async 跑,
        不走 ResourceGate);重算力工具覆盖此方法返回 ResourceCost,
        SerialToolRunner 据此判定是否经 scheduler/resource_gate.py 决策(§7.3.9)。"""
        return None

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> ToolResult: ...
