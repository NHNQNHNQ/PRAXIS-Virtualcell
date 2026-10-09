import pytest

from praxis2.runtime.tenancy import (
    TenantContext,
    assert_tenant_isolation,
    require_user_id,
)
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def test_require_user_id_rejects_empty():

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

    store = InMemoryStore()
    ns_a = Namespace(user_id="A", scope="session")
    ns_b = Namespace(user_id="B", scope="session")
    await store.kv_set(ns_a, "s1", b"A-secret")
    assert await store.kv_get(ns_b, "s1") is None
    assert await store.kv_get(ns_a, "s1") == b"A-secret"


async def test_assert_tenant_isolation_detects_leak():

    store = InMemoryStore()
    await store.kv_set(Namespace(user_id="A", scope="memory"), "m", b"A")

    await assert_tenant_isolation(store, owner="A", intruder="B", scope="memory", key="m")

    await store.kv_set(Namespace(user_id="B", scope="memory"), "m", b"A")
    with pytest.raises(AssertionError, match="User isolation"):
        await assert_tenant_isolation(
            store, owner="A", intruder="B", scope="memory", key="m", expect_intruder_blind=True
        )
