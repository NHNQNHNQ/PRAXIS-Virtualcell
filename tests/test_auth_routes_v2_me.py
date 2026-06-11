"""M9 /api/me 扩展至 11 字段平铺 + balance_yuan + realname_verified 测试。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from tests.test_auth_routes import _make_deps


def _mk_scope(method, path, *, user=None, cookie=None):
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.split(";", 1)[0].encode()))
    s = {"type": "http", "method": method, "path": path, "headers": headers}
    if user:
        s["user"] = user
    return s


def _mk_receive(body=b""):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return receive


async def _capture(fn, scope, receive, deps):
    sent = []
    async def send(msg):
        sent.append(msg)
    await fn(scope, receive, send, deps)
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(m["body"] for m in sent if m["type"] == "http.response.body")
    return start["status"], json.loads(body) if body else {}, start["headers"]


def _mk_userrow(**overrides):
    from praxis2.auth.repository import UserRow
    defaults = dict(
        id="uid", email="x@x", password_hash=b"x",
        display_name=None, role="user", plan="free", status="active",
        balance_li=0, created_at=datetime.now(UTC),
        last_login_at=None, last_login_ip=None,
        realname_verified_at=None, deleted_at=None,
    )
    defaults.update(overrides)
    return UserRow(**defaults)


@pytest.mark.asyncio
async def test_me_shape_11_fields_flat_not_nested():
    """验证 11 字段全在,不嵌套 {user:{}}。"""
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-1"] = _mk_userrow(id="uid-1", email="a@x", role="user")
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-1"})

    status, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert status == 200
    # 不嵌套
    assert "user" not in body, "body 不应嵌套 'user' key"
    # 11 字段全在
    expected_fields = ("id", "phone", "email", "display_name", "role", "plan", "status",
                       "balance_li", "balance_yuan", "realname_verified", "created_at")
    for k in expected_fields:
        assert k in body, f"缺字段: {k}"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_balance_yuan_format():
    """balance_li=10000 → balance_yuan='100.00'。"""
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-2"] = _mk_userrow(id="uid-2", email="b@x", balance_li=10000)
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-2"})
    status, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert status == 200
    assert body["balance_li"] == 10000
    assert body["balance_yuan"] == "100.00"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_realname_verified_false_when_at_null():
    """realname_verified_at=None → realname_verified=False。"""
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-3"] = _mk_userrow(id="uid-3", email="c@x", realname_verified_at=None)
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-3"})
    _, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert body["realname_verified"] is False
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_realname_verified_true_when_at_set():
    """realname_verified_at 有值 → realname_verified=True。"""
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-4"] = _mk_userrow(
        id="uid-4", email="d@x", realname_verified_at=datetime.now(UTC)
    )
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-4"})
    _, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert body["realname_verified"] is True
    await deps["redis"].aclose()


class _InMemoryLedger:
    """测试用 fake Ledger,只实现 recent()。"""
    def __init__(self, rows=None, balance=0):
        self._rows = rows or []
        self._balance = balance

    async def recent(self, user_id, limit=20):
        return self._rows[:limit]


def _mk_inmemory_ledger(rows=None, balance=0):
    return _InMemoryLedger(rows=rows, balance=balance)


@pytest.mark.asyncio
async def test_me_balance_empty_returns_zero():
    deps = await _make_deps()
    deps["ledger"] = _mk_inmemory_ledger()
    deps["repo"]._users["uid-b"] = _mk_userrow(id="uid-b", email="b@x", balance_li=0)
    from praxis2.auth.routes import handle_me_balance
    scope = _mk_scope("GET", "/api/me/balance", user={"user_id": "uid-b"})
    status, body, _ = await _capture(handle_me_balance, scope, _mk_receive(), deps)
    assert status == 200
    assert body["balance_li"] == 0
    assert body["balance_yuan"] == "0.00"
    assert body["recent"] == []
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_balance_returns_recent_with_balance_after():
    deps = await _make_deps()
    deps["ledger"] = _mk_inmemory_ledger(
        rows=[
            {"id": 1, "amount_li": 10000, "kind": "signup_gift",
             "ref_type": None, "ref_id": None, "balance_after": 10000,
             "meta": None, "created_at": datetime.now(UTC)},
            {"id": 2, "amount_li": -200, "kind": "chat_out",
             "ref_type": "chat_session", "ref_id": "sess-x",
             "balance_after": 9800, "meta": None,
             "created_at": datetime.now(UTC)},
        ],
        balance=9800,
    )
    deps["repo"]._users["uid-c"] = _mk_userrow(id="uid-c", email="c@x", balance_li=9800)
    from praxis2.auth.routes import handle_me_balance
    scope = _mk_scope("GET", "/api/me/balance", user={"user_id": "uid-c"})
    status, body, _ = await _capture(handle_me_balance, scope, _mk_receive(), deps)
    assert status == 200
    assert body["balance_li"] == 9800
    assert body["balance_yuan"] == "98.00"
    assert len(body["recent"]) == 2
    assert body["recent"][0]["kind"] == "signup_gift"
    assert body["recent"][1]["kind"] == "chat_out"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_me_balance_recent_caps_at_20():
    rows = [
        {"id": i, "amount_li": -1, "kind": "chat_out",
         "ref_type": None, "ref_id": None, "balance_after": 100 - i,
         "meta": None, "created_at": datetime.now(UTC)}
        for i in range(25)
    ]
    deps = await _make_deps()
    deps["ledger"] = _mk_inmemory_ledger(rows=rows, balance=75)
    deps["repo"]._users["uid-d"] = _mk_userrow(id="uid-d", email="d@x", balance_li=75)
    from praxis2.auth.routes import handle_me_balance
    scope = _mk_scope("GET", "/api/me/balance", user={"user_id": "uid-d"})
    _, body, _ = await _capture(handle_me_balance, scope, _mk_receive(), deps)
    assert len(body["recent"]) == 20  # cap
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_get_returns_all_nulls_when_empty():
    deps = await _make_deps()
    deps["repo"]._users["uid-p1"] = _mk_userrow(id="uid-p1", email="p1@x")
    from praxis2.auth.routes import handle_me_profile_get
    scope = _mk_scope("GET", "/api/me/profile", user={"user_id": "uid-p1"})
    status, body, _ = await _capture(handle_me_profile_get, scope, _mk_receive(), deps)
    assert status == 200
    for k in ("research_field", "affiliation", "expertise_level",
              "projects", "custom_intro", "updated_at"):
        assert body[k] is None
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_post_partial_upsert_and_get_reflects():
    deps = await _make_deps()
    deps["repo"]._users["uid-p2"] = _mk_userrow(id="uid-p2", email="p2@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p2"})
    body = json.dumps({
        "research_field": "Structural Biology",
        "custom_intro": "I work on protein folding.",
    }).encode()
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 200
    assert resp["research_field"] == "Structural Biology"
    assert resp["affiliation"] is None
    assert resp["updated_at"] is not None
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_post_null_keeps_existing():
    deps = await _make_deps()
    deps["repo"]._users["uid-p3"] = _mk_userrow(id="uid-p3", email="p3@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p3"})
    body1 = json.dumps({"research_field": "Bio"}).encode()
    await _capture(handle_me_profile_post, scope, _mk_receive(body1), deps)
    body2 = json.dumps({"research_field": None}).encode()
    _, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body2), deps)
    assert resp["research_field"] == "Bio"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_post_empty_string_clears():
    deps = await _make_deps()
    deps["repo"]._users["uid-p4"] = _mk_userrow(id="uid-p4", email="p4@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p4"})
    body1 = json.dumps({"research_field": "Bio"}).encode()
    await _capture(handle_me_profile_post, scope, _mk_receive(body1), deps)
    body2 = json.dumps({"research_field": ""}).encode()
    _, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body2), deps)
    assert resp["research_field"] is None
    await deps["redis"].aclose()


@pytest.mark.parametrize("field,max_len", [
    ("research_field", 256),
    ("affiliation", 256),
    ("expertise_level", 256),
    ("projects", 2000),
    ("custom_intro", 2000),
])
@pytest.mark.asyncio
async def test_profile_post_field_too_long_400(field, max_len):
    deps = await _make_deps()
    deps["repo"]._users["uid-pL"] = _mk_userrow(id="uid-pL", email="pL@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-pL"})
    body = json.dumps({field: "x" * (max_len + 1)}).encode()
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 400
    assert resp["error"] == "field_too_long"
    assert resp["field"] == field
    assert resp["max"] == max_len
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_post_field_invalid_non_string_400():
    """非 string 值 → 400 field_invalid。"""
    deps = await _make_deps()
    deps["repo"]._users["uid-pi"] = _mk_userrow(id="uid-pi", email="pi@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-pi"})
    body = json.dumps({"research_field": 123}).encode()  # int, not string
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 400
    assert resp["error"] == "field_invalid"
    assert resp["field"] == "research_field"
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_post_unknown_field_ignored():
    """未在 PROFILE_FIELDS 里的 key 静默忽略(不报 400,降低 FE 误传容错)。"""
    deps = await _make_deps()
    deps["repo"]._users["uid-p5"] = _mk_userrow(id="uid-p5", email="p5@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p5"})
    body = json.dumps({"research_field": "Bio", "garbage_field": "xxx"}).encode()
    status, _, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 200
    await deps["redis"].aclose()


@pytest.mark.asyncio
async def test_profile_post_empty_body_noop():
    deps = await _make_deps()
    deps["repo"]._users["uid-p6"] = _mk_userrow(id="uid-p6", email="p6@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p6"})
    body = b"{}"
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 200
    assert resp["research_field"] is None
    assert resp["updated_at"] is None
    await deps["redis"].aclose()


class _RecordingLedger:
    """fake Ledger:record(...) 只记 (user_id, amount, kind),不真写 DB。"""
    def __init__(self):
        self.calls = []

    async def record(self, conn, user_id, amount_li, kind, ref_type, ref_id, meta):
        self.calls.append((user_id, amount_li, kind))
        return amount_li

    async def recent(self, user_id, limit=20):
        return []


@pytest.mark.asyncio
async def test_register_grants_signup_gift_when_env_default():
    """settings.signup_gift_li=10000 → register 后 balance_li=10000 + ledger.record 调一次。"""
    deps = await _make_deps()
    deps["settings"].signup_gift_li = 10000
    deps["ledger"] = _RecordingLedger()
    from praxis2.auth.routes import handle_register, handle_send_code
    body = json.dumps({"email": "gift@x", "purpose": "register"}).encode()
    _, resp, _ = await _capture(handle_send_code, _mk_scope("POST", "/api/auth/email/send-code"),
                                 _mk_receive(body), deps)
    code = resp["dev_code"]
    body = json.dumps({"email": "gift@x", "code": code, "password": "p"}).encode()
    status, resp, _ = await _capture(handle_register, _mk_scope("POST", "/api/auth/register"),
                                      _mk_receive(body), deps)
    assert status == 200
    assert resp["balance_li"] == 10000
    assert len(deps["ledger"].calls) == 1
    assert deps["ledger"].calls[0][1] == 10000
    assert deps["ledger"].calls[0][2] == "signup_gift"


@pytest.mark.asyncio
async def test_register_no_gift_when_env_zero():
    deps = await _make_deps()
    deps["settings"].signup_gift_li = 0
    deps["ledger"] = _RecordingLedger()
    from praxis2.auth.routes import handle_register, handle_send_code
    body = json.dumps({"email": "nogift@x", "purpose": "register"}).encode()
    _, resp, _ = await _capture(handle_send_code, _mk_scope("POST", "/api/auth/email/send-code"),
                                 _mk_receive(body), deps)
    code = resp["dev_code"]
    body = json.dumps({"email": "nogift@x", "code": code, "password": "p"}).encode()
    status, resp, _ = await _capture(handle_register, _mk_scope("POST", "/api/auth/register"),
                                      _mk_receive(body), deps)
    assert status == 200
    assert resp["balance_li"] == 0
    assert deps["ledger"].calls == []
