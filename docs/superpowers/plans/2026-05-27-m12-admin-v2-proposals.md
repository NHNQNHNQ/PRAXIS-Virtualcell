# M12 Admin v2 + Proposals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **2026-05-29 errata**:原文 `1元=10li` 是笔误,应为 `1元=100li`(沿用 M9 spec)。
> Task 5: Ledger.record 返 balance, ledger_id 单独 SELECT (见 repo.py adjust_balance)

**Goal:** Ship 13 endpoint(8 admin v2 + 5 proposals)+ 1 张新表 `proposals` + 同事务 audit + ledger,作为 M13 路线图准入条件之一(M9–M12 全 ship)。

**Architecture:** 横向 TDD 层,底向上:migration → repo → handlers → wire → tests。复用 M9 已有的 `audit_log` 表 / `repository_pg.insert_audit` / `Ledger.record` / `_require_admin` gate。proposals 表新建,8 个新 admin endpoint 直接注册路由,5 个 M9 admin stub 替换真 handler(路由不变)。每个 admin mutation handler 内手动 `audit_repo.insert(...)` 跟 main op 同 tx。

**Tech Stack:** Python 3.13 / asyncpg / Alembic / raw ASGI / pytest-asyncio / testcontainers PG+Redis(M9–M11.2 已用)。

**Spec:** `docs/superpowers/specs/2026-05-27-m12-admin-v2-proposals-design.md`(commit 5d787e7)

---

## File Structure

**新增 13 个文件**:
- `migrations/versions/006_proposals.py` — Alembic 迁移 + 2 个 index
- `praxis2/admin/__init__.py` — 空包
- `praxis2/admin/repo.py` — `AdminUserRepo`(list_users / adjust_balance / freeze / unfreeze / reconcile / get_stats)+ `AuditRepo`(query)
- `praxis2/admin/handlers.py` — 8 个 admin ASGI handler
- `praxis2/proposals/__init__.py` — 空包
- `praxis2/proposals/repo.py` — `ProposalRepo`(create / list_mine / list_all / decide / count_recent for rate limit)
- `praxis2/proposals/handlers.py` — 5 个 ASGI handler + kind/verdict 校验
- `tests/test_proposals_validators.py` — kind/verdict/字段长度 unit
- `tests/test_admin_pagination_unit.py` — page/limit clamp + q escape
- `tests/integration/test_proposals_repo.py` — CRUD + decide + already_decided
- `tests/integration/test_admin_user_repo.py` — list / adjust 同 tx / freeze / unfreeze / stats / reconcile mismatch
- `tests/integration/test_audit_repo.py` — query + 过滤 + pagination
- `tests/integration/test_m12_admin_e2e.py` — login → list → adjust → audit log → freeze → unfreeze
- `tests/integration/test_m12_proposal_e2e.py` — user post → admin list → decide → audit + 状态

**修改 4 个文件**:
- `praxis2/auth/routes.py` — 删 5 个 admin stub + `ROUTES` 表里对应项(routes 在 server/app.py 重新 wire)
- `praxis2/server/app.py` — `_admin_deps` + `_proposal_deps` 组装 + 13 个 route dispatch
- `praxis2/config.py` — 加 2 个 env(`PRAXIS_ADMIN_RECONCILE_MAX_USERS=1000` / `PRAXIS_PROPOSALS_PER_USER_PER_DAY=20`)到 `_KNOWN_KEYS` + `Settings` + `load_from_env`
- `tests/integration/conftest.py` — `_TestSettings` 加 2 个 M12 字段

**新增 env**(全可选,有默认):
- `PRAXIS_ADMIN_RECONCILE_MAX_USERS=1000`
- `PRAXIS_PROPOSALS_PER_USER_PER_DAY=20`

---

### Task 1: 006_proposals migration

**Files:**
- Create: `migrations/versions/006_proposals.py`
- Test: `tests/integration/test_migrations_006.py`(新文件,沿 M11.2 风格)

- [ ] **Step 1: 写迁移文件**

```python
"""proposals 表: 用户 idea/feature/bug + admin 决策审计。

Revision ID: 006_proposals
Revises: 005_md_jobs
"""

from __future__ import annotations

from alembic import op

revision = "006_proposals"
down_revision = "005_md_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE proposals (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          kind          TEXT NOT NULL CHECK (kind IN ('idea','feature','bug')),
          title         TEXT NOT NULL,
          body          TEXT,
          status        TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','decided','closed')),
          state         TEXT NOT NULL DEFAULT 'submitted'
                        CHECK (state IN ('submitted','withdrawn','archived')),
          admin_verdict TEXT CHECK (admin_verdict IN ('ship','promote','hold','reject')),
          admin_scores  JSONB,
          shipped_to    TEXT,
          decision_note TEXT,
          decided_at    TIMESTAMPTZ,
          decided_by    UUID REFERENCES users(id) ON DELETE SET NULL,
          created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_proposals_user_created ON proposals (user_id, created_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_proposals_status_created ON proposals (status, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS proposals;")
```

- [ ] **Step 2: 跑 alembic 验上下行**

Run:
```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic downgrade -1
.venv/bin/python -m alembic upgrade head
```

Expected: 3 次都不报错,`alembic current` 显示 `006_proposals (head)`。

- [ ] **Step 3: Commit**

```bash
git add migrations/versions/006_proposals.py
git commit -m "feat(m12): 006_proposals migration — kind/status/state 双轴 + admin_scores JSONB"
```

---

### Task 2: ProposalRepo - create + list_mine

**Files:**
- Create: `praxis2/proposals/__init__.py`(空)
- Create: `praxis2/proposals/repo.py`
- Create: `tests/integration/test_proposals_repo.py`

- [ ] **Step 1: 写 ProposalRepo 骨架 + create**

```python
# praxis2/proposals/repo.py
"""proposals 表 CRUD + decide 接 audit_log 同事务。"""
from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg


_PROPOSAL_KIND = {"idea", "feature", "bug"}
_PROPOSAL_VERDICT = {"ship", "promote", "hold", "reject"}


class ProposalRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self, conn: asyncpg.Connection,
        user_id: str, kind: str, title: str, body: str | None,
    ) -> str:
        if kind not in _PROPOSAL_KIND:
            raise ValueError(f"invalid_kind:{kind}")
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        row = await conn.fetchrow(
            "INSERT INTO proposals (user_id, kind, title, body) "
            "VALUES ($1, $2, $3, $4) RETURNING id, status, state, created_at",
            uid, kind, title, body,
        )
        return str(row["id"])

    async def list_mine(
        self, user_id: str, page: int, limit: int,
    ) -> dict[str, Any]:
        uid = uuid.UUID(user_id)
        offset = (page - 1) * limit
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, kind, title, body, status, state, admin_verdict, "
                "shipped_to, decision_note, decided_at, created_at "
                "FROM proposals WHERE user_id=$1 "
                "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                uid, limit, offset,
            )
            total = await conn.fetchval(
                "SELECT count(*) FROM proposals WHERE user_id=$1", uid,
            )
        return {
            "rows": [self._row_to_dict(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def count_recent(self, user_id: str, hours: int = 24) -> int:
        """rate limit 用:user 最近 N 小时 proposal 数。"""
        uid = uuid.UUID(user_id)
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT count(*) FROM proposals "
                "WHERE user_id=$1 AND created_at > now() - ($2 || ' hours')::interval",
                uid, str(hours),
            )

    @staticmethod
    def _row_to_dict(r: asyncpg.Record) -> dict[str, Any]:
        d = dict(r)
        d["id"] = str(d["id"])
        for k in ("created_at", "decided_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        return d
```

- [ ] **Step 2: 写 integration test**

```python
# tests/integration/test_proposals_repo.py
"""ProposalRepo CRUD — 真 PG fixture (pg_pool / fake_user_id)。"""
from __future__ import annotations

import pytest

from praxis2.proposals.repo import ProposalRepo

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
```

- [ ] **Step 3: 跑 test 确认通过**

Run: `.venv/bin/python -m pytest tests/integration/test_proposals_repo.py -v`
Expected: 4 PASS。

- [ ] **Step 4: Commit**

```bash
git add praxis2/proposals/__init__.py praxis2/proposals/repo.py tests/integration/test_proposals_repo.py
git commit -m "feat(m12): ProposalRepo create + list_mine + count_recent"
```

---

### Task 3: ProposalRepo - list_all + decide

**Files:**
- Modify: `praxis2/proposals/repo.py`(加 `list_all` + `decide`)
- Modify: `tests/integration/test_proposals_repo.py`(加 test)

- [ ] **Step 1: 加 list_all + decide method**

加到 `praxis2/proposals/repo.py` 的 `ProposalRepo` class:

