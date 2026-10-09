"""auth.email 单元测试(Dev + Smtp 经 aiosmtpd 内存 SMTP)。"""

from __future__ import annotations

import pytest

from praxis2.auth.email import (
    DevEmailGateway,
    EmailGateway,
    SmtpEmailGateway,
    make_email_gateway,
)


@pytest.mark.asyncio
async def test_dev_gateway_returns_dev_code():
    g = DevEmailGateway()
    r = await g.send_code(email="a@b.com", code="123456", purpose="register")
    assert r == {
        "sent": True,
        "dev_code": "123456",
        "dev_note": "SMTP disabled — non-prod",
    }


@pytest.mark.asyncio
async def test_smtp_gateway_real_send_via_aiosmtpd():
    pytest.importorskip("aiosmtpd")
    from aiosmtpd.controller import Controller

    class _Sink:
        def __init__(self):
            self.messages = []

        async def handle_DATA(self, server, session, envelope):
            self.messages.append(
                {
                    "from": envelope.mail_from,
                    "to": list(envelope.rcpt_tos),
                    "data": envelope.content.decode("utf-8", errors="replace"),
                }
            )
            return "250 OK"

    # aiosmtpd 1.4 _trigger_server 不支持 port=0(用 self.port 探活,等于 0 连不上)
    # 改成 OS 提前给空 port
    import socket as _socket

    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as _s:
        _s.bind(("127.0.0.1", 0))
        free_port = _s.getsockname()[1]
    sink = _Sink()
    ctrl = Controller(sink, hostname="127.0.0.1", port=free_port)
    ctrl.start()
    try:
        g = SmtpEmailGateway(
            host="127.0.0.1",
            port=free_port,
            user="",
            password="",
            from_addr="noreply@praxis-2",
            use_ssl=False,
        )
        r = await g.send_code(email="a@b.com", code="654321", purpose="login")
        assert r == {"sent": True}
        assert len(sink.messages) == 1
        msg = sink.messages[0]
        assert msg["from"] == "noreply@praxis-2"
        assert msg["to"] == ["a@b.com"]
        assert "654321" in msg["data"]
    finally:
        ctrl.stop()


def test_make_email_gateway_returns_dev_when_smtp_host_empty():
    class _S:
        smtp_host = ""
        smtp_port = 0
        smtp_user = ""
        smtp_password = ""
        smtp_from = ""

    assert isinstance(make_email_gateway(_S()), DevEmailGateway)


def test_make_email_gateway_returns_smtp_when_configured():
    class _S:
        smtp_host = "smtp.example.com"
        smtp_port = 465
        smtp_user = "u"
        smtp_password = "p"
        smtp_from = "from@example.com"

    assert isinstance(make_email_gateway(_S()), SmtpEmailGateway)


def test_dev_implements_protocol():
    assert isinstance(DevEmailGateway(), EmailGateway)


def test_dev_env_with_empty_smtp_returns_dev_gateway():
    """非 prod 允许 Dev(行为保持)。"""
    from praxis2.auth.email import DevEmailGateway, make_email_gateway

    class _S:
        smtp_host = ""
        env_label = "dev"

    assert isinstance(make_email_gateway(_S()), DevEmailGateway)


def test_prod_env_with_smtp_host_returns_smtp_gateway():
    """prod 配齐 SMTP → SmtpEmailGateway(正常路径)。"""
    from praxis2.auth.email import SmtpEmailGateway, make_email_gateway

    class _S:
        smtp_host = "smtp.example.com"
        smtp_port = 587
        smtp_user = "u"
        smtp_password = "p"
        smtp_from = "noreply@example.com"
        env_label = "prod"

    gw = make_email_gateway(_S())
    assert isinstance(gw, SmtpEmailGateway)
