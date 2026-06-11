"""auth 纯函数层(argon2id+pepper / token / cookie / SessionData,无 IO)。

sync v1 PRAXIS-hou auth_service.py 协议(argon2 参数 / pepper / token / cookie)。
"""

from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)
COOKIE_NAME = "praxis_session"


def _peppered(password: str, pepper: str) -> str:
    return password + "::" + pepper


def hash_password(password: str, *, pepper: str) -> bytes:
    return _hasher.hash(_peppered(password, pepper)).encode("utf-8")


def verify_password(password: str, stored_hash: bytes, *, pepper: str) -> bool:
    try:
        _hasher.verify(stored_hash.decode("utf-8"), _peppered(password, pepper))
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(stored_hash: bytes) -> bool:
    return _hasher.check_needs_rehash(stored_hash.decode("utf-8"))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class SessionData:
    user_id: str
    email: str
    role: str = "user"
    ip: str | None = None
    ua: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def serialize_cookie(token: str, *, ttl_s: int, secure: bool, samesite: str = "Lax") -> str:
    parts = [
        f"{COOKIE_NAME}={token}",
        "HttpOnly",
        f"SameSite={samesite}",
        "Path=/",
        f"Max-Age={int(ttl_s)}",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def parse_cookie(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    for piece in cookie_header.split(";"):
        piece = piece.strip()
        if piece.startswith(f"{COOKIE_NAME}="):
            return piece[len(f"{COOKIE_NAME}=") :]
    return None