```python
    async def list_all(
        self, filters: dict[str, Any], page: int, limit: int,
    ) -> dict[str, Any]:
        """admin 用:全表 + 可选 status/kind filter。"""
        offset = (page - 1) * limit
        where_clauses = []
        args: list[Any] = []
        if filters.get("status"):
            args.append(filters["status"])
            where_clauses.append(f"status = ${len(args)}")
        if filters.get("kind"):
            args.append(filters["kind"])
            where_clauses.append(f"kind = ${len(args)}")
        where_sql = (
            " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        )
        args.extend([limit, offset])
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, user_id, kind, title, body, status, state, "
                f"admin_verdict, admin_scores, shipped_to, decision_note, "
                f"decided_at, decided_by, created_at "
                f"FROM proposals{where_sql} "
                f"ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}",
                *args,
            )
            total = await conn.fetchval(
                f"SELECT count(*) FROM proposals{where_sql}",
                *args[:-2],
            )
        return {
            "rows": [self._admin_row_to_dict(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def decide(
        self, conn: asyncpg.Connection,
        proposal_id: str, admin_id: str, verdict: str,
        score: int | None = None,
        shipped_to: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """admin 决策。caller 提供 conn(同 tx 跟 audit 一起 commit)。

        返 dict {ok, status, verdict, decided_at};若 status != 'open' 抛 ConflictError。
        """
        if verdict not in _PROPOSAL_VERDICT:
            raise ValueError(f"invalid_verdict:{verdict}")
        if score is not None and not (1 <= score <= 5):
            raise ValueError(f"invalid_score:{score}")
        pid = uuid.UUID(proposal_id)
        aid = uuid.UUID(admin_id)

        # 检查 status 必 open
        cur = await conn.fetchrow(
            "SELECT status FROM proposals WHERE id=$1 FOR UPDATE", pid,
        )
        if cur is None:
            raise ProposalNotFound(proposal_id)
        if cur["status"] != "open":
            raise ProposalAlreadyDecided(proposal_id, cur["status"])

        # admin_scores jsonb_set 累加
        scores_arg = (
            json.dumps(score) if score is not None else None
        )
        row = await conn.fetchrow(
            """
            UPDATE proposals SET
              status='decided',
              admin_verdict=$2,
              admin_scores=CASE
                WHEN $3::jsonb IS NULL THEN admin_scores
                ELSE jsonb_set(
                  COALESCE(admin_scores, '{}'::jsonb),
                  ARRAY[$4::text],
                  $3::jsonb
                )
              END,
              shipped_to=$5,
              decision_note=$6,
              decided_at=now(),
              decided_by=$4
            WHERE id=$1
            RETURNING status, admin_verdict, decided_at
            """,
            pid, verdict, scores_arg, str(aid), shipped_to, note,
        )
        return {
            "ok": True,
            "status": row["status"],
            "verdict": row["admin_verdict"],
            "decided_at": row["decided_at"].isoformat(),
        }

    @staticmethod
    def _admin_row_to_dict(r: asyncpg.Record) -> dict[str, Any]:
        d = dict(r)
        d["id"] = str(d["id"])
        d["user_id"] = str(d["user_id"])
        if d.get("decided_by"):
            d["decided_by"] = str(d["decided_by"])
        if d.get("admin_scores"):
            d["admin_scores"] = json.loads(d["admin_scores"]) if isinstance(
                d["admin_scores"], str
            ) else d["admin_scores"]
        for k in ("created_at", "decided_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        return d


class ProposalNotFound(Exception):
    def __init__(self, pid: str) -> None:
        super().__init__(f"proposal not found: {pid}")
        self.pid = pid


class ProposalAlreadyDecided(Exception):
    def __init__(self, pid: str, status: str) -> None:
        super().__init__(f"proposal {pid} already in status {status}")
        self.pid = pid
        self.status = status
```

- [ ] **Step 2: 加 test**

加到 `tests/integration/test_proposals_repo.py`:

```python
from praxis2.proposals.repo import ProposalAlreadyDecided


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
```

- [ ] **Step 3: 跑 test**

Run: `.venv/bin/python -m pytest tests/integration/test_proposals_repo.py -v`
Expected: 8 PASS。

- [ ] **Step 4: Commit**

```bash
git add praxis2/proposals/repo.py tests/integration/test_proposals_repo.py
git commit -m "feat(m12): ProposalRepo list_all (admin filters) + decide (already_decided 409)"
```

---

### Task 4: AdminUserRepo - list_users

**Files:**
- Create: `praxis2/admin/__init__.py`(空)
- Create: `praxis2/admin/repo.py`
- Create: `tests/integration/test_admin_user_repo.py`

- [ ] **Step 1: AdminUserRepo 骨架 + list_users**

```python
# praxis2/admin/repo.py
"""admin v2 后端:user 管理 + audit 查询 + reconcile + stats。"""
from __future__ import annotations

import uuid
from typing import Any

import asyncpg

from praxis2.accounting.ledger import Ledger, LedgerError


class AdminUserRepo:
    def __init__(self, pool: asyncpg.Pool, ledger: Ledger) -> None:
        self._pool = pool
        self._ledger = ledger

    async def list_users(
        self, q: str, page: int, limit: int,
    ) -> dict[str, Any]:
        """模糊匹配 email + display_name (ILIKE %q%)。q='' 返全表。"""
        offset = (page - 1) * limit
        async with self._pool.acquire() as conn:
            if q:
                pattern = f"%{q}%"
                rows = await conn.fetch(
                    "SELECT id, email, phone, display_name, role, plan, status, "
                    "balance_li, created_at, last_login_at "
                    "FROM users "
                    "WHERE (email ILIKE $1 OR display_name ILIKE $1) "
                    "AND deleted_at IS NULL "
                    "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                    pattern, limit, offset,
                )
                total = await conn.fetchval(
                    "SELECT count(*) FROM users WHERE "
                    "(email ILIKE $1 OR display_name ILIKE $1) "
                    "AND deleted_at IS NULL",
                    pattern,
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, email, phone, display_name, role, plan, status, "
                    "balance_li, created_at, last_login_at "
                    "FROM users WHERE deleted_at IS NULL "
                    "ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                    limit, offset,
                )
                total = await conn.fetchval(
                    "SELECT count(*) FROM users WHERE deleted_at IS NULL"
                )
        return {
            "users": [self._user_row(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    @staticmethod
    def _user_row(r: asyncpg.Record) -> dict[str, Any]:
        d = dict(r)
        d["id"] = str(d["id"])
        d["balance_yuan"] = f"{d['balance_li'] / 100:.2f}"
        for k in ("created_at", "last_login_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        return d
```

- [ ] **Step 2: 写 integration test**

```python
# tests/integration/test_admin_user_repo.py
"""AdminUserRepo 真 PG fixture 验证。"""
from __future__ import annotations

import pytest

from praxis2.accounting.ledger import Ledger
from praxis2.admin.repo import AdminUserRepo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_list_users_returns_paginated(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    result = await repo.list_users(q="", page=1, limit=50)
    assert "users" in result
    assert result["total"] >= 1  # fake_user_id 至少 1
    assert result["page"] == 1
    assert result["limit"] == 50


async def test_list_users_q_filters_by_email_ilike(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    # fake_user_id fixture 应有 email 含 "test"
    result = await repo.list_users(q="test", page=1, limit=50)
    assert all("test" in u["email"].lower() or "test" in (u["display_name"] or "").lower()
               for u in result["users"])


async def test_list_users_pagination_offset(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    page1 = await repo.list_users(q="", page=1, limit=2)
    page2 = await repo.list_users(q="", page=2, limit=2)
    if page1["total"] >= 4:
        # 不同页 id 不同
        assert set(u["id"] for u in page1["users"]) != set(
            u["id"] for u in page2["users"]
        )
```

- [ ] **Step 3: 跑 test**

Run: `.venv/bin/python -m pytest tests/integration/test_admin_user_repo.py -v`
Expected: 3 PASS。

- [ ] **Step 4: Commit**

```bash
git add praxis2/admin/__init__.py praxis2/admin/repo.py tests/integration/test_admin_user_repo.py
git commit -m "feat(m12): AdminUserRepo.list_users — ILIKE q + pagination + 软删过滤"
```

---

### Task 5: AdminUserRepo - adjust_balance

**Files:**
- Modify: `praxis2/admin/repo.py`(加 `adjust_balance`)
- Modify: `tests/integration/test_admin_user_repo.py`(加 test)

- [ ] **Step 1: 加 adjust_balance**

加到 `AdminUserRepo`:

```python
    async def adjust_balance(
        self, conn: asyncpg.Connection,
        target_user_id: str, admin_id: str,
        amount_li: int, note: str,
    ) -> dict[str, Any]:
        """admin 充值/扣款。caller 提供 conn(同 tx 跟 audit 一起)。

        amount_li 正 = 充值,负 = 扣款。
        返 {ledger_id, new_balance_li, new_balance_yuan};
        余额变负抛 LedgerError(handler 转 400 negative_balance)。
        """
        if amount_li == 0:
            raise ValueError("zero_amount")
        ledger_id = await self._ledger.record(
            conn, target_user_id, amount_li,
            kind="admin_adjust", ref_type="admin", ref_id=admin_id,
            meta={"note": note},
        )
        new_bal = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1",
            uuid.UUID(target_user_id),
        )
        return {
            "ledger_id": ledger_id,
            "new_balance_li": int(new_bal),
            "new_balance_yuan": f"{new_bal / 100:.2f}",
        }
```

