import pytest

from praxis2.core.seams import PermissionDecision
from praxis2.skills.deps import InstallResult, install_deps_via_permission


async def test_install_blocked_when_permission_denied():

    async def deny_check(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.DENY

    calls: list[list[str]] = []

    async def fake_executor(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return (0, "", "")

    r = await install_deps_via_permission(
        deps=["numpy"],
        env="af3",
        permission_check=deny_check,
        executor=fake_executor,
    )
    assert isinstance(r, InstallResult)
    assert r.ok is False
    assert "Permission" in r.error or "\u62d2\u7edd" in r.error or "denied" in r.error.lower()
    assert calls == []


async def test_install_runs_idempotent_conda_command_when_allowed():

    async def allow_check(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.ALLOW

    calls: list[list[str]] = []

    async def fake_executor(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return (0, "all already installed", "")

    r = await install_deps_via_permission(
        deps=["numpy", "scipy"],
        env="af3",
        permission_check=allow_check,
        executor=fake_executor,
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
        deps=["ghost-pkg"],
        env="af3",
        permission_check=allow,
        executor=failing_executor,
    )
    assert r.ok is False
    assert "PackagesNotFoundError" in r.error


async def test_install_ask_decision_treated_as_deny_in_unattended_path():

    async def ask(*, env: str, deps: list[str]) -> PermissionDecision:
        return PermissionDecision.ASK

    async def noop(cmd):
        return (0, "", "")

    r = await install_deps_via_permission(
        deps=["x"],
        env="af3",
        permission_check=ask,
        executor=noop,
    )
    assert r.ok is False
    assert "ASK" in r.error or "\u672a\u6388\u6743" in r.error or "\u786e\u8ba4" in r.error


async def test_install_empty_deps_short_circuits_ok_true():

    permission_calls: list[None] = []

    async def check(*, env: str, deps: list[str]) -> PermissionDecision:
        permission_calls.append(None)
        return PermissionDecision.ALLOW

    async def exe(cmd):
        return (0, "", "")

    r = await install_deps_via_permission(
        deps=[],
        env="af3",
        permission_check=check,
        executor=exe,
    )
    assert r.ok is True
    assert permission_calls == []


@pytest.mark.integration
async def test_real_conda_install_smoke():

    import shutil

    if shutil.which("conda") is None:
        pytest.skip("\u65e0 conda,\u8df3\u8fc7\u771f\u88c5\u4f9d\u8d56\u6d4b\u8bd5")
