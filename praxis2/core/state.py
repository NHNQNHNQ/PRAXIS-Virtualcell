import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class TerminalReason(StrEnum):
    STOP = "stop"
    MAX_TURNS = "max_turns"  # §7.1.1
    ABORTED = "aborted"  # §7.1.5
    ESCALATED = "escalated"
    ERROR = "error"


@dataclass
class QueryTracking:
    chain_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    depth: int = 0


@dataclass
class State:
    messages: list[dict] = field(default_factory=list)
    tool_use_context: dict = field(default_factory=dict)
    turn_count: int = 0
    transition: str | None = None
    auto_compact_tracking: dict = field(default_factory=lambda: {"consecutive_failures": 0})
    pending_tool_use_summary: str | None = None
    max_output_tokens_recovery_count: int = 0  # §7.1.4 #2

    max_tokens_boost: int = 0

    pending_stop_reasons: list[str] = field(default_factory=list)
    stop_hook_veto_count: int = 0
    last_assistant_text: str = ""
    recovery_attempts: int = 0
    tracking: QueryTracking = field(default_factory=QueryTracking)
    original_task_idx: int | None = None

    usage_total: dict = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})
