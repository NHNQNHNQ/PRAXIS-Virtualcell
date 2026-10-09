"""auth.middleware ASGI 中间件单元测试(fakeredis)。"""

from __future__ import annotations

import json

import pytest


async def _capture_scope_app(scope, receive, send):
    """捕获 scope["user"] 到响应 body(测试用)。"""
    user = scope.get("user")
    body = json.dumps({"user": user}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _drain(scope, app):
    msgs = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(m):
        msgs.append(m)

    await app(scope, receive, send)
    body = b"".join(m["body"] for m in msgs if m["type"] == "http.response.body")
    return msgs[0]["status"], body


def _scope(path="/api/me", cookies: str = ""):
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"cookie", cookies.encode())] if cookies else [],
    }


@pytest.mark.asyncio
async def test_middleware_injects_user_when_cookie_valid():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.auth.middleware import AuthMiddleware
    from praxis2.store.redis import auth_session_set

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await auth_session_set(
        client,
        "tok-abc",
        {"user_id": "u1", "email": "a@b.com", "role": "user"},
        ttl_s=300,
        pepper="test-pepper",
    )
    app = AuthMiddleware(_capture_scope_app, redis_client=client, pepper="test-pepper")
    status, body = await _drain(_scope(cookies="praxis_session=tok-abc"), app)
    assert status == 200
    payload = json.loads(body)
    assert payload["user"] == {"user_id": "u1", "email": "a@b.com", "role": "user"}
    await client.aclose()


@pytest.mark.asyncio
async def test_middleware_sets_user_none_when_no_cookie():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.auth.middleware import AuthMiddleware

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app = AuthMiddleware(_capture_scope_app, redis_client=client, pepper="test-pepper")
    status, body = await _drain(_scope(cookies=""), app)
    payload = json.loads(body)
    assert payload["user"] is None
    await client.aclose()


@pytest.mark.asyncio
async def test_middleware_sets_user_none_when_token_invalid():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.auth.middleware import AuthMiddleware

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app = AuthMiddleware(_capture_scope_app, redis_client=client, pepper="test-pepper")
    status, body = await _drain(_scope(cookies="praxis_session=invalid-token"), app)
    payload = json.loads(body)
    assert payload["user"] is None
    await client.aclose()


@pytest.mark.asyncio
async def test_middleware_passes_through_non_http_scope():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.auth.middleware import AuthMiddleware

    called = []

    async def inner_app(scope, receive, send):
        called.append(scope["type"])

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app = AuthMiddleware(inner_app, redis_client=client, pepper="test-pepper")
    await app({"type": "lifespan"}, None, None)
    assert called == ["lifespan"]
    await client.aclose()
