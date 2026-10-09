from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvChoice:
    env: str | None

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
        choice = EnvChoice(env=next(iter(available_envs)), source="sole")
    elif len(available_envs) > 1:
        choice = EnvChoice(
            env=None,
            source="none",
            ambiguous=True,
            candidates=sorted(available_envs),
        )
    else:
        choice = EnvChoice(env=None, source="none")
    if transcript_sink is not None:
        transcript_sink(
            {
                "type": "env_choice",
                "env": choice.env,
                "source": choice.source,
                "ambiguous": choice.ambiguous,
                "candidates": choice.candidates,
            }
        )
    return choice


class CallableSkillExecutor:
    def __init__(self, fn: Callable[[dict], Awaitable[dict]]) -> None:
        self._fn = fn

    async def call(self, payload: dict) -> dict:
        return await self._fn(payload)


class SubprocessSkillExecutor:
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
                proc.communicate(stdin_data),
                timeout=self._timeout_s,
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
                "error": f"Subprocess stdout is not valid JSON:{e}",
                "stdout_raw": stdout.decode(errors="replace")[:500],
            }