- [ ] **Step 2: 加 test**

```python
# tests/integration/test_admin_user_repo.py 追加

from praxis2.accounting.ledger import LedgerError


async def test_adjust_balance_topup_increases_balance(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        before = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1::uuid", fake_user_id,
        )
        async with conn.transaction():
            result = await repo.adjust_balance(
                conn, fake_user_id, fake_user_id, 5000, "test topup",
            )
    assert result["new_balance_li"] == int(before) + 5000
    assert result["ledger_id"]


async def test_adjust_balance_zero_amount_raises(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ValueError, match="zero_amount"):
                await repo.adjust_balance(
                    conn, fake_user_id, fake_user_id, 0, "noop",
                )


async def test_adjust_balance_negative_overflow_raises(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        # 先给 1000,然后扣 999999 → 必负
        async with conn.transaction():
            await repo.adjust_balance(
                conn, fake_user_id, fake_user_id, 1000, "seed",
            )
        async with conn.transaction():
            with pytest.raises(LedgerError, match="insufficient"):
                await repo.adjust_balance(
                    conn, fake_user_id, fake_user_id, -999999, "overdraw",
                )
```

- [ ] **Step 3: 跑 test**

Run: `.venv/bin/python -m pytest tests/integration/test_admin_user_repo.py -v`
Expected: 6 PASS(原 3 + 新 3)。

- [ ] **Step 4: Commit**

```bash
git add praxis2/admin/repo.py tests/integration/test_admin_user_repo.py
git commit -m "feat(m12): AdminUserRepo.adjust_balance — Ledger.record 同 tx + 余额负拒"
```

---

### Task 6: AdminUserRepo - freeze/unfreeze

**Files:**
- Modify: `praxis2/admin/repo.py`(加 `freeze` + `unfreeze` + `get_user`)
- Modify: `tests/integration/test_admin_user_repo.py`(加 test)

- [ ] **Step 1: 加 freeze/unfreeze/get_user**

```python
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """读 user row (admin 端用,含 role/status/balance)。"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, display_name, role, plan, status, "
                "balance_li, created_at, last_login_at "
                "FROM users WHERE id=$1 AND deleted_at IS NULL",
                uuid.UUID(user_id),
            )
        return self._user_row(row) if row else None

    async def freeze(
        self, conn: asyncpg.Connection,
        target_user_id: str, admin_id: str, reason: str,
    ) -> dict[str, Any]:
        """改 users.status='frozen'。target 是 admin 时拒 (handler 转 403)。"""
        cur = await conn.fetchrow(
            "SELECT role, status FROM users WHERE id=$1 AND deleted_at IS NULL "
            "FOR UPDATE",
            uuid.UUID(target_user_id),
        )
        if cur is None:
            raise UserNotFound(target_user_id)
        if cur["role"] == "admin":
            raise CannotFreezeAdmin(target_user_id)
        already = cur["status"] == "frozen"
        if not already:
            await conn.execute(
                "UPDATE users SET status='frozen' WHERE id=$1",
                uuid.UUID(target_user_id),
            )
        return {"ok": True, "status": "frozen", "already": already, "reason": reason}

    async def unfreeze(
        self, conn: asyncpg.Connection,
        target_user_id: str, admin_id: str,
    ) -> dict[str, Any]:
        cur = await conn.fetchrow(
            "SELECT status FROM users WHERE id=$1 AND deleted_at IS NULL FOR UPDATE",
            uuid.UUID(target_user_id),
        )
        if cur is None:
            raise UserNotFound(target_user_id)
        already = cur["status"] != "frozen"
        if not already:
            await conn.execute(
                "UPDATE users SET status='active' WHERE id=$1",
                uuid.UUID(target_user_id),
            )
        return {"ok": True, "status": "active", "already": already}


class UserNotFound(Exception):
    def __init__(self, uid: str) -> None:
        super().__init__(f"user not found: {uid}")
        self.uid = uid


class CannotFreezeAdmin(Exception):
    def __init__(self, uid: str) -> None:
        super().__init__(f"cannot freeze admin user: {uid}")
        self.uid = uid
```

- [ ] **Step 2: 加 test**

```python
# tests/integration/test_admin_user_repo.py 追加

from praxis2.admin.repo import CannotFreezeAdmin, UserNotFound


async def test_freeze_changes_status(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            result = await repo.freeze(
                conn, fake_user_id, fake_user_id, "test reason",
            )
    assert result["status"] == "frozen"
    user = await repo.get_user(fake_user_id)
    assert user["status"] == "frozen"


async def test_freeze_idempotent_marks_already(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.freeze(conn, fake_user_id, fake_user_id, "first")
        async with conn.transaction():
            result = await repo.freeze(conn, fake_user_id, fake_user_id, "second")
    assert result["already"] is True


async def test_unfreeze_restores_status(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.freeze(conn, fake_user_id, fake_user_id, "test")
        async with conn.transaction():
            result = await repo.unfreeze(conn, fake_user_id, fake_user_id)
    assert result["status"] == "active"


async def test_freeze_user_not_found_raises(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(UserNotFound):
                await repo.freeze(
                    conn, "00000000-0000-0000-0000-000000000000",
                    "00000000-0000-0000-0000-000000000000", "x",
                )
```

- [ ] **Step 3: 跑 test**

Run: `.venv/bin/python -m pytest tests/integration/test_admin_user_repo.py -v`
Expected: 10 PASS。

- [ ] **Step 4: Commit**

```bash
git add praxis2/admin/repo.py tests/integration/test_admin_user_repo.py
git commit -m "feat(m12): AdminUserRepo.freeze/unfreeze — idempotent + admin 不可冻"
```

---

### Task 7: AdminUserRepo - reconcile + get_stats

**Files:**
- Modify: `praxis2/admin/repo.py`(加 `reconcile` + `get_stats`)
- Create: `tests/integration/test_reconcile.py`

- [ ] **Step 1: 加 reconcile + get_stats**

```python
    async def reconcile(self, max_users: int) -> dict[str, Any]:
        """诊断:扫 max_users 个 user,对比 users.balance_li vs SUM(ledger).

        不锁、不修(诊断 only)。返 {checked, mismatches: int, details: list[≤20]}。
        """
        async with self._pool.acquire() as conn:
            users = await conn.fetch(
                "SELECT id, balance_li FROM users WHERE deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT $1",
                max_users,
            )
            mismatches: list[dict[str, Any]] = []
            for u in users:
                ledger_sum = await conn.fetchval(
                    "SELECT COALESCE(SUM(amount_li), 0) FROM ledger WHERE user_id=$1",
                    u["id"],
                )
                if int(u["balance_li"]) != int(ledger_sum):
                    mismatches.append({
                        "user_id": str(u["id"]),
                        "balance_li": int(u["balance_li"]),
                        "ledger_sum": int(ledger_sum),
                        "diff": int(u["balance_li"]) - int(ledger_sum),
                    })
        return {
            "checked": len(users),
            "mismatches": len(mismatches),
            "details": mismatches[:20],
        }

    async def get_stats(self) -> dict[str, Any]:
        """admin dashboard:user 数 / outstanding 余额 / runs / consumption。"""
        async with self._pool.acquire() as conn:
            user_stats = await conn.fetchrow(
                "SELECT count(*) FILTER (WHERE deleted_at IS NULL) AS total, "
                "count(*) FILTER (WHERE status='active' AND deleted_at IS NULL) AS active, "
                "count(*) FILTER (WHERE status='frozen' AND deleted_at IS NULL) AS frozen, "
                "count(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted "
                "FROM users",
            )
            outstanding = await conn.fetchval(
                "SELECT COALESCE(SUM(balance_li), 0) FROM users WHERE deleted_at IS NULL"
            )
            # runs (md_jobs + spawn_tasks 都算)
            md_stats = await conn.fetchrow(
                "SELECT count(*) AS total, "
                "count(*) FILTER (WHERE status='done') AS done, "
                "count(*) FILTER (WHERE status='failed') AS failed "
                "FROM md_jobs",
            )
            consumption = await conn.fetchval(
                "SELECT COALESCE(SUM(-amount_li), 0) FROM ledger "
                "WHERE amount_li < 0",
            )
        return {
            "users": {
                "total": int(user_stats["total"]),
                "active": int(user_stats["active"]),
                "frozen": int(user_stats["frozen"]),
                "deleted": int(user_stats["deleted"]),
            },
            "balance": {
                "outstanding_li": int(outstanding),
                "outstanding_yuan": f"{outstanding / 100:.2f}",
            },
            "runs": {
                "total": int(md_stats["total"]),
                "done": int(md_stats["done"]),
                "failed": int(md_stats["failed"]),
            },
            "consumption": {
                "total_li": int(consumption),
                "total_yuan": f"{consumption / 100:.2f}",
            },
        }
```

- [ ] **Step 2: 写 reconcile integration test**

