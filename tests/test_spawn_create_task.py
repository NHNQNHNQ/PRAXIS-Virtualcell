"""v0.15.0:create_spawn_task 核心函数(handle_spawn_post 与 chat-stream auto 模式都用)。

4 用例:
- happy path → ok + task_id 出
- 空 prompt → missing_prompt
- concurrent 满 → too_many_active
- 余额 0 → insufficient_balance
"""
from __future__ import annotations

from typing import Any

import pytest

from praxis2.spawn.handlers import create_spawn_task


class _FakeRepo:
    def __init__(self, active: int = 0, *, task_id: str = "t-test-001") -> None:
        self.active = active
        self.task_id = task_id
        self.create_calls = 0

    async def count_active(self, user_id: str) -> int:
        return self.active

    async def create(self, conn, user_id: str, prompt: str, model: str) -> str:
        self.create_calls += 1
        return self.task_id


class _FakeConn:
    """模拟 asyncpg.Connection: fetchval('SELECT balance_li...') 返 balance。"""
    def __init__(self, balance: int) -> None:
        self._balance = balance

    async def fetchval(self, query: str, *args) -> int:
        return self._balance


class _FakePool:
    """模拟 asyncpg.Pool, async with pool.acquire() as conn。"""
    def __init__(self, balance: int = 1000) -> None:
        self._balance = balance

    def acquire(self):
        balance = self._balance
        class _Ctx:
            async def __aenter__(self_inner):
                return _FakeConn(balance)
            async def __aexit__(self_inner, *a):
                return False
        return _Ctx()


class _FakeRegistry:
    def __init__(self) -> None:
        self.registered: list[str] = []

    def register(self, task_id: str, task: Any) -> None:
        self.registered.append(task_id)

    def unregister(self, task_id: str) -> None:
        pass


class _FakeClient:
    async def aclose(self) -> None:
        pass


def _deps(*, active: int = 0, balance: int = 1000, task_id: str = "t-x"):
    return {
        "spawn_repo": _FakeRepo(active=active, task_id=task_id),
        "spawn_registry": _FakeRegistry(),
        "ledger": object(),
        "pg_pool": _FakePool(balance=balance),
        "llm_client_factory": lambda: _FakeClient(),
        "max_concurrent_per_user": 2,
        "max_tokens": 16384,
        "price_in_per_m": 3_000,
        "price_out_per_m": 12_000,
        "partial_flush_chunks": 20,
        "keep_last_per_user": 100,
    }


@pytest.mark.asyncio
async def test_create_spawn_task_happy_path():
    deps = _deps(task_id="t-happy")
    r = await create_spawn_task("u1", "echo hi", "deepseek-v4-pro", deps)
    assert r["ok"] is True
    assert r["task_id"] == "t-happy"
    assert r["status"] == "pending"
    assert deps["spawn_repo"].create_calls == 1
    # 让 task 收尾(避免 unraisable warning)
    import asyncio
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_create_spawn_task_missing_prompt():
    """空 prompt(空字串 / 全 whitespace)→ missing_prompt,不该 create。"""
    deps = _deps()
    r = await create_spawn_task("u1", "   \n  ", "m", deps)
    assert r == {"ok": False, "error": "missing_prompt"}
    assert deps["spawn_repo"].create_calls == 0


@pytest.mark.asyncio
async def test_create_spawn_task_too_many_active():
    """count_active >= max → too_many_active,不该 create。"""
    deps = _deps(active=2)  # == max_concurrent_per_user
    r = await create_spawn_task("u1", "echo", "m", deps)
    assert r["ok"] is False
    assert r["error"] == "too_many_active"
    assert r["active"] == 2
    assert r["limit"] == 2
    assert deps["spawn_repo"].create_calls == 0


@pytest.mark.asyncio
async def test_create_spawn_task_insufficient_balance():
    """balance == 0 → insufficient_balance,不该 create。"""
    deps = _deps(balance=0)
    r = await create_spawn_task("u1", "echo", "m", deps)
    assert r["ok"] is False
    assert r["error"] == "insufficient_balance"
    assert r["balance"] == 0
    assert deps["spawn_repo"].create_calls == 0
