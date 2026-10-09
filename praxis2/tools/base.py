from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ResourceCost:
    cpu_cores: int
    mem_gb: float
    wall_time_s: int
    gpu_count: int = 0
    gpu_mem_gb: float = 0.0
    queue_hint: str | None = None  # "gpu" | "cpu" | "big_mem" | None


@dataclass
class ToolResult:
    ok: bool
    value: Any = None
    error: str | None = None
    recovery_hint: str | None = None


class Tool(ABC):
    name: str
    description: str = ""

    rmcp_op: str | None = None

    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """Return the JSON schema used in Anthropic tool input definitions."""

    def validate_input(self, payload: dict[str, Any]) -> None:

        return  # noqa: B027

    def is_concurrency_safe(self, payload: dict[str, Any]) -> bool:

        return False

    def estimated_resource_cost(self, *, payload: dict[str, Any]) -> "ResourceCost | None":

        return None

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> ToolResult: ...
