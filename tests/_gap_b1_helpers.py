"""GAP-B-1 测试共享:驱动 /chat/stream(ASGI)+ fake query 注入。

照搬 tests/test_correctness_session_pool_wire.py 的 drive 范式,抽出复用。"""
from __future__ import annotations

import json as _json


async def drive_chat(app, cookie, *, message, session_id="s1"):
    """走 ASGI 驱动一次 /chat/stream;返回收到的 body frames(bytes 列表)。"""
    arrivals: list[bytes] = []
    started = {"v": False}

    async def receive():
        return {
            "type": "http.request",
            "body": _json.dumps(
                {"message": message, "session_id": session_id}
            ).encode(),
            "more_body": False,
        }

    async def send(msg):
        if msg["type"] == "http.response.start":
            started["v"] = True
        elif msg["type"] == "http.response.body" and msg.get("body"):
            arrivals.append(msg["body"])

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat/stream",
        "headers": [(b"cookie", cookie.encode())],
        "query_string": b"",
    }
    await app(scope, receive, send)
    assert started["v"], "http.response.start 未发送"
    return arrivals


def install_capture_query(monkeypatch, captured, *, assistant_text="ok"):
    """fake query:把本请求开始时(已 append user)的 state.messages 快照进
    captured,然后只 yield text 并设 last_assistant_text(不写 state.messages),
    忠实 query 内核纯文本终答路径——assistant 散文由 chat 路径显式持久。"""
    from praxis2.server import app as app_module

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        captured.append({"messages": list(state.messages)})
        # 忠实内核:纯文本终答只 yield text + 存 last_assistant_text,**不**写
        # state.messages(query.py:196 既有行为)。assistant 散文答复由 chat 路径
        # 显式持久,而非内核写进 messages——fake 若假 append 会掩盖该真相。
        state.last_assistant_text = assistant_text
        yield {"type": "text", "text": assistant_text}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)
