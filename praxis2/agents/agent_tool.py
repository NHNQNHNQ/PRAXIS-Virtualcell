"""Describe isolated subagent tasks and constrain their write scopes."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from praxis2.memory.extract import extract_candidates, persist_candidates
from praxis2.store.base import Namespace, Store
from praxis2.tools.base import Tool, ToolResult


@dataclass
class SubAgentIdentity:
    agent_id: str
    sidechain_id: str
    parent_agent_id: str


class SandboxWriteScope:
    def __init__(self, *, allowed_prefix: str) -> None:
        self._prefix = allowed_prefix

    def check_write(self, key: str) -> None:
        if not key.startswith(self._prefix):
            raise PermissionError(
                f"Write scope denied for key {key!r}outside allowed prefix {self._prefix!r}"
                f"(extraction agents may write only to the candidate inbox)"
            )


class AgentTool(Tool):
    name = "AgentTool"
    description = (
        "Describe an isolated subagent task with its own "
        "identity, context, and token budget. The returne"
        "d descriptor does not represent a completed anal"
        "ysis or final result."
    )
    rmcp_op = None

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": ("Complete task prompt for the subagent descriptor"),
                },
                "discipline": {
                    "type": "string",
                    "description": ("Optional subagent brain, such as virtualcell; otherwise use general routing"),
                },
                "write_prefix": {
                    "type": "string",
                    "description": ("Optional subagent write prefix; default _candidate/"),
                },
                "suggested_model": {
                    "type": "string",
                    "description": ("Optional model identifier supported by the configured provider"),
                },
            },
            "required": ["task"],
        }

    def fork_identity(self, *, parent_agent_id: str) -> SubAgentIdentity:
        sid = uuid.uuid4().hex
        return SubAgentIdentity(
            agent_id=f"sub-{sid}",
            sidechain_id=f"sidechain-{sid}",
            parent_agent_id=parent_agent_id,
        )

    def is_disallowed_for_mode(self, mode: str) -> bool:

        return mode == "discipline"

    async def run(self, payload: dict[str, Any]) -> ToolResult:

        task = (payload.get("task") or "").strip()
        if not task:
            return ToolResult(
                ok=False,
                error="Missing required task prompt",
            )

        discipline = (payload.get("discipline") or "").strip().lower() or None
        write_prefix = payload.get("write_prefix") or "_candidate/"
        suggested_model = (payload.get("suggested_model") or "").strip() or "deepseek-v4-flash"

        sub = self.fork_identity(parent_agent_id="<calling-agent>")
        descriptor = {
            "prompt": task,
            "discipline": discipline,
            "suggested_model": suggested_model,
            "write_prefix": write_prefix,
            "sub_agent_id": sub.agent_id,
            "sidechain_id": sub.sidechain_id,
        }
        return ToolResult(
            ok=True,
            value={
                "task_descriptor": descriptor,
                "spawn_endpoint": "/api/spawn/post",
                "spawn_payload_template": {
                    "prompt": task,
                    "model": suggested_model,
                },
                "next_action": (
                    "Constructed subagent task descriptor, sub_agent_"
                    "id="
                    f"{sub.agent_id}"
                    ". Pass the descriptor to a configured executor a"
                    "nd collect its result before reporting completio"
                    "n."
                ),
            },
        )


async def fork_extract_subagent(
    store: Store,
    ns: Namespace,
    transcript: list[dict],
    *,
    trigger: str,
    transcript_sink: Callable[[dict], None] | None = None,
) -> int:

    from praxis2.memory.extract import CAND_PREFIX

    scope = SandboxWriteScope(allowed_prefix=CAND_PREFIX)
    cands = extract_candidates(transcript, trigger=trigger)
    for c in cands:
        scope.check_write(f"{CAND_PREFIX}{c.id}")
    await persist_candidates(store, ns, cands)
    if transcript_sink is not None:
        transcript_sink(
            {
                "type": "subagent_extract",
                "trigger": trigger,
                "candidates": len(cands),
                "sandbox": CAND_PREFIX,
            }
        )
    return len(cands)
