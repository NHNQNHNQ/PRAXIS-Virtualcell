"""D.3(reviewer M9 #7):audit_log email 必哈希,不入原文(GDPR/CCPA-friendly)。

audit_email_key(email, *, pepper) → 16-char HMAC 前缀:
- 同 email + 同 pepper → 同 hash(可关联)
- 不同 email / pepper → 不同 hash
- 不可逆推原文 email
- 空 email → 空串(audit_log 允许空 resource_id)
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from praxis2.auth.cookie_hash import audit_email_key

# ── 单元:helper 性质 ────────────────────────────────────────────────


def test_audit_key_deterministic():
    k1 = audit_email_key("u@x.com", pepper="p")
    k2 = audit_email_key("u@x.com", pepper="p")
    assert k1 == k2 != ""


def test_audit_key_differs_per_email():
    k1 = audit_email_key("a@x.com", pepper="p")
    k2 = audit_email_key("b@x.com", pepper="p")
    assert k1 != k2


def test_audit_key_differs_per_pepper():
    k1 = audit_email_key("u@x.com", pepper="p1")
    k2 = audit_email_key("u@x.com", pepper="p2")
    assert k1 != k2


def test_audit_key_no_email_substring():
    """原文 email 不应出现在 hash 中,长度 16(64-bit 熵)。"""
    k = audit_email_key("super_secret@admin.com", pepper="p")
    assert "super_secret" not in k
    assert "admin.com" not in k
    assert len(k) == 16


def test_audit_key_empty_returns_empty():
    """空 email 返空(audit_log 允许空 resource_id)。"""
    assert audit_email_key("", pepper="p") == ""


# ── 集成:routes 调用确实写 hash 而非原文 ────────────────────────────


@dataclass
class _Settings:
    password_pepper: str = "test-pepper-audit"
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


async def _post(handler, body: dict, *, scope_user=None):
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
        "headers": [],
        "user": scope_user,
        "client": ("1.2.3.4", 12345),
    }
    await handler(scope, receive, send)
    status = msgs[0]["status"]
    body = b"".join(m["body"] for m in msgs if m["type"] == "http.response.body")
    return status, json.loads(body) if body else None


@pytest.mark.asyncio
async def test_send_code_audit_writes_hashed_email():
    """走 send-code 流程,audit_log.resource_id 应是 hash 不是原文。"""
    from praxis2.auth.routes import handle_send_code

    deps = await _make_deps()
    email = "alice@example.com"
    status, _ = await _post(
        lambda s, r, snd: handle_send_code(s, r, snd, deps),
        {"email": email, "purpose": "register"},
    )
    assert status == 200
    # send_code 的 audit user_id=None
    rows = await deps["repo"].list_audit_by_user(None, limit=10)
    email_audits = [r for r in rows if r.action == "email_send"]
    assert email_audits, "应有 email_send audit"
    rid = email_audits[-1].resource_id
    assert rid != email, "resource_id 不应是原文 email"
    assert "@" not in rid and "alice" not in rid
    expected = audit_email_key(email, pepper=deps["settings"].password_pepper)
    assert rid == expected
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_failed_login_audit_writes_hashed_email_when_user_missing():
    """user 不存在时 fallback 是 hash,不是原文 email。"""
    from praxis2.auth.routes import handle_login

    deps = await _make_deps()
    email = "ghost@example.com"
    status, _ = await _post(
        lambda s, r, snd: handle_login(s, r, snd, deps),
        {"email": email, "password": "wrong"},
    )
    assert status == 401
    # login_fail 且 user 不存在 → user_id=None
    rows = await deps["repo"].list_audit_by_user(None, limit=10)
    fail_audits = [r for r in rows if r.action == "login_fail"]
    assert fail_audits, "应有 login_fail audit"
    rid = fail_audits[-1].resource_id
    assert rid != email, "resource_id 不应是原文 email"
    assert "@" not in rid and "ghost" not in rid
    expected = audit_email_key(email, pepper=deps["settings"].password_pepper)
    assert rid == expected
    await deps["redis"].aclose()
