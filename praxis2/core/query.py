"""query() 工具闭环主循环(总纲 §7.1,对标 Claude query.ts)。

M1 增量建:Task 6 单轮骨架 → Task 7 多轮闭环 → Task 8 恢复路径(§7.1.4)
→ Task 9 abort 清理(§7.1.5)。yield 内核事件 dict(M6 再映射 SSE);
终止以最后一个 {"type":"end","reason": TerminalReason} 事件表达,State 原地更新。"""

from collections.abc import AsyncIterator, Callable
from typing import Any

from praxis2.core.seams import Compactor
from praxis2.core.state import State, TerminalReason
from praxis2.llm.retry import WithheldKind, classify_withheld_error
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner, placeholder_results, to_api_tool_result

# Bug B(2026-05-30):deepseek-v4-pro 实测 max_tokens 上限。
# litellm 强制 [1, 393216],boost 累加越界会直接 400。
_MAX_TOKENS_CEILING = 393_216


class AbortSignal:
    """M1 简单中断信号(§7.1.5)。M6 接 server 端真实取消。"""

    def __init__(self) -> None:
        self._set = False

    def set(self) -> None:
        self._set = True

    def is_set(self) -> bool:
        return self._set


async def query(
    state: State,
    *,
    client: Any,  # AnthropicClient(M0)
    registry: ToolRegistry,
    settings: Any,  # .model/.max_tokens/.max_turns/.recovery_budget/.max_output_recovery
    runner: SerialToolRunner,
    compactor: Compactor,
    system: "str | list[dict] | None" = None,  # M2 起传 core/prompt.to_api_system 产出
    abort: "AbortSignal | None" = None,
    on_request: "Callable[[dict], None] | None" = None,  # §7.2.8 --dump-prompts 注入缝
    # §7.6.1 Stop 缝;契约:返回须有 .veto;veto=True 时须有 .message(为何否决+满足条件)
    stop_hook: "Callable[[State], Any] | None" = None,
    # §12.3 调用前主动 compact 注入缝;gate 由调用方用 usage.should_auto_compact 构造,
    # 返回 True 且本轮未主动 compact 过则压缩。不传则行为与 M3 完全一致(零回归)。
    precompact_gate: "Callable[[State], bool] | None" = None,
) -> AsyncIterator[dict]:
    max_turns = getattr(settings, "max_turns", None)

    while True:
        # §7.1.1 死循环熔断(用 > 不用 >=:满 max_turns 轮 tool 后的终答须放行,
        # 死循环仍被 max_turns+1 兜住)。继承 Task 7/8。
        if max_turns and state.turn_count > max_turns:
            yield {"type": "end", "reason": TerminalReason.MAX_TURNS.value}
            return

        # ---- §12.3 调用前主动 token-gate compact(独立于反应式 PTL 路径)----
        if (
            precompact_gate is not None
            and state.transition != "precompact_done"
            and precompact_gate(state)
        ):
            await compactor.compact(state)
            state.transition = "precompact_done"  # 防无限主动 compact

        tool_use_blocks: list[dict] = []
        text_parts: list[str] = []
        needs_follow_up = False
        stop_reason: str | None = None

        # ---- a. streaming;§7.1.4 ① prompt-too-long → reactive compact → 重试 ----
        if on_request is not None:  # §7.2.8:每次 API 请求前落完整 prompt(可观测)
            try:
                on_request(
                    {
                        "model": settings.model,
                        "system": system,
                        "messages": state.messages,
                        "tools": registry.openai_tools() or None,
                    }
                )
            except Exception:  # noqa: BLE001 - dump 是调试设施,失败不得中断主循环
                pass
        try:
            async for ev in client.stream_messages(
                model=settings.model,
                # Bug B:recovery 时叠加 state.max_tokens_boost,推理模型重试拿更大预算;
                # 防累加越界 _MAX_TOKENS_CEILING(litellm 对 deepseek-v4-pro 硬约束)
                max_tokens=min(
                    settings.max_tokens + state.max_tokens_boost,
                    _MAX_TOKENS_CEILING,
                ),
                messages=state.messages,
                system=system,
                tools=registry.openai_tools() or None,
            ):
                t = ev["type"]
                if t == "text":
                    text_parts.append(ev["text"])
                    yield {"type": "text", "text": ev["text"]}  # §7.1.3 顺序保真
                elif t == "tool_use":
                    tool_use_blocks.append(ev)
                    needs_follow_up = True
                    yield {
                        "type": "tool_use",
                        "id": ev["id"],
                        "name": ev["name"],
                        "input": ev["input"],
                    }
                elif t == "message_stop":
                    stop_reason = ev["stop_reason"]
                elif t == "usage":
                    # 计费:sse 流末补发的真实 usage(message_stop 时 usage 还空,见 sse.py)。
                    # 累计本 query() 闭环 token 用量(多轮工具调用有多次);chat 扣费用。
                    _u = ev.get("usage") or {}
                    state.usage_total["prompt_tokens"] += int(_u.get("prompt_tokens", 0) or 0)
                    state.usage_total["completion_tokens"] += int(
                        _u.get("completion_tokens", 0) or 0
                    )
        except Exception as exc:  # noqa: BLE001 - 分类后定夺恢复或冒泡
            kind = classify_withheld_error(exc)
            if kind == WithheldKind.PROMPT_TOO_LONG and state.transition != "reactive_compact_done":
                await compactor.compact(state)  # M4:Compactor 缝已异步化(§7.4.5 校准)
                state.transition = "reactive_compact_done"  # 防无限 compact
                continue  # 独立 continue 点①
            yield {"type": "end", "reason": TerminalReason.ERROR.value,
                   "message": repr(exc)[:200]}
            return

        # ---- §7.1.5 streaming 结束**立即**检查 abort(在落 messages 之前)----
        if abort is not None and abort.is_set():
            if tool_use_blocks:
                state.messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": b["id"],
                                "name": b["name"],
                                "input": b["input"],
                            }
                            for b in tool_use_blocks
                        ],
                    }
                )
                state.messages.append(
                    {"role": "user", "content": placeholder_results(tool_use_blocks)}
                )
            yield {"type": "end", "reason": TerminalReason.ABORTED.value}
            return

        # 正常路径:本轮 assistant(tool_use)消息落 messages(唯一一次)
        if tool_use_blocks:
            state.messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]}
                        for b in tool_use_blocks
                    ],
                }
            )

        # ---- c. 有 tool_use:串行执行 → tool_result 回填(§3 step3.c)----
        if needs_follow_up:
            results = await runner.run_turn(tool_use_blocks, state)
            for r in results:
                yield {"type": "tool_result", **r}  # SSE/可观测:富结构
            state.messages.append(
                {"role": "user", "content": [to_api_tool_result(r) for r in results]}
            )  # 落 messages 经 §7.3.7 序列化(API 4 键,富字段折叠进 content)
            # §4③⑤ 预算耗尽 → 升级(ESCALATED 是"模型应主动 ask_user"的可测代理)
            if state.recovery_attempts >= settings.recovery_budget:
                yield {"type": "end", "reason": TerminalReason.ESCALATED.value}
                return
            state.turn_count += 1  # turn 在分支末累增(§7.1.1)
            state.transition = "tool_follow_up"
            continue

        # ---- §7.1.4 ② max-output-tokens 基础恢复(独立 continue 点②)----
        if (
            stop_reason == "max_tokens"
            and state.max_output_tokens_recovery_count < settings.max_output_recovery
        ):
            state.max_output_tokens_recovery_count += 1
            # Bug B(2026-05-30):每次 recovery 倍增预算(+= 基准 max_tokens)。
            # 推理模型(deepseek-v4-pro)reasoning 烧光固定 max_tokens → content=0,
            # 不提预算的重试是确定性 0 输出。boost 让重试轮 reasoning + content 都能出。
            state.max_tokens_boost += settings.max_tokens
            state.transition = "max_output_recovery"
            continue

        # ---- 无 tool_use 且无可恢复:Stop hook 终态校验(§7.6.1/§5④#3)----
        # B.4(reviewer M1 C2):每一次终答都跑 stop_hook,不再用 stop_hook_active 旗标
        # "宁松勿死循环"——否决就 continue 再走一轮,死循环由 maxTurns 兜底防护。
        # state.pending_stop_reasons 只是诊断字段,不参与决策(决策完全由 hook 看 state 真实
        # 状态自行判断)。修复漏洞:否决后中间 tool 轮 + 第二终答仍未满足 → 原本静默放行。
        state.turn_count += 1
        state.last_assistant_text = "".join(text_parts)  # GAP-AH-2:本轮终答供 stop_hook 看
        if stop_hook is not None:
            dec = stop_hook(state)
            if getattr(dec, "veto", False):
                state.messages.append({"role": "user", "content": dec.message})
                state.pending_stop_reasons.append(dec.message)
                state.transition = "stop_hook_retry"
                continue
        state.pending_stop_reasons.clear()  # 放行/未否决:清原因(供下一独立终答)
        yield {"type": "end", "reason": TerminalReason.STOP.value}
        return
