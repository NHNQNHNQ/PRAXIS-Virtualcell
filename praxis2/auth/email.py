"""邮箱网关:EmailGateway Protocol + DevEmailGateway + SmtpEmailGateway。"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any, Protocol, runtime_checkable

_BODY_TPL = {
    "register": "您正在注册 PRAXIS-2 账号,验证码:{code}。5 分钟内有效。",
    "login": "您正在登录 PRAXIS-2,验证码:{code}。5 分钟内有效。",
    "reset": "您正在重置 PRAXIS-2 密码,验证码:{code}。5 分钟内有效。",
}
_SUBJECT_TPL = {
    "register": "PRAXIS-2 注册验证码",
    "login": "PRAXIS-2 登录验证码",
    "reset": "PRAXIS-2 密码重置验证码",
}


@runtime_checkable
class EmailGateway(Protocol):
    async def send_code(self, email: str, code: str, purpose: str) -> dict[str, Any]: ...


class DevEmailGateway:
    """dev fallback:不真发,response 回填 dev_code(同 v1 PRAXIS-hou dev)。"""

    async def send_code(self, email, code, purpose):
        return {
            "sent": True,
            "dev_code": code,
            "dev_note": "SMTP disabled — non-prod",
        }


class SmtpEmailGateway:
    """asyncio.to_thread + smtplib 真发(M9 用管理员邮箱)。"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        use_ssl: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr
        self._use_ssl = use_ssl

    def _send_sync(self, to: str, code: str, purpose: str) -> None:
        msg = EmailMessage()
        msg["From"] = self._from
        msg["To"] = to
        msg["Subject"] = _SUBJECT_TPL.get(purpose, "PRAXIS-2 验证码")
        msg.set_content(_BODY_TPL.get(purpose, "您的 PRAXIS-2 验证码:{code}").format(code=code))
        smtp_cls = smtplib.SMTP_SSL if self._use_ssl else smtplib.SMTP
        with smtp_cls(self._host, self._port, timeout=10) as s:
            if self._user:
                s.login(self._user, self._password)
            s.send_message(msg)

    async def send_code(self, email, code, purpose):
        await asyncio.to_thread(self._send_sync, email, code, purpose)
        return {"sent": True}


def make_email_gateway(settings) -> EmailGateway:
    """按 settings.smtp_host 切换:空 → Dev,有 → Smtp。

    Prod 守卫已上移到 Settings.__post_init__(§6⑤ fail-fast,boot 即崩)。"""
    if not getattr(settings, "smtp_host", ""):
        return DevEmailGateway()
    return SmtpEmailGateway(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        from_addr=settings.smtp_from,
        use_ssl=settings.smtp_port == 465,
    )
