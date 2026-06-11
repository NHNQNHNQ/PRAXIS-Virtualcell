"""auth.errors 单元测试。"""

from __future__ import annotations

from praxis2.auth.errors import (
    AuthError,
    CodeMismatch,
    EmailConflict,
    InvalidCredentials,
    SessionExpired,
    SignupClosed,
    TooManyAttempts,
)


def test_all_subclass_auth_error():
    for cls in (
        InvalidCredentials,
        SessionExpired,
        CodeMismatch,
        EmailConflict,
        SignupClosed,
        TooManyAttempts,
    ):
        assert issubclass(cls, AuthError)


def test_error_status_codes():
    assert InvalidCredentials("x").status == 401
    assert SessionExpired("x").status == 401
    assert CodeMismatch("x").status == 400
    assert EmailConflict("x").status == 409
    assert SignupClosed("x").status == 403
    assert TooManyAttempts("x").status == 429
