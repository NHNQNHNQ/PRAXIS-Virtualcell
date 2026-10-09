# M12 — admin v2 + proposals 设计 (PRAXIS-2 v0.14.0)

> 2026-05-27 brainstorm 产出。M13 准入条件之一(M9–M12 全 ship)。
>
> **2026-05-29 errata**:原文 `1元=10li` 是笔误,应为 `1元=100li`(沿用 M9 spec)。

## 1. 目标

Ship 13 个 backend endpoint(8 admin v2 + 5 proposals)+ 1 个新表(`proposals`),作为 staging → M13 路线图的最后一块。

**驱动**:M13 准入(`M9–M12 全 ship` 是 §4.6 列的 3 个 trigger 之一)。**不是**为当下 staging 痛点,也不是为用户 feedback 急需 — 走完整 13 endpoint。

**非目标**:不动 FE(`admin.ts` 已定义 client function 等接);不改 v1 链路(冻结);不加 admin v2 之外的 dashboard 功能。

## 2. 范围

| 类 | 内容 |
|---|---|
| Endpoint | 8 admin v2 + 5 proposals = 13 |
| 新 package | `praxis2/admin/` + `praxis2/proposals/` |
| 新 table | 1 张 `proposals`(`006_proposals` migration) |
| 复用 | `audit_log` 表(M9 001 已建)+ `repository_pg.insert_audit` + `Ledger.record` |
| 改动 M9 | 5 个 admin GET stub 在 `auth/routes.py` 替换真 handler(路由不变) |
| 工程量 | ~3–4d(< §4.4 估的 7d,因 audit_log + 5 stub 复用) |

## 3. 架构

```
praxis2/admin/        ← M12 新
├── __init__.py
├── handlers.py       ← 8 个 admin v2 handler
└── repo.py           ← AdminUserRepo + AuditRepo

praxis2/proposals/    ← M12 新
├── __init__.py
├── handlers.py       ← 5 个 proposals handler
└── repo.py           ← ProposalRepo

migrations/versions/006_proposals.py    ← 唯一新表
praxis2/server/app.py                   ← +8 个新路由 + 5 个 stub→real swap
```

**数据流总图**:

```
HTTP → CORS → auth middleware (cookie→user) → require_admin gate(admin endpoint)
     → handler → tx { repo + audit_log.insert (mutation only) } → JSON
```

- audit_log **仅 mutation** 写(POST/PUT/DELETE);GET endpoint 不写 audit(避免膨胀)
- audit 是**手动 `await audit_repo.insert(...)`**,跟 main op 同 tx;**不用 decorator**

## 4. 数据模型

### `proposals` 表(006_proposals)

**长度约束**(handler 校验,不进 schema 防加索引麻烦):`title ≤ 200 char`,`body ≤ 5000 char`,`decision_note ≤ 1000 char`,`shipped_to ≤ 200 char`。超长 → 400 `field_too_long`。


```sql
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
  admin_scores  JSONB,        -- {admin_uid: 1-5} 多人评分
  shipped_to    TEXT,         -- commit hash / PR url(decide 时手填)
  decision_note TEXT,
  decided_at    TIMESTAMPTZ,
  decided_by    UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_proposals_user_created ON proposals (user_id, created_at DESC);
CREATE INDEX ix_proposals_status_created ON proposals (status, created_at DESC);
```

**字段分工**(resolve §4.4 status/state 双轴 ambiguity):
- `status` = **admin lifecycle**(open → decided → closed)
- `state` = **user lifecycle**(submitted / withdrawn / archived)
- 两字段正交,各自由不同 actor 推进
- M12 endpoint 仅写 `state='submitted'`(创建时);withdrawn/archived 字段保留以便后续 carry 加 withdraw 不用 migration

### `audit_log` 表(M9 已建,001 migration)

字段:`id BIGSERIAL`,`user_id UUID`,`actor TEXT`,`action TEXT`,`resource TEXT`,`resource_id TEXT`,`ip TEXT`,`ua TEXT`,`meta JSONB`,`created_at TIMESTAMPTZ`。

M12 直接 INSERT,无需改 schema。

## 5. 组件细节

### 5.1 `praxis2/admin/repo.py`

