"""D.2(reviewer M9 #6):登录锁双维度(email + per-IP)+ 401 统一防枚举/防 DoS 锁号。

关键不变量:
1. 已锁(email ≥5 / IP ≥20)时不递增 fail 计数(防 spam)
2. 邮箱不存在 vs 密码错 vs 已锁 全部返完全相同 body:
   {"error": "unauthorized", "reason": "邮箱或密码错误"}
3. 成功登录清两维度计数
"""

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
    signup_gift_li: int = 10000
    env_label: str = "dev"
    model: str = "claude-3-5-sonnet-20241022"


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


async def _post(handler, body: dict, *, scope_user=None, cookie: str = "", ip: str = "1.2.3.4"):
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
        "client": (ip, 12345),
    }
    await handler(scope, receive, send)
    status = msgs[0]["status"]
    headers = dict(msgs[0]["headers"])
    body = b"".join(m["body"] for m in msgs if m["type"] == "http.response.body")
    return status, headers, json.loads(body) if body else None


async def _register(deps, email: str, password: str):
    """注册一个用户便于后续 login 测试。"""
    from praxis2.auth.routes import handle_register, handle_send_code

    _, _, sc = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": email, "purpose": "register"},
    )
    await _post(
        lambda s, r, snd: handle_register(s, r, snd, deps),
        {
            "email": email,
            "code": sc["dev_code"],
            "password": password,
            "display_name": "U",
        },
    )


_UNIFIED_401 = {"error": "unauthorized", "reason": "邮箱或密码错误"}


@pytest.mark.asyncio
async def test_email_locked_after_5_fails_returns_401_not_429():
    """同 email 5 次失败 → 第 6 次仍 401 + 统一 body(不再返 429 暴露 locked 状态)。"""
    from praxis2.auth.routes import handle_login

    deps = await _make_deps()
    await _register(deps, "victim@b.com", "right-pw")

    # 5 次错密码 → 触发 email 锁
    for _ in range(5):
        await _post(
            lambda s, r, snd: handle_login(s, r, snd, deps),
            {"email": "victim@b.com", "password": "wrong-pw"},
        )

    # 第 6 次:即便密码正确,也被锁(但 client 看到的是统一 401)
    status, _, body = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "victim@b.com", "password": "right-pw"},
    )
    assert status == 401
    assert body == _UNIFIED_401
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_ip_locked_after_20_fails_returns_401():
    """同 IP 20 次失败(可跨 email)→ 第 21 次返 401(IP 锁,防扫号)。"""
    from praxis2.auth.routes import handle_login

    deps = await _make_deps()
    # 不需要预注册,反正都是 wrong path
    attacker_ip = "9.9.9.9"

    for i in range(20):
        # 跨 20 个不同 email,各 1 次错(单 email 维度永远不锁,只考验 IP 锁)
        await _post(
            lambda s, r, snd: handle_login(s, r, snd, deps),
            {"email": f"u{i}@b.com", "password": "wrong"},
            ip=attacker_ip,
        )

    # 第 21 次:IP 已锁 → 401(即便用全新的 email)
    status, _, body = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "fresh@b.com", "password": "any"},
        ip=attacker_ip,
    )
    assert status == 401
    assert body == _UNIFIED_401
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_unknown_email_returns_same_body_as_wrong_password():
    """邮箱不存在 vs 密码错 → 完全相同响应(防账号枚举)。"""
    from praxis2.auth.routes import handle_login

    deps = await _make_deps()
    await _register(deps, "exists@b.com", "right-pw")

    # case 1: 邮箱不存在
    status1, _, body1 = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "ghost@b.com", "password": "anything"},
        ip="2.2.2.2",
    )
    # case 2: 邮箱存在,密码错
    status2, _, body2 = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "exists@b.com", "password": "wrong-pw"},
        ip="3.3.3.3",
    )
    assert status1 == status2 == 401
    assert body1 == body2 == _UNIFIED_401
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_ip_lockout_scoped_to_attacker_ip_not_victim_ip():
    """IP 维度锁定只影响该 IP;其他 IP 的合法用户不受影响。

    扫号 attacker 用 attacker_ip 撞 21 次 → attacker_ip 锁;
    victim 从自己 IP 用正确密码 → 仍能 200(IP 计数不在 victim_ip)。
    """
    from praxis2.auth.routes import handle_login

    deps = await _make_deps()
    await _register(deps, "alice@b.com", "alice-pw")

    attacker_ip = "9.9.9.9"
    # 21 次错登从 attacker_ip(用不同 email,避免触发 email 锁)
    for i in range(21):
        await _post(
            lambda s, r, snd: handle_login(s, r, snd, deps),
            {"email": f"scan{i}@b.com", "password": "wrong"},
            ip=attacker_ip,
        )

    # Alice 从自己 IP 用正确密码 → 应成功(她从未失败过,且不是 attacker_ip)
    status, _, body = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "alice@b.com", "password": "alice-pw"},
        ip="1.1.1.1",
    )
    assert status == 200
    assert body["user"]["email"] == "alice@b.com"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_successful_login_clears_both_counters():
    """成功登录清两维度 fail counter(email + IP)。"""
    from praxis2.auth.routes import handle_login

    deps = await _make_deps()
    await _register(deps, "u@b.com", "right-pw")
    ip = "4.4.4.4"

    # 错 3 次(都没触发锁,email <5、ip <20)
    for _ in range(3):
        await _post(
            lambda s, r, snd: handle_login(s, r, snd, deps),
            {"email": "u@b.com", "password": "wrong"},
            ip=ip,
        )

    # 计数确认非零
    redis = deps["redis"]
    assert int(await redis.get("login_fail:u@b.com") or 0) == 3
    assert int(await redis.get(f"login_fail_ip:{ip}") or 0) == 3

    # 成功登录
    status, _, _ = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": "u@b.com", "password": "right-pw"},
        ip=ip,
    )
    assert status == 200

    # 两维度计数清零
    assert await redis.get("login_fail:u@b.com") is None
    assert await redis.get(f"login_fail_ip:{ip}") is None
    await deps["redis"].aclose()
