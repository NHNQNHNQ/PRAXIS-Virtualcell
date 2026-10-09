from __future__ import annotations

import json as _json


async def drive_chat(app, cookie, *, message, session_id="s1"):

    arrivals: list[bytes] = []
    started = {"v": False}

    async def receive():
        return {
            "type": "http.request",
            "body": _json.dumps({"message": message, "session_id": session_id}).encode(),
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
    assert started["v"], "http.response.start \u672a\u53d1\u9001"
    return arrivals


def install_capture_query(monkeypatch, captured, *, assistant_text="ok"):

    from praxis2.server import app as app_module

    async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw):
        captured.append({"messages": list(state.messages)})

        state.last_assistant_text = assistant_text
        yield {"type": "text", "text": assistant_text}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)
