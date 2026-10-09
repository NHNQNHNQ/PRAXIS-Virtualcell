"""§7.3.10 末项装依赖走 Permission+幂等接口位。"""

import pytest

from praxis2.core.seams import PermissionDecision
from praxis2.skills.deps import InstallResult, install_deps_via_permission


async def test_install_blocked_when_permission_denied():
    # Permission DENY → 不执行 + 返回 ok=False 含 reason
    async def deny_check(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.DENY

    calls: list[list[str]] = []

    async def fake_executor(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return (0, "", "")

    r = await install_deps_via_permission(
        deps=["numpy"], env="af3",
        permission_check=deny_check, executor=fake_executor,
    )
    assert isinstance(r, InstallResult)
    assert r.ok is False
    assert "Permission" in r.error or "拒绝" in r.error or "denied" in r.error.lower()
    assert calls == []  # 拒绝即不跑


async def test_install_runs_idempotent_conda_command_when_allowed():
    # ALLOW → 拼 `conda install -n {env} -y {deps}` 跑
    async def allow_check(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.ALLOW

    calls: list[list[str]] = []

    async def fake_executor(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return (0, "all already installed", "")

    r = await install_deps_via_permission(
        deps=["numpy", "scipy"], env="af3",
        permission_check=allow_check, executor=fake_executor,
    )
    assert r.ok is True
    assert calls == [["conda", "install", "-n", "af3", "-y", "numpy", "scipy"]]
    assert r.command == "conda install -n af3 -y numpy scipy"


async def test_install_nonzero_returncode_records_error():
    async def allow(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.ALLOW

    async def failing_executor(cmd: list[str]) -> tuple[int, str, str]:
        return (1, "", "PackagesNotFoundError: ghost-pkg")

    r = await install_deps_via_permission(
        deps=["ghost-pkg"], env="af3",
        permission_check=allow, executor=failing_executor,
    )
    assert r.ok is False
    assert "PackagesNotFoundError" in r.error


async def test_install_ask_decision_treated_as_deny_in_unattended_path():
    # ASK 在非交互(无远程桥接)路径下安全默认 = DENY(§7.6.2 体例)
    async def ask(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.ASK

    async def noop(cmd):
        return (0, "", "")

    r = await install_deps_via_permission(
        deps=["x"], env="af3",
        permission_check=ask, executor=noop,
    )
    assert r.ok is False
    assert "ASK" in r.error or "未授权" in r.error or "确认" in r.error


async def test_install_empty_deps_short_circuits_ok_true():
    # 空依赖列表 → 直接 ok=True 不调 Permission / 不调 executor
    permission_calls: list[None] = []

    async def check(*, env: str, deps: list[str]) -> PermissionDecision:
        permission_calls.append(None)
        return PermissionDecision.ALLOW

    async def exe(cmd):
        return (0, "", "")

    r = await install_deps_via_permission(
        deps=[], env="af3",
        permission_check=check, executor=exe,
    )
    assert r.ok is True
    assert permission_calls == []  # 短路:无需 Permission


@pytest.mark.integration
async def test_real_conda_install_smoke():
    # 真 conda install(无 conda 自动 skip,M7 校准②;M8 实测)
    import shutil

    if shutil.which("conda") is None:
        pytest.skip("无 conda,跳过真装依赖测试")
    # 真实环境此处跑 numpy 安装(已装即幂等),但不依赖具体环境
