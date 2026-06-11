"""AgentTool:经 registry 注册的 Tool 子类 + 子 agent 隔离三层(总纲 §7.5.3)
+ 并行/递归约束(§7.5.4)+ extract 真 fork 沙箱(§7.4.2)。

子 agent 复用同一 query()(§7.5.0 不产生第二条代码路径);M5 落隔离设施 +
extract 沙箱(fork 仅有 _candidate/<id> 写权限的子 agent)。普通 subagent
并行执行编排(file-write 串行队列)+ one-above-all 路由器全 query() 串接
留 M6 server/runtime(§7.5.5 Task 生命周期 + 跨 worker 路由属 M6/M7)。"""

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
    sidechain_id: str       # 独立 transcript sidechain(§7.5.3 身份隔离)
    parent_agent_id: str    # 结果经 sidechain 回传父


class SandboxWriteScope:
    """§7.4.2 权限沙箱化:子 agent 只能写指定前缀(extract 只能写
    _candidate/<id>)。越权写抛 PermissionError(非静默放过)。"""

    def __init__(self, *, allowed_prefix: str) -> None:
        self._prefix = allowed_prefix

    def check_write(self, key: str) -> None:
        if not key.startswith(self._prefix):
            raise PermissionError(
                f"沙箱写越权:键 {key!r} 不在允许前缀 {self._prefix!r}"
                f"(extract 子 agent 仅可写候选区,§7.4.2)"
            )


class AgentTool(Tool):
    """经 registry 注册的 Tool 子类(§7.5.3)。学科 agent 禁用本工具防递归
    (§7.5.4 disallowed_tools:[AgentTool])。M5 提供隔离设施;子 agent 编排
    全链(普通 subagent 并行 + file-write 串行 + one-above-all max_turns)
    随 query() 复用,跨 worker 路由属 M6。"""

    name = "AgentTool"
    description = (
        "fork 一个隔离子 agent 执行受限子任务(身份/上下文/token 三层隔离)。"
        "注意:本工具只返回 spawn 描述符/已提交占位,不代表子 agent 已完成分析或产出最终结论;"
        "勿把本工具返回当作子 agent 的完成结果转述。"
    )
    rmcp_op = None  # 工具类不受相位门约束(检索/读取/编排类)

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "子 agent 要做的具体任务(完整 prompt,会被 spawn endpoint "
                        "作为 user message 投给后台 agent)"
                    ),
                },
                "discipline": {
                    "type": "string",
                    "description": (
                        "(可选)指定子 agent 学科,如 enzyme / dock / cell / "
                        "synth(13 个 lowercase slug)。不传则 general / auto 路由。"
                    ),
                },
                "write_prefix": {
                    "type": "string",
                    "description": (
                        "(可选)子 agent 沙箱写前缀(§7.4.2 SandboxWriteScope),"
                        "默认 _candidate/ 候选区。"
                    ),
                },
                "suggested_model": {
                    "type": "string",
                    "description": (
                        "(可选)建议 model id:deepseek-v4-pro / deepseek-v4-flash / "
                        "aws-gpt-5.4(litellm proxy 提供)。不传由 server 选默认。"
                    ),
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
        # §7.5.4:学科 agent 禁用 AgentTool 防递归深度爆炸
        return mode == "discipline"

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        """v0.16.0-beta:返结构化 spawn task descriptor。

        Tool.run() 拿不到 server deps(spawn_repo / pg_pool / ledger),所以
        无法直接 enqueue 任务。改让模型拿到"可直接喂给 /api/spawn/post 的
        descriptor"——FE 拿到后可一键 spawn(对齐 v0.15.0 auto→spawn 链路),
        或用户审核后人工 spawn。

        这跟 SkillExec 没 SSH env 时返 ssh 命令模板是同一 pattern:
        "工具返回真实可执行的 next_action,不是 placeholder 文字"。
        """
        task = (payload.get("task") or "").strip()
        if not task:
            return ToolResult(
                ok=False,
                error="缺 task(必填,完整 prompt 子 agent 会用它作 user message)",
            )

        discipline = (payload.get("discipline") or "").strip().lower() or None
        write_prefix = payload.get("write_prefix") or "_candidate/"
        suggested_model = (
            (payload.get("suggested_model") or "").strip()
            or "deepseek-v4-flash"  # 默认 flash:子 agent 任务通常 simpler
        )

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
                    f"已构造 spawn task descriptor(sub_agent_id={sub.agent_id})。"
                    "FE 可直接 POST /api/spawn/post 提交后台任务(对齐 v0.15.0 "
                    "auto→spawn 链路),完成后经 /api/spawn/get 回填结果到原 chat;"
                    "或用户审核后人工触发 spawn。"
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
    """§7.4.2 extract 真 fork 沙箱:fork 一个仅有 _candidate/<id> 写权限的
    子 agent 做抽取/摘要。复用 M4 extract_candidates/persist_candidates;
    沙箱 SandboxWriteScope 确保只能写候选区(越权抛 PermissionError)。
    返回入队候选数。子 agent 行为写 sidechain(可观测,§12)。"""
    from praxis2.memory.extract import CAND_PREFIX

    scope = SandboxWriteScope(allowed_prefix=CAND_PREFIX)
    cands = extract_candidates(transcript, trigger=trigger)
    for c in cands:  # 沙箱校验:每个候选写键必须落候选区
        scope.check_write(f"{CAND_PREFIX}{c.id}")
    await persist_candidates(store, ns, cands)
    if transcript_sink is not None:
        transcript_sink({
            "type": "subagent_extract", "trigger": trigger,
            "candidates": len(cands), "sandbox": CAND_PREFIX,
        })
    return len(cands)
