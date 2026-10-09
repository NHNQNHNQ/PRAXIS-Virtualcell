"""Run conversation turns with tools, recovery budgets, and context compaction."""

from collections.abc import AsyncIterator, Callable
from typing import Any

from praxis2.core.seams import Compactor
from praxis2.core.state import State, TerminalReason
from praxis2.llm.retry import WithheldKind, classify_withheld_error
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner, placeholder_results, to_api_tool_result

_MAX_TOKENS_CEILING = 393_216


class AbortSignal:
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
    system: "str | list[dict] | None" = None,
    abort: "AbortSignal | None" = None,
    on_request: "Callable[[dict], None] | None" = None,
    stop_hook: "Callable[[State], Any] | None" = None,
    precompact_gate: "Callable[[State], bool] | None" = None,
) -> AsyncIterator[dict]:
    max_turns = getattr(settings, "max_turns", None)

    while True:
        if max_turns and state.turn_count > max_turns:
            yield {"type": "end", "reason": TerminalReason.MAX_TURNS.value}
            return

        if precompact_gate is not None and state.transition != "precompact_done" and precompact_gate(state):
            await compactor.compact(state)
            state.transition = "precompact_done"

        tool_use_blocks: list[dict] = []
        text_parts: list[str] = []
        needs_follow_up = False
        stop_reason: str | None = None

        if on_request is not None:
            try:
                on_request(
                    {
                        "model": settings.model,
                        "system": system,
                        "messages": state.messages,
                        "tools": registry.openai_tools() or None,
                    }
                )
            except Exception:  # noqa: BLE001
                pass
        try:
            async for ev in client.stream_messages(
                model=settings.model,
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
                    yield {"type": "text", "text": ev["text"]}
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
                    _u = ev.get("usage") or {}
                    state.usage_total["prompt_tokens"] += int(_u.get("prompt_tokens", 0) or 0)
                    state.usage_total["completion_tokens"] += int(_u.get("completion_tokens", 0) or 0)
        except Exception as exc:  # noqa: BLE001
            kind = classify_withheld_error(exc)
            if kind == WithheldKind.PROMPT_TOO_LONG and state.transition != "reactive_compact_done":
                await compactor.compact(state)
                state.transition = "reactive_compact_done"
                continue
            yield {"type": "end", "reason": TerminalReason.ERROR.value, "message": repr(exc)[:200]}
            return

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
                state.messages.append({"role": "user", "content": placeholder_results(tool_use_blocks)})
            yield {"type": "end", "reason": TerminalReason.ABORTED.value}
            return

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

        if needs_follow_up:
            results = await runner.run_turn(tool_use_blocks, state)
            for r in results:
                yield {"type": "tool_result", **r}
            state.messages.append({"role": "user", "content": [to_api_tool_result(r) for r in results]})

            if state.recovery_attempts >= settings.recovery_budget:
                yield {"type": "end", "reason": TerminalReason.ESCALATED.value}
                return
            state.turn_count += 1
            state.transition = "tool_follow_up"
            continue

        if stop_reason == "max_tokens" and state.max_output_tokens_recovery_count < settings.max_output_recovery:
            state.max_output_tokens_recovery_count += 1

            state.max_tokens_boost += settings.max_tokens
            state.transition = "max_output_recovery"
            continue

        state.turn_count += 1
        state.last_assistant_text = "".join(text_parts)
        if stop_hook is not None:
            dec = stop_hook(state)
            if getattr(dec, "veto", False):
                state.messages.append({"role": "user", "content": dec.message})
                state.pending_stop_reasons.append(dec.message)
                state.transition = "stop_hook_retry"
                continue
        state.pending_stop_reasons.clear()
        yield {"type": "end", "reason": TerminalReason.STOP.value}
        return