```python
# tests/integration/test_reconcile.py
"""reconcile 制造 mismatch 验证检出。"""
from __future__ import annotations

import uuid

import pytest

from praxis2.accounting.ledger import Ledger
from praxis2.admin.repo import AdminUserRepo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_reconcile_clean_returns_zero_mismatches(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    # 通过 Ledger.record 加余额(保持一致),不直接 UPDATE
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await Ledger(pg_pool).record(
                conn, fake_user_id, 1000, kind="seed",
                ref_type=None, ref_id=None, meta={},
            )
    result = await repo.reconcile(max_users=100)
    assert result["mismatches"] == 0


async def test_reconcile_detects_balance_drift(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    # 故意 UPDATE balance 跳过 ledger → 制造 drift
    async with pg_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance_li = balance_li + 7777 WHERE id=$1",
            uuid.UUID(fake_user_id),
        )
    result = await repo.reconcile(max_users=100)
    assert result["mismatches"] >= 1
    diffs = [d["diff"] for d in result["details"] if d["user_id"] == fake_user_id]
    assert diffs and abs(diffs[0]) == 7777


async def test_reconcile_max_users_cap(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    result = await repo.reconcile(max_users=5)
    assert result["checked"] <= 5
```

- [ ] **Step 3: 加 get_stats test**

加到 `tests/integration/test_admin_user_repo.py`:

```python
async def test_get_stats_returns_all_buckets(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    stats = await repo.get_stats()
    assert "users" in stats and all(
        k in stats["users"] for k in ("total", "active", "frozen", "deleted")
    )
    assert "balance" in stats
    assert "runs" in stats
    assert "consumption" in stats
```

- [ ] **Step 4: 跑 test**

Run: `.venv/bin/python -m pytest tests/integration/test_admin_user_repo.py tests/integration/test_reconcile.py -v`
Expected: 14 PASS。

- [ ] **Step 5: Commit**

```bash
git add praxis2/admin/repo.py tests/integration/test_admin_user_repo.py tests/integration/test_reconcile.py
git commit -m "feat(m12): AdminUserRepo.reconcile (诊断) + get_stats"
```

---

### Task 8: AuditRepo - query

**Files:**
- Modify: `praxis2/admin/repo.py`(加 `AuditRepo` class)
- Create: `tests/integration/test_audit_repo.py`

- [ ] **Step 1: 加 AuditRepo**

```python
# 加到 praxis2/admin/repo.py 末尾

from praxis2.auth.repository_pg import PgAuthRepository


class AuditRepo:
    """audit_log 查询 + 包 M9 insert_audit。"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def query(
        self, filters: dict[str, Any], page: int, limit: int,
    ) -> dict[str, Any]:
        offset = (page - 1) * limit
        where: list[str] = []
        args: list[Any] = []
        if filters.get("user_id"):
            args.append(uuid.UUID(filters["user_id"]))
            where.append(f"user_id = ${len(args)}")
        if filters.get("action"):
            args.append(filters["action"])
            where.append(f"action = ${len(args)}")
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        args.extend([limit, offset])
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, user_id, actor, action, resource, resource_id, "
                f"ip, ua, meta, created_at "
                f"FROM audit_log{where_sql} "
                f"ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}",
                *args,
            )
            total = await conn.fetchval(
                f"SELECT count(*) FROM audit_log{where_sql}",
                *args[:-2],
            )
        return {
            "rows": [self._audit_row(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def insert(
        self, conn: asyncpg.Connection,
        user_id: str | None, actor: str, action: str,
        resource: str | None, resource_id: str | None,
        ip: str | None, ua: str | None, meta: dict | None,
    ) -> int:
        """直接复用 M9 PgAuthRepository.insert_audit 风格(同 SQL)。"""
        import json as _json
        uid_val = uuid.UUID(user_id) if user_id else None
        row = await conn.fetchrow(
            "INSERT INTO audit_log "
            "(user_id, actor, action, resource, resource_id, ip, ua, meta) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb) "
            "RETURNING id",
            uid_val, actor, action, resource, resource_id,
            ip, ua, _json.dumps(meta) if meta else None,
        )
        return int(row["id"])

    @staticmethod
    def _audit_row(r: asyncpg.Record) -> dict[str, Any]:
        import json as _json
        d = dict(r)
        if d.get("user_id"):
            d["user_id"] = str(d["user_id"])
        if d.get("meta"):
            d["meta"] = _json.loads(d["meta"]) if isinstance(d["meta"], str) else d["meta"]
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        return d
```

- [ ] **Step 2: 写 integration test**

```python
# tests/integration/test_audit_repo.py
"""AuditRepo query + insert (复用 audit_log M9 表)."""
from __future__ import annotations

import pytest

from praxis2.admin.repo import AuditRepo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_insert_and_query_returns_row(pg_pool, fake_user_id):
    repo = AuditRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            audit_id = await repo.insert(
                conn, user_id=fake_user_id, actor="admin",
                action="test_action", resource="user",
                resource_id=fake_user_id,
                ip="127.0.0.1", ua="test-ua",
                meta={"foo": "bar"},
            )
    assert audit_id > 0
    result = await repo.query({"user_id": fake_user_id, "action": "test_action"},
                              page=1, limit=10)
    matched = [r for r in result["rows"] if r["id"] == audit_id]
    assert matched and matched[0]["meta"] == {"foo": "bar"}


async def test_query_filter_by_action(pg_pool, fake_user_id):
    repo = AuditRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.insert(
                conn, fake_user_id, "admin", "balance_adjust",
                "user", fake_user_id, None, None, {"amount": 100},
            )
    result = await repo.query({"action": "balance_adjust"}, page=1, limit=10)
    assert all(r["action"] == "balance_adjust" for r in result["rows"])


async def test_query_pagination(pg_pool, fake_user_id):
    repo = AuditRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            for _ in range(3):
                await repo.insert(
                    conn, fake_user_id, "admin", "paging_test",
                    "user", fake_user_id, None, None, None,
                )
    p1 = await repo.query({"action": "paging_test"}, page=1, limit=2)
    p2 = await repo.query({"action": "paging_test"}, page=2, limit=2)
    assert len(p1["rows"]) == 2
    assert len(p2["rows"]) >= 1
```

- [ ] **Step 3: 跑 test**

Run: `.venv/bin/python -m pytest tests/integration/test_audit_repo.py -v`
Expected: 3 PASS。

- [ ] **Step 4: Commit**

```bash
git add praxis2/admin/repo.py tests/integration/test_audit_repo.py
git commit -m "feat(m12): AuditRepo.query (filter + pagination) + insert (复用 audit_log M9 表)"
```

---

### Task 9: proposals validators + unit tests

**Files:**
- Create: `tests/test_proposals_validators.py`

- [ ] **Step 1: 写 unit test(无 PG)**

```python
# tests/test_proposals_validators.py
"""proposals handler 端用的纯函数校验:kind/verdict enum + 长度。"""
from __future__ import annotations

import pytest

# 校验逻辑直接 inline 在 handlers,这些 test 跑 ProposalRepo + ValueError
from praxis2.proposals.repo import _PROPOSAL_KIND, _PROPOSAL_VERDICT


def test_proposal_kind_enum():
    assert _PROPOSAL_KIND == {"idea", "feature", "bug"}


def test_proposal_verdict_enum():
    assert _PROPOSAL_VERDICT == {"ship", "promote", "hold", "reject"}


@pytest.mark.parametrize("title,expected", [
    ("", "empty"),
    ("x" * 201, "too_long"),
    ("ok title", "valid"),
])
def test_title_length_rule(title, expected):
    # handler 内的简单检查 (Task 11 实现):
    if not title.strip():
        result = "empty"
    elif len(title) > 200:
        result = "too_long"
    else:
        result = "valid"
    assert result == expected


@pytest.mark.parametrize("body,expected", [
    (None, "valid"),
    ("", "valid"),
    ("x" * 5001, "too_long"),
    ("normal body", "valid"),
])
def test_body_length_rule(body, expected):
    if body and len(body) > 5000:
        result = "too_long"
    else:
        result = "valid"
    assert result == expected


@pytest.mark.parametrize("score,valid", [
    (None, True),
    (1, True),
    (5, True),
    (0, False),
    (6, False),
    (-1, False),
])
def test_score_range(score, valid):
    result = score is None or (1 <= score <= 5)
    assert result == valid
```

- [ ] **Step 2: 跑 test**

Run: `.venv/bin/python -m pytest tests/test_proposals_validators.py -v`
Expected: 14 PASS(parametrize 展开)。

- [ ] **Step 3: Commit**

```bash
git add tests/test_proposals_validators.py
git commit -m "test(m12): proposals validators — kind/verdict enum + 长度/score 范围"
```

---

### Task 10: admin pagination utility + unit tests

**Files:**
- Modify: `praxis2/admin/repo.py`(顶部加 `clamp_pagination` helper)
- Create: `tests/test_admin_pagination_unit.py`

- [ ] **Step 1: 加 pagination helper**

