"""执行环境选择(总纲 §7.3.10)+ 进程内执行器。

选择优先级:SKILL.md env: > agent 级默认。歧义(均未给且多候选)显式报候选
(不静默挑,§7.3.10 末项)。选择结果写 transcript(可观测,§12)。

M5 仅进程内 CallableSkillExecutor(类比 v1 executors.py:246-260)。
SubprocessSkillExecutor 已 M7 落地(asyncio.create_subprocess_exec + conda env
+ CUDA_VISIBLE_DEVICES + 超时 + stdout JSON 解析,详见类 docstring;
真 HPC GPU 作业由 scheduler/hpc_submit.py 投递,§7.3.9/§7.5.5/§11.5,
Web ≠ 计算端,本 Executor 处理本地子进程)。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvChoice:
    env: str | None
    # §12 可观测须诚实标注来源:skill=SKILL.md env: / agent=agent 级配置 /
    # sole=skill+agent 均未给但可用环境恰一个(回退,非 agent 配置) / none=无
    source: str  # skill | agent | sole | none
    ambiguous: bool = False
    candidates: list[str] = field(default_factory=list)


def choose_env(
    manifest: Any,
    *,
    agent_env: str | None,
    available_envs: set[str],
    transcript_sink: Callable[[dict], None] | None = None,
) -> EnvChoice:
    skill_env = getattr(manifest, "skill_env", None)
    if skill_env:
        choice = EnvChoice(env=skill_env, source="skill")
    elif agent_env:
        choice = EnvChoice(env=agent_env, source="agent")
    elif len(available_envs) == 1:
        # skill/agent 均未给、可用环境恰一个 → 回退该唯一环境;
        # source 标 "sole"(非 "agent":§12 可观测须诚实,此非 agent 配置)
        choice = EnvChoice(env=next(iter(available_envs)), source="sole")
    elif len(available_envs) > 1:
        choice = EnvChoice(
            env=None, source="none", ambiguous=True,
            candidates=sorted(available_envs),
        )
    else:
        choice = EnvChoice(env=None, source="none")
    if transcript_sink is not None:  # §12 可观测:选择依据写 transcript
        transcript_sink({
            "type": "env_choice", "env": choice.env, "source": choice.source,
            "ambiguous": choice.ambiguous, "candidates": choice.candidates,
        })
    return choice


class CallableSkillExecutor:
    """进程内执行器(类比 v1 CallableSkillExecutor)。测试/轻量 skill 用。"""

    def __init__(self, fn: Callable[[dict], Awaitable[dict]]) -> None:
        self._fn = fn

    async def call(self, payload: dict) -> dict:
        return await self._fn(payload)


class SubprocessSkillExecutor:
    """M7 真实现:asyncio.create_subprocess_exec 跑 python -m skills.workflows.<>.run。

    设 CONDA_DEFAULT_ENV / CUDA_VISIBLE_DEVICES 环境变量(由 SchedulerRegistry.reserve
    后调用方注入);wait_for 超时;stdout 必须是 JSON({result|error/returncode}),
    解析后回给调用方;stderr+非零 returncode → 结构化 {ok:False, error, returncode}。
    payload 经 stdin JSON 喂子进程(供 skills.workflows.<>.run 读)。

    本 Executor 处理**本地子进程**(conda env 切换、CUDA 设备分配);真 HPC GPU 作业
    由 hpc_submit.py 投递(§7.3.9/§7.5.5/§11.5,Web ≠ 计算端)。"""

    def __init__(
        self,
        *,
        cmd: list[str],
        timeout_s: float,
        env: "dict[str, str] | None" = None,
    ) -> None:
        self._cmd = list(cmd)
        self._timeout_s = timeout_s
        self._env = dict(env or {})

    async def call(self, payload: dict) -> dict:
        import asyncio as _asyncio
        import json
        import os

        full_env = {**os.environ, **self._env}
        proc = await _asyncio.create_subprocess_exec(
            *self._cmd,
            stdin=_asyncio.subprocess.PIPE,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.PIPE,
            env=full_env,
        )
        stdin_data = json.dumps(payload, ensure_ascii=False).encode()
        try:
            stdout, stderr = await _asyncio.wait_for(
                proc.communicate(stdin_data), timeout=self._timeout_s,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": stderr.decode(errors="replace"),
                "returncode": proc.returncode,
            }
        try:
            return json.loads(stdout.decode())
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "ok": False,
                "error": f"子进程 stdout 非 JSON(无法解析):{e}",
                "stdout_raw": stdout.decode(errors="replace")[:500],
            }
