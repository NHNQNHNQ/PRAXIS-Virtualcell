from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from praxis2.core.seams import PermissionDecision


@dataclass
class DepReport:
    ok: bool
    missing: list[str]
    env: str | None
    install_command: str | None = None
    alternative_envs: list[str] = field(default_factory=list)
    message: str = ""

    def to_tool_result_payload(self) -> dict:

        parts = [self.message or "Dependency check did not pass"]
        if self.missing:
            parts.append(f"Missing packages:{', '.join(self.missing)}(environment:{self.env or 'unspecified'})")
        if self.install_command:
            parts.append(f"Suggested installation:{self.install_command}")
        if self.alternative_envs:
            parts.append(f"Candidate environments; select one explicitly:{', '.join(self.alternative_envs)}")
        return {
            "type": "tool_result",
            "is_error": not self.ok,
            "content": "\n".join(parts),
        }


def probe_dependencies(
    deps: list[str],
    *,
    env: str | None,
    available: set[str],
    env_catalog: dict[str, set[str]] | None = None,
) -> DepReport:

    missing = [d for d in deps if d not in available]
    if not missing:
        return DepReport(ok=True, missing=[], env=env, message="Dependencies available")

    alt: list[str] = []
    if env_catalog:
        alt = sorted(name for name, pkgs in env_catalog.items() if all(d in pkgs for d in deps))

    if env is None and alt:
        kind = "Ambiguous" if len(alt) > 1 else "No environment selected"
        return DepReport(
            ok=False,
            missing=missing,
            env=None,
            alternative_envs=alt,
            message=(
                f"Environment selection: {kind}; {len(alt)} candidate "
                "environments satisfy dependencies; select one explicitly"
            ),
        )

    mgr = "conda"
    target = env or "<target environment: explicitly required>"
    cmd = f"{mgr} install -n {target} {' '.join(missing)}"
    where = f"Target environment {env!r}" if env else "No target environment selected"
    return DepReport(
        ok=False,
        missing=missing,
        env=env,
        install_command=cmd,
        alternative_envs=alt,
        message=(
            f"{where}missing {len(missing)}dependencies; an installation suggestion is provided without executing it"
        ),
    )


@dataclass
class InstallResult:
    ok: bool
    command: str = ""
    installed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    error: str = ""


PermissionCheck = Callable[..., Awaitable[PermissionDecision]]
SubprocessExecutor = Callable[[list[str]], Awaitable[tuple[int, str, str]]]


async def install_deps_via_permission(
    *,
    deps: list[str],
    env: str,
    permission_check: PermissionCheck,
    executor: SubprocessExecutor,
) -> InstallResult:

    if not deps:
        return InstallResult(ok=True, command="(no deps)")

    decision = await permission_check(env=env, deps=deps)
    if decision is PermissionDecision.DENY:
        return InstallResult(
            ok=False,
            error="Permission denied: the active policy disallows installation in environment "
            f"{env!r}of {deps}(§7.3.5/§7.3.6)",
        )
    if decision is PermissionDecision.ASK:
        return InstallResult(
            ok=False,
            error="Permission ASK has no approval; use an interactive approval handler and retry",
        )

    cmd = ["conda", "install", "-n", env, "-y", *deps]
    cmd_str = " ".join(cmd)
    rc, stdout, stderr = await executor(cmd)
    if rc != 0:
        return InstallResult(
            ok=False,
            command=cmd_str,
            error=f"conda install failed, returncode={rc}):{stderr.strip()}",
        )
    return InstallResult(
        ok=True,
        command=cmd_str,
        installed=list(deps),
    )
