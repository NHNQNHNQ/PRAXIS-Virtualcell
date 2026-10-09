"""Describe skill execution steps or run a skill through an explicitly configured SSH host."""

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


_ENV_SSH_HOST = "PRAXIS_SKILL_SSH_HOST"
_ENV_REMOTE_BRAINS = "PRAXIS_SKILL_REMOTE_BRAINS"
_ENV_CONDA_INIT = "PRAXIS_SKILL_CONDA_INIT"
_ENV_TIMEOUT = "PRAXIS_SKILL_TIMEOUT_S"


def _find_skill_dir(name: str, brain_hint: str | None = None) -> Path | None:

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

    if skill_md_text.startswith("---"):
        parts = skill_md_text.split("---", 2)
        body = parts[2] if len(parts) >= 3 else skill_md_text
    else:
        body = skill_md_text

    lines = body.splitlines()
    target_headers = ("## SOP", "## Execution", "## Quick execution", "## Usage", "## How to run")
    start = None
    for i, ln in enumerate(lines):
        for h in target_headers:
            if ln.strip().startswith(h):
                start = i
                break
        if start is not None:
            break
    if start is None:
        return body.strip()[:max_chars]

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()[:max_chars]


class SkillExecTool(Tool):
    name = "SkillExec"
    description = (
        "Invoke a brain skill with its name and input argument dictionary"
        ".Return configured execution steps and an SOP summary; a skill w"
        "ith run.py can execute through an explicitly configured SSH host"
        "."
    )
    rmcp_op = "call_skill"

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill directory name from SKILL.md frontmatter, for example perturbation_predict",
                },
                "brain": {
                    "type": "string",
                    "description": "Optional brain identifier; search all brains when omitted",
                },
                "inputs": {
                    "type": "object",
                    "description": "Skill argument dictionary following its SKILL.md input contract",
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
            return ToolResult(ok=False, error="Missing required skill name, for example perturbation_predict")

        skill_dir = _find_skill_dir(name, brain_hint=brain_hint)
        if skill_dir is None:
            return ToolResult(
                ok=False,
                error=(
                    "Skill directory not found: brains/*/skills/workf"
                    "lows/"
                    f"{name}"
                    "/. Choose an exact name from the system prompt o"
                    "r specify the brain parameter."
                ),
                recovery_hint="Choose an exact name from the available skills in the system prompt.",
            )

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            return ToolResult(ok=False, error=f"Skill directory {skill_dir}has no SKILL.md")

        text = skill_md.read_text(encoding="utf-8")
        host_env = _parse_frontmatter_field(text, "host_env")
        status = _parse_frontmatter_field(text, "status")

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
                    f"skill `{name}` has no host_env in SKILL.md frontmatter: "
                    f"the target environment cannot be selected. Supply host_env."
                ),
                value={"execution_plan": execution_plan, "sop": sop},
            )

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

        host_for_display = ssh_host or "<PRAXIS_SKILL_SSH_HOST>"
        brains_for_display = remote_brains or "<PRAXIS_SKILL_REMOTE_BRAINS>"
        conda_for_display = conda_init or "<PRAXIS_SKILL_CONDA_INIT>"

        cmd_lines = [
            "# Run on the explicitly configured skill host:",
            f"ssh {host_for_display} 'bash -lc \"",
            f"  source {conda_for_display} && \\",
            f"  conda activate {host_env} && \\",
            f"  cd {brains_for_display} && \\",
        ]
        if has_run_py:
            inputs_json = json.dumps(inputs, ensure_ascii=False)
            cmd_lines.append(f"  echo {inputs_json!r} | python {rel}/run.py")
        else:
            cmd_lines.append("  # This skill has no run.py; follow the SOP manually.")
        cmd_lines.append("\"'")

        why_not_exec = []
        if not has_run_py:
            why_not_exec.append("The skill directory has no run.py; documentation only")
        if not ssh_host:
            why_not_exec.append(f"Not configured: {_ENV_SSH_HOST}environment variable")
        if not remote_brains:
            why_not_exec.append(f"Not configured: {_ENV_REMOTE_BRAINS}")
        if not conda_init:
            why_not_exec.append(f"Not configured: {_ENV_CONDA_INIT}")

        value = {
            "execution_plan": execution_plan,
            "ssh_command_template": "\n".join(cmd_lines),
            "sop_excerpt": sop,
            "exec_via": "manual (no auto-exec)",
            "why_not_executed": "; ".join(why_not_exec),
            "next_action": (
                "Execution was not started. Review the SOP and co"
                "mmand template. To enable execution, configure "
                f"{_ENV_SSH_HOST}"
                "/"
                f"{_ENV_REMOTE_BRAINS}"
                "/"
                f"{_ENV_CONDA_INIT}"
                "and provide run.py."
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

        remote_cmd = (
            f"source {shlex.quote(conda_init)} && "
            f"conda activate {shlex.quote(host_env)} && "
            f"cd {shlex.quote(remote_brains)} && "
            f"python {shlex.quote(rel + '/run.py')}"
        )

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
                proc.communicate(stdin_data),
                timeout=timeout_s,
            )
        except TimeoutError:
            try:
                proc.kill()  # type: ignore[has-type]
                await proc.wait()  # type: ignore[has-type]
            except (OSError, ProcessLookupError):
                pass
            return {
                "ok": False,
                "error": f"SSH timed out after {timeout_s}s)",
                "exec_via": f"ssh {ssh_host}",
            }
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": f"SSH or remote command failed, rc={proc.returncode})",
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
                "error": f"Remote stdout is not valid JSON:{e}",
                "stdout_raw": stdout.decode(errors="replace")[:500],
                "exec_via": f"ssh {ssh_host}",
            }
