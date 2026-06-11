"""串行工具执行器(总纲 §7.1.8 第一版串行;StreamingToolExecutor 并发为 v2)。

执行序(§7.3.7):schema/语义校验 → PreToolUse hook → ★Permission★ →
★ResourceGate(§7.3.9/M8)★ → 执行 → PostToolUse hook → tool_result 回填
(过 §7.1.6 预算)。错误回喂结构见 §7.3.7;diagnostics M1 恒 None(M5 大脑诊断填)。"""

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

if TYPE_CHECKING:  # 防循环 import:scheduler 不应反依赖 tools 运行时
    from praxis2.scheduler.resource_gate import AvailableResources, ResourceGate

TOOL_RESULT_MAX_CHARS = 20000  # §7.1.6 科研工具常产巨量输出;超出截断+占位


def apply_tool_result_budget(content: str, max_chars: int = TOOL_RESULT_MAX_CHARS) -> str:
    if len(content) <= max_chars:
        return content
    head = content[: max_chars - 200]
    return head + (
        f"\n…[截断:原 {len(content)} 字符超 tool_result 预算,"
        f"保留前 {max_chars - 200};完整输出请缩小工具产出或分批]"
    )


def _ok_result(tool_use_id: str, tr: ToolResult) -> dict:
    try:
        content = str(tr.value)
    except Exception as e:  # noqa: BLE001 - 返回值 __str__ 异常也不得逃逸成孤儿 tool_use
        content = f"[工具返回值无法序列化:{type(e).__name__}:{e}]"
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "is_error": False,
        "content": apply_tool_result_budget(content),
    }


def _error_result(tool_use_id: str, tr: ToolResult, budget_remaining: int) -> dict:
    # §7.3.7 错误回喂结构
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "is_error": True,
        "content": apply_tool_result_budget(tr.error or "工具执行失败(无错误信息)"),
        "diagnostics": None,  # M5 PostToolUse 大脑诊断填充(§4②)
        "recovery_hint": tr.recovery_hint,
        "recovery_budget_remaining": budget_remaining,
    }


