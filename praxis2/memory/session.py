"""Session 持久化 + resume(总纲 §7.4.3/.4/.6)。append-only,经 store 抽象不落本地盘。
transcript 整序列 JSON 进 blob;UUID 去重保证并发追加幂等。"""

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
    phase: str | None = None  # RMCP 相位(§7.4.6;phase-transition entry 必填)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid, "type": self.type, "content": self.content,
            "userId": self.user_id, "sessionId": self.session_id,
            "parentUuid": self.parent_uuid, "phase": self.phase,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(d: dict) -> "SessionEntry":
        return SessionEntry(
            uuid=d["uuid"], type=d["type"], content=d["content"],
            user_id=d["userId"], session_id=d["sessionId"],
            parent_uuid=d.get("parentUuid"), phase=d.get("phase"),
            timestamp=d.get("timestamp", 0.0),  # 旧/损坏记录时间未知,回落 0.0
        )


class SessionStore:
    """transcript 经 store.blob 持久化;一个 session 一个 blob(整序列 JSON)。"""

    def __init__(self, store: Store) -> None:
        self._store = store

    def _ns(self, user_id: str) -> Namespace:
        return Namespace(user_id=user_id, scope="transcript")

    async def load_transcript(
        self, *, user_id: str, session_id: str
    ) -> list[SessionEntry]:
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
                continue  # 损坏行跳过(§7.4.4),不整会话失败
            if e.uuid in seen:
                continue  # 读侧 UUID 去重(§7.4.3 idempotency):写侧已 append-only
            seen.add(e.uuid)
            out.append(e)
        return out

    async def append_entry(self, entry: SessionEntry) -> None:
        """O(1) 单条原子追加(reviewer M1 C1 修复)。

        旧实现:load 整盘 → 写侧 dedup → put 整盘 → O(K²) 读写 + 并发互相覆盖。
        新实现:序列化一行 → blob_append 原子追加 → O(1) + 并发无丢失。
        UUID dedup 移到 load_transcript 读侧,对外契约保留(重复 UUID 仍只看到一次)。
        """
        if entry.type not in _LEGAL_TYPES:
            raise ValueError(f"非法 entry.type={entry.type!r}(progress/未完成 tool_use 不入库)")
        line = json.dumps(entry.to_dict(), ensure_ascii=False) + "\n"
        await self._store.blob_append(
            self._ns(entry.user_id), entry.session_id, line.encode()
        )


async def record_phase_transition(
    ss: SessionStore, *, user_id: str, session_id: str,
    to: Phase, uuid_: str, parent: str | None = None,
) -> None:
    """相位跃迁落 transcript(§7.4.6):一条 phase-transition entry。"""
    await ss.append_entry(SessionEntry(
        uuid=uuid_, type="phase-transition", content={"to": to.value},
        user_id=user_id, session_id=session_id, parent_uuid=parent,
        phase=to.value,
    ))


async def rebuild_phase(
    ss: SessionStore, state: State, *, user_id: str, session_id: str
) -> None:
    """从最后一条 phase-transition 恢复相位(§7.4.6;不从消息历史反推)。"""
    seq = await ss.load_transcript(user_id=user_id, session_id=session_id)
    last = None
    for e in seq:
        if e.type == "phase-transition" and e.phase:
            last = e.phase
    if last is not None:
        set_phase(state, Phase(last))


def apply_snip_removals(seq: list[SessionEntry]) -> list[SessionEntry]:
    """§7.4.4#1:parent 指向已删(不在序列)的孤立消息接回最近存活祖先;
    无更早存活者则置根(parent=None)。原序不变,只改 parent_uuid。"""
    alive = {e.uuid for e in seq}
    for i, e in enumerate(seq):
        if e.parent_uuid is not None and e.parent_uuid not in alive:
            # 最近存活祖先 = 序列中本条之前最后一个 entry
            e.parent_uuid = seq[i - 1].uuid if i > 0 else None
    return seq


def _is_boundary(e: SessionEntry) -> bool:
    return (
        e.type == "system"
        and isinstance(e.content, dict)
        and e.content.get("compact_boundary") is True
    )


def apply_preserved_segment_relinks(
    seq: list[SessionEntry],
) -> list[SessionEntry]:
    """§7.4.4#2:compact boundary 后首条若 parent 指向被压段(不在序列),
    重接到 boundary entry。无 boundary 即 no-op。"""
    alive = {e.uuid for e in seq}
    for i, e in enumerate(seq):
        if _is_boundary(e) and i + 1 < len(seq):
            nxt = seq[i + 1]  # 只重接 boundary 之后第一条
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
    """§7.4.4#3:重建 API messages;孤儿 tool_result 丢弃、缺失补占位 error;
    末条未完成 assistant(有 tool_use 无对应 result)→ needs_continue=True。"""
    # 收集所有出现过的 tool_use id
    seen_tu: set[str] = set()
    for e in seq:
        for b in _blocks(e.content, "tool_use"):
            seen_tu.add(b["id"])
    messages: list[dict] = []
    answered: set[str] = set()
    for e in seq:
        if e.type == "phase-transition" or _is_boundary(e):
            continue  # 不入 API messages(boundary 的 summary 由 compact 重注负责)
        if e.type == "assistant":
            messages.append({"role": "assistant", "content": e.content})
        elif e.type == "user":
            trs = _blocks(e.content, "tool_result")
            if trs:
                kept = [t for t in trs if t["tool_use_id"] in seen_tu]
                for t in kept:
                    answered.add(t["tool_use_id"])
                if kept:  # 全孤儿丢弃后勿留空 content(Anthropic API 拒 content=[])
                    messages.append({"role": "user", "content": kept})
            else:
                messages.append({"role": "user", "content": e.content})
        elif e.type in ("system", "attachment"):
            messages.append({"role": "user", "content": e.content})
    # 缺失 tool_result 补占位 error(防 API orphaned tool_use 400)
    missing = seen_tu - answered
    if missing:
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": i, "is_error": True,
             "content": "[resume:工具结果丢失,已占位]"} for i in sorted(missing)
        ]})
    # 中断检测:末条 entry 是 assistant 且其 tool_use 全无 result
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
    dropped_lines: int  # load_transcript 跳过的损坏行(§7.4.4)


async def resume(
    ss: SessionStore, state: State, *, user_id: str, session_id: str
) -> ResumeResult:
    """§7.4.4 完整编排:去重→snip→relink→孤儿配对→中断注入→相位重建。
    SessionStart hook 重跑留 M6(独立 HookManager,§7.6.1 已校准)。"""
    raw = await ss._store.blob_get(ss._ns(user_id), session_id)
    total_lines = 0 if raw is None else len([
        x for x in raw.decode().splitlines() if x.strip()
    ])
    seq = await ss.load_transcript(user_id=user_id, session_id=session_id)
    dropped = total_lines - len(seq)
    seq = apply_snip_removals(seq)
    seq = apply_preserved_segment_relinks(seq)
    messages, needs_continue = recover_orphaned_parallel_tool_results(seq)
    if needs_continue:
        messages.append({"role": "user", "content": "[resume] 上一轮未完成,请继续"})
    state.messages = messages
    await rebuild_phase(ss, state, user_id=user_id, session_id=session_id)
    return ResumeResult(
        messages_count=len(messages), needs_continue=needs_continue,
        phase=get_phase(state).value, dropped_lines=dropped,
    )
