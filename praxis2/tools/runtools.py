from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from praxis2.core.seams import (
    AllowAllPermission,
    PermissionDecision,
    PermissionPolicy,
)
from praxis2.core.state import State
from praxis2.tools.base import ToolResult
from praxis2.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from praxis2.scheduler.resource_gate import AvailableResources, ResourceGate

TOOL_RESULT_MAX_CHARS = 20000


def apply_tool_result_budget(content: str, max_chars: int = TOOL_RESULT_MAX_CHARS) -> str:
    if len(content) <= max_chars:
        return content
    head = content[: max_chars - 200]
    return head + (
        "\n...[Truncated: original "
        f"{len(content)}"
        "characters exceed the tool result budget; retain"
        "ed first "
        f"{max_chars - 200}"
        "; use smaller or batched tool output]"
    )


def _ok_result(tool_use_id: str, tr: ToolResult) -> dict:
    try:
        content = str(tr.value)
    except Exception as e:  # noqa: BLE001
        content = f"[Tool result could not be serialized:{type(e).__name__}:{e}]"
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "is_error": False,
        "content": apply_tool_result_budget(content),
    }


def _error_result(tool_use_id: str, tr: ToolResult, budget_remaining: int) -> dict:

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "is_error": True,
        "content": apply_tool_result_budget(tr.error or "Tool execution failed without an error message"),
        "diagnostics": None,
        "recovery_hint": tr.recovery_hint,
        "recovery_budget_remaining": budget_remaining,
    }


def placeholder_results(blocks: list[dict]) -> list[dict]:

    return [
        {
            "type": "tool_result",
            "tool_use_id": b["id"],
            "is_error": True,
            "content": "Aborted before tool execution",
        }
        for b in blocks
    ]


class SerialToolRunner:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        recovery_budget: int,
        permission: PermissionPolicy | None = None,
        pre_hooks: list | None = None,
        post_hooks: list | None = None,
        resource_gate: "ResourceGate | None" = None,
        resource_available: "AvailableResources | None" = None,
    ) -> None:
        self._registry = registry
        self._recovery_budget = recovery_budget
        self._permission = permission or AllowAllPermission()
        self._pre = pre_hooks or []
        self._post = post_hooks or []
        self._remaining: list[dict] = []

        self._resource_gate = resource_gate
        self._resource_available = resource_available

    def get_remaining_results(self) -> list[dict]:
        out = placeholder_results(self._remaining)
        self._remaining = []
        return out

    async def run_blocks(self, tool_use_blocks: list[dict], state: State) -> AsyncIterator[dict]:

        self._remaining = list(tool_use_blocks)
        while self._remaining:
            blk = self._remaining.pop(0)
            tid, name, payload = blk["id"], blk["name"], blk.get("input", {})

            tool = self._registry.get(name)
            if tool is None:
                state.recovery_attempts += 1
                yield _error_result(
                    tid,
                    ToolResult(
                        ok=False,
                        error=f"Unregistered tool {name!r}",
                        recovery_hint="Choose a registered tool or check its spelling",
                    ),
                    max(0, self._recovery_budget - state.recovery_attempts),
                )
                continue

            try:
                tool.validate_input(payload)
            except Exception as e:  # noqa: BLE001
                state.recovery_attempts += 1
                yield _error_result(
                    tid,
                    ToolResult(
                        ok=False,
                        error=f"Input validation failed:{e}",
                        recovery_hint="Correct the arguments to match input_schema and retry",
                    ),
                    max(0, self._recovery_budget - state.recovery_attempts),
                )
                continue

            for h in self._pre:
                h(blk, state)

            decision = await self._permission.acheck(tool=tool, payload=payload, state=state)
            if decision.decision is not PermissionDecision.ALLOW:
                state.recovery_attempts += 1
                yield _error_result(
                    tid,
                    ToolResult(
                        ok=False,
                        error=f"Permission {decision.decision.value}:{decision.reason or 'unspecified'}",
                        recovery_hint=decision.reason,
                    ),
                    max(0, self._recovery_budget - state.recovery_attempts),
                )
                continue

            if self._resource_gate is not None and self._resource_available is not None:
                cost = tool.estimated_resource_cost(payload=payload)
                if cost is not None:
                    user_id = state.tool_use_context.get("user_id", "")
                    gate_decision = self._resource_gate.decide(
                        cost=cost,
                        user_id=user_id,
                        available=self._resource_available,
                    )

                    if gate_decision.behavior.value != "submit_now":
                        payload_out = gate_decision.to_tool_result_payload() | {
                            "tool_use_id": tid,
                        }

                        for h in self._post:
                            replaced = h(tool, blk, payload_out, state)
                            if replaced is not None:
                                payload_out = replaced
                        yield payload_out
                        continue

            try:
                tr = await tool.run(payload)
            except Exception as e:  # noqa: BLE001
                tr = ToolResult(ok=False, error=f"Tool raised an exception:{type(e).__name__}: {e}")

            result = (
                _ok_result(tid, tr)
                if tr.ok
                else _error_result(
                    tid,
                    tr,
                    max(0, self._recovery_budget - (state.recovery_attempts + 1)),
                )
            )
            if not tr.ok:
                state.recovery_attempts += 1

            for h in self._post:
                replaced = h(tool, blk, result, state)
                if replaced is not None:
                    result = replaced

            yield result

    async def run_turn(self, tool_use_blocks: list[dict], state: State) -> list[dict]:

        return [r async for r in self.run_blocks(tool_use_blocks, state)]


_API_TOOL_RESULT_KEYS = ("type", "tool_use_id", "content", "is_error")


def to_api_tool_result(result: dict) -> dict:

    content = str(result.get("content", ""))
    extra = []
    if result.get("diagnostics"):
        extra.append(f"[Diagnosis] {result['diagnostics']}")
    if result.get("recovery_hint"):
        extra.append(f"[Suggested next step] {result['recovery_hint']}")
    if result.get("recovery_budget_remaining") is not None:
        extra.append(f"[Remaining recovery budget] {result['recovery_budget_remaining']}")
    if extra:
        content = content + "\n\n" + "\n".join(extra)
    return {
        "type": result["type"],
        "tool_use_id": result["tool_use_id"],
        "is_error": result.get("is_error", False),
        "content": content,
    }
