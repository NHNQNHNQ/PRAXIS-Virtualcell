"""Session token 哈希:cookie 持原 token,Redis 存 HMAC-SHA256。

即使 Redis dump 泄露,原 token 不可逆推。
Pepper rotation:更换 password_pepper 自动让所有旧 session 失效。"""

from __future__ import annotations

import hashlib
import hmac


def session_key_from_token(token: str, *, pepper: str) -> str:
    """HMAC-SHA256(pepper, token) → 64-char lowercase hex。"""
    if not token:
        raise ValueError("token 必填")
    if not pepper:
        raise ValueError("pepper 必填(配置 PRAXIS_PASSWORD_PEPPER)")
    return hmac.new(
        pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def audit_email_key(email: str, *, pepper: str) -> str:
    """email → 16-char HMAC 前缀,用作 audit_log.resource_id(GDPR/CCPA-friendly)。

    可关联(同 email 多次操作 → 同 hash)但不可逆推。
    16 chars = 64-bit 熵,足够无冲突(billion entries 内)。
    Pepper rotation 自动让旧 audit 与新 audit 关联断开
    (可接受:rotation 是稀有事件,断开换增量隐私)。

    与 session_key_from_token(64-char)语义不同、长度不同,不可混用。
    """
    if not email:
        return ""
    return hmac.new(
        pepper.encode("utf-8"), email.encode("utf-8"), hashlib.sha256
    ).hexdigest()[:16]
