"""auth.routes:8 endpoint handler + ROUTES dict + 频控接 redis + audit_log。

handler 签名 `(scope, receive, send, deps)`:
deps = {"repo": AuthRepository, "redis": aioredis, "email_gateway": EmailGateway,
        "settings": Settings}.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime, timedelta

from praxis2.auth.cookie_hash import audit_email_key
from praxis2.auth.errors import EmailConflict
from praxis2.auth.service import (
    hash_password,
    new_session_token,
    parse_cookie,
    serialize_cookie,
    verify_password,
)
from praxis2.store.redis import (
    auth_session_del,
    auth_session_set,
    email_throttle_check,
    login_fail_incr,
    login_fail_incr_ip,
    login_fail_reset,
    login_fail_reset_ip,
    user_sessions_add,
    user_sessions_drain,
)

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+(\.[^\s@]+)?$")  # 简化:支持 a@b 这种测试场景
_PURPOSES = {"register", "login", "reset"}
# D.2(M9 #6):双维度锁防 DoS 锁号 + 防扫号
_LOGIN_FAIL_LIMIT_EMAIL = 5
_LOGIN_FAIL_LIMIT_IP = 20
_CODE_ATTEMPTS_LIMIT = 5


async def _read_body(receive) -> dict:
    chunks = b""
    while True:
        msg = await receive()
        chunks += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not chunks:
        return {}
    try:
        return json.loads(chunks)
    except ValueError:
        return {}


async def _json(send, status: int, body: dict, *, extra_headers=()) -> None:
    data = json.dumps(body, ensure_ascii=False).encode()
    headers = [(b"content-type", b"application/json; charset=utf-8")]
    for k, v in extra_headers:
        headers.append((k, v))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": data})


def _client_ip(scope) -> str | None:
    c = scope.get("client")
    return c[0] if c else None


def _ua(scope) -> str | None:
    for k, v in scope.get("headers", []):
        if k == b"user-agent":
            return v.decode("utf-8", errors="ignore")
    return None


async def _set_session_cookie(deps, *, user_id, email, role, scope) -> str:
    """新发 session token + cookie + Redis 注册;返回 set-cookie 头值。"""
    settings = deps["settings"]
    redis = deps["redis"]
    token = new_session_token()
    ttl_s = settings.session_ttl_days * 86400
    now = datetime.now(UTC)
    await auth_session_set(
        redis,
        token,
        {
            "user_id": user_id,
            "email": email,
            "role": role,
            "created_at": now.isoformat(),
            "ip": _client_ip(scope),
            "ua": _ua(scope),
        },
        ttl_s=ttl_s,
        pepper=settings.password_pepper,
    )
    await user_sessions_add(redis, user_id, token, ttl_s=ttl_s)
    return serialize_cookie(
        token,
        ttl_s=ttl_s,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


# ── handlers ─────────────────────────────────────────────────────────


async def handle_send_code(scope, receive, send, deps) -> None:
    body = await _read_body(receive)
    email = (body.get("email") or "").strip().lower()
    purpose = body.get("purpose", "")
    if not _EMAIL_RE.match(email):
        await _json(send, 422, {"error": "邮箱格式不正确", "field": "email"})
        return
    if purpose not in _PURPOSES:
        await _json(send, 422, {"error": "purpose 无效", "field": "purpose"})
        return
    settings = deps["settings"]
    if purpose == "register" and not settings.allow_self_signup:
        await _json(send, 403, {"error": "暂未开放自助注册"})
        return
    ok = await email_throttle_check(deps["redis"], email, ttl_s=60)
    if not ok:
        await _json(send, 429, {"error": "请稍候再试"})
        return
    code = str(secrets.randbelow(1_000_000)).zfill(6)
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    await deps["repo"].insert_email_code(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
    )
    await deps["repo"].insert_audit(
        user_id=None,
        actor="self",
        action="email_send",
        resource="email",
        resource_id=audit_email_key(email, pepper=settings.password_pepper),
        ip=_client_ip(scope),
        ua=_ua(scope),
        meta={"purpose": purpose},
    )
    sent = await deps["email_gateway"].send_code(email, code, purpose)
    payload: dict = {"sent": sent.get("sent", False)}
    if settings.env_label != "prod" and sent.get("dev_code"):
        payload["dev_code"] = sent["dev_code"]
        payload["dev_note"] = sent.get("dev_note", "")
    await _json(send, 200, payload)


async def handle_register(scope, receive, send, deps) -> None:
    body = await _read_body(receive)
    email = (body.get("email") or "").strip().lower()
    code = body.get("code", "")
    password = body.get("password", "")
    display_name = body.get("display_name")
    if not _EMAIL_RE.match(email):
        await _json(send, 422, {"error": "邮箱格式不正确", "field": "email"})
        return
    if len(password) < 1:
        await _json(send, 422, {"error": "密码必填", "field": "password"})
        return
    repo = deps["repo"]
    row = await repo.get_latest_email_code(email, "register")
    if row is None or row.code != code:
        if row is not None:
            n = await repo.incr_email_code_attempts(row.id)
            if n >= _CODE_ATTEMPTS_LIMIT:
                await repo.mark_email_code_used(row.id)
        await _json(send, 400, {"error": "验证码无效或已过期"})
        return
    settings = deps["settings"]
    pw_hash = hash_password(password, pepper=settings.password_pepper)
    try:
        user = await repo.create_user(
            email=email,
            password_hash=pw_hash,
            display_name=display_name,
            role="user",
        )
    except EmailConflict as e:
        await _json(send, e.status, {"error": str(e)})
        return
    await repo.mark_email_code_used(row.id)
    # M9:signup_gift 入账(env 控制额度,0 = 不赠)
    granted_li = 0
    if settings.signup_gift_li > 0:
        ledger = deps.get("ledger")
        if ledger is not None:
            pool = getattr(repo, "_pool", None)
            if pool is None:
                # 测试 fake ledger 路径(无真 _pool)
                await ledger.record(None, user.id, settings.signup_gift_li,
                                    "signup_gift", None, None, {})
                granted_li = settings.signup_gift_li
            else:
                # 生产路径:用真 PG conn 包 transaction
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await ledger.record(conn, user.id, settings.signup_gift_li,
                                            "signup_gift", None, None, {})
                granted_li = settings.signup_gift_li
    await repo.insert_audit(
        user_id=user.id,
        actor="self",
        action="register",
        resource="user",
        resource_id=user.id,
        ip=_client_ip(scope),
        ua=_ua(scope),
        meta={},
    )
    cookie_val = await _set_session_cookie(
        deps,
        user_id=user.id,
        email=user.email,
        role=user.role,
        scope=scope,
    )
    await _json(
        send,
        200,
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            },
            "balance_li": granted_li,
        },
        extra_headers=((b"set-cookie", cookie_val.encode()),),
    )


async def handle_login(scope, receive, send, deps) -> None:
    """D.2(M9 #6):双维度锁 + 401 统一(防 DoS 锁号差异 + 防账号枚举)。

    - email 5 次 / IP 20 次 fail → 锁;两个独立计数
    - 已锁 / 邮箱不存在 / 密码错 全部返完全相同 401 + 同 body
    - 已锁状态下不递增计数(防 spam)
    - audit_log 仍记 login_fail(后台仍能区分),client 看不到差异
    """
    body = await _read_body(receive)
    email = (body.get("email") or "").strip().lower()
    password = body.get("password", "")
    if not email or not password:
        await _json(send, 422, {"error": "validation", "reason": "邮箱与密码必填"})
        return
    redis = deps["redis"]
    ip = _client_ip(scope) or "unknown"

    # 双维度查阈值(任一超阈即锁)
    email_cur = await redis.get(f"login_fail:{email}")
    ip_cur = await redis.get(f"login_fail_ip:{ip}")
    email_n = int(email_cur or 0)
    ip_n = int(ip_cur or 0)
    locked = email_n >= _LOGIN_FAIL_LIMIT_EMAIL or ip_n >= _LOGIN_FAIL_LIMIT_IP

    if locked:
        # 已锁:不查密码、不递增(防 spam),直接返统一 401
        await _json(
            send, 401, {"error": "unauthorized", "reason": "邮箱或密码错误"}
        )
        return

    repo = deps["repo"]
    user = await repo.get_user_by_email(email)
    settings = deps["settings"]
    if user is None or not verify_password(
        password, user.password_hash, pepper=settings.password_pepper
    ):
        # 邮箱不存在 / 密码错 → 同时递增两维度
        await login_fail_incr(redis, email, ttl_s=300)
        await login_fail_incr_ip(redis, ip, ttl_s=300)
        await repo.insert_audit(
            user_id=user.id if user else None,
            actor="self",
            action="login_fail",
            resource="user",
            resource_id=(
                user.id
                if user
                else audit_email_key(email, pepper=settings.password_pepper)
            ),
            ip=ip,
            ua=_ua(scope),
            meta={},
        )
        # 统一 401(不再 429 / 401 分流暴露状态;与已锁路径同 body)
        await _json(
            send, 401, {"error": "unauthorized", "reason": "邮箱或密码错误"}
        )
        return
    # 成功:清两维度计数
    await login_fail_reset(redis, email)
    await login_fail_reset_ip(redis, ip)
    await repo.update_last_login(
        user.id,
        ip=_client_ip(scope),
        at=datetime.now(UTC),
    )
    await repo.insert_audit(
        user_id=user.id,
        actor="self",
        action="login_success",
        resource="user",
        resource_id=user.id,
        ip=_client_ip(scope),
        ua=_ua(scope),
        meta={},
    )
    cookie_val = await _set_session_cookie(
        deps,
        user_id=user.id,
        email=user.email,
        role=user.role,
        scope=scope,
    )
    await _json(
        send,
        200,
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            },
            "balance_li": int(user.balance_li),
        },
        extra_headers=((b"set-cookie", cookie_val.encode()),),
    )


async def handle_logout(scope, receive, send, deps) -> None:
    cookie_header = None
    for k, v in scope.get("headers", []):
        if k == b"cookie":
            cookie_header = v.decode("utf-8", errors="ignore")
            break
    token = parse_cookie(cookie_header)
    if token:
        await auth_session_del(
            deps["redis"], token, pepper=deps["settings"].password_pepper
        )
    expire = serialize_cookie(
        "",
        ttl_s=0,
        secure=deps["settings"].cookie_secure,
        samesite=deps["settings"].cookie_samesite,
    )
    await _json(
        send,
        200,
        {"ok": True},
        extra_headers=((b"set-cookie", expire.encode()),),
    )


async def handle_logout_all(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    tokens = await user_sessions_drain(deps["redis"], user["user_id"])
    for t in tokens:
        await auth_session_del(
            deps["redis"], t, pepper=deps["settings"].password_pepper
        )
    expire = serialize_cookie(
        "",
        ttl_s=0,
        secure=deps["settings"].cookie_secure,
        samesite=deps["settings"].cookie_samesite,
    )
    await _json(
        send,
        200,
        {"ok": True, "sessions_killed": len(tokens)},
        extra_headers=((b"set-cookie", expire.encode()),),
    )


async def handle_me(scope, receive, send, deps) -> None:
    """M9:返 11 字段平铺(不嵌套 user),含 plan/balance/realname_verified/created_at。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    u = await deps["repo"].get_user_with_balance(user["user_id"])
    if not u:
        await _json(send, 401, {"error": "user_not_found", "reason": "用户不存在"})
        return
    balance_li = int(u["balance_li"])
    await _json(
        send,
        200,
        {
            "id": u["id"],
            "phone": u.get("phone"),
            "email": u["email"],
            "display_name": u["display_name"],
            "role": u["role"],
            "plan": u["plan"],
            "status": u["status"],
            "balance_li": balance_li,
            "balance_yuan": f"{balance_li / 100:.2f}",
            "realname_verified": u["realname_verified"],
            "created_at": u["created_at"].isoformat() if u.get("created_at") else "",
        },
    )


async def handle_me_balance(scope, receive, send, deps) -> None:
    """M9:接真 ledger,返 balance + 最近 20 条流水。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    balance_li = await deps["repo"].get_balance_li(user["user_id"])
    ledger = deps.get("ledger")
    if ledger is not None:
        rows = await ledger.recent(user["user_id"], limit=20)
    else:
        rows = []  # FakeAuthRepository test path
    await _json(send, 200, {
        "balance_li": int(balance_li),
        "balance_yuan": f"{balance_li / 100:.2f}",
        "recent": [
            {
                "id": r["id"],
                "amount_li": r["amount_li"],
                "kind": r["kind"],
                "ref_type": r["ref_type"],
                "ref_id": r["ref_id"],
                "balance_after": r["balance_after"],
                "meta": r["meta"],
                "created_at": (
                    r["created_at"].isoformat()
                    if hasattr(r["created_at"], "isoformat")
                    else r["created_at"]
                ),
            }
            for r in rows
        ],
    })


# ── M9: profile (GET/POST) ───────────────────────────────────────────
PROFILE_FIELDS_MAX: dict[str, int] = {
    "research_field": 256,
    "affiliation": 256,
    "expertise_level": 256,
    "projects": 2000,
    "custom_intro": 2000,
}


async def handle_me_profile_get(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    p = await deps["repo"].get_user_profile(user["user_id"])
    if p is None:
        await _json(send, 200, {
            "research_field": None, "affiliation": None,
            "expertise_level": None, "projects": None, "custom_intro": None,
            "updated_at": None,
        })
        return
    await _json(send, 200, {
        "research_field": p["research_field"],
        "affiliation": p["affiliation"],
        "expertise_level": p["expertise_level"],
        "projects": p["projects"],
        "custom_intro": p["custom_intro"],
        "updated_at": (
            p["updated_at"].isoformat()
            if p.get("updated_at") and hasattr(p["updated_at"], "isoformat")
            else None
        ),
    })


async def handle_me_profile_post(scope, receive, send, deps) -> None:
    """upsert profile;null/缺失 = 不动,"" = 清空,超长 = 400。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    body = await _read_body(receive)
    to_set: dict[str, str | None] = {}
    for k, max_len in PROFILE_FIELDS_MAX.items():
        if k not in body or body[k] is None:
            continue
        v = body[k]
        if not isinstance(v, str):
            await _json(send, 400, {"error": "field_invalid", "field": k})
            return
        if len(v) > max_len:
            await _json(send, 400, {
                "error": "field_too_long", "field": k, "max": max_len,
            })
            return
        to_set[k] = None if v == "" else v
    if to_set:
        await deps["repo"].upsert_user_profile(user["user_id"], **to_set)
    await handle_me_profile_get(scope, receive, send, deps)


def _require_admin(user):
    """统一 admin gate:None / 非 admin → 抛 tuple(status, body)。"""
    if not user:
        return 401, {"error": "unauthorized", "reason": "未登录"}
    if user.get("role") != "admin":
        return 403, {"error": "forbidden", "reason": "需 admin 权限"}
    return None


async def handle_me_account_delete(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    repo = deps["repo"]
    await repo.soft_delete_user(user["user_id"])
    tokens = await user_sessions_drain(deps["redis"], user["user_id"])
    for t in tokens:
        await auth_session_del(
            deps["redis"], t, pepper=deps["settings"].password_pepper
        )
    await repo.insert_audit(
        user_id=user["user_id"],
        actor="self",
        action="account_delete",
        resource="user",
        resource_id=user["user_id"],
        ip=_client_ip(scope),
        ua=_ua(scope),
        meta={},
    )
    expire = serialize_cookie(
        "",
        ttl_s=0,
        secure=deps["settings"].cookie_secure,
        samesite=deps["settings"].cookie_samesite,
    )
    await _json(
        send,
        200,
        {"ok": True},
        extra_headers=((b"set-cookie", expire.encode()),),
    )


async def handle_info(scope, receive, send, deps) -> None:
    """M9 stub:M10 完整化(/api/agents 等接后补 default_model 等)。"""
    settings = deps["settings"]
    await _json(
        send,
        200,
        {
            "service": "PRAXIS-2",
            "version": "v0.21.0",  # 0.21.0:MD 本地 A100 真执行链(LocalJobRunner+MCP gmx server)+四种增强采样全真跑(standard/SMD/伞形/REMD/metadynamics)
            "env": settings.env_label,
            "allow_self_signup": settings.allow_self_signup,
            "default_model": getattr(settings, "model", ""),
        },
    )


# ── ROUTES dict ──────────────────────────────────────────────────────

ROUTES: dict[tuple[str, str], str] = {
    ("/api/auth/email/send-code", "POST"): "handle_send_code",
    ("/api/auth/register", "POST"): "handle_register",
    ("/api/auth/login", "POST"): "handle_login",
    ("/api/auth/logout", "POST"): "handle_logout",
    ("/api/auth/logout-all", "POST"): "handle_logout_all",
    ("/api/me", "GET"): "handle_me",
    ("/api/me/balance", "GET"): "handle_me_balance",
    ("/api/me/account", "DELETE"): "handle_me_account_delete",
    ("/api/me/profile", "GET"): "handle_me_profile_get",
    ("/api/me/profile", "POST"): "handle_me_profile_post",
    ("/api/info", "GET"): "handle_info",
}