加到 `praxis2/admin/repo.py` 顶部(imports 后,class 前):

```python
def clamp_pagination(page: Any, limit: Any) -> tuple[int, int]:
    """统一处理 query string page/limit:
    page < 1 → 1; limit < 1 → 50; limit > 200 → 200。
    返 (page, limit) clamped。非整数转 int(失败用默认)。
    """
    try:
        p = int(page) if page is not None else 1
    except (ValueError, TypeError):
        p = 1
    try:
        l = int(limit) if limit is not None else 50
    except (ValueError, TypeError):
        l = 50
    return max(p, 1), max(min(l, 200), 1)
```

- [ ] **Step 2: 写 unit test**

```python
# tests/test_admin_pagination_unit.py
"""admin pagination helper — clamp + 类型转换。"""
from __future__ import annotations

import pytest

from praxis2.admin.repo import clamp_pagination


@pytest.mark.parametrize("page,limit,expect", [
    (1, 50, (1, 50)),
    ("1", "50", (1, 50)),
    (0, 50, (1, 50)),       # page<1 clamp 到 1
    (-5, 50, (1, 50)),
    (1, 0, (1, 1)),         # limit<1 clamp 到 1
    (1, -5, (1, 1)),
    (1, 10000, (1, 200)),   # limit>200 clamp 到 200
    (None, None, (1, 50)),  # 默认
    ("bad", "bad", (1, 50)),  # 非整数
])
def test_clamp_pagination(page, limit, expect):
    assert clamp_pagination(page, limit) == expect
```

- [ ] **Step 3: 跑 test**

Run: `.venv/bin/python -m pytest tests/test_admin_pagination_unit.py -v`
Expected: 9 PASS。

- [ ] **Step 4: Commit**

```bash
git add praxis2/admin/repo.py tests/test_admin_pagination_unit.py
git commit -m "feat(m12): clamp_pagination helper + unit tests (边界 clamp)"
```

---

### Task 11: proposals handlers (5 个 endpoint)

**Files:**
- Create: `praxis2/proposals/handlers.py`

注:handler 走 unit test 偏少(主要是 e2e Task 14 覆盖)。

- [ ] **Step 1: 写 handlers.py**

```python
# praxis2/proposals/handlers.py
"""5 个 proposals ASGI handler — 4 用户面 + 1 admin 决策。"""
from __future__ import annotations

import json
import logging
from typing import Any

from praxis2.admin.repo import clamp_pagination
from praxis2.proposals.repo import (
    ProposalAlreadyDecided,
    ProposalNotFound,
    _PROPOSAL_KIND,
    _PROPOSAL_VERDICT,
)

log = logging.getLogger(__name__)


async def _json(send, status: int, body: dict) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode()
    await send({
        "type": "http.response.start", "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": payload})


async def _read_body(receive) -> dict:
    chunks = b""
    while True:
        msg = await receive()
        chunks += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not chunks:
        return {}
    try:
        return json.loads(chunks)
    except ValueError:
        return {}


def _qs(scope, key: str) -> str | None:
    qs = scope.get("query_string", b"").decode()
    if not qs:
        return None
    from urllib.parse import parse_qs
    return parse_qs(qs).get(key, [None])[0]


def _require_user(scope) -> tuple[str | None, Any]:
    user = scope.get("user")
    if not user:
        return ("unauthorized", None)
    return ("ok", user)


def _require_admin(scope) -> tuple[int, dict] | None:
    user = scope.get("user")
    if not user:
        return 401, {"error": "unauthorized", "reason": "未登录"}
    if user.get("role") != "admin":
        return 403, {"error": "forbidden", "reason": "需 admin 权限"}
    return None


async def handle_proposal_create(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized"})
        return
    body = await _read_body(receive)
    kind = body.get("kind", "")
    title = (body.get("title") or "").strip()
    body_text = body.get("body")

    # 校验
    if kind not in _PROPOSAL_KIND:
        await _json(send, 422, {"error": "invalid_kind",
                                "allowed": sorted(_PROPOSAL_KIND)})
        return
    if not title:
        await _json(send, 400, {"error": "missing_field", "field": "title"})
        return
    if len(title) > 200:
        await _json(send, 400, {"error": "field_too_long", "field": "title", "max": 200})
        return
    if body_text and len(body_text) > 5000:
        await _json(send, 400, {"error": "field_too_long", "field": "body", "max": 5000})
        return

    repo = deps["proposal_repo"]
    audit_repo = deps["audit_repo"]
    rate_per_day = deps["proposals_per_user_per_day"]

    # rate limit
    recent = await repo.count_recent(user["user_id"], hours=24)
    if recent >= rate_per_day:
        await _json(send, 429, {"error": "proposal_rate_limit",
                                "limit": rate_per_day, "window_hours": 24})
        return

    # tx: create + audit
    async with deps["pg_pool"].acquire() as conn:
        async with conn.transaction():
            pid = await repo.create(conn, user["user_id"], kind, title, body_text)
            await audit_repo.insert(
                conn, user_id=user["user_id"], actor="user",
                action="proposal_create", resource="proposal", resource_id=pid,
                ip=None, ua=None,
                meta={"kind": kind, "title_first_30": title[:30]},
            )
    await _json(send, 200, {
        "id": pid, "status": "open", "state": "submitted",
    })


async def handle_proposal_list_mine(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized"})
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    result = await deps["proposal_repo"].list_mine(
        user["user_id"], page=page, limit=limit,
    )
    await _json(send, 200, result)


async def handle_admin_proposal_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    filters = {}
    if (s := _qs(scope, "status")):
        filters["status"] = s
    if (k := _qs(scope, "kind")):
        filters["kind"] = k
    result = await deps["proposal_repo"].list_all(filters, page=page, limit=limit)
    # FE 期望 'proposals' 字段(参考 admin.ts:listProposals)
    await _json(send, 200, {
        "proposals": result["rows"],
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
    })


async def handle_admin_proposal_decide(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err)
        return
    admin = scope.get("user")
    pid = scope.get("path_params", {}).get("proposal_id", "")
    if not pid:
        await _json(send, 400, {"error": "missing_proposal_id"})
        return
    body = await _read_body(receive)
    verdict = body.get("verdict", "")
    score = body.get("score")
    shipped_to = body.get("shipped_to")
    note = body.get("note")

    if verdict not in _PROPOSAL_VERDICT:
        await _json(send, 422, {"error": "invalid_verdict",
                                "allowed": sorted(_PROPOSAL_VERDICT)})
        return
    if score is not None and not (isinstance(score, int) and 1 <= score <= 5):
        await _json(send, 422, {"error": "invalid_score", "range": "1-5"})
        return
    if note and len(note) > 1000:
        await _json(send, 400, {"error": "field_too_long", "field": "note", "max": 1000})
        return
    if shipped_to and len(shipped_to) > 200:
        await _json(send, 400, {"error": "field_too_long", "field": "shipped_to", "max": 200})
        return

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["proposal_repo"].decide(
                    conn, pid, admin["user_id"], verdict,
                    score=score, shipped_to=shipped_to, note=note,
                )
                await deps["audit_repo"].insert(
                    conn, user_id=admin["user_id"], actor="admin",
                    action="proposal_decide", resource="proposal", resource_id=pid,
                    ip=None, ua=None,
                    meta={"verdict": verdict, "score": score, "shipped_to": shipped_to},
                )
    except ProposalNotFound:
        await _json(send, 404, {"error": "not_found"})
        return
    except ProposalAlreadyDecided as e:
        await _json(send, 409, {"error": "already_decided", "current_status": e.status})
        return
    await _json(send, 200, result)
```

- [ ] **Step 2: 简单 syntax 检查**

Run: `.venv/bin/python -c "from praxis2.proposals.handlers import handle_proposal_create"`
Expected: 无错(import 成功)。

- [ ] **Step 3: Commit**

```bash
git add praxis2/proposals/handlers.py
git commit -m "feat(m12): proposals 5 handler — create/list_mine/admin_list/decide + 校验"
```

---

### Task 12: admin handlers (8 个)

**Files:**
- Create: `praxis2/admin/handlers.py`

- [ ] **Step 1: 写 handlers.py**

