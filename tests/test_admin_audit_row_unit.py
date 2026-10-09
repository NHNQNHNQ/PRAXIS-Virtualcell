"""AuditRepo._audit_row — IPv4/IPv6 → str + UUID/json/datetime 转换。

回归保护:asyncpg 把 INET 列反序列化成 ipaddress.IPv4Address/IPv6Address,
json.dumps 直接遇到会 TypeError → 500。修复后 _audit_row 必须 str() 化。
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import uuid

from praxis2.admin.repo import AuditRepo


class _FakeRecord(dict):
    """伪 asyncpg.Record:asyncpg.Record 不可直接 dict() in tests,用 dict 子类替。"""


def _make_row(**overrides):
    base = {
        "id": 42,
        "user_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "actor": "admin",
        "action": "balance_adjust",
        "resource": "user",
        "resource_id": "uid-1",
        "ip": None,
        "ua": "test-ua",
        "meta": None,
        "created_at": dt.datetime(2026, 5, 29, 6, 51, 0, tzinfo=dt.UTC),
    }
    base.update(overrides)
    return _FakeRecord(base)


def test_audit_row_ipv4_serialized_as_str():
    row = _make_row(ip=ipaddress.IPv4Address("127.0.0.1"))
    out = AuditRepo._audit_row(row)
    assert out["ip"] == "127.0.0.1"
    assert isinstance(out["ip"], str)


def test_audit_row_ipv6_serialized_as_str():
    row = _make_row(ip=ipaddress.IPv6Address("::1"))
    out = AuditRepo._audit_row(row)
    assert out["ip"] == "::1"
    assert isinstance(out["ip"], str)


def test_audit_row_ip_none_preserved():
    row = _make_row(ip=None)
    out = AuditRepo._audit_row(row)
    assert out["ip"] is None


def test_audit_row_user_id_str_and_created_at_iso():
    row = _make_row()
    out = AuditRepo._audit_row(row)
    assert out["user_id"] == "00000000-0000-0000-0000-000000000001"
    assert out["created_at"] == "2026-05-29T06:51:00+00:00"


def test_audit_row_meta_str_decoded():
    row = _make_row(meta='{"k": "v"}')
    out = AuditRepo._audit_row(row)
    assert out["meta"] == {"k": "v"}


def test_audit_row_meta_dict_kept():
    row = _make_row(meta={"k": "v"})
    out = AuditRepo._audit_row(row)
    assert out["meta"] == {"k": "v"}


def test_audit_row_full_json_serializable():
    """端到端:_audit_row 输出能 json.dumps,不抛 TypeError。"""
    import json

    row = _make_row(ip=ipaddress.IPv4Address("10.0.0.1"), meta={"x": 1})
    out = AuditRepo._audit_row(row)
    s = json.dumps(out)
    assert '"ip": "10.0.0.1"' in s
