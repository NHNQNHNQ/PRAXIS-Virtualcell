"""§5⑥⑧ M6 整合不变量(横向兜底)。
SSE 契约完整集 + 并发同会话串行 + 跨租户隔离 + 限流背压 SSE 形状,
单文件可读兜底。各 Task 单点测试在前,本文件做集合断言。

M9 校准:user_id 来源切 cookie,inv5 改用 cookie session 替代 body user_id;
"无 user_id 400" → "无 cookie 401"。
"""

import asyncio

import httpx
import pytest
import respx

from praxis2.runtime.locks import InMemoryLockBackend, acquire_session_lock
from praxis2.runtime.ratelimit import Backpressure
from praxis2.runtime.tenancy import assert_tenant_isolation
from praxis2.server.sse import SSE_EVENT_TYPES
from praxis2.store.base import Namespace
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests.cassette import load


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
    bp = Backpressure(http_status=429, queue_position=5, eta_s=20.0, reason="并发上限")
    ev = bp.to_sse_event()
    assert ev["type"] == "error"
    assert ev["http_status"] == 429
    assert ev["queue_position"] == 5
    assert "排队" in ev["message"]


@respx.mock
@pytest.mark.asyncio
async def test_inv5_chat_stream_invariants_end_to_end():
    """§5⑥/§5⑧ 端到端:/chat/stream 返回 SSE + 强制 cookie session + 并发串行。"""
    from praxis2.server.app import make_app

    respx.post("https://up.example/v1/messages").mock(
        return_value=httpx.Response(
            200,
            text=load("m1_turn_final_text.sse"),
            headers={"content-type": "text/event-stream"},
        )
    )
    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # 无 cookie → 401(M9 校准,原 400)
        r0 = await c.post("/chat/stream", json={"message": "x"})
        assert r0.status_code == 401
        # 有 cookie → 200 + SSE
        r1 = await c.post(
            "/chat/stream",
            json={"message": "x", "session_id": "s1"},
            headers={"Cookie": cookie},
        )
        assert r1.status_code == 200
        assert r1.headers["content-type"].startswith("text/event-stream")
    await deps.redis.aclose()
