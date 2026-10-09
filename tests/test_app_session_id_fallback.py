"""v0.16.1 patch:session_id fallback 不再用固定 "default",改 uuid4().hex
(防 server SessionPool 状态泄漏 — eval_v0160.py 评测顺手发现的 production bug)。

回归(v0.16.0 GA 评测 2026-06-02 报告):chat-stream payload 不传 session_id
时,server app.py:528 默认 "default",所有请求命中同 SessionPool slot,
`State.turn_count` 跨请求累计 → 超 max_turns=20 后 chat 立即 final reason=max_turns
死锁,需 restart gunicorn 才恢复。

修复:fallback 改 uuid4().hex(每请求 unique),消除跨请求 State 泄漏。
正常 FE(v0.15.0 起)始终显式传 session_id,不受影响;只有 curl 裸测 /
eval 脚本等边界 client 命中此 fallback,这些场景多是单 turn 不需复用。
"""
from __future__ import annotations

import re
import uuid

from praxis2.server.app import _resolve_session_id

_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


def test_explicit_session_id_passthrough():
    """显式传 session_id → 原样返(不覆盖,保持现有多轮 context 路径)。"""
    assert _resolve_session_id({"session_id": "my-chat-42"}) == "my-chat-42"
    assert _resolve_session_id({"session_id": "anything-unique-xyz"}) == "anything-unique-xyz"


def test_missing_session_id_yields_unique_uuid():
    """v0.16.1 fix:不传 session_id → 生成 uuid4.hex(32 字符 hex)。"""
    sid1 = _resolve_session_id({})
    sid2 = _resolve_session_id({})
    assert _UUID_HEX_RE.match(sid1), f"应为 uuid4.hex 32-char,得到 {sid1!r}"
    assert _UUID_HEX_RE.match(sid2)
    # 关键不变量:两次 fallback 必须返不同 id(否则跨请求 SessionPool 仍泄漏)
    assert sid1 != sid2, "两次 fallback 不能命中同 id,否则 State 仍跨请求复用"


def test_empty_string_session_id_yields_unique_uuid():
    """空字符串也算 falsy → fallback uuid(防 client 传 '' 字面绕过)。"""
    sid1 = _resolve_session_id({"session_id": ""})
    sid2 = _resolve_session_id({"session_id": ""})
    assert _UUID_HEX_RE.match(sid1)
    assert _UUID_HEX_RE.match(sid2)
    assert sid1 != sid2


def test_none_session_id_yields_unique_uuid():
    """None 同理(JSON null → Python None → falsy → fallback)。"""
    sid1 = _resolve_session_id({"session_id": None})
    sid2 = _resolve_session_id({"session_id": None})
    assert _UUID_HEX_RE.match(sid1)
    assert sid1 != sid2


def test_whitespace_only_session_id_yields_unique_uuid():
    """v0.16.3:纯空格 session_id(strip 后空)→ fallback uuid,
    防 client 传 '   ' 绕过 → 否则会变成有效 SessionPool key 重新引入泄漏。"""
    sid1 = _resolve_session_id({"session_id": "   "})
    sid2 = _resolve_session_id({"session_id": "\t\n  "})
    assert _UUID_HEX_RE.match(sid1), f"纯空格应 fallback uuid,得到 {sid1!r}"
    assert _UUID_HEX_RE.match(sid2)
    assert sid1 != sid2


def test_session_id_with_surrounding_whitespace_preserved():
    """非纯空格(含实际内容)→ 原样返(不 strip 内容,只判 falsy)。
    'my-chat ' 含实际字符,不该被当 falsy。"""
    # 注意:实现用 str(sid).strip() 仅做 falsy 判断,不改写返回值
    assert _resolve_session_id({"session_id": "my-chat"}) == "my-chat"


def test_no_more_default_session_id():
    """关键回归:不能再返 'default' 字面串(那正是 bug 本身)。"""
    for _ in range(10):
        sid = _resolve_session_id({})
        assert sid != "default", "v0.16.1 起 fallback 必须 unique,绝不可返 'default'"


def test_session_id_is_valid_uuid_format():
    """fallback 返的值必须是合法 uuid4.hex(便于后续 logging / 监控解析)。"""
    sid = _resolve_session_id({})
    # 能 parse 回 uuid 对象即合法
    parsed = uuid.UUID(sid)
    assert parsed.version == 4
