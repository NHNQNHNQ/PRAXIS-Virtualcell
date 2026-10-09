"""Bug(2026-05-31 FE smoke):GET /api/me/proposals 返回 envelope key 与 admin handler 不一致。

handle_proposal_list_mine 直接落 repo.list_mine() 原生 dict(含 'rows'),
但 admin 兄弟 handler 显式 wrap 成 'proposals' 字段(FE 期望)。
FE ProposalsModal 走 'proposals' 兜底 → MyList 误显示"提案功能尚未上线"。

修法:user-面 handler 也 wrap 成 'proposals' + 'total/page/limit',与 admin 对齐。
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from praxis2.proposals.handlers import handle_proposal_list_mine


class _FakeRepo:
    async def list_mine(self, user_id: str, *, page: int, limit: int) -> dict[str, Any]:
        # 模拟真实 repo 返回:rows + 分页元数据
        return {
            "rows": [
                {"id": "r1", "kind": "idea", "title": "hi", "status": "open"},
                {"id": "r2", "kind": "bug", "title": "bug", "status": "open"},
            ],
            "total": 2,
            "page": page,
            "limit": limit,
        }


def _send_collector() -> tuple[list[dict], Any]:
    """返回 (events, send_callable);send_callable 把每个 ASGI event 落到 list。"""
    events: list[dict] = []

    async def send(ev: dict) -> None:
        events.append(ev)

    return events, send


def _parse_body(events: list[dict]) -> dict:
    body_bytes = b"".join(ev.get("body", b"") for ev in events if ev["type"] == "http.response.body")
    return json.loads(body_bytes.decode("utf-8"))


@pytest.mark.asyncio
async def test_list_mine_returns_proposals_key_not_rows():
    """user-面 list 必须返 'proposals' key(与 admin handler + FE 期望对齐)。"""
    scope = {
        "user": {"user_id": "u1"},
        "query_string": b"",
    }
    events, send = _send_collector()
    deps = {"proposal_repo": _FakeRepo()}

    async def _noop_receive() -> dict:
        return {}

    await handle_proposal_list_mine(scope, _noop_receive, send, deps)

    body = _parse_body(events)
    # ★ 核心契约:envelope key 是 'proposals'(不是 'rows'),与 admin handler 一致
    assert "proposals" in body
    assert "rows" not in body  # 旧 key 不应再泄漏
    assert isinstance(body["proposals"], list)
    assert len(body["proposals"]) == 2
    # 分页元数据透传
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["limit"] == 50  # clamp 默认