```python
class AdminUserRepo:
    async def list_users(q: str, page: int, limit: int) -> Paginated[UserRow]
        # q 模糊匹配 email + display_name (ILIKE '%q%'); q='' 时返全表
    async def adjust_balance(conn, target_user_id: str, admin_id: str,
                             amount_li: int, note: str) -> dict
        # 返 {ledger_id, new_balance_li, new_balance_yuan}
        # 内部调 Ledger.record (caller 提供 conn 同 tx);audit 由 handler 内调
    async def freeze(conn, target_user_id: str, admin_id: str, reason: str) -> dict
    async def unfreeze(conn, target_user_id: str, admin_id: str) -> dict
    async def reconcile(max_users: int) -> dict
        # 不锁,SELECT FOR UPDATE 不要(reconcile 是诊断不是修复)
    async def get_stats() -> dict

class AuditRepo:
    async def query(filters: dict, page: int, limit: int) -> Paginated[AuditRow]
    async def insert(conn, user_id, actor, action, resource, resource_id, ip, ua, meta) -> int
        # 直接调 M9 auth/repository_pg.insert_audit (已实现)
```

### 5.2 `praxis2/admin/handlers.py`

8 个 handler,每个 mutation handler 内显式调 `audit_repo.insert(conn, ...)`,跟 main op 同 tx。

| Handler | Route | mutation? |
|---|---|---|
| `handle_admin_users_list` | GET `/api/admin/users?q=&page=&limit=` | no |
| `handle_admin_user_adjust` | POST `/api/admin/users/{id}/adjust` | yes(audit `balance_adjust`)|
| `handle_admin_user_freeze` | POST `/api/admin/users/{id}/freeze` | yes(audit `user_freeze`)|
| `handle_admin_user_unfreeze` | POST `/api/admin/users/{id}/unfreeze` | yes(audit `user_unfreeze`)|
| `handle_admin_reconcile` | POST `/api/admin/reconcile` | yes(audit `reconcile_run`,只一条)|
| `handle_admin_ledger_list` | GET `/api/admin/ledger?...` | no |
| `handle_admin_audit_list` | GET `/api/admin/audit-log?...` | no |
| `handle_admin_stats` | GET `/api/admin/stats` | no |

### 5.3 `praxis2/proposals/repo.py`

```python
class ProposalRepo:
    async def create(conn, user_id, kind, title, body) -> str  # 返 proposal_id
    async def list_mine(user_id, page, limit) -> Paginated[ProposalRow]
    async def list_all(filters: dict, page, limit) -> Paginated[ProposalRow]  # admin
    async def decide(conn, proposal_id, admin_id, verdict, score=None,
                     shipped_to=None, note=None) -> dict
```

### 5.4 `praxis2/proposals/handlers.py`

| Handler | Route | mutation? |
|---|---|---|
| `handle_proposal_create` | POST `/api/proposals` | yes(audit `proposal_create`)|
| `handle_proposal_list_mine` | GET `/api/me/proposals` | no |
| `handle_admin_proposal_list` | GET `/api/admin/proposals?...` | no |
| `handle_admin_proposal_decide` | POST `/api/admin/proposals/{id}/decide` | yes(audit `proposal_decide`)|
| **(无 withdraw endpoint)** | — | — |

withdraw 留 carry,schema 字段 `state='withdrawn'` 已留位。

### 5.5 `praxis2/server/app.py`

5 stub swap + 8 新 route:

```python
# 替换 M9 stub(routes 不变,只改 handler):
("/api/admin/users",      "GET"):  self._admin_users_list      # was stub
("/api/admin/ledger",     "GET"):  self._admin_ledger_list     # was stub
("/api/admin/audit-log",  "GET"):  self._admin_audit_list      # was stub
("/api/admin/proposals",  "GET"):  self._admin_proposal_list   # was stub
("/api/admin/stats",      "GET"):  self._admin_stats           # was stub

# 新加:
("/api/admin/users/{id}/adjust",       "POST"): self._admin_user_adjust
("/api/admin/users/{id}/freeze",       "POST"): self._admin_user_freeze
("/api/admin/users/{id}/unfreeze",     "POST"): self._admin_user_unfreeze
("/api/admin/reconcile",               "POST"): self._admin_reconcile
("/api/proposals",                     "POST"): self._proposal_create
("/api/me/proposals",                  "GET"):  self._proposal_list_mine
("/api/admin/proposals/{id}/decide",   "POST"): self._admin_proposal_decide
```

### 5.6 `praxis2/config.py` 加 env

```python
# M12 admin/proposals
PRAXIS_ADMIN_RECONCILE_MAX_USERS = 1000      # reconcile 一次最多扫
PRAXIS_PROPOSALS_PER_USER_PER_DAY = 20       # 防刷
```

加到 `_KNOWN_KEYS` 白名单 + `load_from_env` 的 default 值。

## 6. 数据流

### 流 1 — POST `/api/proposals`

```
1. require_user (M9 middleware)
2. validate kind/title (kind ∈ enum, title 非空 ≤ 200)
3. rate limit: 检 user 最近 24h 在 proposals 表的 count < PER_DAY
4. tx:
   a. ProposalRepo.create(conn, user_id, kind, title, body) → pid
   b. AuditRepo.insert(conn, user_id, actor='user', action='proposal_create',
                       resource='proposal', resource_id=pid,
                       meta={kind, title_first_30})
5. 200 {id, status:'open', state:'submitted', created_at}
```

