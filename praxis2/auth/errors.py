"""结构化认证错误派生(每类自带 HTTP status code,design §6 错误表)。"""

from __future__ import annotations


class AuthError(Exception):
    status: int = 500


class InvalidCredentials(AuthError):
    status = 401


class SessionExpired(AuthError):
    status = 401


class CodeMismatch(AuthError):
    status = 400


class EmailConflict(AuthError):
    status = 409


class SignupClosed(AuthError):
    status = 403


class TooManyAttempts(AuthError):
    status = 429
