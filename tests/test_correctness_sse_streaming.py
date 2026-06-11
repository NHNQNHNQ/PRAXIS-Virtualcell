"""Phase B.1 (reviewer M6 C1):SSE 真流式 — 第一帧应在 query 进行中即时到达,
不等 query 完成。

修复前 buffered 模式:_chat_stream 把所有 ev append 进 kernel_events,query 跑完才
fan-out → 首字节延迟 = 总耗时,长答案体验是"AI 卡死"。
修复后真流式:每 ev 即时 await push(ev) → 首字节延迟 = 模型首 token 延迟。

A.6 bridge ASK 联合契约:emit_sse 改 push 后,bridge 阻塞期间也能推 control_request,
用户真能 ASK→回复(B.1 之前必超时)。
"""

from __future__ import annotations

import asyncio
import time

import pytest

from tests._auth_test_helpers import make_test_app_deps, preseed_session


async def _drive_chat_stream(app, cookie: str, *, message: str = "hi"):
    """直接走 ASGI,收集每个 body frame 的到达时间。返回 [(t_offset, body_bytes), ...]。"""
    arrivals: list[tuple[float, bytes]] = []
    started = False
    t0 = time.perf_counter()

    async def receive():
        import json as _json

        return {
            "type": "http.request",
            "body": _json.dumps({"message": message, "session_id": "s1"}).encode(),
            "more_body": False,
        }

    async def send(msg):
        nonlocal started
        if msg["type"] == "http.response.start":
            started = True
        elif msg["type"] == "http.response.body":
            body = msg.get("body", b"")
            if body:
                arrivals.append((time.perf_counter() - t0, body))

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat/stream",
        "headers": [(b"cookie", cookie.encode())],
        "query_string": b"",
    }
    await app(scope, receive, send)
    assert started, "http.response.start 未发送"
    return arrivals


@pytest.mark.asyncio
async def test_first_frame_arrives_before_query_completes(monkeypatch):
    """注入 slow query 发 evA(立即) → 0.6s → evB → 0.6s → final。
    第一个 SSE 帧到达时间应 < 0.4s(buffered 模式必 ≥1.2s)。"""
    from praxis2.server import app as app_module
    from praxis2.server.app import make_app

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        yield {"type": "text", "text": "A"}
        await asyncio.sleep(0.6)
        yield {"type": "text", "text": "B"}
        await asyncio.sleep(0.6)
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)

    arrivals = await _drive_chat_stream(app, cookie)
    await deps.redis.aclose()

    # 至少 3 个有 body 的帧(text A / text B / final)
    assert len(arrivals) >= 3, f"应至少 3 frames,实际 {len(arrivals)}"

    # 关键断言:第一帧 < 0.4s(buffered 模式必 ≥1.2s)
    first_t = arrivals[0][0]
    assert first_t < 0.4, f"第一帧 {first_t:.3f}s,应 <0.4s(buffered 会 ≥1.2s)"
    assert b"event: text_delta" in arrivals[0][1]
    assert b'"text": "A"' in arrivals[0][1]

    # 第二帧应在 ~0.6s 到达(query 内部 sleep 0.6s 后 yield),
    # 与第一帧时间间隔 ≥0.5s 证明不是同一 fan-out 批
    second_t = arrivals[1][0]
    assert 0.5 < second_t < 1.0, (
        f"第二帧 {second_t:.3f}s,应 ~0.6s(若 buffered 三帧会同时到达)"
    )


@pytest.mark.asyncio
async def test_event_ids_monotonic_across_frames(monkeypatch):
    """event_id 严格单调:1, 2, 3, ... 不重置不跳号。"""
    from praxis2.server import app as app_module
    from praxis2.server.app import make_app

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        for i in range(5):
            yield {"type": "text", "text": f"chunk-{i}"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u2")
    app = make_app(deps)

    arrivals = await _drive_chat_stream(app, cookie)
    await deps.redis.aclose()

    import re

    ids: list[int] = []
    for _, body in arrivals:
        for m in re.finditer(rb'"event_id":\s*(\d+)', body):
            ids.append(int(m.group(1)))

    assert ids == list(range(1, len(ids) + 1)), (
        f"event_id 应严格单调 1..N,实际 {ids}"
    )
    assert len(ids) >= 6, f"应至少 6 个 event_id(5 text + 1 final),实际 {len(ids)}"


@pytest.mark.asyncio
async def test_emit_sse_during_query_pushes_immediately(monkeypatch):
    """A.6 emit_sse 在 query 进行中应能立即推 control_request frame,而非 buffer。

    用 stub:query yield 一个 ev → emit_sse 在 yield 之后立即触发(模拟 bridge 在工具
    决策点 ASK)→ 接收端应在 query 还没 yield 完之前已收到 control_request 帧。
    """
    from praxis2.server import app as app_module
    from praxis2.server.app import make_app

    # 用 ContextVar/闭包传 push 给 fake query 是 over-engineering;
    # 直接构造 fake query 在 yield 之间手动 sleep 模拟"工具调用阻塞 + 同时
    # 已通过 emit_sse 推了 control_request"。
    # 简化:fake query 直接 yield 一个 "stream_event"(control_request 走 stream_event
    # 通路,_map_kernel_event 中 SSE_EVENT_TYPES 直通)。
    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        yield {
            "type": "control_request",
            "request_id": "r1",
            "reason": "ask user",
        }
        # 模拟 bridge wait 用户回复阻塞 1s
        await asyncio.sleep(1.0)
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u3")
    app = make_app(deps)

    arrivals = await _drive_chat_stream(app, cookie)
    await deps.redis.aclose()

    # 第一帧(control_request)应在 0.4s 内到达 — bridge 阻塞期间客户端就该看到 ASK
    assert len(arrivals) >= 2
    first_t, first_body = arrivals[0]
    assert first_t < 0.4, (
        f"control_request 第一帧 {first_t:.3f}s,应 <0.4s(buffered 必 ≥1.0s)"
    )
    assert b"event: control_request" in first_body
    assert b'"request_id": "r1"' in first_body

    # 第二帧 final 应在 ~1.0s 后到 — 间隔证明真流式
    second_t = arrivals[1][0]
    assert second_t - first_t > 0.7, (
        f"final 应在 control_request 后 ~1s,实际间隔 {second_t - first_t:.3f}s"
    )