### 流 2 — POST `/api/admin/users/{id}/adjust`

**Body**:`{"amount_yuan": float, "note": str}` —— FE 传**元**(跟 `admin.ts:adjustBalance` 一致),backend 转 `amount_li = round(amount_yuan * 100)`(1 元 = 100 li)。负 amount_yuan = 扣款,正 = 充值。

> **Errata (2026-05-29)**:`Ledger.record` 返 `balance_after` (非 ledger.id)。`adjust_balance` 实现单独 `SELECT id FROM ledger WHERE user_id=$1 ORDER BY id DESC LIMIT 1`(同 tx 内 read-own-write)拿到刚插入的 ledger.id 后再返。下面 step 3a 的 `Ledger.record(...) → ledger_id` 心智模型是 spec 错误,实际等价于 record + 后续 SELECT 两步。

```
1. require_admin
2. amount_li = round(amount_yuan * 100); validate amount_li != 0, note 非空
3. tx:
   a. Ledger.record(conn, target_uid, amount_li, kind='admin_adjust',
                    ref_type='admin', ref_id=admin_id, meta={note})
      → 内部 SELECT FOR UPDATE users + UPDATE balance + INSERT ledger
      → 抛 NegativeBalanceError 若余额变负 → 400 `negative_balance`
   b. AuditRepo.insert(conn, user_id=admin_id, actor='admin',
                       action='balance_adjust', resource='user', resource_id=target_uid,
                       meta={amount_li, note, new_balance_li})
4. 200 {ok, ledger_id, new_balance_li, new_balance_yuan}
```

### 流 3 — POST `/api/admin/proposals/{id}/decide`

**Body**:`{"verdict": "ship"|"promote"|"hold"|"reject", "score"?: 1-5, "shipped_to"?: str, "note"?: str}`

**admin_scores 多人评分语义**:用 `jsonb_set` 累加每个 admin 的分(以 `decided_by` 作 key),而非覆盖。例:已有 `{"adminA-uid": 4}`,adminB decide score=5 → 变 `{"adminA-uid": 4, "adminB-uid": 5}`。但 status 一旦 = decided 不能 re-decide(409),所以多人评分是 carry(MVP 单 admin)。

```
1. require_admin
2. validate verdict ∈ enum, score 1-5 if given
3. SELECT 当前 status, 若 != 'open' → 409 already_decided
4. tx:
   a. UPDATE proposals SET
        status='decided',
        admin_verdict=?,
        admin_scores=jsonb_set(COALESCE(admin_scores, '{}'::jsonb),
                               ARRAY[admin_id::text],
                               to_jsonb(?)),
        shipped_to=?,
        decision_note=?,
        decided_at=now(),
        decided_by=admin_id
      WHERE id=? AND status='open'
   b. AuditRepo.insert(conn, user_id=admin_id, actor='admin',
                       action='proposal_decide', resource='proposal', resource_id=pid,
                       meta={verdict, score, shipped_to})
5. 200 {ok, status:'decided', verdict, decided_at}
```

### 流 4 — POST `/api/admin/reconcile`

```
1. require_admin
2. async batch(LIMIT PRAXIS_ADMIN_RECONCILE_MAX_USERS):
     SELECT id, balance_li FROM users
     for u in batch:
       sum = SUM(amount_li) FROM ledger WHERE user_id=u.id
       if u.balance_li != sum: mismatches.append({u.id, balance_li, sum, diff})
3. tx:
   AuditRepo.insert(conn, user_id=admin_id, actor='admin', action='reconcile_run',
                    resource='system', meta={checked, mismatches_count})
4. 200 {checked, mismatches: len(mismatches), details: mismatches[:20]}
```

不锁、不修。诊断用,真修复要 admin 后续手动 adjust。

## 7. 错误处理

| Code | error_code | 场景 |
|---|---|---|
| 401 | `unauthorized` | 未登录 / cookie 失效 |
| 403 | `forbidden` | 已登录非 admin |
| 403 | `cannot_freeze_admin` | 试 freeze 一个 admin user |
| 404 | `not_found` | user_id / proposal_id 不存在或不属于 caller |
| 400 | `missing_field` | required 字段缺 |
| 400 | `bad_pagination` | page<1 / limit>200 |
| 400 | `zero_amount` | adjust amount=0 |
| 400 | `negative_balance` | adjust 后余额变负 |
| 422 | `invalid_kind` | proposal kind 非 enum |
| 422 | `invalid_verdict` | decide verdict 非 enum |
| 422 | `invalid_score` | score 非 1-5 |
| 409 | `already_decided` | 试 re-decide |
| 409 | `closed_proposal` | 试 decide status=closed |
| 429 | `proposal_rate_limit` | 24h 内 > PER_DAY |
| 500 | `server_error` | 未捕异常 fallback |

