"""ProposalRepo CRUD — 真 PG fixture (pg_pool / fake_user_id)."""
from __future__ import annotations

import uuid as _uuid

import pytest

from praxis2.proposals.repo import (
    ProposalAlreadyDecided,
    ProposalNotFound,
    ProposalRepo,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_create_returns_proposal_id(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        pid = await repo.create(conn, fake_user_id, "idea", "test title", "body")
    assert isinstance(pid, str)
    assert len(pid) == 36  # UUID


async def test_create_invalid_kind_raises(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        with pytest.raises(ValueError, match="invalid_kind"):
            await repo.create(conn, fake_user_id, "bogus", "t", "b")


async def test_list_mine_pagination(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        for i in range(5):
            await repo.create(conn, fake_user_id, "idea", f"title {i}", None)
    page1 = await repo.list_mine(fake_user_id, page=1, limit=3)
    assert len(page1["rows"]) == 3
    assert page1["total"] >= 5
    page2 = await repo.list_mine(fake_user_id, page=2, limit=3)
    assert len(page2["rows"]) >= 2


async def test_count_recent_filters_by_time(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        await repo.create(conn, fake_user_id, "bug", "recent", None)
    count = await repo.count_recent(fake_user_id, hours=24)
    assert count >= 1


async def test_list_all_admin_with_filters(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        await repo.create(conn, fake_user_id, "idea", "i1", None)
        await repo.create(conn, fake_user_id, "bug", "b1", None)
    by_bug = await repo.list_all({"kind": "bug"}, page=1, limit=50)
    assert all(r["kind"] == "bug" for r in by_bug["rows"])
    assert by_bug["total"] >= 1


async def test_decide_marks_decided_and_sets_verdict(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        pid = await repo.create(conn, fake_user_id, "feature", "f1", None)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            result = await repo.decide(
                conn, pid, admin_id=fake_user_id,
                verdict="ship", score=4, shipped_to="abc123",
                note="lgtm",
            )
    assert result["status"] == "decided"
    assert result["verdict"] == "ship"
    # 验 DB 真写入 (regression guard for plan SQL $4/$7 bug)
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT decided_by, admin_scores FROM proposals WHERE id=$1",
            _uuid.UUID(pid),
        )
    assert str(row["decided_by"]) == fake_user_id
    import json as _json
    raw = row["admin_scores"]
    scores = _json.loads(raw) if isinstance(raw, str) else raw
    assert scores[fake_user_id] == 4


async def test_decide_already_decided_raises(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        pid = await repo.create(conn, fake_user_id, "feature", "f2", None)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.decide(conn, pid, fake_user_id, "hold")
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ProposalAlreadyDecided):
                await repo.decide(conn, pid, fake_user_id, "ship")


async def test_decide_invalid_verdict_raises(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        pid = await repo.create(conn, fake_user_id, "idea", "i", None)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ValueError, match="invalid_verdict"):
                await repo.decide(conn, pid, fake_user_id, "bogus")


async def test_decide_unknown_id_raises(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ProposalNotFound):
                await repo.decide(conn, str(_uuid.uuid4()), fake_user_id, "ship")


async def test_decide_invalid_score_raises(pg_pool, fake_user_id):
    repo = ProposalRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        pid = await repo.create(conn, fake_user_id, "idea", "i", None)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ValueError, match="invalid_score"):
                await repo.decide(conn, pid, fake_user_id, "ship", score=0)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ValueError, match="invalid_score"):
                await repo.decide(conn, pid, fake_user_id, "ship", score=6)
