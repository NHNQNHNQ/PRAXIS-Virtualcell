"""Compact conversation history while preserving tool calls and recovery state."""

import json
from typing import Any


def _ids(msg: dict, kind: str, id_key: str) -> set[str]:
    c = msg.get("content")
    if not isinstance(c, list):
        return set()
    return {b[id_key] for b in c if isinstance(b, dict) and b.get("type") == kind and id_key in b}


def adjust_index_to_preserve_api_invariants(msgs: list[dict], cut: int) -> int:

    if cut <= 0 or cut >= len(msgs):
        return cut
    while cut > 0:
        kept = msgs[cut:]
        tu: set[str] = set()
        for m in kept:
            tu |= _ids(m, "tool_use", "id")
        orphan = False
        for m in kept:
            if not _ids(m, "tool_result", "tool_use_id") <= tu:
                orphan = True
                break
        if not orphan:
            return cut
        cut -= 1
    return cut


_CB_THRESHOLD = 3


def reinject_pinned(state: Any, summary: str, *, cut: int) -> None:

    msgs = state.messages
    pinned = []
    if state.original_task_idx is not None and 0 <= state.original_task_idx < cut:
        pinned = [msgs[state.original_task_idx]]
    boundary = {"role": "user", "content": [{"type": "text", "text": f"[Previous summary]{summary}"}]}
    state.messages = pinned + [boundary] + msgs[cut:]


class AutoCompactor:
    def __init__(self, client: Any, settings: Any) -> None:
        self._client = client
        self._s = settings

    async def _summarize(self, msgs: list[dict]) -> str:
        parts: list[str] = []
        async for ev in self._client.stream_messages(
            model=self._s.model,
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize the key state of the following conversation in three sentences:\n"
                    f"{json.dumps(msgs, ensure_ascii=False)}",
                }
            ],
            max_tokens=self._s.max_tokens,
            system="You compact conversation context. Return only the key state summary.",
            tools=None,
        ):
            if ev["type"] == "text":
                parts.append(ev["text"])
        return "".join(parts).strip()

    async def _summarize_ptl_safe(self, hist: list[dict]) -> str:

        try:
            s = await self._summarize(hist)
            if not s:
                raise RuntimeError("empty summary")
            return s
        except Exception:  # noqa: BLE001
            s = await self._summarize(hist[len(hist) // 2 :])
            if not s:
                raise RuntimeError("empty summary") from None
            return s

    async def compact(self, state: Any) -> None:
        track = state.auto_compact_tracking
        if track.get("consecutive_failures", 0) >= _CB_THRESHOLD:
            return
        keep = getattr(self._s, "compact_keep_recent", 2)
        n = len(state.messages)

        cut = adjust_index_to_preserve_api_invariants(state.messages, max(0, n - keep))
        if cut <= 0:
            return
        try:
            summary = await self._summarize_ptl_safe(state.messages[:cut])
        except Exception:  # noqa: BLE001
            track["consecutive_failures"] = track.get("consecutive_failures", 0) + 1
            return
        track["consecutive_failures"] = 0
        reinject_pinned(state, summary, cut=cut)
        state.transition = "auto_compact_done"


class MicroCompactor:
    def __init__(self, *, max_age_turns: int) -> None:
        self._max_age = max_age_turns

    def compact_local(self, state: Any) -> None:
        msgs = state.messages

        cutoff = len(msgs) - self._max_age * 2
        for i, m in enumerate(msgs):
            if i >= cutoff or m.get("role") != "user":
                continue
            c = m.get("content")
            if not isinstance(c, list):
                continue
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    b["content"] = "[old result cleared]"
        state.transition = "micro_compact_done"
