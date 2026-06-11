"""chat-stream 启动时的 ToolRegistry 组装(TEST-AGENT-FRAMEWORK.md §5)。

修复点:此前 app.py:_chat_stream 里 `reg = ToolRegistry()` 后没有任何 register
调用,导致 query() 给 Anthropic API 的 `tools=[]` 永远为空,模型无法发起
`tool_use`。本模块把组装独立为可单测函数,并接入 mode-aware 过滤
(discipline 模式禁用 AgentTool 防递归,§7.5.4)。

v0.9.2 carry:BrainQueryTool / SkillExecTool / RMCPWriteCaseTool /
RMCPPromoteTool / MemoryRecallTool 尚无 Tool 子类实体,补全后在此追加 register。
"""

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
    """组装单次 chat-stream 请求用的 ToolRegistry。
    每次请求独立实例(避免跨请求状态泄漏)。

    selection=None  → 安全默认:注册 AgentTool(用于 chat-stream 未接入
        resolve_agent 的旧调用点或测试)。
    selection.is_discipline=True → 学科 agent,**不** 注册 AgentTool
        (§7.5.4 防递归深度爆炸)。
    其他 selection → 注册 AgentTool。

    v0.16.0:加挂 BrainQuery + RMCPWriteCase,消除"system prompt 里列了 brain
    但没工具能查/写"的幻觉缺口(智能体只能纯文字回答 → 现在能 tool_use)。

    v0.17:新增 mcp_tools 参数(默认 None),把外部 MCP server 暴露的工具
    (MCPTool,mcp__<server>__<tool> 命名)以 builtin=False 挂入。不传则零回归。

    v0.17 子项目2:bash_sandbox_root 非 None 时注册 BashTool(沙盒根=该路径);
    None=不启用(零回归)。

    v0.18 子项目1:bash_isolation/bash_isolation_mask 透传 BashTool(默认 False/"");
    app.py 负责 fail-closed 判断(userns 不可用则不传 bash_sandbox_root)。

    v0.18 子项目2:bash_cgroup/mem_mb/cpu_pct 透传 BashTool(默认 False/1024/100);
    app.py 负责 fail-open 判断(scope 不可用 → bash_cgroup=False,Bash 仍注册)。

    v0.18 子项目3:bash_netns 透传 BashTool(默认 False);
    app.py 负责 fail-closed 判断(netns 不可用 → 不传 bash_sandbox_root)。
    """
    reg = ToolRegistry()
    discipline = bool(selection and selection.is_discipline)
    if not discipline:
        reg.register(AgentTool())
    # SkillExec 所有模式都注册(包括 discipline):学科 agent 的核心动作就是
    # 调用本学科 skill。AgentTool 在 discipline 模式禁用(防 fork 递归),
    # 但 SkillExec 是"调本学科子工具",不会递归。
    reg.register(SkillExecTool())
    # BrainQuery 所有模式都注册:检索 brain(cases/rules/skills/neg_cases)
    # 是 RMCP retrieve 相位的核心动作,任何模式都该有。rmcp_op=None,
    # 检索类不受相位门约束。
    reg.register(BrainQueryTool())
    # RMCPWriteCase 所有模式都注册:SEAL 相位的 write_case op(rmcp.py:43-45)。
    # 没有这个工具,模型在 SEAL 相位只能纯文字描述"应该把这个 case 存起来"
    # (幻觉),无法真正落库。第一版写到 _proposed inbox 等审核。
    reg.register(RMCPWriteCaseTool())
    # v0.16.0-beta 加挂 3 个工具,补齐 P0 5/5:
    # FileRead:沙盒读 repo 内 brains/+docs/(模型能查 SKILL.md / case markdown 原文)
    # WebFetch:白名单 GET(doi/arxiv/pubmed/uniprot/rcsb/wikipedia/nature.com 等)
    # (AgentTool.run() 已在本提交强化:返 spawn task descriptor 而非 placeholder)
    reg.register(FileReadTool())
    reg.register(WebFetchTool())
    # v0.17:挂 MCP 工具(外部 server,mcp__<server>__<tool> 命名)。
    # builtin=False:同名内建优先(命名前缀已防冲突,此为双保险);
    # 不传 mcp_tools → 零回归(行为 == v0.16)。
    for mt in mcp_tools or []:
        reg.register(mt, builtin=False)
    # v0.17 子项目2:有 sandbox 根才注册 BashTool(opt-in;无值=不启用,零回归)
    # v0.18 子项目1:透传 isolation 参数;fail-closed 由 app.py 在调用前判断。
    if bash_sandbox_root:
        from pathlib import Path

        from praxis2.tools.bash import BashTool
        reg.register(BashTool(
            sandbox_root=Path(bash_sandbox_root),
            isolation=bash_isolation,
            isolation_mask=bash_isolation_mask,
            cgroup=bash_cgroup,
            cgroup_mem_mb=bash_cgroup_mem_mb,
            cgroup_cpu_pct=bash_cgroup_cpu_pct,
            netns=bash_netns,
        ))
    return reg