**Response shape**:`{"error": "code_snake", "reason": "中文", ...context}`(跟 M11.x 一致)。

**Idempotent**:freeze 已 frozen / unfreeze 已 unfrozen → 200 但**不重写 audit**(避免重复审计噪声)。

**Tx 原子性**:audit insert 跟 main op 同 tx,任一失败整 tx 回滚。audit 失败不静默吞。

## 8. 测试策略

### 3 层金字塔(~37 test,跟 M11.2 同量级)

| 层 | 文件 | 数量 |
|---|---|---|
| unit | `tests/test_proposals_validators.py`(kind/verdict/pagination 校验)| 6 |
| unit | `tests/test_admin_pagination_unit.py`(page/limit/q clamp)| 4 |
| integration(PG)| `tests/integration/test_proposals_repo.py` | 8 |
| integration(PG)| `tests/integration/test_admin_user_repo.py` | 10 |
| integration(PG)| `tests/integration/test_audit_repo.py` | 4 |
| integration(PG)| `tests/integration/test_reconcile.py` | 3 |
| e2e(PG+HTTP)| `tests/integration/test_m12_admin_e2e.py`(login→list→adjust→audit→freeze→unfreeze)| 1 |
| e2e(PG+HTTP)| `tests/integration/test_m12_proposal_e2e.py`(user post→admin list→decide→audit+状态)| 1 |

### 关键覆盖点

1. **audit + main op 同 tx**:`Ledger.record` 抛异常时 `audit_log` 不写(回滚)
2. **enum 校验**:invalid kind/verdict/score → 422
3. **pagination 边界**:page=0 / limit=10000 → 400
4. **idempotent**:freeze 已 frozen → 200 不重写 audit
5. **冲突拒绝**:already_decided 不能 re-decide
6. **reconcile 检出**:故意制造 ledger sum ≠ balance,reconcile 报 mismatch
7. **rate limit**:连发 21 个 proposal → 第 21 个 429
8. **非 admin 访问**:403 forbidden
9. **未登录访问**:401 unauthorized
10. **freeze admin**:403 cannot_freeze_admin

### Test 跑法

```bash
.venv/bin/python -m pytest tests/test_proposals_validators.py tests/test_admin_pagination_unit.py -v
.venv/bin/python -m pytest tests/integration/test_proposals_repo.py tests/integration/test_admin_user_repo.py tests/integration/test_audit_repo.py tests/integration/test_reconcile.py -v   # 需 docker compose pg
.venv/bin/python -m pytest tests/integration/test_m12_*.py -v
```

## 9. 部署

跟 M11.2 流程一致:
1. 本地 commit + push
2. `BACKEND_HOST=10.102.106.53 BACKEND_USER=zkyd BACKEND_PATH=/home/zkyd/data1/mzy/PRAXIS-2 SERVICE_NAME=skip bash deploy/push_backend.sh`(push_backend.sh 已 fix migrations 同步)
3. ssh `.53` `alembic upgrade head`(跑 006_proposals)
4. ssh `.53` `bash /tmp/restart_praxis2.sh`(拉新 code)
5. curl `/api/info`,curl 几个 endpoint 验通

## 10. Carry(M12 后)

- **withdraw endpoint** — schema state='withdrawn' 已留,加 endpoint 时不用 migration
- **archive endpoint** — 同上
- **audit decorator 化** — 现在 handler 手动 insert,carry 可统一为 decorator(若数量增多)
- **reconcile race** — 现在不锁,admin 并发操作可能 false positive,carry 加 advisory lock
- **shipped_to 自动追** — 现在 admin decide 时手填 commit hash,carry 接 git/PR 自动
- **proposal 多人评分流** — schema admin_scores JSONB 留位,carry 加 vote endpoint
- **rate limit 用 redis** — 现在 SQL count 算 rate,carry 改 redis sorted set 高效
- **stats 实时 vs cached** — 现在每次实算,carry 加 1min cache
- **/api/me/proposals 翻页 vs 全拉** — MVP 翻页 50,carry 加 since_id incremental

## 11. 路线图位置

- 当前:v0.13.0(M11.2 MD+HPC ship)
- M12 ship → v0.14.0
- M12 后 → staging 24h–2 周观察(`docs/superpowers/specs/2026-05-24-...routemap... §4.6`)
- staging 通过 + user 显式批准 + v1 retention 可接受 → M13 触发条件满足
