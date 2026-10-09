import pytest

from praxis2.agents.agent_tool import (
    AgentTool,
    SandboxWriteScope,
    fork_extract_subagent,
)
from praxis2.memory.extract import CAND_PREFIX
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore
from praxis2.tools.base import Tool
from praxis2.tools.registry import ToolRegistry


def test_agent_tool_is_registered_tool_subclass():
    assert issubclass(AgentTool, Tool)
    t = AgentTool()
    assert t.name == "AgentTool"
    reg = ToolRegistry()
    reg.register(t)
    assert reg.get("AgentTool") is t
    assert "input_schema" in dir(t)


def test_sandbox_write_scope_only_allows_candidate_prefix():
    sc = SandboxWriteScope(allowed_prefix=CAND_PREFIX)
    sc.check_write(f"{CAND_PREFIX}abc")
    with pytest.raises(PermissionError, match="Write scope"):
        sc.check_write("brain:Cryo/cases/c1")
    with pytest.raises(PermissionError):
        sc.check_write("any/other/key")


def test_subagent_identity_isolation_distinct_agent_id_and_sidechain():
    t = AgentTool()
    parent_id = "agent-parent"
    sub = t.fork_identity(parent_agent_id=parent_id)
    assert sub.agent_id != parent_id
    assert sub.sidechain_id != parent_id
    assert sub.parent_agent_id == parent_id


def test_discipline_agent_disallows_agent_tool_anti_recursion():

    t = AgentTool()
    assert t.is_disallowed_for_mode("discipline") is True
    assert t.is_disallowed_for_mode("general") is False


async def test_fork_extract_subagent_writes_only_candidate_region():
    store = InMemoryStore()
    ns = Namespace(user_id="u1", scope="session")
    transcript = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "t1",
                    "is_error": True,
                    "content": "\u5931\u8d25:\u4f9d\u8d56\u7f3a\u5931",
                }
            ],
        },
    ]
    rec: list[dict] = []
    n = await fork_extract_subagent(
        store,
        ns,
        transcript,
        trigger="tool_failure",
        transcript_sink=rec.append,
    )
    assert n >= 1

    raw = await store.kv_get(ns, f"{CAND_PREFIX}tool_failure-1")
    assert raw is not None

    assert any(e.get("type") == "subagent_extract" for e in rec)


async def test_fork_extract_subagent_cannot_write_brain_directly():

    sc = SandboxWriteScope(allowed_prefix=CAND_PREFIX)
    with pytest.raises(PermissionError):
        sc.check_write("brain:general/cases/x")
