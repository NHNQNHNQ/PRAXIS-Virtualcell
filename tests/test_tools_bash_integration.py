"""BashTool 端到端集成:BashCommandPolicy + BashTool 经 SerialToolRunner 串通
(final review I-2:此前 policy/bash 只单独单测,核心契约 ALLOW→执行 / DENY→拒 无集成覆盖)。"""
from pathlib import Path

import pytest

from praxis2.core.state import State
from praxis2.server.permission_bridge import (
    BridgePermissionAdapter,
    PendingPermissionRegistry,
)
from praxis2.tools.bash import BashTool
from praxis2.tools.bash_policy import BashCommandPolicy
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner


def _runner(tmp_path):
    reg = ToolRegistry()
    reg.register(BashTool(sandbox_root=tmp_path))
    return SerialToolRunner(reg, recovery_budget=3, permission=BashCommandPolicy())


def _bridge_runner(tmp_path, registry, emit_sse, *, timeout_s=2.0):
    """灰区命令经 BridgePermissionAdapter(包 BashCommandPolicy)→ ASK → SSE bridge。"""
    reg = ToolRegistry()
    reg.register(BashTool(sandbox_root=tmp_path))
    perm = BridgePermissionAdapter(
        BashCommandPolicy(),
        registry=registry,
        emit_sse=emit_sse,
        user_id="u_test",
        timeout_s=timeout_s,
    )
    return SerialToolRunner(reg, recovery_budget=3, permission=perm)


@pytest.mark.asyncio
async def test_bash_allow_through_runner(tmp_path: Path):
    """白名单命令 pwd:policy ALLOW → BashTool 执行 → is_error=False。"""
    runner = _runner(tmp_path)
    st = State()
    results = await runner.run_turn(
        [{"id": "t1", "name": "Bash", "input": {"command": "pwd"}}], st
    )
    assert results[0]["is_error"] is False
    assert str(tmp_path.resolve()) in results[0]["content"]


@pytest.mark.asyncio
async def test_bash_deny_through_runner(tmp_path: Path):
    """黑名单命令 rm -rf /:policy DENY → 权限拒 → is_error=True,BashTool 不执行。"""
    runner = _runner(tmp_path)
    st = State()
    results = await runner.run_turn(
        [{"id": "t1", "name": "Bash", "input": {"command": "rm -rf /"}}], st
    )
    assert results[0]["is_error"] is True
    assert "权限" in results[0]["content"] or "黑名单" in results[0]["content"] or "deny" in results[0]["content"].lower()


@pytest.mark.asyncio
async def test_bash_ask_allow_through_bridge_runs(tmp_path: Path):
    """灰区命令 mkdir:policy ASK → bridge 发 control_request → 用户 allow → BashTool 真执行(目录创建)。"""
    emitted: list[dict] = []
    registry = PendingPermissionRegistry()

    async def emit_sse(ev: dict) -> None:
        emitted.append(ev)
        # 模拟前端 HTTP 回传 allow
        await registry.resolve(ev["request_id"], "allow", caller_user_id="u_test")

    runner = _bridge_runner(tmp_path, registry, emit_sse)
    st = State()
    results = await runner.run_turn(
        [{"id": "t1", "name": "Bash", "input": {"command": "mkdir created_via_ask"}}], st
    )
    # 用户 allow → 命令真到 BashTool.run 并执行
    assert results[0]["is_error"] is False
    assert (tmp_path / "created_via_ask").is_dir()
    # bridge 确实发出了 control_request 帧(tool_name=Bash)
    assert emitted[0]["type"] == "control_request"
    assert emitted[0]["tool_name"] == "Bash"
    assert "request_id" in emitted[0]
    assert len(emitted) == 1  # allow 路径只发一帧 control_request


@pytest.mark.asyncio
async def test_bash_ask_deny_through_bridge_blocks(tmp_path: Path):
    """灰区命令 mkdir:policy ASK → 用户 deny → BashTool 不执行(目录不创建,is_error=True)。"""
    registry = PendingPermissionRegistry()

    async def emit_sse(ev: dict) -> None:
        await registry.resolve(ev["request_id"], "deny", caller_user_id="u_test")

    runner = _bridge_runner(tmp_path, registry, emit_sse)
    st = State()
    results = await runner.run_turn(
        [{"id": "t1", "name": "Bash", "input": {"command": "mkdir should_not_exist"}}], st
    )
    assert results[0]["is_error"] is True
    assert not (tmp_path / "should_not_exist").exists()