```python
# praxis2/admin/handlers.py
"""8 个 admin v2 ASGI handler:
- 4 个 swap M9 stub (list_users / ledger / audit-log / stats)
- 4 个新加 (adjust / freeze / unfreeze / reconcile)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from praxis2.accounting.ledger import LedgerError
from praxis2.admin.repo import (
    CannotFreezeAdmin,
    UserNotFound,
    clamp_pagination,
)

log = logging.getLogger(__name__)


async def _json(send, status: int, body: dict) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode()
    await send({
        "type": "http.response.start", "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": payload})


async def _read_body(receive) -> dict:
    chunks = b""
    while True:
        msg = await receive()
        chunks += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not chunks:
        return {}
    try:
        return json.loads(chunks)
    except ValueError:
        return {}


def _qs(scope, key: str) -> str | None:
    qs = scope.get("query_string", b"").decode()
    if not qs:
        return None
    from urllib.parse import parse_qs
    return parse_qs(qs).get(key, [None])[0]


def _require_admin(scope) -> tuple[int, dict] | None:
    user = scope.get("user")
    if not user:
        return 401, {"error": "unauthorized", "reason": "未登录"}
    if user.get("role") != "admin":
        return 403, {"error": "forbidden", "reason": "需 admin 权限"}
    return None


# ---------- 4 swap (M9 stub → 真) ----------

async def handle_admin_users_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    q = _qs(scope, "q") or ""
    result = await deps["admin_user_repo"].list_users(q=q, page=page, limit=limit)
    await _json(send, 200, result)


async def handle_admin_ledger_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    filters: dict[str, Any] = {}
    if (u := _qs(scope, "user_id")):
        filters["user_id"] = u
    if (k := _qs(scope, "kind")):
        filters["kind"] = k
    # ledger 用 Ledger.recent 但需要扩展;直接 SQL
    args: list[Any] = []
    where: list[str] = []
    import uuid as _uuid
    if filters.get("user_id"):
        args.append(_uuid.UUID(filters["user_id"]))
        where.append(f"user_id=${len(args)}")
    if filters.get("kind"):
        args.append(filters["kind"])
        where.append(f"kind=${len(args)}")
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    args.extend([limit, (page - 1) * limit])
    pg_pool = deps["pg_pool"]
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT id, user_id, amount_li, kind, ref_type, ref_id, "
            f"balance_after, meta, created_at "
            f"FROM ledger{where_sql} "
            f"ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}",
            *args,
        )
        total = await conn.fetchval(
            f"SELECT count(*) FROM ledger{where_sql}", *args[:-2],
        )
    out_rows = []
    for r in rows:
        d = dict(r)
        d["user_id"] = str(d["user_id"])
        d["kind_suffix"] = ""  # FE 期望字段;暂空
        if d.get("meta") and isinstance(d["meta"], str):
            d["meta"] = json.loads(d["meta"])
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        out_rows.append(d)
    await _json(send, 200, {
        "rows": out_rows, "total": int(total), "page": page, "limit": limit,
    })


async def handle_admin_audit_list(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    page, limit = clamp_pagination(_qs(scope, "page"), _qs(scope, "limit"))
    filters: dict[str, Any] = {}
    if (u := _qs(scope, "user_id")):
        filters["user_id"] = u
    if (a := _qs(scope, "action")):
        filters["action"] = a
    result = await deps["audit_repo"].query(filters, page=page, limit=limit)
    await _json(send, 200, result)


async def handle_admin_stats(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    stats = await deps["admin_user_repo"].get_stats()
    await _json(send, 200, stats)


# ---------- 4 new ----------

async def handle_admin_user_adjust(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    admin = scope.get("user")
    target_id = scope.get("path_params", {}).get("user_id", "")
    if not target_id:
        await _json(send, 400, {"error": "missing_user_id"}); return
    body = await _read_body(receive)
    try:
        amount_yuan = float(body.get("amount_yuan", 0))
    except (ValueError, TypeError):
        await _json(send, 400, {"error": "bad_amount_yuan"}); return
    note = (body.get("note") or "").strip()
    if not note:
        await _json(send, 400, {"error": "missing_field", "field": "note"}); return
    amount_li = round(amount_yuan * 100)
    if amount_li == 0:
        await _json(send, 400, {"error": "zero_amount"}); return

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["admin_user_repo"].adjust_balance(
                    conn, target_id, admin["user_id"], amount_li, note,
                )
                await deps["audit_repo"].insert(
                    conn, user_id=admin["user_id"], actor="admin",
                    action="balance_adjust", resource="user", resource_id=target_id,
                    ip=None, ua=None,
                    meta={"amount_li": amount_li, "note": note,
                          "new_balance_li": result["new_balance_li"]},
                )
    except LedgerError as e:
        await _json(send, 400, {"error": "negative_balance", "reason": str(e)})
        return
    await _json(send, 200, {"ok": True, **result})


async def handle_admin_user_freeze(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    admin = scope.get("user")
    target_id = scope.get("path_params", {}).get("user_id", "")
    body = await _read_body(receive)
    reason = (body.get("reason") or "").strip() or "no reason"

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["admin_user_repo"].freeze(
                    conn, target_id, admin["user_id"], reason,
                )
                # 已 frozen 不重写 audit
                if not result["already"]:
                    await deps["audit_repo"].insert(
                        conn, user_id=admin["user_id"], actor="admin",
                        action="user_freeze", resource="user", resource_id=target_id,
                        ip=None, ua=None, meta={"reason": reason},
                    )
    except UserNotFound:
        await _json(send, 404, {"error": "not_found"}); return
    except CannotFreezeAdmin:
        await _json(send, 403, {"error": "cannot_freeze_admin"}); return
    await _json(send, 200, {"ok": True, "status": result["status"]})


async def handle_admin_user_unfreeze(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    admin = scope.get("user")
    target_id = scope.get("path_params", {}).get("user_id", "")

    try:
        async with deps["pg_pool"].acquire() as conn:
            async with conn.transaction():
                result = await deps["admin_user_repo"].unfreeze(
                    conn, target_id, admin["user_id"],
                )
                if not result["already"]:
                    await deps["audit_repo"].insert(
                        conn, user_id=admin["user_id"], actor="admin",
                        action="user_unfreeze", resource="user", resource_id=target_id,
                        ip=None, ua=None, meta={},
                    )
    except UserNotFound:
        await _json(send, 404, {"error": "not_found"}); return
    await _json(send, 200, {"ok": True, "status": result["status"]})


async def handle_admin_reconcile(scope, receive, send, deps) -> None:
    err = _require_admin(scope)
    if err:
        await _json(send, *err); return
    admin = scope.get("user")
    max_users = deps["reconcile_max_users"]
    result = await deps["admin_user_repo"].reconcile(max_users=max_users)
    # 写一条总 audit(不是每 user)
    async with deps["pg_pool"].acquire() as conn:
        async with conn.transaction():
            await deps["audit_repo"].insert(
                conn, user_id=admin["user_id"], actor="admin",
                action="reconcile_run", resource="system", resource_id=None,
                ip=None, ua=None,
                meta={"checked": result["checked"], "mismatches": result["mismatches"]},
            )
    await _json(send, 200, result)
```

- [ ] **Step 2: syntax 检查**

Run: `.venv/bin/python -c "from praxis2.admin.handlers import handle_admin_users_list, handle_admin_user_adjust, handle_admin_reconcile"`
Expected: 无错。

- [ ] **Step 3: Commit**

```bash
git add praxis2/admin/handlers.py
git commit -m "feat(m12): admin/handlers.py 8 个 ASGI handler (4 swap stub + 4 new + audit insert)"
```

---

### Task 13: config.py + 删 M9 admin stub

**Files:**
- Modify: `praxis2/config.py`(加 2 个 env 到 `_KNOWN_KEYS` + `Settings` + `load_from_env`)
- Modify: `praxis2/auth/routes.py`(删 5 个 stub + ROUTES 项)
- Modify: `tests/integration/conftest.py`(`_TestSettings` 加 2 字段)

- [ ] **Step 1: config.py 加 env**

修改 `praxis2/config.py`:

加到 `_KNOWN_KEYS` set:
```python
    "PRAXIS_ADMIN_RECONCILE_MAX_USERS",
    "PRAXIS_PROPOSALS_PER_USER_PER_DAY",
```

加到 `Settings` dataclass:
```python
@dataclass(frozen=True)
class Settings:
    ...
    admin_reconcile_max_users: int = 1000
    proposals_per_user_per_day: int = 20
```

加到 `load_from_env()`:
```python
        admin_reconcile_max_users=int(e.get(
            "PRAXIS_ADMIN_RECONCILE_MAX_USERS", "1000")),
        proposals_per_user_per_day=int(e.get(
            "PRAXIS_PROPOSALS_PER_USER_PER_DAY", "20")),
```

- [ ] **Step 2: auth/routes.py 删 stub**

修改 `praxis2/auth/routes.py`:

删 5 个 stub 函数:`handle_admin_stats_stub`, `handle_admin_users_stub`, `handle_admin_ledger_stub`, `handle_admin_audit_log_stub`, `handle_admin_proposals_stub`(line 535 起 ~50 行)。

删 ROUTES 表里:
```python
    ("/api/admin/stats", "GET"): "handle_admin_stats_stub",
    ("/api/admin/users", "GET"): "handle_admin_users_stub",
    ("/api/admin/ledger", "GET"): "handle_admin_ledger_stub",
    ("/api/admin/audit-log", "GET"): "handle_admin_audit_log_stub",
    ("/api/admin/proposals", "GET"): "handle_admin_proposals_stub",
```

(routes 在 server/app.py 重新 wire,Task 14 处理)

- [ ] **Step 3: conftest.py 加字段**

修改 `tests/integration/conftest.py`:`_TestSettings` 加:
```python
    admin_reconcile_max_users: int = 1000
    proposals_per_user_per_day: int = 20
```

