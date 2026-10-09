# M9 — 用户中心扩展 + 真 SMTP(代码就绪) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 v2 后端 `/api/me*` 系列接到真 ledger / profile / signup_gift,FE adapter 删,M9 ship 后 v2 用户中心面板完整可用,**v1 链路全程不动**。

**Architecture:** 002 alembic migration 新建 `user_profiles` + `ledger` 两表(不动 001),新模块 `praxis2/accounting/ledger.py` 用 asyncpg 显式事务管理余额一致,4 个新 `/api/me/*` handler 走 `auth/routes.py:ROUTES` dict 自动注册,FE `fetchMe()` 删 unwrap hack 直返后端 shape。

**Tech Stack:** Python 3.13 / asyncpg / alembic raw SQL / pytest / TypeScript (FE) / Vite

**Spec:** `docs/superpowers/specs/2026-05-24-m9-user-center-design.md`

---

## File Structure

### 新增文件
| 路径 | 责任 |
|------|------|
| `migrations/versions/002_user_profile_billing.py` | DB 002:user_profiles + ledger 建表 |
| `praxis2/accounting/__init__.py` | 空 |
| `praxis2/accounting/ledger.py` | `Ledger` class:`record(conn, ...)` / `recent(user_id, limit)` / `LedgerError` |
| `tests/test_accounting_ledger.py` | Ledger 单测(in-memory + integration 双层) |
| `tests/test_auth_routes_v2_me.py` | 4 个新 /api/me/* handler 单测 |
| `tests/test_auth_repository_pg_profile.py` | repository_pg profile/balance 方法 integration |
| `tests/test_config_signup_gift.py` | config env 3 例 |

### 修改文件
| 路径 | 改动概述 |
|------|---------|
| `praxis2/config.py` | 加 `signup_gift_li: int = 10000` + env `PRAXIS_SIGNUP_GIFT_LI` |
| `praxis2/auth/repository.py` | UserRow 加 `realname_verified_at` 字段;AuthRepository Protocol 加 4 个 profile/balance 方法;InMemoryAuthRepository 实现这 4 个 |
| `praxis2/auth/repository_pg.py` | SELECT 加 realname_verified_at;`_row_to_user` 映射;新 `upsert_user_profile` / `get_user_profile` / `get_user_with_balance` / `get_balance_li` |
| `praxis2/auth/routes.py` | `handle_me` 扩 11 字段;`handle_me_balance` 接真 ledger;新 `handle_me_profile_get` / `handle_me_profile_post` / `handle_me_proposals_stub`;`handle_register` 末尾接 ledger.record;ROUTES 加 3 行 |
| `praxis2/server/app.py` | `_App.__init__` 构造 `Ledger` 加进 auth_deps;不动 AppDeps |
| `frontend/src/lib/api.ts` | `fetchMe()` 删 unwrap hack,直返后端 MeResponse |

### 不动
- `praxis2/auth/email.py`(SmtpEmailGateway 已就绪)
- 任何 brain / agents / scheduler / runtime / core / tools / hooks
- v1 任何东西

---

## 测试策略

每 task 含「单元 + integration 标分层」原则:
- **单元测**(默认跑):用 fakeredis + InMemoryAuthRepository,不需要 docker;`@pytest.mark.integration` 的反义
- **Integration**(`@pytest.mark.integration`):需要 docker PG / Redis,本机 `PRAXIS_INTEGRATION=1` 才跑,CI 后续接

测试基线:M8 ship 后 1543 pass。M9 目标 ≥ 1575(+32 新增)。

---

## Task 1: Config 加 `signup_gift_li` env

**Files:**
- Modify: `praxis2/config.py`
- Test: `tests/test_config_signup_gift.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config_signup_gift.py
"""M9 config:PRAXIS_SIGNUP_GIFT_LI 默认 10000(=100元)"""
from __future__ import annotations

import pytest

from praxis2.config import Settings, from_env


def test_default_signup_gift_li_is_10000():
    s = Settings(password_pepper="x", smtp_host="")
    assert s.signup_gift_li == 10000


def test_env_override_sets_value(monkeypatch):
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "x")
    monkeypatch.setenv("PRAXIS_SIGNUP_GIFT_LI", "20000")
    s = from_env()
    assert s.signup_gift_li == 20000


def test_env_0_means_no_gift(monkeypatch):
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "x")
    monkeypatch.setenv("PRAXIS_SIGNUP_GIFT_LI", "0")
    s = from_env()
    assert s.signup_gift_li == 0
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_config_signup_gift.py -v`
Expected: 3 FAIL with `AttributeError: 'Settings' object has no attribute 'signup_gift_li'`

- [ ] **Step 3: 实现 — `praxis2/config.py` 加字段**

Find the `Settings` dataclass(around lines 50-70),在 `smtp_from: str = ""` 后加:

```python
    smtp_from: str = ""
    # M9:注册赠送 li(=100元 默认),0 = 不赠
    signup_gift_li: int = 10000
```

在 `from_env()` 函数里(约 line 200),在 `smtp_from=e.get(...)` 后加:

```python
        smtp_from=e.get("PRAXIS_SMTP_FROM", ""),
        signup_gift_li=int(e.get("PRAXIS_SIGNUP_GIFT_LI", "10000")),
```

- [ ] **Step 4: 跑测试确认绿**

Run: `pytest tests/test_config_signup_gift.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add praxis2/config.py tests/test_config_signup_gift.py
git commit -m "$(cat <<'EOF'
feat(M9/T1): config 加 signup_gift_li 字段 + PRAXIS_SIGNUP_GIFT_LI env

默认 10000(=100元,按 1元=100li);可设 0 表示不赠。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: alembic 002 migration — user_profiles + ledger 建表

**Files:**
- Create: `migrations/versions/002_user_profile_billing.py`
- Test: 手动 `alembic upgrade head` + `alembic downgrade -1`(本地 docker PG 或 integration)

- [ ] **Step 1: 写 002 migration**

```python
# migrations/versions/002_user_profile_billing.py
"""user_profiles + ledger.

Revision ID: 002_user_profile_billing
Revises: 001_initial_auth
"""

from __future__ import annotations

from alembic import op

revision = "002_user_profile_billing"
down_revision = "001_initial_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_profiles (
            user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            research_field  VARCHAR(256),
            affiliation     VARCHAR(256),
            expertise_level VARCHAR(256),
            projects        VARCHAR(2000),
            custom_intro    VARCHAR(2000),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE ledger (
            id            BIGSERIAL PRIMARY KEY,
            user_id       UUID         NOT NULL REFERENCES users(id),
            amount_li     BIGINT       NOT NULL,
            kind          VARCHAR(32)  NOT NULL,
            ref_type      VARCHAR(32),
            ref_id        VARCHAR(64),
            balance_after BIGINT       NOT NULL,
            meta          JSONB,
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX ix_ledger_user_created ON ledger(user_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ledger_user_created;")
    op.execute("DROP TABLE IF EXISTS ledger;")
    op.execute("DROP TABLE IF EXISTS user_profiles;")
```

- [ ] **Step 2: 本地 dry-run(若有 docker PG)**

```bash
# 若你本机有 docker PG 起来跑(否则跳过到 Step 3)
export PRAXIS_DB_URL="postgresql://praxis2:praxis2@127.0.0.1:5432/praxis2_test"
alembic upgrade head
psql $PRAXIS_DB_URL -c '\d user_profiles' -c '\d ledger'
alembic downgrade -1
psql $PRAXIS_DB_URL -c '\dt'  # 应不含 user_profiles / ledger
alembic upgrade head           # 再 up,验幂等
```

无 docker:跳过,等 Task 13 真到 staging 时跑。

- [ ] **Step 3: ruff + commit**

```bash
ruff check migrations/versions/002_user_profile_billing.py
git add migrations/versions/002_user_profile_billing.py
git commit -m "$(cat <<'EOF'
feat(M9/T2): alembic 002 — user_profiles + ledger 建表

- user_profiles:5 字段 nullable(256/256/256/2000/2000)+ updated_at
- ledger:append-only,带 balance_after 冗余字段 + 索引
- 不动 001(users 表保留 realname_verified_at timestamptz)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `praxis2/accounting/ledger.py` 新模块

**Files:**
- Create: `praxis2/accounting/__init__.py` (空)
- Create: `praxis2/accounting/ledger.py`
- Test: `tests/test_accounting_ledger.py`

- [ ] **Step 1: 写失败测试(integration 标分两层)**

```python
# tests/test_accounting_ledger.py
"""Ledger.record() 单元 + integration 测试。

整笔事务要外层(handler / register)管;Ledger 方法自身只保证 SELECT FOR UPDATE
+ INSERT ledger + UPDATE users 在传入 conn 上原子执行。
"""
from __future__ import annotations

import os
import uuid

import pytest


pytestmark = pytest.mark.integration  # 需 PRAXIS_INTEGRATION=1 + docker PG


@pytest.fixture
async def pool():
    pytest.importorskip("asyncpg")
    import asyncpg
    url = os.environ.get("PRAXIS_DB_URL", "")
    if not url:
        pytest.skip("PRAXIS_DB_URL not set")
    p = await asyncpg.create_pool(url.replace("postgresql+asyncpg://", "postgresql://"))
    yield p
    await p.close()


@pytest.fixture
async def user_id(pool):
    """造一个测试 user,返 id;测试结束删干净。"""
    uid = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, balance_li) "
            "VALUES ($1, $2, $3, 0)",
            uid, f"t_{uid}@x", b"x",
        )
    yield str(uid)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ledger WHERE user_id=$1", uid)
        await conn.execute("DELETE FROM users WHERE id=$1", uid)


async def test_record_signup_gift_inserts_row_and_updates_balance(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            new_bal = await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
    assert new_bal == 10000
    async with pool.acquire() as conn:
        bal = await conn.fetchval("SELECT balance_li FROM users WHERE id=$1", uuid.UUID(user_id))
        rows = await conn.fetch("SELECT amount_li, kind, balance_after FROM ledger WHERE user_id=$1", uuid.UUID(user_id))
    assert bal == 10000
    assert len(rows) == 1
    assert rows[0]["amount_li"] == 10000
    assert rows[0]["kind"] == "signup_gift"
    assert rows[0]["balance_after"] == 10000


async def test_record_consumption_negative_amount(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
        async with conn.transaction():
            new_bal = await L.record(conn, user_id, -200, "chat_out", "chat_session", "sess-x", {"req": 1})
    assert new_bal == 9800


async def test_record_zero_amount_allowed(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            new_bal = await L.record(conn, user_id, 0, "admin_adjust", None, None, {"note": "noop"})
    assert new_bal == 0


async def test_record_insufficient_balance_raises(pool, user_id):
    from praxis2.accounting.ledger import Ledger, LedgerError
    L = Ledger(pool)
    with pytest.raises(LedgerError, match="insufficient_balance"):
        async with pool.acquire() as conn:
            async with conn.transaction():
                await L.record(conn, user_id, -100, "chat_out", None, None, {})


async def test_record_unknown_user_raises(pool):
    from praxis2.accounting.ledger import Ledger, LedgerError
    L = Ledger(pool)
    fake_uid = str(uuid.uuid4())
    with pytest.raises(LedgerError, match="user_not_found"):
        async with pool.acquire() as conn:
            async with conn.transaction():
                await L.record(conn, fake_uid, 100, "topup", None, None, {})


async def test_recent_returns_desc_by_created_at(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
        async with conn.transaction():
            await L.record(conn, user_id, -200, "chat_out", None, None, {})
        async with conn.transaction():
            await L.record(conn, user_id, -100, "chat_out", None, None, {})
    rows = await L.recent(user_id, limit=20)
    assert len(rows) == 3
    assert [r["amount_li"] for r in rows] == [-100, -200, 10000]  # DESC


async def test_recent_limit_default_20(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 100000, "signup_gift", None, None, {})
        for _ in range(25):
            async with conn.transaction():
                await L.record(conn, user_id, -10, "chat_out", None, None, {})
    rows = await L.recent(user_id)  # default 20
    assert len(rows) == 20


async def test_recent_empty_for_new_user(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    rows = await L.recent(user_id)
    assert rows == []


async def test_record_meta_json_roundtrip(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    payload = {"req_id": "abc", "tokens": {"in": 12, "out": 34}}
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
        async with conn.transaction():
            await L.record(conn, user_id, -100, "chat_out", "chat_session", "sess-x", payload)
    rows = await L.recent(user_id)
    assert rows[0]["meta"] == payload


async def test_concurrent_records_no_lost_update(pool, user_id):
    """5 个并发 +100 入账,最终余额必须 = 500(SELECT FOR UPDATE 防 lost update)。"""
    import asyncio
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)

    async def credit():
        async with pool.acquire() as conn:
            async with conn.transaction():
                await L.record(conn, user_id, 100, "topup", None, None, {})

    await asyncio.gather(*[credit() for _ in range(5)])
    async with pool.acquire() as conn:
        bal = await conn.fetchval("SELECT balance_li FROM users WHERE id=$1", uuid.UUID(user_id))
    assert bal == 500
```

- [ ] **Step 2: 跑测试确认红**

```bash
# 如无 docker PG,会自动 skip。若设了 PRAXIS_INTEGRATION=1,会真跑并红
PRAXIS_INTEGRATION=1 PRAXIS_DB_URL=... pytest tests/test_accounting_ledger.py -v
```

Expected: 10 FAIL with `ModuleNotFoundError: praxis2.accounting`(无 docker → 10 SKIP)

- [ ] **Step 3: 实现 — 新 `praxis2/accounting/__init__.py`(空文件)**

```bash
mkdir -p praxis2/accounting
echo > praxis2/accounting/__init__.py
```

- [ ] **Step 4: 实现 — `praxis2/accounting/ledger.py`**

```python
# praxis2/accounting/ledger.py
"""Ledger:append-only 流水 + 余额一致(SELECT FOR UPDATE 防 lost update)。

设计:`record(conn, ...)` 不自己开事务,要求调用方传入已 begin 的 conn;
便于跟 register / chat 等更大事务组合(原子 user 创建 + 赠送)。

`recent(user_id, limit)` 自己拿 conn(只读,不卡)。
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg


class LedgerError(Exception):
    """ledger 业务错误:user_not_found / insufficient_balance。"""


class Ledger:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(
        self,
        conn: asyncpg.Connection,
        user_id: str,
        amount_li: int,
        kind: str,
        ref_type: str | None,
        ref_id: str | None,
        meta: dict | None,
    ) -> int:
        """append + 更新余额。返 balance_after。

        调用方必须已 `async with conn.transaction():` 包住此调用。
        """
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        cur = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1 FOR UPDATE", uid
        )
        if cur is None:
            raise LedgerError(f"user_not_found: {user_id}")
        new_balance = int(cur) + int(amount_li)
        if new_balance < 0:
            raise LedgerError(
                f"insufficient_balance: cur={cur} amount={amount_li}"
            )
        await conn.execute(
            "INSERT INTO ledger "
            "(user_id, amount_li, kind, ref_type, ref_id, balance_after, meta) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)",
            uid,
            int(amount_li),
            kind,
            ref_type,
            ref_id,
            new_balance,
            json.dumps(meta or {}),
        )
        await conn.execute(
            "UPDATE users SET balance_li=$1 WHERE id=$2", new_balance, uid
        )
        return new_balance

    async def recent(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """读最近 N 条流水(DESC)。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, amount_li, kind, ref_type, ref_id, balance_after, "
                "       meta, created_at "
                "FROM ledger WHERE user_id=$1 "
                "ORDER BY created_at DESC, id DESC LIMIT $2",
                uid,
                int(limit),
            )
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "id": int(r["id"]),
        "amount_li": int(r["amount_li"]),
        "kind": r["kind"],
        "ref_type": r["ref_type"],
        "ref_id": r["ref_id"],
        "balance_after": int(r["balance_after"]),
        "meta": json.loads(r["meta"]) if r["meta"] else None,
        "created_at": r["created_at"],
    }
```

- [ ] **Step 5: 跑测试确认绿(若 PRAXIS_INTEGRATION=1)**

```bash
PRAXIS_INTEGRATION=1 PRAXIS_DB_URL=postgresql://... pytest tests/test_accounting_ledger.py -v
```

Expected: 10 PASS

无 docker 本地:确认 10 SKIP(`-v` 输出含 "SKIPPED"),后到 staging 验。

- [ ] **Step 6: ruff + commit**

```bash
ruff check praxis2/accounting tests/test_accounting_ledger.py
git add praxis2/accounting/ tests/test_accounting_ledger.py
git commit -m "$(cat <<'EOF'
feat(M9/T3): accounting/ledger.py — record + recent 模块

- record(conn, ...) 不自开事务,由调用方组合;SELECT FOR UPDATE 防 lost update
- recent(user_id, limit=20) 只读 DESC
- LedgerError:user_not_found / insufficient_balance
- 10 integration 测试(并发不丢更新 / meta JSONB roundtrip / 边界)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: UserRow + repository.py / repository_pg.py 加 `realname_verified_at`

**Files:**
- Modify: `praxis2/auth/repository.py:14-26`(UserRow 加字段)
- Modify: `praxis2/auth/repository.py:80-120`(InMemoryAuthRepository.create_user)
- Modify: `praxis2/auth/repository_pg.py:20-58`(3 个 SELECT 加列 + `_row_to_user` 映射)
- Test: 复用现有 `tests/test_auth_repository.py`,1 个新断言

- [ ] **Step 1: 写失败测试(在 test_auth_repository.py 末尾追加)**

```python
# tests/test_auth_repository.py 末尾追加
def test_userrow_has_realname_verified_at_field():
    """M9:UserRow 需含 realname_verified_at(TIMESTAMPTZ | None)以便 handle_me 算 bool。"""
    from praxis2.auth.repository import UserRow
    fields = {f.name for f in UserRow.__dataclass_fields__.values()}
    assert "realname_verified_at" in fields


async def test_inmemory_create_user_realname_verified_at_default_none():
    from praxis2.auth.repository import InMemoryAuthRepository
    repo = InMemoryAuthRepository()
    user = await repo.create_user(
        email="x@x", password_hash=b"x", display_name="X", role="user",
    )
    assert user.realname_verified_at is None
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_auth_repository.py -v -k realname`
Expected: 2 FAIL — `realname_verified_at` not in fields

- [ ] **Step 3: 实现 — `praxis2/auth/repository.py` UserRow 加字段**

在 `UserRow` 的 `deleted_at: datetime | None = None` **前**加(保持 deleted_at 在末尾):

```python
    last_login_ip: str | None = None
    realname_verified_at: datetime | None = None
    deleted_at: datetime | None = None
```

InMemoryAuthRepository.create_user(约 line 100)构造 UserRow 不传 realname_verified_at(自动用默认 None)。**确认**该处构造 UserRow 时没有用位置参数排列(若用了,新字段插入位置可能错)。

- [ ] **Step 4: 实现 — `praxis2/auth/repository_pg.py` SELECT + 映射**

在 `create_user` / `get_user_by_email` / `get_user_by_id` 三个 SELECT 的列表里加 `realname_verified_at`(放在 `last_login_ip` 之后):

```python
RETURNING id, email, password_hash, display_name, role, plan,
          status, balance_li, created_at, last_login_at,
          last_login_ip, realname_verified_at, deleted_at
```

3 处都改。然后 `_row_to_user`(约 line 156)在 `last_login_ip=...` 之后加:

```python
    return UserRow(
        ...
        last_login_ip=str(r["last_login_ip"]) if r["last_login_ip"] else None,
        realname_verified_at=r["realname_verified_at"],
        deleted_at=r["deleted_at"],
    )
```

- [ ] **Step 5: 跑测试确认绿**

```bash
pytest tests/test_auth_repository.py -v -k realname
pytest tests/test_auth_repository.py -v  # 全部仍过
pytest tests/test_auth_routes.py -v       # 现有测试无回归
```

Expected: 2 PASS + 旧测试 0 回归

- [ ] **Step 6: ruff + commit**

```bash
ruff check praxis2/auth/repository.py praxis2/auth/repository_pg.py
git add praxis2/auth/repository.py praxis2/auth/repository_pg.py tests/test_auth_repository.py
git commit -m "$(cat <<'EOF'
feat(M9/T4): UserRow 加 realname_verified_at(timestamptz | None)

001 已建该列,本 task 只是把它接到 dataclass + SELECT + _row_to_user 映射。
不动 schema。handle_me 后续将算 bool(row.realname_verified_at)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `repository_pg.py` 加 4 个 profile/balance 方法

**Files:**
- Modify: `praxis2/auth/repository.py`(AuthRepository Protocol + InMemoryAuthRepository)
- Modify: `praxis2/auth/repository_pg.py`(PgAuthRepository 加方法)
- Test: `tests/test_auth_repository_pg_profile.py`(integration)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_auth_repository_pg_profile.py
"""PgAuthRepository profile + balance 方法 integration 测试。"""
from __future__ import annotations

import os
import uuid

import pytest


pytestmark = pytest.mark.integration


@pytest.fixture
async def repo():
    pytest.importorskip("asyncpg")
    import asyncpg
    from praxis2.auth.repository_pg import PgAuthRepository
    url = os.environ.get("PRAXIS_DB_URL", "")
    if not url:
        pytest.skip("PRAXIS_DB_URL not set")
    pool = await asyncpg.create_pool(url.replace("postgresql+asyncpg://", "postgresql://"))
    yield PgAuthRepository(pool)
    await pool.close()


@pytest.fixture
async def user(repo):
    u = await repo.create_user(
        email=f"t_{uuid.uuid4()}@x", password_hash=b"x",
        display_name="X", role="user",
    )
    yield u
    async with repo._pool.acquire() as conn:
        await conn.execute("DELETE FROM user_profiles WHERE user_id=$1", uuid.UUID(u.id))
        await conn.execute("DELETE FROM ledger WHERE user_id=$1", uuid.UUID(u.id))
        await conn.execute("DELETE FROM users WHERE id=$1", uuid.UUID(u.id))


async def test_get_user_profile_returns_none_when_absent(repo, user):
    p = await repo.get_user_profile(user.id)
    assert p is None


async def test_upsert_user_profile_creates_row_when_absent(repo, user):
    await repo.upsert_user_profile(user.id, research_field="Bio", affiliation="X Univ")
    p = await repo.get_user_profile(user.id)
    assert p["research_field"] == "Bio"
    assert p["affiliation"] == "X Univ"
    assert p["expertise_level"] is None
    assert p["projects"] is None
    assert p["custom_intro"] is None
    assert p["updated_at"] is not None


async def test_upsert_partial_keeps_existing(repo, user):
    await repo.upsert_user_profile(user.id, research_field="Bio")
    await repo.upsert_user_profile(user.id, affiliation="Y Inst")
    p = await repo.get_user_profile(user.id)
    assert p["research_field"] == "Bio"
    assert p["affiliation"] == "Y Inst"


async def test_upsert_none_value_clears_field(repo, user):
    """null = 清空(handler 转 None 后传到 repo,repo SET NULL)。"""
    await repo.upsert_user_profile(user.id, research_field="Bio")
    await repo.upsert_user_profile(user.id, research_field=None)
    p = await repo.get_user_profile(user.id)
    assert p["research_field"] is None


async def test_get_user_with_balance_includes_balance_li(repo, user):
    u = await repo.get_user_with_balance(user.id)
    assert u["balance_li"] == 0
    assert u["email"] == user.email
    assert u["plan"] == "free"
    assert u["realname_verified"] is False
    assert u["created_at"] is not None
```

- [ ] **Step 2: 跑测试确认红**

Run: `PRAXIS_INTEGRATION=1 PRAXIS_DB_URL=... pytest tests/test_auth_repository_pg_profile.py -v`
Expected: 5 FAIL with `AttributeError: ... has no attribute 'upsert_user_profile'`(或本机无 docker → 5 SKIP,Step 4 实现后远端 staging 验)

- [ ] **Step 3: 实现 — `praxis2/auth/repository_pg.py` 4 个方法**

在 `list_audit_by_user` 之后(class 末尾,约 line 153)加:

```python
    # ── M9:profile + balance ─────────────────────────────────────────
    PROFILE_FIELDS = (
        "research_field", "affiliation", "expertise_level",
        "projects", "custom_intro",
    )

    async def get_user_profile(self, user_id: str) -> dict | None:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT research_field, affiliation, expertise_level, "
                "       projects, custom_intro, updated_at "
                "FROM user_profiles WHERE user_id=$1",
                uid,
            )
        if row is None:
            return None
        return {
            "research_field": row["research_field"],
            "affiliation": row["affiliation"],
            "expertise_level": row["expertise_level"],
            "projects": row["projects"],
            "custom_intro": row["custom_intro"],
            "updated_at": row["updated_at"],
        }

    async def upsert_user_profile(self, user_id: str, **fields) -> None:
        """fields 只含调用方真要写的字段;值可为 None(SET NULL = 清空)。

        缺失字段不进 SET clause。空 fields 视为 no-op。
        """
        if not fields:
            return
        unknown = set(fields) - set(self.PROFILE_FIELDS)
        if unknown:
            raise ValueError(f"unknown profile field: {unknown}")
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        cols = list(fields.keys())
        col_list = ", ".join(cols)
        val_placeholders = ", ".join(f"${i+2}" for i in range(len(cols)))
        set_clause = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols)
        sql = (
            f"INSERT INTO user_profiles (user_id, {col_list}, updated_at) "
            f"VALUES ($1, {val_placeholders}, now()) "
            f"ON CONFLICT (user_id) DO UPDATE SET {set_clause}, updated_at=now()"
        )
        async with self._pool.acquire() as conn:
            await conn.execute(sql, uid, *[fields[c] for c in cols])

    async def get_user_with_balance(self, user_id: str) -> dict | None:
        """读 user 全字段 + balance_li(已在 users 表里)+ realname_verified bool。

        balance_li 在 ledger 写入时跟着 UPDATE users 同步,这里直接读。
        """
        u = await self.get_user_by_id(user_id)
        if u is None:
            return None
        return {
            "id": u.id,
            "email": u.email,
            "phone": None,  # M9 schema 无该列(001 有 phone 但 InMemoryAuth 无,统一 None)
            "display_name": u.display_name,
            "role": u.role,
            "plan": u.plan,
            "status": u.status,
            "balance_li": u.balance_li,
            "realname_verified": bool(u.realname_verified_at),
            "created_at": u.created_at,
        }

    async def get_balance_li(self, user_id: str) -> int:
        """便利方法:只取 balance_li,handle_me_balance 用。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            cur = await conn.fetchval(
                "SELECT balance_li FROM users WHERE id=$1 AND deleted_at IS NULL", uid
            )
        return int(cur) if cur is not None else 0
```

文件顶部加 `import uuid`(若已有就跳过)。

- [ ] **Step 4: 同步 — `praxis2/auth/repository.py` Protocol + InMemoryAuthRepository**

AuthRepository Protocol 末尾加 4 个签名:

```python
    async def get_user_profile(self, user_id: str) -> dict | None: ...
    async def upsert_user_profile(self, user_id: str, **fields: str | None) -> None: ...
    async def get_user_with_balance(self, user_id: str) -> dict | None: ...
    async def get_balance_li(self, user_id: str) -> int: ...
```

InMemoryAuthRepository 末尾(class 内)加:

```python
    PROFILE_FIELDS = (
        "research_field", "affiliation", "expertise_level",
        "projects", "custom_intro",
    )

    async def get_user_profile(self, user_id):
        return self._profiles.get(user_id)

    async def upsert_user_profile(self, user_id, **fields):
        if not fields:
            return
        unknown = set(fields) - set(self.PROFILE_FIELDS)
        if unknown:
            raise ValueError(f"unknown profile field: {unknown}")
        from datetime import datetime, UTC
        cur = self._profiles.get(user_id) or {
            "research_field": None, "affiliation": None,
            "expertise_level": None, "projects": None, "custom_intro": None,
            "updated_at": None,
        }
        for k, v in fields.items():
            cur[k] = v
        cur["updated_at"] = datetime.now(UTC)
        self._profiles[user_id] = cur

    async def get_user_with_balance(self, user_id):
        u = self._users.get(user_id)
        if u is None:
            return None
        return {
            "id": u.id, "email": u.email, "phone": None,
            "display_name": u.display_name, "role": u.role,
            "plan": u.plan, "status": u.status, "balance_li": u.balance_li,
            "realname_verified": bool(u.realname_verified_at),
            "created_at": u.created_at,
        }

    async def get_balance_li(self, user_id):
        u = self._users.get(user_id)
        return u.balance_li if u else 0
```

并在 `InMemoryAuthRepository.__init__` 里加:

```python
        self._profiles: dict[str, dict] = {}
```

- [ ] **Step 5: 跑测试确认绿**

```bash
pytest tests/test_auth_repository.py -v
PRAXIS_INTEGRATION=1 PRAXIS_DB_URL=... pytest tests/test_auth_repository_pg_profile.py -v
```

Expected: 全 PASS(无 docker → integration SKIP,等 staging 验)

- [ ] **Step 6: ruff + commit**

```bash
ruff check praxis2/auth/ tests/test_auth_repository_pg_profile.py
git add praxis2/auth/ tests/test_auth_repository_pg_profile.py
git commit -m "$(cat <<'EOF'
feat(M9/T5): repository 加 4 个 profile/balance 方法

PgAuthRepository + InMemoryAuthRepository + AuthRepository Protocol 都加:
- get_user_profile / upsert_user_profile(动态 SET,缺失字段=不动,None=清空)
- get_user_with_balance(返 dict + realname_verified bool 算)
- get_balance_li(便利方法,handle_me_balance 用)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `handle_me` 扩 11 字段(取消嵌套)

**Files:**
- Modify: `praxis2/auth/routes.py:371-391`(handle_me)
- Test: `tests/test_auth_routes_v2_me.py`(新文件)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_auth_routes_v2_me.py
"""M9 /api/me + /api/me/balance + /api/me/profile + /api/me/proposals 测试。"""
from __future__ import annotations

import json
from datetime import datetime, UTC

import pytest

from tests.test_auth_routes import _Settings, _make_deps  # 复用现有 fixture


async def _login_get_cookie(deps, email="m9@x", password="pass"):
    """注册 + 登录,返回 set-cookie 字符串供后续请求带。"""
    # 触发 register 路径取得 dev_code
    sent = []
    captured = {}

    async def fake_send(msg):
        sent.append(msg)
        if msg["type"] == "http.response.body":
            captured["body"] = msg.get("body", b"")

    # send-code
    from praxis2.auth.routes import handle_send_code, handle_register, handle_login
    body = json.dumps({"email": email, "purpose": "register"}).encode()
    receive = _mk_receive(body)
    await handle_send_code(_mk_scope("POST", "/api/auth/email/send-code"), receive, fake_send, deps)
    resp = json.loads(captured["body"])
    code = resp["dev_code"]
    # register
    sent.clear(); captured.clear()
    body = json.dumps({"email": email, "code": code, "password": password}).encode()
    await handle_register(_mk_scope("POST", "/api/auth/register"), _mk_receive(body), fake_send, deps)
    # 抓 set-cookie
    start = next(m for m in sent if m["type"] == "http.response.start")
    cookie = next(v for k, v in start["headers"] if k == b"set-cookie").decode()
    return cookie


def _mk_scope(method, path, *, user=None, cookie=None):
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.split(";", 1)[0].encode()))
    s = {"type": "http", "method": method, "path": path, "headers": headers}
    if user:
        s["user"] = user
    return s


def _mk_receive(body=b""):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return receive


async def _capture(fn, *args):
    sent = []
    async def send(msg):
        sent.append(msg)
    await fn(*args, send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(m["body"] for m in sent if m["type"] == "http.response.body")
    return start["status"], json.loads(body) if body else {}, start["headers"]


async def test_me_shape_11_fields_flat_not_nested():
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    # 直造 user_id 注入 scope
    deps["repo"]._users["uid-1"] = _mk_userrow(id="uid-1", email="a@x", role="user")
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-1"})

    status, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert status == 200
    # 11 字段全在,不嵌套
    assert "user" not in body  # NOT nested
    for k in ("id", "phone", "email", "display_name", "role", "plan", "status",
              "balance_li", "balance_yuan", "realname_verified", "created_at"):
        assert k in body, f"missing field: {k}"


async def test_me_balance_yuan_format():
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-2"] = _mk_userrow(id="uid-2", email="b@x", balance_li=10000)
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-2"})
    status, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert body["balance_li"] == 10000
    assert body["balance_yuan"] == "100.00"


async def test_me_realname_verified_false_when_at_null():
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-3"] = _mk_userrow(id="uid-3", email="c@x", realname_verified_at=None)
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-3"})
    _, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert body["realname_verified"] is False


async def test_me_realname_verified_true_when_at_set():
    deps = await _make_deps()
    from praxis2.auth.routes import handle_me
    deps["repo"]._users["uid-4"] = _mk_userrow(
        id="uid-4", email="d@x", realname_verified_at=datetime.now(UTC)
    )
    scope = _mk_scope("GET", "/api/me", user={"user_id": "uid-4"})
    _, body, _ = await _capture(handle_me, scope, _mk_receive(), deps)
    assert body["realname_verified"] is True


def _mk_userrow(**overrides):
    from praxis2.auth.repository import UserRow
    defaults = dict(
        id="uid", email="x@x", password_hash=b"x",
        display_name=None, role="user", plan="free", status="active",
        balance_li=0, created_at=datetime.now(UTC),
        last_login_at=None, last_login_ip=None,
        realname_verified_at=None, deleted_at=None,
    )
    defaults.update(overrides)
    return UserRow(**defaults)
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k "shape or balance_yuan or realname"`
Expected: 4 FAIL with assertion errors(原 handle_me 返嵌套 `{user: ...}`)

- [ ] **Step 3: 实现 — `praxis2/auth/routes.py:371-391` 重写 handle_me**

```python
async def handle_me(scope, receive, send, deps) -> None:
    """M9:返 11 字段平铺(不嵌套 user),含 plan/balance/realname_verified/created_at。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    u = await deps["repo"].get_user_with_balance(user["user_id"])
    if not u:
        await _json(send, 401, {"error": "user_not_found", "reason": "用户不存在"})
        return
    balance_li = int(u["balance_li"])
    await _json(send, 200, {
        "id": u["id"],
        "phone": u.get("phone"),  # M9:repo 总返 None(schema 有列但 InMemoryAuth 不映射)
        "email": u["email"],
        "display_name": u["display_name"],
        "role": u["role"],
        "plan": u["plan"],
        "status": u["status"],
        "balance_li": balance_li,
        "balance_yuan": f"{balance_li / 100:.2f}",
        "realname_verified": bool(u["realname_verified"]),
        "created_at": u["created_at"].isoformat() if u.get("created_at") else "",
    })
```

- [ ] **Step 4: 跑测试确认绿**

```bash
pytest tests/test_auth_routes_v2_me.py -v -k "shape or balance_yuan or realname"
pytest tests/test_auth_routes.py -v  # 现有不回归
```

Expected: 4 PASS + 现有所有过

> ⚠️ 现有 test_auth_routes.py 里可能有断言旧 `body["user"]` shape 的 case,需要同步改。grep 一下:`grep -n '"user"\]' tests/test_auth_routes.py`。如果有,把那些断言改成扁平 shape。

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/auth/routes.py tests/test_auth_routes_v2_me.py
git add praxis2/auth/routes.py tests/test_auth_routes_v2_me.py tests/test_auth_routes.py
git commit -m "$(cat <<'EOF'
feat(M9/T6): handle_me 扩 11 字段平铺(取消 {user:{}} 嵌套)

- 走 repo.get_user_with_balance 拿 dict
- balance_yuan = f"{balance_li/100:.2f}" 直接算
- realname_verified = bool(row.realname_verified_at)
- created_at ISO 8601

破坏性:返回 shape 从 {user:{...}, balance_li} 改为平铺 11 字段。
FE adapter 在 T12 同步删,backend ship + FE rebuild ± 30 min 内完成。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `handle_me_balance` 接真 ledger + Ledger 注入

**Files:**
- Modify: `praxis2/server/app.py`(_App.__init__ 构造 Ledger 加进 auth_deps)
- Modify: `praxis2/auth/routes.py:394-400`(handle_me_balance 重写)
- Test: `tests/test_auth_routes_v2_me.py` 加 3 例

- [ ] **Step 1: 写失败测试(追加到 test_auth_routes_v2_me.py)**

```python
async def test_me_balance_empty_returns_zero():
    deps = await _make_deps()
    deps["ledger"] = _mk_inmemory_ledger()
    deps["repo"]._users["uid-b"] = _mk_userrow(id="uid-b", email="b@x", balance_li=0)
    from praxis2.auth.routes import handle_me_balance
    scope = _mk_scope("GET", "/api/me/balance", user={"user_id": "uid-b"})
    status, body, _ = await _capture(handle_me_balance, scope, _mk_receive(), deps)
    assert status == 200
    assert body["balance_li"] == 0
    assert body["balance_yuan"] == "0.00"
    assert body["recent"] == []


async def test_me_balance_returns_recent_with_balance_after():
    deps = await _make_deps()
    deps["ledger"] = _mk_inmemory_ledger(
        rows=[
            {"id": 1, "amount_li": 10000, "kind": "signup_gift",
             "ref_type": None, "ref_id": None, "balance_after": 10000,
             "meta": None, "created_at": datetime.now(UTC)},
            {"id": 2, "amount_li": -200, "kind": "chat_out",
             "ref_type": "chat_session", "ref_id": "sess-x",
             "balance_after": 9800, "meta": None,
             "created_at": datetime.now(UTC)},
        ],
        balance=9800,
    )
    deps["repo"]._users["uid-c"] = _mk_userrow(id="uid-c", email="c@x", balance_li=9800)
    from praxis2.auth.routes import handle_me_balance
    scope = _mk_scope("GET", "/api/me/balance", user={"user_id": "uid-c"})
    status, body, _ = await _capture(handle_me_balance, scope, _mk_receive(), deps)
    assert status == 200
    assert body["balance_li"] == 9800
    assert body["balance_yuan"] == "98.00"
    assert len(body["recent"]) == 2
    assert body["recent"][0]["kind"] == "signup_gift"
    assert body["recent"][1]["kind"] == "chat_out"


async def test_me_balance_recent_caps_at_20():
    rows = [
        {"id": i, "amount_li": -1, "kind": "chat_out",
         "ref_type": None, "ref_id": None, "balance_after": 100 - i,
         "meta": None, "created_at": datetime.now(UTC)}
        for i in range(25)
    ]
    deps = await _make_deps()
    deps["ledger"] = _mk_inmemory_ledger(rows=rows, balance=75)
    deps["repo"]._users["uid-d"] = _mk_userrow(id="uid-d", email="d@x", balance_li=75)
    from praxis2.auth.routes import handle_me_balance
    scope = _mk_scope("GET", "/api/me/balance", user={"user_id": "uid-d"})
    _, body, _ = await _capture(handle_me_balance, scope, _mk_receive(), deps)
    assert len(body["recent"]) == 20  # cap


class _InMemoryLedger:
    """测试用 fake Ledger,只实现 recent()。"""
    def __init__(self, rows=None, balance=0):
        self._rows = rows or []
        self._balance = balance

    async def recent(self, user_id, limit=20):
        return self._rows[:limit]


def _mk_inmemory_ledger(rows=None, balance=0):
    return _InMemoryLedger(rows=rows, balance=balance)
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k balance`
Expected: 3 FAIL — `deps["ledger"]` 不存在 / shape 不对

- [ ] **Step 3: 实现 — `praxis2/server/app.py` 注入 Ledger**

在 `_App.__init__` 里(约 line 167,设置 auth_deps 之前)加:

```python
        # M9:Ledger 用于 /api/me/balance + register signup_gift
        from praxis2.accounting.ledger import Ledger
        try:
            ledger = Ledger(deps.repo._pool)  # PgAuthRepository 有 _pool
        except AttributeError:
            ledger = None   # InMemoryAuthRepository(测试)不需要,handler 兜底
        auth_deps = {
            "repo": deps.repo,
            "redis": deps.redis,
            "email_gateway": deps.email_gateway,
            "settings": deps.settings,
            "ledger": ledger,                    # ← 新增
        }
```

- [ ] **Step 4: 实现 — `praxis2/auth/routes.py:394-400` 重写 handle_me_balance**

```python
async def handle_me_balance(scope, receive, send, deps) -> None:
    """M9:接真 ledger,返 balance + 最近 20 条流水。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    balance_li = await deps["repo"].get_balance_li(user["user_id"])
    ledger = deps.get("ledger")
    if ledger is not None:
        rows = await ledger.recent(user["user_id"], limit=20)
    else:
        rows = []  # InMemoryAuthRepository 测试路径
    await _json(send, 200, {
        "balance_li": int(balance_li),
        "balance_yuan": f"{balance_li / 100:.2f}",
        "recent": [
            {
                "id": r["id"],
                "amount_li": r["amount_li"],
                "kind": r["kind"],
                "ref_type": r["ref_type"],
                "ref_id": r["ref_id"],
                "balance_after": r["balance_after"],
                "meta": r["meta"],
                "created_at": (
                    r["created_at"].isoformat()
                    if hasattr(r["created_at"], "isoformat")
                    else r["created_at"]
                ),
            }
            for r in rows
        ],
    })
```

- [ ] **Step 5: 跑测试确认绿**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k balance`
Expected: 3 PASS

- [ ] **Step 6: ruff + commit**

```bash
ruff check praxis2/auth/routes.py praxis2/server/app.py tests/test_auth_routes_v2_me.py
git add praxis2/auth/routes.py praxis2/server/app.py tests/test_auth_routes_v2_me.py
git commit -m "$(cat <<'EOF'
feat(M9/T7): handle_me_balance 接真 ledger + Ledger 注入 auth_deps

- _App.__init__ 构造 Ledger(repo._pool),InMemoryAuthRepository 无 _pool → None
- handle_me_balance:ledger=None 时返空 recent(测试路径)
- Schema:{balance_li, balance_yuan, recent: [...]}

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `handle_me_profile_get` + `handle_me_profile_post`

**Files:**
- Modify: `praxis2/auth/routes.py`(末尾加 2 个 handler + ROUTES 加 2 行)
- Test: `tests/test_auth_routes_v2_me.py` 加 ~9 例

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_auth_routes_v2_me.py

async def test_profile_get_returns_all_nulls_when_empty():
    deps = await _make_deps()
    deps["repo"]._users["uid-p1"] = _mk_userrow(id="uid-p1", email="p1@x")
    from praxis2.auth.routes import handle_me_profile_get
    scope = _mk_scope("GET", "/api/me/profile", user={"user_id": "uid-p1"})
    status, body, _ = await _capture(handle_me_profile_get, scope, _mk_receive(), deps)
    assert status == 200
    for k in ("research_field", "affiliation", "expertise_level",
              "projects", "custom_intro", "updated_at"):
        assert body[k] is None


async def test_profile_post_partial_upsert_and_get_reflects():
    deps = await _make_deps()
    deps["repo"]._users["uid-p2"] = _mk_userrow(id="uid-p2", email="p2@x")
    from praxis2.auth.routes import handle_me_profile_post, handle_me_profile_get
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p2"})
    body = json.dumps({
        "research_field": "Structural Biology",
        "custom_intro": "I work on protein folding.",
    }).encode()
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 200
    assert resp["research_field"] == "Structural Biology"
    assert resp["affiliation"] is None  # 未填 → 仍 null
    assert resp["updated_at"] is not None


async def test_profile_post_null_keeps_existing():
    deps = await _make_deps()
    deps["repo"]._users["uid-p3"] = _mk_userrow(id="uid-p3", email="p3@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p3"})
    # 先填
    body1 = json.dumps({"research_field": "Bio"}).encode()
    await _capture(handle_me_profile_post, scope, _mk_receive(body1), deps)
    # 再发 null
    body2 = json.dumps({"research_field": None}).encode()
    _, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body2), deps)
    assert resp["research_field"] == "Bio"  # null = 不动


async def test_profile_post_empty_string_clears():
    deps = await _make_deps()
    deps["repo"]._users["uid-p4"] = _mk_userrow(id="uid-p4", email="p4@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p4"})
    body1 = json.dumps({"research_field": "Bio"}).encode()
    await _capture(handle_me_profile_post, scope, _mk_receive(body1), deps)
    body2 = json.dumps({"research_field": ""}).encode()
    _, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body2), deps)
    assert resp["research_field"] is None   # "" → NULL = 清空


@pytest.mark.parametrize("field,max_len", [
    ("research_field", 256),
    ("affiliation", 256),
    ("expertise_level", 256),
    ("projects", 2000),
    ("custom_intro", 2000),
])
async def test_profile_post_field_too_long_400(field, max_len):
    deps = await _make_deps()
    deps["repo"]._users["uid-pL"] = _mk_userrow(id="uid-pL", email="pL@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-pL"})
    body = json.dumps({field: "x" * (max_len + 1)}).encode()
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 400
    assert resp["error"] == "field_too_long"
    assert resp["field"] == field
    assert resp["max"] == max_len


async def test_profile_post_unknown_field_ignored():
    """未在 PROFILE_FIELDS 里的 key 静默忽略(不报 400,降低 FE 误传容错)。"""
    deps = await _make_deps()
    deps["repo"]._users["uid-p5"] = _mk_userrow(id="uid-p5", email="p5@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p5"})
    body = json.dumps({"research_field": "Bio", "garbage_field": "xxx"}).encode()
    status, _, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 200


async def test_profile_post_empty_body_noop():
    deps = await _make_deps()
    deps["repo"]._users["uid-p6"] = _mk_userrow(id="uid-p6", email="p6@x")
    from praxis2.auth.routes import handle_me_profile_post
    scope = _mk_scope("POST", "/api/me/profile", user={"user_id": "uid-p6"})
    body = b"{}"
    status, resp, _ = await _capture(handle_me_profile_post, scope, _mk_receive(body), deps)
    assert status == 200
    # 没填过 → 仍全 null
    assert resp["research_field"] is None
    assert resp["updated_at"] is None
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k profile`
Expected: 多个 FAIL — handler 不存在

- [ ] **Step 3: 实现 — `praxis2/auth/routes.py` 加 2 个 handler**

在 `handle_me_balance` 之后追加(约 line 401):

```python
# ── M9: profile (GET/POST) ───────────────────────────────────────────
PROFILE_FIELDS_MAX: dict[str, int] = {
    "research_field": 256,
    "affiliation": 256,
    "expertise_level": 256,
    "projects": 2000,
    "custom_intro": 2000,
}


async def handle_me_profile_get(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    p = await deps["repo"].get_user_profile(user["user_id"])
    if p is None:
        await _json(send, 200, {
            "research_field": None, "affiliation": None,
            "expertise_level": None, "projects": None, "custom_intro": None,
            "updated_at": None,
        })
        return
    await _json(send, 200, {
        "research_field": p["research_field"],
        "affiliation": p["affiliation"],
        "expertise_level": p["expertise_level"],
        "projects": p["projects"],
        "custom_intro": p["custom_intro"],
        "updated_at": (
            p["updated_at"].isoformat()
            if p.get("updated_at") and hasattr(p["updated_at"], "isoformat")
            else None
        ),
    })


async def handle_me_profile_post(scope, receive, send, deps) -> None:
    """upsert profile;null/缺失 = 不动,"" = 清空,超长 = 400。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    body = await _read_body(receive)
    to_set: dict[str, str | None] = {}
    for k, max_len in PROFILE_FIELDS_MAX.items():
        if k not in body or body[k] is None:
            continue           # null / 缺失 → 不动
        v = body[k]
        if not isinstance(v, str):
            await _json(send, 400, {"error": "field_invalid", "field": k})
            return
        if len(v) > max_len:
            await _json(send, 400, {
                "error": "field_too_long", "field": k, "max": max_len,
            })
            return
        to_set[k] = None if v == "" else v   # 空串 → NULL(清空)
    if to_set:
        await deps["repo"].upsert_user_profile(user["user_id"], **to_set)
    # 返最新值(再读一次 GET 同 shape)
    await handle_me_profile_get(scope, receive, send, deps)
```

> 注意:`_read_body` 在 routes.py 顶部已有;若该 helper 未导出,自己定义同一行 `body = json.loads(...)`。

- [ ] **Step 4: ROUTES 加 2 行**

在 `auth/routes.py:ROUTES` dict 末尾加:

```python
    ("/api/me/profile", "GET"): "handle_me_profile_get",
    ("/api/me/profile", "POST"): "handle_me_profile_post",
```

- [ ] **Step 5: 跑测试确认绿**

```bash
pytest tests/test_auth_routes_v2_me.py -v -k profile
pytest tests/test_app_routes_table.py -v  # ROUTES 注册正确
```

Expected: 全 PASS

- [ ] **Step 6: ruff + commit**

```bash
ruff check praxis2/auth/routes.py
git add praxis2/auth/routes.py tests/test_auth_routes_v2_me.py
git commit -m "$(cat <<'EOF'
feat(M9/T8): /api/me/profile GET/POST + 5 字段独立长度校验

- POST:null/缺失=不动,""=清空(SET NULL),超长 400 {error,field,max}
- GET:未填过返全 null + updated_at null
- ROUTES 加 2 行

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `handle_me_proposals_stub`

**Files:**
- Modify: `praxis2/auth/routes.py`(加 1 个 handler + ROUTES 加 1 行)
- Test: `tests/test_auth_routes_v2_me.py` 加 1 例

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_auth_routes_v2_me.py
async def test_me_proposals_stub_empty():
    deps = await _make_deps()
    deps["repo"]._users["uid-pp"] = _mk_userrow(id="uid-pp", email="pp@x")
    from praxis2.auth.routes import handle_me_proposals_stub
    scope = _mk_scope("GET", "/api/me/proposals", user={"user_id": "uid-pp"})
    status, body, _ = await _capture(handle_me_proposals_stub, scope, _mk_receive(), deps)
    assert status == 200
    assert body == {"proposals": [], "total": 0}
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k proposals_stub`
Expected: 1 FAIL — handler 不存在

- [ ] **Step 3: 实现 — `praxis2/auth/routes.py` 加 handler**

在 `handle_me_profile_post` 之后追加:

```python
async def handle_me_proposals_stub(scope, receive, send, deps) -> None:
    """M9 stub:返空列表,合约对齐 M12 真实现时无需 FE 改。"""
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    await _json(send, 200, {"proposals": [], "total": 0})
```

ROUTES 末尾加:

```python
    ("/api/me/proposals", "GET"): "handle_me_proposals_stub",
```

- [ ] **Step 4: 跑测试确认绿**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k proposals_stub`
Expected: 1 PASS

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/auth/routes.py
git add praxis2/auth/routes.py tests/test_auth_routes_v2_me.py
git commit -m "$(cat <<'EOF'
feat(M9/T9): /api/me/proposals stub 返 {proposals:[], total:0}

M12 接真业务时合约不变,只填 proposals 数组。
避免 FE staging 期间报 404 banner。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: `handle_register` 末尾接 signup_gift ledger.record

**Files:**
- Modify: `praxis2/auth/routes.py:157-220`(handle_register)
- Test: `tests/test_auth_routes_v2_me.py` 加 2 例

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_auth_routes_v2_me.py
async def test_register_grants_signup_gift_when_env_default():
    """settings.signup_gift_li=10000 → register 后 balance_li 必须 10000。"""
    deps = await _make_deps()
    deps["settings"].signup_gift_li = 10000
    deps["ledger"] = _RecordingLedger()
    # 走真 register 路径
    from praxis2.auth.routes import handle_send_code, handle_register
    # send-code
    body = json.dumps({"email": "gift@x", "purpose": "register"}).encode()
    _, resp, _ = await _capture(handle_send_code, _mk_scope("POST", "/api/auth/email/send-code"),
                                 _mk_receive(body), deps)
    code = resp["dev_code"]
    # register
    body = json.dumps({"email": "gift@x", "code": code, "password": "p"}).encode()
    status, resp, _ = await _capture(handle_register, _mk_scope("POST", "/api/auth/register"),
                                      _mk_receive(body), deps)
    assert status == 200
    assert resp["balance_li"] == 10000
    # ledger 收到 +10000 signup_gift
    assert deps["ledger"].calls == [("gift_user_id_placeholder", 10000, "signup_gift")] or \
           len(deps["ledger"].calls) == 1 and deps["ledger"].calls[0][1] == 10000


async def test_register_no_gift_when_env_zero():
    deps = await _make_deps()
    deps["settings"].signup_gift_li = 0
    deps["ledger"] = _RecordingLedger()
    from praxis2.auth.routes import handle_send_code, handle_register
    body = json.dumps({"email": "nogift@x", "purpose": "register"}).encode()
    _, resp, _ = await _capture(handle_send_code, _mk_scope("POST", "/api/auth/email/send-code"),
                                 _mk_receive(body), deps)
    code = resp["dev_code"]
    body = json.dumps({"email": "nogift@x", "code": code, "password": "p"}).encode()
    status, resp, _ = await _capture(handle_register, _mk_scope("POST", "/api/auth/register"),
                                      _mk_receive(body), deps)
    assert status == 200
    assert resp["balance_li"] == 0
    assert deps["ledger"].calls == []   # 完全不调


class _RecordingLedger:
    """fake Ledger:record(...) 只记 (user_id, amount, kind),不真写 DB。"""
    def __init__(self):
        self.calls = []

    async def record(self, conn, user_id, amount_li, kind, ref_type, ref_id, meta):
        self.calls.append((user_id, amount_li, kind))
        return amount_li  # 假装是 balance_after

    async def recent(self, user_id, limit=20):
        return []
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_auth_routes_v2_me.py -v -k register`
Expected: 2 FAIL — handle_register 没接 ledger

- [ ] **Step 3: 实现 — `praxis2/auth/routes.py:217` handle_register 接 ledger**

把 `handle_register` 的 `balance_li: 0` 行替换为真值,在 `mark_email_code_used` 之后、`insert_audit` 之前插入 signup_gift:

```python
    # 现有(line 190):await repo.mark_email_code_used(row.id)
    # M9:signup_gift 入账(env 控制额度,0 = 不赠)
    granted_li = 0
    if settings.signup_gift_li > 0:
        ledger = deps.get("ledger")
        if ledger is not None:
            # InMemoryAuthRepository 测试路径:无 _pool,RecordingLedger 直接接受 conn=None
            pool = getattr(repo, "_pool", None)
            if pool is None:
                # 测试 fake ledger 路径
                await ledger.record(None, user.id, settings.signup_gift_li,
                                    "signup_gift", None, None, {})
                granted_li = settings.signup_gift_li
            else:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        await ledger.record(conn, user.id, settings.signup_gift_li,
                                            "signup_gift", None, None, {})
                granted_li = settings.signup_gift_li

    await repo.insert_audit(...)  # 保留原 audit 调用
    ...
    await _json(
        send,
        200,
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            },
            "balance_li": granted_li,   # ← 改自原 0
        },
        extra_headers=((b"set-cookie", cookie_val.encode()),),
    )
```

> ⚠️ 这里 register 跟 signup_gift 跨了两个独立 conn(create_user 用 PgAuthRepository 自己拿 conn,ledger 拿另一个 conn)。**严格 atomicity** 要求两者同 transaction,但 PgAuthRepository.create_user 内部已 commit。
> M9 接受这个非严格弱原子:create_user 失败 → 整体 422(无 gift);create_user 成功但 ledger.record 失败 → user 已落 + balance_li=0 + audit 漏 signup_gift。
> 监控点:`/api/admin/reconcile`(M12)会发现这种 drift,届时再补强一致(用 advisory lock 或重构 create_user 接受 conn 参数,carry M11/M12)。

需要 update settings dataclass 让 test_auth_routes.py `_Settings` 也有 signup_gift_li 字段。在该文件顶部 `_Settings` 加 `signup_gift_li: int = 0`(测试默认 0,防影响现有 register 测试)。

- [ ] **Step 4: 跑测试确认绿**

```bash
pytest tests/test_auth_routes_v2_me.py -v -k register
pytest tests/test_auth_routes.py -v  # 现有 register 测试不回归(_Settings 默认 0)
```

Expected: 2 PASS + 0 回归

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/auth/routes.py tests/
git add praxis2/auth/routes.py tests/test_auth_routes_v2_me.py tests/test_auth_routes.py
git commit -m "$(cat <<'EOF'
feat(M9/T10): register 末尾接 signup_gift ledger.record

- settings.signup_gift_li > 0 → ledger.record(+amount, 'signup_gift')
- response.balance_li 返赠送金额(原 0)
- 弱原子:create_user 跟 ledger 不在同一 transaction;
  M12 admin/reconcile 端点会发现 drift 并修正(carry)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: FE `fetchMe()` 删 unwrap hack

**Files:**
- Modify: `frontend/src/lib/api.ts:84-103`

- [ ] **Step 1: 删除 unwrap 代码**

在 `frontend/src/lib/api.ts` 把 `fetchMe` 函数替换为:

```typescript
// ── me ──────────────────────────────────────────────────────────────
// M9:后端 /api/me 已直返扁平 11 字段(MeResponse shape),无需 unwrap。
export const fetchMe = (): Promise<MeResponse> =>
  apiFetch<MeResponse>('/api/me');
```

(删 v2.0.1 那段注释 + unwrap + 硬编码默认值,16 行 → 3 行)

- [ ] **Step 2: 跑 typecheck**

```bash
cd frontend && npm run typecheck
```

Expected: 0 error

- [ ] **Step 3: 跑 FE build 确认 dist 出**

```bash
cd frontend && VITE_API_BASE='' npm run build
ls dist/assets/index-*.js  # 应有
grep -c "balance_yuan" dist/assets/index-*.js  # 应 ≥ 1
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "$(cat <<'EOF'
feat(M9/T11): FE fetchMe() 删 unwrap hack,直返后端 MeResponse

后端 M9 已扩 /api/me 为扁平 11 字段(取消 {user:{}} 嵌套),
FE 不再需要硬编码默认值补齐。

破坏性:dist 必须跟 backend ship 同步推 .40(否则 FE 拿不到 user.balance_yuan)。
Task 12 staging 部署里一起 rsync。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: 全测试 + ruff + typecheck + 自审

**Files:** 无新建,跑全套验证

- [ ] **Step 1: pytest 全量(不含 integration)**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
pytest -q tests/ -k "not integration" --ignore=tests/test_skills 2>&1 | tail -20
```

Expected:
- `1575+ passed`(基线 1543 + ~32 新增)
- `26 xfailed`(synth skill schema 不变)
- `18 skipped`(integration auto-skip)
- 0 failed

如失败,定位修复后再跑。

- [ ] **Step 2: ruff 全过**

```bash
ruff check praxis2/ tests/
```

Expected: 0 new errors(基线 32 errors 不增)

- [ ] **Step 3: FE typecheck + build**

```bash
cd frontend && npm run typecheck && VITE_API_BASE='' npm run build
```

Expected: 0 typecheck error,build 成功(`dist/index.html` + `dist/assets/index-*.js`)

- [ ] **Step 4: 反查 spec 覆盖(self review)**

逐条对照 `docs/superpowers/specs/2026-05-24-m9-user-center-design.md`:
- [ ] §1 P0 项全部对应到 task(T1-T11)
- [ ] §2 schema 全部在 T2 实现
- [ ] §4 5 个 endpoint 合约全部有对应 handler 实现 + 测试
- [ ] §5 5 个一致性约束在 T3/T5/T8 落地
- [ ] §6 32 个测试全在 T1/T3/T5/T6/T7/T8/T9/T10

如发现 spec 有 requirement 没 task → 补 task 后再 commit。

- [ ] **Step 5: 无需 commit(只是验证步骤,代码已 commit)**

---

## Task 13: Staging 部署 + smoke + tag v0.10.0

**Files:** 部署操作,无代码改动

> ⚠️ **执行前再确认**:`.40:8088` 老 v1(`PRAXIS/server.py` + `PRAXIS/dist` + `.53:7788` PRAXIS-hou)整条链路**不动**。本 task 只动 `.53:8001` v2 backend + `.40:8080` v2 反代下挂的 `PRAXIS-2/dist`。

- [ ] **Step 1: staging migration on `.53` PG**

```bash
ssh zkyd@10.102.106.53 'cd /home/zkyd/PRAXIS-2 && \
    git pull origin main && \
    source .venv/bin/activate && \
    alembic upgrade head'
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade 001_initial_auth -> 002_user_profile_billing`

验证表存在:
```bash
ssh zkyd@10.102.106.53 'docker exec praxis2-pg \
    psql -U praxis2 -d praxis2 -c "\dt"' | grep -E "user_profiles|ledger"
```
应见 2 行。

- [ ] **Step 2: backend restart**

```bash
ssh zkyd@10.102.106.53 'tmux send-keys -t praxis2-backend C-c Enter'
sleep 3
ssh zkyd@10.102.106.53 'tmux send-keys -t praxis2-backend \
    "cd /home/zkyd/PRAXIS-2 && source .venv/bin/activate && \
     gunicorn -c gunicorn.conf.py praxis2.server.app:make_app_default" Enter'
sleep 5
```

- [ ] **Step 3: backend smoke**

```bash
# /api/info 通
curl -s http://10.102.106.53:8001/api/info | python3 -m json.tool
# /api/me 无 cookie 返 401 JSON(不是 SPA HTML)
curl -s -i http://10.102.106.53:8001/api/me | head -5
# /api/me/balance 无 cookie 401
curl -s -i http://10.102.106.53:8001/api/me/balance | head -5
# /api/me/profile 无 cookie 401
curl -s -i http://10.102.106.53:8001/api/me/profile | head -5
# /api/me/proposals 无 cookie 401
curl -s -i http://10.102.106.53:8001/api/me/proposals | head -5
```

Expected: 5 条全过(`401 {"error":"unauthorized"...}`)。

- [ ] **Step 4: 注册一个测试用户并验 signup_gift + balance**

```bash
EMAIL="m9test$(date +%s)@x.com"

# send-code
curl -s -c /tmp/m9cj -X POST http://10.102.106.53:8001/api/auth/email/send-code \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"purpose\":\"register\"}" | tee /tmp/sc.json
CODE=$(python3 -c "import json;print(json.load(open('/tmp/sc.json'))['dev_code'])")

# register(默认 PRAXIS_SIGNUP_GIFT_LI=10000)
curl -s -c /tmp/m9cj -X POST http://10.102.106.53:8001/api/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"code\":\"$CODE\",\"password\":\"pw123\"}" | tee /tmp/reg.json

# /api/me 验 balance_yuan = "100.00"
curl -s -b /tmp/m9cj http://10.102.106.53:8001/api/me | python3 -m json.tool

# /api/me/balance 验 recent 有 signup_gift +10000
curl -s -b /tmp/m9cj http://10.102.106.53:8001/api/me/balance | python3 -m json.tool

# /api/me/profile POST
curl -s -b /tmp/m9cj -X POST http://10.102.106.53:8001/api/me/profile \
    -H 'Content-Type: application/json' \
    -d '{"research_field":"Structural Biology","custom_intro":"M9 smoke"}'

# /api/me/profile GET 验 round-trip
curl -s -b /tmp/m9cj http://10.102.106.53:8001/api/me/profile | python3 -m json.tool
```

Expected:
- `/api/me`:`balance_li: 10000`, `balance_yuan: "100.00"`, 11 字段平铺
- `/api/me/balance.recent[0].kind` == "signup_gift",amount_li=10000
- `/api/me/profile` GET 返刚 POST 的字段值

- [ ] **Step 5: FE rebuild + rsync 到 `.40`**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2/frontend
VITE_API_BASE='' npm run build
rsync -avz --delete --exclude '._*' dist/ \
    hipeson@10.102.106.40:/home/hipeson/mzy/PRAXIS-2/dist/
```

Expected: rsync 完成。

- [ ] **Step 6: 浏览器手测(必跑 4 条)**

打开 `http://10.102.106.40:8080/`:
- [ ] 登录 `m9test...@x.com` / `pw123` → 看 sidebar 右上角余额「¥100.00」
- [ ] 打开「个人资料」/「Profile」→ 显示 research_field 等字段已填
- [ ] 填一个新字段 → 保存 → 刷新页面值仍在
- [ ] 主聊天 chat 一次 → 无 console error

**同时手测 v1 没被影响**:
- [ ] 打开 `http://10.102.106.40:8088/`(老 v1 入口)→ 老 v1 dist 正常加载,登录 v1 账号能聊天

任一红 → 跑 §7.2 回滚(spec §7.2)。

- [ ] **Step 7: tag v0.10.0**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git tag v0.10.0 -m "M9 ship: 用户中心 + ledger + profile + signup_gift"
git push origin main --tags
```

- [ ] **Step 8: 标 task #8 + 任务全部 completed,通知用户**

报告:M9 ship 完成,v0.10.0 已 tag,smoke 全过。24h 内观察:
- backend log error 率
- ledger 表写入有无 drift(`/api/me/balance` 数值一致)
- FE console 无报错

---

## Self-Review

### Spec 覆盖检查

| Spec section | 实现 task |
|---|---|
| §1 P0 — 002 migration | T2 |
| §1 P0 — accounting/ledger.py | T3 |
| §1 P0 — repository_pg 4 方法 | T5 |
| §1 P0 — /api/me 扩 11 字段 | T6 |
| §1 P0 — /api/me/balance 接 ledger | T7 |
| §1 P0 — /api/me/profile GET/POST | T8 |
| §1 P0 — /api/me/proposals stub | T9 |
| §1 P0 — register signup_gift | T10 |
| §1 P0 — FE adapter 删 | T11 |
| §1 P0 — config env | T1 |
| §2 schema | T2 |
| §3.1 7 个新文件 | T1/T2/T3/T5/T6 |
| §3.2 6 个改文件 | T1/T4/T5/T6/T7/T8/T9/T10/T11 |
| §4 6 个 endpoint 合约 | T6/T7/T8/T9/T10 |
| §5.1 ledger 事务 | T3 |
| §5.2 profile upsert 动态 SQL | T5/T8 |
| §5.3 401/404/400 schema | T6/T7/T8/T9 |
| §5.4 realname 计算 | T4/T6 |
| §5.5 balance_yuan 格式 | T6/T7 |
| §6 32 个测试 | T1(3) + T3(10) + T4(2) + T5(5) + T6(4) + T7(3) + T8(9) + T9(1) + T10(2) ≈ 39 |
| §7 ship/回滚 | T13 |

### 已识别的妥协(明确写在 task 内)
- **T10 register/ledger 弱原子**:create_user 跟 ledger.record 跨 conn,不在同一 PG transaction。M12 admin/reconcile 修。
- **T7 Ledger 在 InMemoryAuthRepository 时为 None**:测试路径降级返空 recent,生产路径正常。
- **T13 backend restart 命令假设 tmux session 名 `praxis2-backend`**,实际操作时若名不一致需调整。

### 不在 plan 内的 carry
- 真 SMTP 选型(M9 后 demo 决策)
- M11 spawn/md 接 ledger.record(kind='chat_out'/'md_run')
- M12 admin/reconcile + admin 调账

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-24-m9-user-center.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - 每 task 一个 fresh subagent,两阶段 review,iteration 快

**2. Inline Execution** - 本会话顺序执行 tasks,checkpoint review

**Which approach?**
