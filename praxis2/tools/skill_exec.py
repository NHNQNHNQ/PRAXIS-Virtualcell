"""SkillExecTool:模型可调用的 skill 调度工具(PLAN §11 闭环最后一步)。

此前 chat_registry 只挂 AgentTool → 智能体看见 system prompt 里的 skill 名,
但没工具能"调用"它,只能回话 fall-through(用户最终拿不到具体方案)。
本工具补上"调用"动作。

行为分两路:
1. **可执行 skill**(目录里有 run.py + host_env 已装):返回 "to execute"
   的 conda + ssh 真命令,后续 M7 接 SubprocessSkillExecutor / SSHExecutor
   后切到真跑。
2. **文档-only skill**(没 run.py):返回 SKILL.md 的 SOP 摘要 + 预填好的
   `conda activate <env> && ...` 起手命令。

无论哪条,**模型都得到结构化回执**,可以基于"这是用户在 .53 上要跑的步骤"
继续把方案讲清楚 / 把参数填具体 / 引用 SKILL.md 输入契约。
"""
from __future__ import annotations

import asyncio
import json
import os
import shlex
from pathlib import Path
from typing import Any

from praxis2.tools.base import Tool, ToolResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"

# 真 ssh 执行三件套(均通过 env var 注入,缺一即降级到只返回 SOP)
_ENV_SSH_HOST = "PRAXIS_SKILL_SSH_HOST"         # e.g. zkyd@10.102.106.53
_ENV_REMOTE_BRAINS = "PRAXIS_SKILL_REMOTE_BRAINS"  # e.g. /home/zkyd/data1/mzy/praxis2-brains
_ENV_CONDA_INIT = "PRAXIS_SKILL_CONDA_INIT"     # e.g. /home/zkyd/software/miniconda3/etc/profile.d/conda.sh
_ENV_TIMEOUT = "PRAXIS_SKILL_TIMEOUT_S"         # 默认 300


def _find_skill_dir(name: str, brain_hint: str | None = None) -> Path | None:
    """按 skill 目录名定位 brains/<brain>/skills/workflows/<name>/。优先 brain_hint。"""
    if brain_hint:
        cand = _BRAINS_ROOT_DEFAULT / brain_hint / "skills" / "workflows" / name
        if cand.is_dir():
            return cand
    for brain_dir in _BRAINS_ROOT_DEFAULT.iterdir():
        cand = brain_dir / "skills" / "workflows" / name
        if cand.is_dir():
            return cand
    return None


def _parse_frontmatter_field(text: str, key: str) -> str | None:
    if not text.startswith("---"):
        return None
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None


def _extract_sop_excerpt(skill_md_text: str, max_chars: int = 1200) -> str:
    """抓 SOP/SOP 等小节作为可执行步骤;失败则 fallback 取 body 前若干字符。"""
    # 去 frontmatter
    if skill_md_text.startswith("---"):
        parts = skill_md_text.split("---", 2)
        body = parts[2] if len(parts) >= 3 else skill_md_text
    else:
        body = skill_md_text
    # 找 ## SOP 或 ## 跑法 段
    lines = body.splitlines()
    target_headers = ("## SOP", "## 跑法", "## 简单跑法", "## 用法", "## How to run")
    start = None
    for i, ln in enumerate(lines):
        for h in target_headers:
            if ln.strip().startswith(h):
                start = i
                break
        if start is not None:
            break
    if start is None:
        # 截 body 前若干字符兜底
        return body.strip()[:max_chars]
    # 取到下一个 ## 为止
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()[:max_chars]


