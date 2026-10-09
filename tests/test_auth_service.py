"""auth.service 单元测试(argon2 + token + cookie)。"""

from __future__ import annotations

import re

from praxis2.auth.service import (
    SessionData,
    hash_password,
    needs_rehash,
    new_session_token,
    parse_cookie,
    serialize_cookie,
    verify_password,
)

_PEPPER = "test-pepper-secret"


def test_hash_and_verify_password():
    h = hash_password("strong-pw", pepper=_PEPPER)
    assert isinstance(h, bytes) and h.startswith(b"$argon2id$")
    assert verify_password("strong-pw", h, pepper=_PEPPER)
    assert not verify_password("wrong-pw", h, pepper=_PEPPER)
    assert not verify_password("strong-pw", h, pepper="different")


def test_needs_rehash_false_for_current_params():
    h = hash_password("p", pepper=_PEPPER)
    assert needs_rehash(h) is False


def test_new_session_token_urlsafe_unique():
    tokens = {new_session_token() for _ in range(50)}
    assert len(tokens) == 50
    for t in tokens:
        assert re.match(r"^[A-Za-z0-9_-]+$", t) and len(t) >= 40


def test_serialize_cookie_dev():
    c = serialize_cookie("tok-abc", ttl_s=86400 * 30, secure=False, samesite="Lax")
    assert "praxis_session=tok-abc" in c
    assert "HttpOnly" in c
    assert "SameSite=Lax" in c
    assert "Secure" not in c
    assert "Max-Age=2592000" in c
    assert "Path=/" in c


def test_serialize_cookie_prod():
    c = serialize_cookie("tok-xyz", ttl_s=300, secure=True, samesite="Strict")
    assert "Secure" in c
    assert "SameSite=Strict" in c


def test_serialize_cookie_expire():
    c = serialize_cookie("", ttl_s=0, secure=False, samesite="Lax")
    assert "Max-Age=0" in c


def test_parse_cookie_extracts_session_token():
    assert parse_cookie("praxis_session=tok-abc") == "tok-abc"
    assert parse_cookie("foo=bar; praxis_session=tok-xyz; baz=qux") == "tok-xyz"
    assert parse_cookie("foo=bar") is None
    assert parse_cookie("") is None
    assert parse_cookie(None) is None


def test_session_data_to_dict():
    sd = SessionData(user_id="u1", email="a@b.com", role="user", ip="1.2.3.4", ua="curl/8.0")
    assert sd.to_dict() == {
        "user_id": "u1",
        "email": "a@b.com",
        "role": "user",
        "ip": "1.2.3.4",
        "ua": "curl/8.0",
    }
