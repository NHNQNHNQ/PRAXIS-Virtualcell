"""Persist and resume completed conversation entries without incomplete tool calls."""

import json
import time
from dataclasses import dataclass, field

from praxis2.core.rmcp import Phase, get_phase, set_phase
from praxis2.core.state import State
from praxis2.store.base import Namespace, Store

_LEGAL_TYPES = {"user", "assistant", "system", "attachment", "phase-transition"}


@dataclass
class SessionEntry:
    uuid: str
    type: str
    content: object
    user_id: str
    session_id: str
    parent_uuid: str | None = None
    phase: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "type": self.type,
            "content": self.content,
            "userId": self.user_id,
            "sessionId": self.session_id,
            "parentUuid": self.parent_uuid,
            "phase": self.phase,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(d: dict) -> "SessionEntry":
        return SessionEntry(
            uuid=d["uuid"],
            type=d["type"],
            content=d["content"],
            user_id=d["userId"],
            session_id=d["sessionId"],
            parent_uuid=d.get("parentUuid"),
            phase=d.get("phase"),
            timestamp=d.get("timestamp", 0.0),
        )


class SessionStore:
    def __init__(self, store: Store) -> None:
        self._store = store

    def _ns(self, user_id: str) -> Namespace:
        return Namespace(user_id=user_id, scope="transcript")

    async def load_transcript(self, *, user_id: str, session_id: str) -> list[SessionEntry]:
        raw = await self._store.blob_get(self._ns(user_id), session_id)
        if raw is None:
            return []
        out: list[SessionEntry] = []
        seen: set[str] = set()
        for line in raw.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = SessionEntry.from_dict(json.loads(line))
            except (ValueError, KeyError):
                continue
            if e.uuid in seen:
                continue
            seen.add(e.uuid)
            out.append(e)
        return out

    async def append_entry(self, entry: SessionEntry) -> None:

        if entry.type not in _LEGAL_TYPES:
            raise ValueError(
                f"Invalid entry.type={entry.type!r}(progress and incomplete tool_use entries are not persisted)"
            )
        line = json.dumps(entry.to_dict(), ensure_ascii=False) + "\n"
        await self._store.blob_append(self._ns(entry.user_id), entry.session_id, line.encode())


async def record_phase_transition(
    ss: SessionStore,
    *,
    user_id: str,
    session_id: str,
    to: Phase,
    uuid_: str,
    parent: str | None = None,
) -> None:

    await ss.append_entry(
        SessionEntry(
            uuid=uuid_,
            type="phase-transition",
            content={"to": to.value},
            user_id=user_id,
            session_id=session_id,
            parent_uuid=parent,
            phase=to.value,
        )
    )


async def rebuild_phase(ss: SessionStore, state: State, *, user_id: str, session_id: str) -> None:

    seq = await ss.load_transcript(user_id=user_id, session_id=session_id)
    last = None
    for e in seq:
        if e.type == "phase-transition" and e.phase:
            last = e.phase
    if last is not None:
        set_phase(state, Phase(last))


def apply_snip_removals(seq: list[SessionEntry]) -> list[SessionEntry]:

    alive = {e.uuid for e in seq}
    for i, e in enumerate(seq):
        if e.parent_uuid is not None and e.parent_uuid not in alive:
            e.parent_uuid = seq[i - 1].uuid if i > 0 else None
    return seq


def _is_boundary(e: SessionEntry) -> bool:
    return e.type == "system" and isinstance(e.content, dict) and e.content.get("compact_boundary") is True


def apply_preserved_segment_relinks(
    seq: list[SessionEntry],
) -> list[SessionEntry]:

    alive = {e.uuid for e in seq}
    for i, e in enumerate(seq):
        if _is_boundary(e) and i + 1 < len(seq):
            nxt = seq[i + 1]
            if nxt.parent_uuid is not None and nxt.parent_uuid not in alive:
                nxt.parent_uuid = e.uuid
    return seq


def _blocks(content: object, kind: str) -> list[dict]:
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") == kind]


def recover_orphaned_parallel_tool_results(
    seq: list[SessionEntry],
) -> tuple[list[dict], bool]:

    seen_tu: set[str] = set()
    for e in seq:
        for b in _blocks(e.content, "tool_use"):
            seen_tu.add(b["id"])
    messages: list[dict] = []
    answered: set[str] = set()
    for e in seq:
        if e.type == "phase-transition" or _is_boundary(e):
            continue
        if e.type == "assistant":
            messages.append({"role": "assistant", "content": e.content})
        elif e.type == "user":
            trs = _blocks(e.content, "tool_result")
            if trs:
                kept = [t for t in trs if t["tool_use_id"] in seen_tu]
                for t in kept:
                    answered.add(t["tool_use_id"])
                if kept:
                    messages.append({"role": "user", "content": kept})
            else:
                messages.append({"role": "user", "content": e.content})
        elif e.type in ("system", "attachment"):
            messages.append({"role": "user", "content": e.content})

    missing = seen_tu - answered
    if missing:
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": i,
                        "is_error": True,
                        "content": "[resume: missing tool result placeholder]",
                    }
                    for i in sorted(missing)
                ],
            }
        )

    needs_continue = False
    if seq:
        last = seq[-1]
        if last.type == "assistant":
            tu = {b["id"] for b in _blocks(last.content, "tool_use")}
            if tu and not (tu & answered):
                needs_continue = True
    return messages, needs_continue


@dataclass
class ResumeResult:
    messages_count: int
    needs_continue: bool
    phase: str
    dropped_lines: int


async def resume(ss: SessionStore, state: State, *, user_id: str, session_id: str) -> ResumeResult:

    raw = await ss._store.blob_get(ss._ns(user_id), session_id)
    total_lines = 0 if raw is None else len([x for x in raw.decode().splitlines() if x.strip()])
    seq = await ss.load_transcript(user_id=user_id, session_id=session_id)
    dropped = total_lines - len(seq)
    seq = apply_snip_removals(seq)
    seq = apply_preserved_segment_relinks(seq)
    messages, needs_continue = recover_orphaned_parallel_tool_results(seq)
    if needs_continue:
        messages.append({"role": "user", "content": "[resume] The previous turn was incomplete; continue it"})
    state.messages = messages
    await rebuild_phase(ss, state, user_id=user_id, session_id=session_id)
    return ResumeResult(
        messages_count=len(messages),
        needs_continue=needs_continue,
        phase=get_phase(state).value,
        dropped_lines=dropped,
    )