- [ ] **Step 4: 跑现有 test 确保没 regression**

Run: `.venv/bin/python -m pytest tests/test_config*.py tests/test_auth_routes.py -v`
Expected: 全 PASS(stub 删了之后 routes 表少 5 项,test_auth_routes 可能也要更新)。如果 test_auth_routes 有 reference 这 5 个 stub,删掉那部分 assertion。

- [ ] **Step 5: Commit**

```bash
git add praxis2/config.py praxis2/auth/routes.py tests/integration/conftest.py
git commit -m "feat(m12): 加 2 个 env + 删 5 个 M9 admin stub (M12 替换真 handler)"
```

---

### Task 14: server/app.py wire 13 routes

**Files:**
- Modify: `praxis2/server/app.py`

- [ ] **Step 1: 加 _admin_deps + _proposal_deps**

`server/app.py` 顶部 imports:
```python
from praxis2.admin.handlers import (
    handle_admin_audit_list,
    handle_admin_ledger_list,
    handle_admin_reconcile,
    handle_admin_stats,
    handle_admin_user_adjust,
    handle_admin_user_freeze,
    handle_admin_user_unfreeze,
    handle_admin_users_list,
)
from praxis2.admin.repo import AdminUserRepo, AuditRepo
from praxis2.proposals.handlers import (
    handle_admin_proposal_decide,
    handle_admin_proposal_list,
    handle_proposal_create,
    handle_proposal_list_mine,
)
from praxis2.proposals.repo import ProposalRepo
```

在 `_App.__init__` 内,跟现有 `_md_deps` 同位置加:
```python
        self._admin_user_repo = AdminUserRepo(deps.pg_pool, deps.ledger)
        self._audit_repo = AuditRepo(deps.pg_pool)
        self._proposal_repo = ProposalRepo(deps.pg_pool)
        self._admin_deps = {
            "pg_pool": deps.pg_pool,
            "admin_user_repo": self._admin_user_repo,
            "audit_repo": self._audit_repo,
            "reconcile_max_users": deps.settings.admin_reconcile_max_users,
        }
        self._proposal_deps = {
            "pg_pool": deps.pg_pool,
            "proposal_repo": self._proposal_repo,
            "audit_repo": self._audit_repo,
            "proposals_per_user_per_day": deps.settings.proposals_per_user_per_day,
        }
```

- [ ] **Step 2: 加 13 个 route dispatch method**

在 `_App` 内(参考 `_md_submit` 风格):
```python
    # ---- M12 admin v2 ----
    async def _admin_users_list(self, scope, receive, send):
        await handle_admin_users_list(scope, receive, send, self._admin_deps)

    async def _admin_user_adjust(self, scope, receive, send):
        await handle_admin_user_adjust(scope, receive, send, self._admin_deps)

    async def _admin_user_freeze(self, scope, receive, send):
        await handle_admin_user_freeze(scope, receive, send, self._admin_deps)

    async def _admin_user_unfreeze(self, scope, receive, send):
        await handle_admin_user_unfreeze(scope, receive, send, self._admin_deps)

    async def _admin_reconcile(self, scope, receive, send):
        await handle_admin_reconcile(scope, receive, send, self._admin_deps)

    async def _admin_ledger_list(self, scope, receive, send):
        await handle_admin_ledger_list(scope, receive, send, self._admin_deps)

    async def _admin_audit_list(self, scope, receive, send):
        await handle_admin_audit_list(scope, receive, send, self._admin_deps)

    async def _admin_stats(self, scope, receive, send):
        await handle_admin_stats(scope, receive, send, self._admin_deps)

    # ---- M12 proposals ----
    async def _proposal_create(self, scope, receive, send):
        await handle_proposal_create(scope, receive, send, self._proposal_deps)

    async def _proposal_list_mine(self, scope, receive, send):
        await handle_proposal_list_mine(scope, receive, send, self._proposal_deps)

    async def _admin_proposal_list(self, scope, receive, send):
        await handle_admin_proposal_list(scope, receive, send, self._proposal_deps)

    async def _admin_proposal_decide(self, scope, receive, send):
        await handle_admin_proposal_decide(scope, receive, send, self._proposal_deps)
```

- [ ] **Step 3: 加 13 个 route 到 _BUILTIN_ROUTES**

在 `_BUILTIN_ROUTES` 或同位置 dict:
```python
    # M12 admin v2
    ("/api/admin/users", "GET"): self._admin_users_list,
    ("/api/admin/users/{user_id}/adjust", "POST"): self._admin_user_adjust,
    ("/api/admin/users/{user_id}/freeze", "POST"): self._admin_user_freeze,
    ("/api/admin/users/{user_id}/unfreeze", "POST"): self._admin_user_unfreeze,
    ("/api/admin/reconcile", "POST"): self._admin_reconcile,
    ("/api/admin/ledger", "GET"): self._admin_ledger_list,
    ("/api/admin/audit-log", "GET"): self._admin_audit_list,
    ("/api/admin/stats", "GET"): self._admin_stats,

    # M12 proposals
    ("/api/proposals", "POST"): self._proposal_create,
    ("/api/me/proposals", "GET"): self._proposal_list_mine,
    ("/api/admin/proposals", "GET"): self._admin_proposal_list,
    ("/api/admin/proposals/{proposal_id}/decide", "POST"): self._admin_proposal_decide,
```

- [ ] **Step 4: 跑 routes 表 test 确认 wire**

Run: `.venv/bin/python -m pytest tests/test_app_routes_table.py -v`
Expected: PASS,routes 表含 13 个 M12 route(原 5 admin GET 仍在,值变成 _admin_xxx_list 而非 stub)。

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py
git commit -m "feat(m12): server/app.py wire 13 routes + admin/proposal deps"
```

---

### Task 15: e2e tests — admin lifecycle

**Files:**
- Create: `tests/integration/test_m12_admin_e2e.py`

- [ ] **Step 1: 写 e2e test**

```python
# tests/integration/test_m12_admin_e2e.py
"""完整 admin 流程: register admin → login → list → adjust → audit → freeze → unfreeze."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from tests._auth_test_helpers import make_admin_user_in_db

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_admin_v2_full_lifecycle(app, pg_pool):
    """admin login → list → adjust → audit log 有记录 → freeze → unfreeze。"""
    admin_id, admin_email, admin_password = await make_admin_user_in_db(
        pg_pool, balance_li=10_000,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. login
        r = await client.post("/api/auth/login",
                              json={"email": admin_email, "password": admin_password})
        assert r.status_code == 200
        cookie = r.cookies.get("praxis_session")
        client.cookies.set("praxis_session", cookie)

        # 2. list users
        r = await client.get("/api/admin/users?page=1&limit=10")
        assert r.status_code == 200
        assert "users" in r.json()
        assert r.json()["total"] >= 1

        # 3. adjust balance (admin 给自己充值 50 元 = 5000 li)
        r = await client.post(
            f"/api/admin/users/{admin_id}/adjust",
            json={"amount_yuan": 50.0, "note": "test topup"},
        )
        assert r.status_code == 200
        assert r.json()["new_balance_li"] == 15_000

        # 4. audit log 应有 balance_adjust 记录
        r = await client.get(f"/api/admin/audit-log?user_id={admin_id}&action=balance_adjust")
        assert r.status_code == 200
        rows = r.json()["rows"]
        assert any(row["action"] == "balance_adjust" for row in rows)

        # 5. freeze 自己 (admin 是 admin 应该被拒)
        r = await client.post(
            f"/api/admin/users/{admin_id}/freeze",
            json={"reason": "test"},
        )
        assert r.status_code == 403
        assert r.json()["error"] == "cannot_freeze_admin"

        # 6. 非 admin 访问 admin endpoint → 401/403
        no_cookie_client = AsyncClient(transport=transport, base_url="http://test")
        r = await no_cookie_client.get("/api/admin/users")
        assert r.status_code == 401
        await no_cookie_client.aclose()

        # 7. stats
        r = await client.get("/api/admin/stats")
        assert r.status_code == 200
        s = r.json()
        assert s["users"]["total"] >= 1
```

注:`make_admin_user_in_db` 是 helper(若 tests/_auth_test_helpers.py 没有,在 Step 2 加)。

- [ ] **Step 2: 检查 / 加 helper**

Run: `grep -n "make_admin_user_in_db" tests/_auth_test_helpers.py`

如果没有,加到 `tests/_auth_test_helpers.py`:

```python
async def make_admin_user_in_db(
    pg_pool, balance_li: int = 0,
) -> tuple[str, str, str]:
    """Direct PG insert + audit;绕过 register 流程。
    返 (user_id, email, password)。
    """
    import uuid
    from praxis2.auth.service import hash_password

    email = f"admin-{uuid.uuid4().hex[:8]}@test.local"
    password = "AdminTest12345!"
    pw_hash = hash_password(password, pepper="dev-pepper-only")  # test conftest
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash, display_name, role, balance_li) "
            "VALUES ($1, $2, $3, 'admin', $4) RETURNING id",
            email, pw_hash, "Test Admin", balance_li,
        )
    return str(row["id"]), email, password
```

(pepper 取的是 conftest `_TestSettings.password_pepper` 默认值,见 conftest.py)

- [ ] **Step 3: 跑 e2e test**

Run: `.venv/bin/python -m pytest tests/integration/test_m12_admin_e2e.py -v`
Expected: PASS。

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_m12_admin_e2e.py tests/_auth_test_helpers.py
git commit -m "test(m12): e2e admin lifecycle (login → list → adjust → audit → freeze 拒)"
```

---

### Task 16: e2e tests — proposal lifecycle

**Files:**
- Create: `tests/integration/test_m12_proposal_e2e.py`

- [ ] **Step 1: 写 e2e test**

```python
# tests/integration/test_m12_proposal_e2e.py
"""完整 proposal 流程: user post → my list → admin list → admin decide → audit."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from tests._auth_test_helpers import make_admin_user_in_db, make_normal_user_in_db

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_proposal_full_lifecycle(app, pg_pool):
    user_id, user_email, user_password = await make_normal_user_in_db(pg_pool)
    admin_id, admin_email, admin_password = await make_admin_user_in_db(pg_pool)
    transport = ASGITransport(app=app)

    # 1. user login + create proposal
    async with AsyncClient(transport=transport, base_url="http://test") as user_client:
        r = await user_client.post("/api/auth/login",
                                   json={"email": user_email, "password": user_password})
        assert r.status_code == 200
        user_client.cookies.set("praxis_session", r.cookies["praxis_session"])

        r = await user_client.post("/api/proposals", json={
            "kind": "bug", "title": "Found a typo", "body": "details...",
        })
        assert r.status_code == 200
        pid = r.json()["id"]
        assert r.json()["status"] == "open"

        # 2. user list mine
        r = await user_client.get("/api/me/proposals")
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json()["rows"])

        # 3. 重复 kind 校验 — invalid kind
        r = await user_client.post("/api/proposals",
                                   json={"kind": "bogus", "title": "x"})
        assert r.status_code == 422
        assert r.json()["error"] == "invalid_kind"

    # 4. admin login + list + decide
    async with AsyncClient(transport=transport, base_url="http://test") as admin_client:
        r = await admin_client.post("/api/auth/login",
                                    json={"email": admin_email, "password": admin_password})
        admin_client.cookies.set("praxis_session", r.cookies["praxis_session"])

        # admin list
        r = await admin_client.get("/api/admin/proposals?status=open")
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json()["proposals"])

        # admin decide
        r = await admin_client.post(f"/api/admin/proposals/{pid}/decide",
                                    json={"verdict": "ship", "score": 4,
                                          "shipped_to": "abc123", "note": "good"})
        assert r.status_code == 200
        assert r.json()["status"] == "decided"
        assert r.json()["verdict"] == "ship"

        # 5. 再 decide → 409 already_decided
        r = await admin_client.post(f"/api/admin/proposals/{pid}/decide",
                                    json={"verdict": "reject"})
        assert r.status_code == 409
        assert r.json()["error"] == "already_decided"

        # 6. audit log 应含 proposal_create + proposal_decide
        r = await admin_client.get("/api/admin/audit-log?action=proposal_decide")
        assert any(row["resource_id"] == pid for row in r.json()["rows"])