class SkillExecTool(Tool):
    """让模型用名字调起 brain skill。

    M5 carry(v0.9.2):此前 chat_registry 注释里点名了它要建,本次落地。
    第一版:返回 "to-execute" 指令包(SOP + 预填命令);run.py 真存在时
    可由 SchedulerRegistry 接 SubprocessSkillExecutor 真跑 — 本工具留 hook
    在 value['execution_plan'] 里。
    """

    name = "SkillExec"
    description = (
        "调用大脑里的一个 skill 来推进分析。输入 skill 名(如 vina_gnina_dock)+ 输入参数 dict;"
        "返回 staging .53 上要跑的 conda + 命令,以及 SOP 摘要;若 skill 已装 run.py 则可真跑。"
    )
    rmcp_op = "call_skill"  # §7.3.7:写/执行类显式声明;须 ∈ ALLOWED_OPS[EXECUTE]={"call_skill"}

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "skill 目录名(SKILL.md frontmatter 的 name 字段),例: vina_gnina_dock",
                },
                "brain": {
                    "type": "string",
                    "description": "(可选)skill 所属 brain(cell/dock/enzyme/...),不传则全 brain 搜",
                },
                "inputs": {
                    "type": "object",
                    "description": "skill 的输入参数 dict;按 SKILL.md 的 inputs 契约填",
                    "additionalProperties": True,
                },
            },
            "required": ["name"],
        }

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        name = payload.get("name") or ""
        brain_hint = payload.get("brain")
        inputs = payload.get("inputs") or {}

        if not name:
            return ToolResult(ok=False, error="缺 skill name(必填),例: vina_gnina_dock")

        skill_dir = _find_skill_dir(name, brain_hint=brain_hint)
        if skill_dir is None:
            return ToolResult(
                ok=False,
                error=(
                    f"未找到 skill 目录 brains/*/skills/workflows/{name}/。"
                    "请用 system prompt 里列出的精确名(SKILL.md 的 name 字段),"
                    "或传 brain 参数(cell/dock/enzyme/...)。"
                ),
                recovery_hint="先看 system prompt 的 # 可用 skill 摘要,挑里面已列出的名字。",
            )

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            return ToolResult(ok=False, error=f"skill 目录 {skill_dir} 缺 SKILL.md")

        text = skill_md.read_text(encoding="utf-8")
        host_env = _parse_frontmatter_field(text, "host_env")
        status = _parse_frontmatter_field(text, "status")
        # skill brain 由路径反推
        brain = skill_dir.parent.parent.parent.name
        rel = skill_dir.relative_to(_BRAINS_ROOT_DEFAULT)
        sop = _extract_sop_excerpt(text)

        has_run_py = (skill_dir / "run.py").is_file()

        execution_plan = {
            "brain": brain,
            "skill": name,
            "host_env": host_env,
            "status": status,
            "skill_md_path": f"brains/{rel}/SKILL.md",
            "has_run_py": has_run_py,
            "inputs": inputs,
        }

        if not host_env:
            return ToolResult(
                ok=False,
                error=(
                    f"skill `{name}` 未在 SKILL.md frontmatter 标 host_env: → "
                    f"无法定位 .53 上的 conda env。请补 frontmatter。"
                ),
                value={"execution_plan": execution_plan, "sop": sop},
            )

        # ---- 真 ssh 执行分支 ----
        ssh_host = os.environ.get(_ENV_SSH_HOST)
        remote_brains = os.environ.get(_ENV_REMOTE_BRAINS)
        conda_init = os.environ.get(_ENV_CONDA_INIT)
        timeout_s = float(os.environ.get(_ENV_TIMEOUT, "300"))

        can_exec = bool(ssh_host and remote_brains and conda_init and has_run_py)

        if can_exec:
            result = await self._exec_via_ssh(
                ssh_host=ssh_host,
                conda_init=conda_init,
                host_env=host_env,
                remote_brains=remote_brains,
                rel=str(rel),
                inputs=inputs,
                timeout_s=timeout_s,
            )
            execution_plan["exec_via"] = f"ssh {ssh_host}"
            value = {
                "execution_plan": execution_plan,
                **result,
            }
            return ToolResult(ok=result.get("ok", False), value=value, error=result.get("error"))

        # ---- 降级:返回 SOP + ssh 命令模板,让用户/模型自行推进 ----
        host_for_display = ssh_host or "zkyd@10.102.106.53"
        brains_for_display = remote_brains or "/home/zkyd/data1/mzy/praxis2-brains"
        conda_for_display = conda_init or "/home/zkyd/software/miniconda3/etc/profile.d/conda.sh"

        cmd_lines = [
            "# 在 staging .53 上跑:",
            f"ssh {host_for_display} 'bash -lc \"",
            f"  source {conda_for_display} && \\",
            f"  conda activate {host_env} && \\",
            f"  cd {brains_for_display} && \\",
        ]
        if has_run_py:
            inputs_json = json.dumps(inputs, ensure_ascii=False)
            cmd_lines.append(f"  echo {inputs_json!r} | python {rel}/run.py")
        else:
            cmd_lines.append(
                "  # 注意:本 skill 目前是文档-only(无 run.py),按下方 SOP 手动执行"
            )
        cmd_lines.append('"\'')

        why_not_exec = []
        if not has_run_py:
            why_not_exec.append("skill 目录缺 run.py(文档-only)")
        if not ssh_host:
            why_not_exec.append(f"未设 {_ENV_SSH_HOST} 环境变量")
        if not remote_brains:
            why_not_exec.append(f"未设 {_ENV_REMOTE_BRAINS}")
        if not conda_init:
            why_not_exec.append(f"未设 {_ENV_CONDA_INIT}")

        value = {
            "execution_plan": execution_plan,
            "ssh_command_template": "\n".join(cmd_lines),
            "sop_excerpt": sop,
            "exec_via": "manual (no auto-exec)",
            "why_not_executed": "; ".join(why_not_exec),
            "next_action": (
                "本工具未自动执行,返回 SOP + 预填 ssh 命令。"
                f"接入自动执行:设 {_ENV_SSH_HOST}/{_ENV_REMOTE_BRAINS}/{_ENV_CONDA_INIT} 并补 run.py。"
            ),
        }
        return ToolResult(ok=True, value=value)

    async def _exec_via_ssh(
        self,
        *,
        ssh_host: str,
        conda_init: str,
        host_env: str,
        remote_brains: str,
        rel: str,
        inputs: dict,
        timeout_s: float,
    ) -> dict:
        """真 ssh 执行:Mac → ssh .53 → conda activate <env> → python run.py < stdin."""
        # 远端命令:source conda + activate env + cd brains + run python with stdin JSON
        # v0.16.2 patch:`{shlex.quote(rel)}/run.py` 引号在 /run.py 前剥离,
        # 若 rel 含空格 / Unicode,shell 把 /run.py 当独立参数 → python 调用失败。
        # 改为 quote 整个 `rel/run.py` 路径(目前 167 skill 无空格,防御性修)。
        # 注:torch/CUDA 遮蔽(bash -lc 经 /etc/profile 注入系统 CUDA 12.2 遮蔽 pip cu12 12.4)
        # 由各 torch env 的 etc/conda/activate.d/zzz_praxis_ld.sh 在 conda activate 时按 env 级
        # 前置自身 nvidia/*/lib 修复(env 级 scoping,只装在需要的 5 个 torch env 上)。
        # 曾尝试在此处统一全局前置 env nvidia 库(durable),但全局前置会把 praxis-dock 的 pip
        # cuDNN 9 / cu13 塞进 LD_LIBRARY_PATH,遮蔽 gnina(自带 cuDNN 的编译二进制)期望的版本 →
        # CUDNN_STATUS_NOT_INITIALIZED,打破 vina_gnina_dock。故保留 env 级 activate.d,不在此全局前置。
        remote_cmd = (
            f"source {shlex.quote(conda_init)} && "
            f"conda activate {shlex.quote(host_env)} && "
            f"cd {shlex.quote(remote_brains)} && "
            f"python {shlex.quote(rel + '/run.py')}"
        )
        # ssh 把 argv 用空格拼回一行扔给远端 shell;remote_cmd 内含空格,
        # 必须 shlex.quote 把它当单一参数,否则远端 shell 会把 "source X &&" 拆开
        # → source 拿不到 filename 参数。
        argv = ["ssh", "-o", "BatchMode=yes", ssh_host, "bash", "-lc", shlex.quote(remote_cmd)]
        stdin_data = json.dumps(inputs, ensure_ascii=False).encode("utf-8")
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(stdin_data), timeout=timeout_s,
            )
        except TimeoutError:
            try:
                proc.kill()  # type: ignore[has-type]
                await proc.wait()  # type: ignore[has-type]
            except (OSError, ProcessLookupError):
                # v0.16.3:收窄异常捕获 — proc 已退出(ProcessLookupError)
                # 或 kill 系统调用失败(OSError)是 cleanup 可忽略路径;
                # 其余异常(如 AttributeError)应冒泡暴露,不静默吞。
                pass
            return {
                "ok": False,
                "error": f"ssh 调用超时(>{timeout_s}s)",
                "exec_via": f"ssh {ssh_host}",
            }
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": f"ssh/远端命令失败(rc={proc.returncode})",
                "stderr": stderr.decode(errors="replace")[:800],
                "exec_via": f"ssh {ssh_host}",
            }
        try:
            payload = json.loads(stdout.decode("utf-8"))
            return {
                "ok": True,
                "result": payload,
                "exec_via": f"ssh {ssh_host}",
            }
        except json.JSONDecodeError as e:
            return {
                "ok": False,
                "error": f"远端 stdout 非 JSON:{e}",
                "stdout_raw": stdout.decode(errors="replace")[:500],
                "exec_via": f"ssh {ssh_host}",
            }