def placeholder_results(blocks: list[dict]) -> list[dict]:
    """§7.1.5:为未执行的 tool_use 配平占位 tool_result,杜绝孤儿 tool_use。"""
    return [
        {
            "type": "tool_result",
            "tool_use_id": b["id"],
            "is_error": True,
            "content": "已中断,该工具未执行(abort)",
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
        self._remaining: list[dict] = []  # §7.1.5 abort 用
        # M8/§7.3.9:重算力 cost 非 None 时过闸,决策回喂模型(§4④)
        # 二者必须同时注入才生效;任一缺失 → 跳过 gate(M0-M7 零回归)
        self._resource_gate = resource_gate
        self._resource_available = resource_available

    def get_remaining_results(self) -> list[dict]:
        out = placeholder_results(self._remaining)
        self._remaining = []
        return out

    async def run_blocks(
        self, tool_use_blocks: list[dict], state: State
    ) -> AsyncIterator[dict]:
        """流式逐块执行,每个 tool_result(含 gate 决策回喂)yield 一次(§7.3.9)。

        M8 接入点:`validate_input + check_permissions` 之后、`tool.run()` 之前,
        若注入了 resource_gate 且工具 `estimated_resource_cost(payload=...)` 非 None,
        过 `ResourceGate.decide`;非 SUBMIT_NOW → `decision.to_tool_result_payload()`
        包成 tool_result yield 出,不真 run(§4④ 由模型自决等/改参/换工具)。"""
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
                        error=f"未注册工具 {name!r}",
                        recovery_hint="改用已注册工具或检查工具名拼写",
                    ),
                    max(0, self._recovery_budget - state.recovery_attempts),
                )
                continue

            try:
                tool.validate_input(payload)
            except Exception as e:  # noqa: BLE001 - 校验失败回喂模型自救
                state.recovery_attempts += 1
                yield _error_result(
                    tid,
                    ToolResult(
                        ok=False,
                        error=f"输入语义校验失败:{e}",
                        recovery_hint="按 input_schema 修正参数后重试",
                    ),
                    max(0, self._recovery_budget - state.recovery_attempts),
                )
                continue

            for h in self._pre:  # M1 默认空;M3 接入
                h(blk, state)

            # A.6:统一走 async acheck(默认基类实现转 sync check;
            # BridgePermissionAdapter 覆写以走 SSE control_request bridge,§7.6.2)。
            decision = await self._permission.acheck(
                tool=tool, payload=payload, state=state
            )
            if decision.decision is not PermissionDecision.ALLOW:
                state.recovery_attempts += 1
                yield _error_result(
                    tid,
                    ToolResult(
                        ok=False,
                        error=f"权限{decision.decision.value}:{decision.reason or '未说明'}",
                        recovery_hint=decision.reason,
                    ),
                    max(0, self._recovery_budget - state.recovery_attempts),
                )
                continue

            # ---- M8/§7.3.9 ResourceGate:重算力 cost 非 None 时过闸 ----
            if (
                self._resource_gate is not None
                and self._resource_available is not None
            ):
                cost = tool.estimated_resource_cost(payload=payload)
                if cost is not None:
                    user_id = state.tool_use_context.get("user_id", "")
                    gate_decision = self._resource_gate.decide(
                        cost=cost,
                        user_id=user_id,
                        available=self._resource_available,
                    )
                    # 非 SUBMIT_NOW → 决策回喂(§4④),不真 run;continue 下一块
                    if gate_decision.behavior.value != "submit_now":
                        payload_out = gate_decision.to_tool_result_payload() | {
                            "tool_use_id": tid,
                        }
                        # 决策回喂同样走 PostToolUse hook 链(便于审计/诊断注入)
                        for h in self._post:
                            replaced = h(tool, blk, payload_out, state)
                            if replaced is not None:
                                payload_out = replaced
                        yield payload_out
                        continue
                    # SUBMIT_NOW:落入下方 tool.run() 原路径

            try:
                tr = await tool.run(payload)
            except Exception as e:  # noqa: BLE001 - 工具异常包成 is_error 回喂(§4①)
                tr = ToolResult(
                    ok=False, error=f"工具抛异常:{type(e).__name__}: {e}"
                )

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

            for h in self._post:  # M1 默认空;M5 在此把大脑诊断写进 diagnostics
                replaced = h(tool, blk, result, state)
                if replaced is not None:
                    result = replaced

            yield result

    async def run_turn(self, tool_use_blocks: list[dict], state: State) -> list[dict]:
        """聚合版:M0-M7 调用方继续用此 list 形式(零回归)。"""
        return [r async for r in self.run_blocks(tool_use_blocks, state)]


_API_TOOL_RESULT_KEYS = ("type", "tool_use_id", "content", "is_error")


def to_api_tool_result(result: dict) -> dict:
    """把内部富 tool_result 折叠成 Anthropic API 合法子集(总纲 §7.3.7 API 序列化边界)。

    API 的 tool_result 块只接受 type/tool_use_id/content/is_error,多余键 400。
    diagnostics/recovery_hint/recovery_budget_remaining 等富字段并入 content 文本
    (模型只读 content,§4② 大脑诊断可见性靠这步)。对已是 4 键的 dict 幂等。"""
    content = str(result.get("content", ""))
    extra = []
    if result.get("diagnostics"):
        extra.append(f"[诊断] {result['diagnostics']}")
    if result.get("recovery_hint"):
        extra.append(f"[建议下一步] {result['recovery_hint']}")
    if result.get("recovery_budget_remaining") is not None:
        extra.append(f"[剩余自主恢复预算] {result['recovery_budget_remaining']}")
    if extra:
        content = content + "\n\n" + "\n".join(extra)
    return {
        "type": result["type"],
        "tool_use_id": result["tool_use_id"],
        "is_error": result.get("is_error", False),
        "content": content,
    }
