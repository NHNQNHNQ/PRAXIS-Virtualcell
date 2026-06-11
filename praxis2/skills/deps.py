"""依赖探测产结构化报告(总纲 §7.3.10)。缺依赖不裸失败 → 结构化
tool_result(is_error)(缺什么/哪个环境/建议安装命令/可否换环境),
回喂模型自救(§4①②),受 recovery_budget 约束(由调用方/AgentTool 经
M1 SerialToolRunner 既有机制约束)。env 歧义显式报候选不静默挑(末项)。

装依赖本身是副作用、走 Permission+幂等留 M7(§7.3.10 末项 + 总纲校准①):
本模块只探测+产建议命令,不执行安装。"""

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
        """折叠成模型可读 is_error 文本(§7.3.7 4 键形态由调用方再过
        to_api_tool_result;此处给富 content)。"""
        parts = [self.message or "依赖探测未通过"]
        if self.missing:
            parts.append(
                f"缺失包:{', '.join(self.missing)}(环境:{self.env or '未指定'})"
            )
        if self.install_command:
            parts.append(f"建议安装:{self.install_command}")
        if self.alternative_envs:
            parts.append(f"可换环境(候选,需显式选定):{', '.join(self.alternative_envs)}")
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
    """import 探针近似:`available` 是目标环境已装包集合(调用方探测填,
    M5 测试用集合;真 conda list / import 探针在 M7 SubprocessSkillExecutor
    接 HPC 时落地——M5 不在 Web 进程内跑重算力,校准①)。

    候选 env 须满足**全部 deps**(切换后整个 skill 在该 env 跑,非仅补当前
    env 缺失;故 alt 判定用 deps 而非 missing——有意语义,勿改:用 missing
    会建议切到一个缺了「当前 env 恰好已装」依赖的 env,反引入 bug)。
    env 未指定且有候选 env(单/多个都算)→ 显式报候选,绝不静默挑、也不
    伪造 <目标env> 占位命令(§7.3.10 末项)。"""
    missing = [d for d in deps if d not in available]
    if not missing:
        return DepReport(ok=True, missing=[], env=env, message="依赖齐备")

    alt: list[str] = []
    if env_catalog:
        alt = sorted(
            name for name, pkgs in env_catalog.items()
            if all(d in pkgs for d in deps)
        )

    if env is None and alt:
        kind = "歧义" if len(alt) > 1 else "未指定环境"
        return DepReport(
            ok=False, missing=missing, env=None, alternative_envs=alt,
            message=f"环境选择{kind}:{len(alt)} 个候选 env 均满足依赖,"
                    f"须显式选定(绝不静默挑一个)",
        )

    mgr = "conda"
    target = env or "<目标env:未指定,须显式选定>"
    cmd = f"{mgr} install -n {target} {' '.join(missing)}"
    where = f"目标环境 {env!r}" if env else "未指定目标环境"
    return DepReport(
        ok=False, missing=missing, env=env, install_command=cmd,
        alternative_envs=alt,
        message=f"{where} 缺 {len(missing)} 个依赖,产建议命令供自救"
                f"(装依赖走 Permission+幂等留 M7,不在此执行)",
    )


@dataclass
class InstallResult:
    """装依赖结果(§7.3.10 末项)。"""

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
    """装依赖走 Permission+幂等(§7.3.10 末项)。

    流程:
    1. 空 deps 短路 ok=True(无副作用,不调 Permission)
    2. Permission 检查(注入的 callback;DENY/ASK 都不放行,ASK 在非交互默认 deny)
    3. 拼 `conda install -n {env} -y {pkgs}`(`-y` 自动确认,装已装包是 no-op = 幂等)
    4. 由 executor 跑 → returncode/stdout/stderr,returncode≠0 → 失败结构化报告

    真 conda 调用走 Task 6 SubprocessSkillExecutor 风格,本函数解耦 executor
    供测试用 fake;真 conda 实测标 @pytest.mark.integration(M7 校准②,M8 实测)。"""
    if not deps:
        return InstallResult(ok=True, command="(no deps)")

    decision = await permission_check(env=env, deps=deps)
    if decision is PermissionDecision.DENY:
        return InstallResult(
            ok=False,
            error="Permission 拒绝:管理员/规则不允许在 env "
                  f"{env!r} 安装 {deps}(§7.3.5/§7.3.6)",
        )
    if decision is PermissionDecision.ASK:
        return InstallResult(
            ok=False,
            error="Permission ASK 未授权(非交互路径安全默认 deny,§7.6.2):"
                  "请通过 admin/前端确认后重试",
        )

    cmd = ["conda", "install", "-n", env, "-y", *deps]
    cmd_str = " ".join(cmd)
    rc, stdout, stderr = await executor(cmd)
    if rc != 0:
        return InstallResult(
            ok=False, command=cmd_str,
            error=f"conda install 失败(returncode={rc}):{stderr.strip()}",
        )
    return InstallResult(
        ok=True, command=cmd_str, installed=list(deps),
    )