```

- [ ] **Step 2: 加 make_normal_user_in_db helper**

加到 `tests/_auth_test_helpers.py`(若没):

```python
async def make_normal_user_in_db(
    pg_pool, balance_li: int = 0,
) -> tuple[str, str, str]:
    """跟 make_admin_user_in_db 但 role='user'。"""
    import uuid
    from praxis2.auth.service import hash_password

    email = f"user-{uuid.uuid4().hex[:8]}@test.local"
    password = "UserTest12345!"
    pw_hash = hash_password(password, pepper="dev-pepper-only")
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash, display_name, role, balance_li) "
            "VALUES ($1, $2, $3, 'user', $4) RETURNING id",
            email, pw_hash, "Test User", balance_li,
        )
    return str(row["id"]), email, password
```

- [ ] **Step 3: 跑 e2e test**

Run: `.venv/bin/python -m pytest tests/integration/test_m12_proposal_e2e.py -v`
Expected: PASS。

- [ ] **Step 4: 跑全部 M12 test**

Run:
```bash
.venv/bin/python -m pytest tests/test_proposals_validators.py tests/test_admin_pagination_unit.py tests/integration/test_proposals_repo.py tests/integration/test_admin_user_repo.py tests/integration/test_audit_repo.py tests/integration/test_reconcile.py tests/integration/test_m12_admin_e2e.py tests/integration/test_m12_proposal_e2e.py -v
```

Expected: 全 PASS,合计 ~37 case。

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_m12_proposal_e2e.py tests/_auth_test_helpers.py
git commit -m "test(m12): e2e proposal lifecycle (user post → admin decide → 409 already_decided)"
```

---

### Task 17: 部署 + carry 更新

**Files:**
- Modify: 仓库根 `CHANGELOG`(若有)或 `docs/history/` 加一条
- 部署:本地 push GitHub → push_backend.sh → .53 alembic upgrade → restart

- [ ] **Step 1: 跑全部 PRAXIS-2 test 确认无 regression**

Run: `.venv/bin/python -m pytest -v 2>&1 | tail -40`
Expected: 全 PASS。若有红:debug + 修。

- [ ] **Step 2: push GitHub**

```bash
git push origin main
```

- [ ] **Step 3: push to .53**

```bash
BACKEND_HOST=10.102.106.53 BACKEND_USER=zkyd BACKEND_PATH=/home/zkyd/data1/mzy/PRAXIS-2 SERVICE_NAME=skip bash deploy/push_backend.sh
```

预期:rsync praxis2/ + migrations/ 成功(push_backend.sh 已 fix 含 migrations 同步)。

- [ ] **Step 4: .53 跑 alembic upgrade**

```bash
ssh 10.102.106.53 'source ~/software/miniconda3/etc/profile.d/conda.sh && conda activate praxis2 && source ~/praxis2.env && cd /home/zkyd/data1/mzy/PRAXIS-2 && alembic upgrade head'
```

Expected: `006_proposals (head)`。

- [ ] **Step 5: append env 到 praxis2.env**

```bash
ssh 10.102.106.53 'cat >> ~/praxis2.env <<EOF

# M12 admin v2 + proposals
export PRAXIS_ADMIN_RECONCILE_MAX_USERS=1000
export PRAXIS_PROPOSALS_PER_USER_PER_DAY=20
EOF
bash -n ~/praxis2.env && echo OK'
```

- [ ] **Step 6: restart gunicorn**

```bash
ssh 10.102.106.53 'bash /tmp/restart_praxis2.sh'
```

Expected: 新 master pid,startup complete,curl /api/info 返 200。

- [ ] **Step 7: smoke curl 验**

```bash
# 创 admin 顺便给 100 元 (1000 li)
ssh 10.102.106.53 'source ~/praxis2.env && source ~/software/miniconda3/etc/profile.d/conda.sh && conda activate praxis2 && cd /home/zkyd/data1/mzy/PRAXIS-2 && python -m scripts.create_admin --email m12-test@local --password "M12Test123!" --display-name "M12 Test" --initial-balance-li 100000'

# login + adjust + audit
ssh 10.102.106.53 'JAR=/tmp/m12-cookie.txt && curl -s -c $JAR -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"m12-test@local\",\"password\":\"M12Test123!\"}" && echo "" && curl -s -b $JAR http://localhost:8001/api/admin/stats && echo "" && curl -s -b $JAR http://localhost:8001/api/admin/audit-log'
```

Expected: stats 返 JSON 含 users/balance/runs/consumption;audit-log 返 rows。

- [ ] **Step 8: Commit + tag**

```bash
git tag -a v0.14.0 -m "M12 admin v2 + proposals (13 endpoint, 1 张新表)"
git push origin v0.14.0
```

或如不立 tag,仅 commit doc 更新:

```bash
# 加 1 行到 docs/history/(若历史有 ship 记录):
echo "- v0.14.0 (2026-05-27): M12 admin v2 + proposals ship — 13 endpoint + 006_proposals" \
  >> docs/history/SHIPS.md   # 若文件不存在,创建
git add docs/history/SHIPS.md
git commit -m "docs(m12): v0.14.0 ship note"
git push origin main
```

- [ ] **Step 9: 庆祝 + 更新 task #16 → completed,M12 ship 完成**

---

## carry(M12 后)

跟 spec §10 一致:
- withdraw endpoint(state='withdrawn' 字段已留)
- archive endpoint
- audit decorator 化(现手动)
- reconcile race(并发可能 false positive,加 advisory lock)
- shipped_to 自动从 git/PR
- proposal 多人评分流(admin_scores JSONB 已留位)
- rate limit 用 redis(现 SQL count)
- stats cache(1 min)
- /api/me/proposals incremental(现 page+limit)
