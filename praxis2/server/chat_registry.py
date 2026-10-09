"""Assemble generic tools for agent conversations."""

from praxis2.agents.agent_tool import AgentTool
from praxis2.agents.loader import AgentSelection
from praxis2.tools.brain_query import BrainQueryTool
from praxis2.tools.file_read import FileReadTool
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.rmcp_write import RMCPWriteCaseTool
from praxis2.tools.skill_exec import SkillExecTool
from praxis2.tools.web_fetch import WebFetchTool


def build_chat_registry(
    *,
    selection: AgentSelection | None = None,
    mcp_tools: "list | None" = None,
    bash_sandbox_root: "str | None" = None,
    bash_isolation: bool = False,
    bash_isolation_mask: str = "",
    bash_cgroup: bool = False,
    bash_cgroup_mem_mb: int = 1024,
    bash_cgroup_cpu_pct: int = 100,
    bash_netns: bool = False,
) -> ToolRegistry:

    reg = ToolRegistry()
    discipline = bool(selection and selection.is_discipline)
    if not discipline:
        reg.register(AgentTool())

    reg.register(SkillExecTool())

    reg.register(BrainQueryTool())

    reg.register(RMCPWriteCaseTool())

    reg.register(FileReadTool())
    reg.register(WebFetchTool())

    for mt in mcp_tools or []:
        reg.register(mt, builtin=False)

    if bash_sandbox_root:
        from pathlib import Path

        from praxis2.tools.bash import BashTool

        reg.register(
            BashTool(
                sandbox_root=Path(bash_sandbox_root),
                isolation=bash_isolation,
                isolation_mask=bash_isolation_mask,
                cgroup=bash_cgroup,
                cgroup_mem_mb=bash_cgroup_mem_mb,
                cgroup_cpu_pct=bash_cgroup_cpu_pct,
                netns=bash_netns,
            )
        )
    return reg
