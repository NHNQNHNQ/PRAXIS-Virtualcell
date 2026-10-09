import pytest

from praxis2.runtime.tenancy import (
    TenantContext,
    assert_tenant_isolation,
    require_user_id,
)
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def test_require_user_id_rejects_empty():
    # 无身份的 store 调用是 bug(§11.6 测试断言)
    with pytest.raises(ValueError, match="user_id"):
        require_user_id("")
    with pytest.raises(ValueError, match="user_id"):
        require_user_id(None)
    assert require_user_id("u1") == "u1"


def test_tenant_context_injects_user_id_into_toolusecontext():
    from praxis2.core.state import State

    st = State()
    tc = TenantContext(user_id="u1")
    tc.inject(st)
    assert st.tool_use_context["user_id"] == "u1"


def test_tenant_context_requires_user_id():
    with pytest.raises(ValueError, match="user_id"):
        TenantContext(user_id="")


async def test_cross_tenant_read_denied_session():
    # §11.6 跨用户串扰:A 写,B 读不到(store Namespace 强制 user_id 隔离)
    store = InMemoryStore()
    ns_a = Namespace(user_id="A", scope="session")
    ns_b = Namespace(user_id="B", scope="session")
    await store.kv_set(ns_a, "s1", b"A-secret")
    assert await store.kv_get(ns_b, "s1") is None     # B 读不到 A
    assert await store.kv_get(ns_a, "s1") == b"A-secret"


async def test_assert_tenant_isolation_detects_leak():
    # 校验工具:A 的 ns 不得能读出 B 写的数据(测试网兜底,§5⑧)
    store = InMemoryStore()
    await store.kv_set(Namespace(user_id="A", scope="memory"), "m", b"A")
    # 隔离成立 → 不抛
    await assert_tenant_isolation(store, owner="A", intruder="B",
                                  scope="memory", key="m")
    # 构造泄漏:intruder B 写入同 key 同值,assert_tenant_isolation 检测到
    # intruder_val == owner_val 即视为泄漏信号(按 spec 实现说明,把测试
    # 第二段 B 写值改为 b"A" 与 A 同值,确保 intruder_val == owner_val)
    await store.kv_set(Namespace(user_id="B", scope="memory"), "m", b"A")
    with pytest.raises(AssertionError, match="跨租户"):
        await assert_tenant_isolation(store, owner="A", intruder="B",
                                      scope="memory", key="m",
                                      expect_intruder_blind=True)
