import asyncio

import pytest

from praxis2.runtime.locks import InMemoryLockBackend, acquire_session_lock
from praxis2.runtime.ratelimit import Backpressure
from praxis2.runtime.tenancy import assert_tenant_isolation
from praxis2.server.sse import SSE_EVENT_TYPES
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore


def test_inv1_sse_event_set_full_per_spec():
    assert SSE_EVENT_TYPES == {
        "text_delta",
        "tool_start",
        "tool_end",
        "tool_progress",
        "stream_event",
        "phase_change",
        "compact_boundary",
        "control_request",
        "control_cancel_request",
        "auth_status",
        "final",
        "error",
        "queue_position",
    }


@pytest.mark.asyncio
async def test_inv2_same_session_serialized_across_concurrent_requests():
    backend = InMemoryLockBackend()
    order: list[str] = []

    async def hit(tag: str) -> None:
        async with acquire_session_lock(backend, "u1", "s1"):
            order.append(f"{tag}-in")
            await asyncio.sleep(0.005)
            order.append(f"{tag}-out")

    await asyncio.gather(hit("A"), hit("B"), hit("C"))
    for i in range(0, len(order), 2):
        tag = order[i].split("-")[0]
        assert order[i] == f"{tag}-in"
        assert order[i + 1] == f"{tag}-out"


@pytest.mark.asyncio
async def test_inv3_cross_tenant_isolation_holds():
    store = InMemoryStore()
    await store.kv_set(Namespace(user_id="A", scope="memory"), "m", b"A")
    await assert_tenant_isolation(store, owner="A", intruder="B", scope="memory", key="m")


def test_inv4_backpressure_sse_shape_matches_spec():
    bp = Backpressure(http_status=429, queue_position=5, eta_s=20.0, reason="\u5e76\u53d1\u4e0a\u9650")
    ev = bp.to_sse_event()
    assert ev["type"] == "error"
    assert ev["http_status"] == 429
    assert ev["queue_position"] == 5
    assert "queued" in ev["message"]
