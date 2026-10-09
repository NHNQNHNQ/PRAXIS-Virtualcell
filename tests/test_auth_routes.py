"""auth.routes 单元测试(每 endpoint happy + 错误码,Fake repo + fakeredis)。"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest


@dataclass
class _Settings:
    password_pepper: str = "test-pepper"
    cookie_secure: bool = False
    cookie_samesite: str = "Lax"
    session_ttl_days: int = 30
    allow_self_signup: bool = True
    smtp_host: str = ""
    smtp_port: int = 0
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    env_label: str = "dev"
    model: str = "claude-3-5-sonnet-20241022"
    signup_gift_li: int = 0


async def _make_deps():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.auth.email import DevEmailGateway
    from praxis2.auth.repository import FakeAuthRepository

    return {
        "repo": FakeAuthRepository(),
        "redis": fakeredis.aioredis.FakeRedis(decode_responses=True),
        "email_gateway": DevEmailGateway(),
        "settings": _Settings(),
    }


async def _post(handler, body: dict, *, scope_user=None, cookie: str = ""):
    msgs = []
    bytes_body = json.dumps(body).encode()
    state = {"sent": False}

    async def receive():
        if state["sent"]:
            return {"type": "http.disconnect"}
        state["sent"] = True
        return {"type": "http.request", "body": bytes_body, "more_body": False}

    async def send(m):
        msgs.append(m)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"cookie", cookie.encode())] if cookie else [],
        "user": scope_user,
        "client": ("1.2.3.4", 12345),
    }
    await handler(scope, receive, send)
    status = msgs[0]["status"]
    headers = dict(msgs[0]["headers"])
    body = b"".join(m["body"] for m in msgs if m["type"] == "http.response.body")
    return status, headers, json.loads(body) if body else None


@pytest.mark.asyncio
async def test_send_code_register_happy_returns_dev_code():
    from praxis2.auth.routes import handle_send_code

    deps = await _make_deps()
    status, _, body = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    assert status == 200
    assert body["sent"] is True
    assert body["dev_code"] and len(body["dev_code"]) == 6
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_send_code_throttled_60s():
    from praxis2.auth.routes import handle_send_code

    deps = await _make_deps()
    await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    status, _, body = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    assert status == 429
    assert "请稍候" in body["error"]
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_send_code_register_refused_when_signup_closed():
    from praxis2.auth.routes import handle_send_code

    deps = await _make_deps()
    deps["settings"].allow_self_signup = False
    status, _, body = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    assert status == 403
    assert "未开放" in body["error"]
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_register_happy_sets_cookie():
    from praxis2.auth.routes import handle_register, handle_send_code

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    code = sc["dev_code"]
    status, headers, body = await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": code,
            "password": "strong-pw",
            "display_name": "A",
        },
    )
    assert status == 200
    assert body["user"]["email"] == "a@b.com"
    assert body["balance_li"] == 0
    set_cookie = headers.get(b"set-cookie", b"").decode()
    assert "praxis_session=" in set_cookie
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_register_invalid_code():
    from praxis2.auth.routes import handle_register

    deps = await _make_deps()
    status, _, body = await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": "000000",
            "password": "pw12345",
            "display_name": "A",
        },
    )
    assert status == 400
    assert "验证码" in body["error"]
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_register_email_conflict():
    from praxis2.auth.routes import handle_register, handle_send_code

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc["dev_code"],
            "password": "pw12345",
            "display_name": "A",
        },
    )
    # 清 throttle 让第二次 send-code 通过
    await deps["redis"].delete("email_throttle:a@b.com")
    _, _, sc2 = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    status, _, body = await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc2["dev_code"],
            "password": "pw12345",
            "display_name": "A",
        },
    )
    assert status == 409
    assert "已注册" in body["error"]
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_login_happy_sets_cookie():
    from praxis2.auth.routes import handle_login, handle_register, handle_send_code

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc["dev_code"],
            "password": "the-password",
            "display_name": "A",
        },
    )
    status, headers, body = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "a@b.com", "password": "the-password"},
    )
    assert status == 200
    assert body["user"]["email"] == "a@b.com"
    assert b"set-cookie" in headers
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_login_wrong_password_401():
    from praxis2.auth.routes import handle_login, handle_register, handle_send_code

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc["dev_code"],
            "password": "right-pw",
            "display_name": "A",
        },
    )
    status, _, body = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "a@b.com", "password": "wrong-pw"},
    )
    assert status == 401
    # D.2(M9 #6):统一 401 body schema(防账号枚举)
    assert body == {"error": "unauthorized", "reason": "邮箱或密码错误"}
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_login_lockout_after_5_fails():
    """D.2:email 5 次失败后已锁;第 6 次返统一 401(不再 429)。"""
    from praxis2.auth.routes import handle_login, handle_register, handle_send_code

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc["dev_code"],
            "password": "right-pw",
            "display_name": "A",
        },
    )
    for _ in range(5):
        await _post(
            lambda s, r, snd: handle_login(s, r, snd, deps),
            {"email": "a@b.com", "password": "wrong-pw"},
        )
    status, _, body = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "a@b.com", "password": "right-pw"},
    )
    # 即使密码正确,email 维度已锁 → 返统一 401(M9 #6:防 DoS 锁号 + 防枚举)
    assert status == 401
    assert body == {"error": "unauthorized", "reason": "邮箱或密码错误"}
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_logout_clears_cookie():
    from praxis2.auth.routes import (
        handle_logout,
        handle_register,
        handle_send_code,
    )

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "x@y.com", "purpose": "register"},
    )
    _, reg_headers, reg_body = await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "x@y.com",
            "code": sc["dev_code"],
            "password": "pw",
            "display_name": "x",
        },
    )
    set_cookie = reg_headers[b"set-cookie"].decode()
    token = set_cookie.split("praxis_session=")[1].split(";")[0]

    status, headers, body = await _post(
        lambda s, r, snd: handle_logout(s, r, snd, deps),
        {},
        scope_user={
            "user_id": reg_body["user"]["id"],
            "email": "x@y.com",
            "role": "user",
        },
        cookie=f"praxis_session={token}",
    )
    assert status == 200
    assert body["ok"] is True
    expire = headers[b"set-cookie"].decode()
    assert "Max-Age=0" in expire
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_401_when_no_cookie_user():
    from praxis2.auth.routes import handle_me

    deps = await _make_deps()
    status, _, body = await _post(
        lambda s, r, snd: handle_me(s, r, snd, deps),
        {},
        scope_user=None,
    )
    assert status == 401
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_returns_simplified_payload():
    from praxis2.auth.routes import handle_me, handle_register, handle_send_code

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    _, _, reg = await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc["dev_code"],
            "password": "pw",
            "display_name": "Display A",
        },
    )
    user_id = reg["user"]["id"]
    status, _, body = await _post(
        lambda s, r, snd: handle_me(s, r, snd, deps),
        {},
        scope_user={"user_id": user_id, "email": "a@b.com", "role": "user"},
    )
    assert status == 200
    # M9:11 字段平铺(不嵌套)
    assert body["id"] == user_id and body["email"] == "a@b.com"
    assert body["display_name"] == "Display A" and body["role"] == "user"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_balance_returns_zero_stub():
    from praxis2.auth.routes import handle_me_balance

    deps = await _make_deps()
    status, _, body = await _post(
        lambda s, r, snd: handle_me_balance(s, r, snd, deps),
        {},
        scope_user={"user_id": "u1", "email": "a@b", "role": "user"},
    )
    assert status == 200
    assert body["balance_li"] == 0
    assert body["balance_yuan"] == "0.00"
    assert body["recent"] == []
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_account_delete_soft_deletes_and_logs_audit():
    from praxis2.auth.routes import (
        handle_me_account_delete,
        handle_register,
        handle_send_code,
    )

    deps = await _make_deps()
    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": "a@b.com", "purpose": "register"},
    )
    _, _, reg = await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": "a@b.com",
            "code": sc["dev_code"],
            "password": "pw",
            "display_name": "A",
        },
    )
    user_id = reg["user"]["id"]
    status, _, body = await _post(
        lambda s, r, snd: handle_me_account_delete(s, r, snd, deps),
        {},
        scope_user={"user_id": user_id, "email": "a@b.com", "role": "user"},
    )
    assert status == 200 and body["ok"] is True
    assert await deps["repo"].get_user_by_id(user_id) is None
    rows = await deps["repo"].list_audit_by_user(user_id, limit=10)
    actions = {r.action for r in rows}
    assert "account_delete" in actions
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_info_stub_returns_service_metadata():
    from praxis2.auth.routes import handle_info

    deps = await _make_deps()
    status, _, body = await _post(
        lambda s, r, snd: handle_info(s, r, snd, deps),
        {},
    )
    assert status == 200
    assert body["service"] == "PRAXIS-2"
    assert body["env"] == "dev"
    assert body["allow_self_signup"] is True
    assert "version" in body
    await deps["redis"].aclose()


def test_routes_dict_has_9_endpoints():
    from praxis2.auth.routes import ROUTES

    assert ("/api/auth/email/send-code", "POST") in ROUTES
    assert ("/api/auth/register", "POST") in ROUTES
    assert ("/api/auth/login", "POST") in ROUTES
    assert ("/api/auth/logout", "POST") in ROUTES
    assert ("/api/auth/logout-all", "POST") in ROUTES
    assert ("/api/me", "GET") in ROUTES
    assert ("/api/me/balance", "GET") in ROUTES
    assert ("/api/me/account", "DELETE") in ROUTES
    assert ("/api/info", "GET") in ROUTES
