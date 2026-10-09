# M9 — 用户中心扩展 + 真 SMTP(代码就绪) 设计稿

> 起草:2026-05-24
> 来源:`/Volumes/T7/clade-learn/PRAXIS-2-计划-v2-完整重写-路线图.md` §5,经 2026-05-24 brainstorming 10 个决策点收紧后定稿。
> 上游约束:[M13 推迟](/Users/mzy/.claude/projects/-Volumes-T7-clade-learn/memory/project_m13_deferred.md)— v1 全程冻结,v2 改动只在 `.40:8080` + `.53:8001` 上做。

---

## §0 决策摘要(10 项已锁,brainstorming 输出)

| # | 决策 | 取值 |
|---|------|------|
| 1 | SMTP 提供商 | **暂不接真 SMTP**(DevEmailGateway 仍默认),SmtpEmailGateway 代码已就绪;真接通推迟到 M9 后 demo 阶段再选型 |
| 2 | `realname_verified` schema 冲突 | **保留 001 `realname_verified_at TIMESTAMPTZ`**;handler 算 `bool(row.realname_verified_at)` 返 FE。路线图 §4.2 的 ADD bool 列改为 NO-OP |
| 3 | `user_profiles` 字段终稿 | 5 字段:`research_field` / `affiliation` / `expertise_level` / `projects` / `custom_intro`,全 nullable text |
| 4 | 注册赠送 `signup_gift_li` | env `PRAXIS_SIGNUP_GIFT_LI` 默认 **10000**(= 100元);可设 0 表示不赠 |
| 5 | li ↔ 元 换算 | **1 元 = 100 li**(按人民币分);`balance_yuan = f"{balance_li/100:.2f}"` |
| 6 | `/api/me/balance.recent` | **固定 20 条 DESC**,不参数化。分页走 admin `/api/admin/ledger`(M12) |
| 7 | `/api/me/proposals` | M9 stub 返 `{"proposals":[], "total":0}`,M12 接真业务 |
| 8 | `plan` 字段语义 | 返 DB 原值(默认 `'free'`),read-only;FE 仅展示,付费升级 carry M12 admin |
| 9 | `/api/me/profile` POST 校验 | 各字段独立上限:`custom_intro`/`projects` 2000 字符,其余三项 256;超出 400 + `{"error":"field_too_long","field":...,"max":...}` |
| 10 | FE adapter 删除时机 | **M9 ship 末尾**,后端 ± 30 min 同步 FE rebuild + rsync,**合并为 v0.10.0 单 tag** |

---

## §1 范围(P0 / P1 / carry)

### P0 — M9 必做(~4d)
- DB 002 migration:`user_profiles` 表 + `ledger` 表
- `praxis2/accounting/ledger.py` 新模块(record + recent + 事务原子)
- `praxis2/auth/repository_pg.py` 扩 4 个方法
- `/api/me` 扩 11 字段(取消嵌套 `{user:{}}`)
- `/api/me/balance` 接真 ledger(balance + 20 条 recent)
- `/api/me/profile` GET / POST(5 字段 + 长度校验)
- `/api/me/proposals` stub
- `register handler` 末尾接 `ledger.record(kind='signup_gift', amount=+PRAXIS_SIGNUP_GIFT_LI)`
- FE `fetchMe()` 删 unwrap hack + rebuild + rsync
- Config 加 env `PRAXIS_SIGNUP_GIFT_LI`(int,默认 10000)

### P1 — M9 不做,carry 出去
| Carry 项 | 推到哪里 |
|----------|---------|
| 真 SMTP 选型(腾讯企业邮 / 阿里云邮件推送 / 自建) | M9 后 demo 决策点;代码已就绪 |
| token cost 真定价 + markup_x 真值 | M11(spawn/md 真消费才需要) |
| `plan='pro'` 付费升级流程 | M12 admin v2 |
| 真 `/api/me/proposals` 业务 | M12 |
| `quota_md_per_day` / `quota_spawn_concurrent` 列 | M11(实际用到时再 ALTER) |
| ledger 分页接口 | M12 admin `/api/admin/ledger` |

---

## §2 DB schema — `002_user_profile_billing.py`

```sql
-- 1. user_profiles
CREATE TABLE user_profiles (
  user_id        UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  research_field VARCHAR(256),
  affiliation    VARCHAR(256),
  expertise_level VARCHAR(256),
  projects       VARCHAR(2000),
  custom_intro   VARCHAR(2000),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. ledger
CREATE TABLE ledger (
  id            BIGSERIAL PRIMARY KEY,
  user_id       UUID NOT NULL REFERENCES users(id),
  amount_li     BIGINT NOT NULL,                  -- 正=入账, 负=消费
  kind          VARCHAR(32) NOT NULL,             -- 'signup_gift'|'topup'|'chat_in'|'chat_out'|'md_run'|'admin_adjust'
  ref_type      VARCHAR(32),                      -- 'spawn_task'|'md_job'|'chat_session'|null
  ref_id        VARCHAR(64),
  balance_after BIGINT NOT NULL,
  meta          JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ledger_user_created ON ledger(user_id, created_at DESC);
```

**不动**:
- `users.realname_verified_at`(001 timestamptz 保留)
- `users.plan`(001 default 'free' 保留)
- `users.balance_li`(001 已有 BIGINT NOT NULL DEFAULT 0,M9 用 SELECT FOR UPDATE 维护一致)

**downgrade**:DROP TABLE ledger + user_profiles(简单可逆)。

---

## §3 模块清单

### 3.1 新增文件

| 路径 | 说明 |
|------|------|
| `migrations/versions/002_user_profile_billing.py` | alembic revision,upgrade/downgrade 实现 §2 |
| `praxis2/accounting/__init__.py` | 空 |
| `praxis2/accounting/ledger.py` | `Ledger` class(接 asyncpg pool),`record()` / `recent()` / `get_balance()` |
| `tests/test_accounting_ledger.py` | ~10 case,见 §6 |
| `tests/test_auth_routes_v2_me.py` | ~10 case |
| `tests/test_auth_repository_pg_profile.py` | ~5 case |
| `tests/test_config_signup_gift.py` | ~3 case |

### 3.2 改动文件

| 路径 | 改动 |
|------|------|
| `praxis2/auth/repository_pg.py` | 加 `get_user_with_balance(user_id)` / `upsert_user_profile(user_id, fields)` / `get_user_profile(user_id)` / `get_balance_li(user_id)` |
| `praxis2/auth/routes.py` | `handle_me` 扩 11 字段;`handle_me_balance` 接 ledger;新 `handle_me_profile_get` / `handle_me_profile_post` / `handle_me_proposals_stub`;`handle_register` 末尾接 ledger.record;ROUTES 加 4 行 |
| `praxis2/config.py` | 加 `signup_gift_li: int = 10000` 字段 + env `PRAXIS_SIGNUP_GIFT_LI` 读取 |
| `praxis2/server/app.py` | M9 不动(auth routes 已经走 ROUTES dict 自动注册,新 endpoint 自然挂上) |
| `frontend/src/lib/api.ts` | `fetchMe()` 删 unwrap,直接返后端 `MeResponse`(11 字段对齐) |
| `frontend/src/types/api.ts` | 不动(types 本来就期望 11 字段,只是后端追上) |

### 3.3 不动文件
- `praxis2/auth/email.py`(SmtpEmailGateway 已写好,M9 不改)
- `praxis2/server/app.py`(`_routes` 不加,走 auth ROUTES merge)
- 任何 brain / agents / scheduler / runtime 文件
- frontend 其他组件(`fetchMe` 内部改,调用方代码不变,因 MeResponse shape 已对齐 FE types)

---

## §4 Endpoint 合约

### 4.1 `GET /api/me` → 200

```json
{
  "id": "uuid",
  "phone": null,
  "email": "alice@example.com",
  "display_name": "Alice",
  "role": "user",
  "plan": "free",
  "status": "active",
  "balance_li": 10000,
  "balance_yuan": "100.00",
  "realname_verified": false,
  "created_at": "2026-05-24T08:30:12+00:00"
}
```

- **不嵌套** `{user: {...}}`,取消 v2.0.1 兼容层
- 401 → `{"error":"unauthorized","reason":"未登录"}`
- `realname_verified` = `bool(realname_verified_at)`
- `created_at` ISO 8601 带时区
- `balance_yuan` 是 string("100.00"),Python `f"{li/100:.2f}"`

### 4.2 `GET /api/me/balance` → 200

```json
{
  "balance_li": 9800,
  "balance_yuan": "98.00",
  "recent": [
    {"id":12,"amount_li":-200,"kind":"chat_out","ref_type":"chat_session",
     "ref_id":"sess-xxx","balance_after":9800,"created_at":"2026-05-24T09:00:00+00:00","meta":null},
    {"id":1,"amount_li":10000,"kind":"signup_gift","ref_type":null,
     "ref_id":null,"balance_after":10000,"created_at":"2026-05-24T08:30:12+00:00","meta":null}
  ]
}
```

- recent 固定 20 条 DESC by created_at
- 用户刚注册(只有 signup_gift)→ recent 长度 1
- 完全空 ledger → recent: []

### 4.3 `GET /api/me/profile` → 200

```json
{
  "research_field": null,
  "affiliation": null,
  "expertise_level": null,
  "projects": null,
  "custom_intro": null,
  "updated_at": null
}
```

- 用户没填过 → 全 null + updated_at null(handler 不强制 upsert 空行)
- 填过 → 各字段取真值,updated_at ISO 8601

### 4.4 `POST /api/me/profile` → 200

**Request body**(任意子集,key 缺失 = 不改,null = 不改,空字符串 = 清空):
```json
{"research_field": "Structural Biology", "custom_intro": "..."}
```

**字段长度上限**(超出 400):
| 字段 | 最大字符 |
|------|---------|
| research_field | 256 |
| affiliation | 256 |
| expertise_level | 256 |
| projects | 2000 |
| custom_intro | 2000 |

**400 错误体**:
```json
{"error":"field_too_long","field":"projects","max":2000}
```

**成功 200**:返跟 §4.3 GET 同 shape(upsert 后最新值,updated_at 跟新)。

### 4.5 `GET /api/me/proposals` → 200(stub)

```json
{"proposals": [], "total": 0}
```

M12 接真业务时合约不变,只 proposals 数组填充。

### 4.6 `POST /api/auth/register`(已有,扩)

**Request body 不变**:`{email, code, password, display_name?}`

**Response body**:
```json
{
  "user": {"id":"uuid","email":"alice@...","display_name":"Alice"},
  "balance_li": 10000
}
```

`balance_li` 字段从 0 变 10000(若 env `PRAXIS_SIGNUP_GIFT_LI=10000`)。

**事务**:
```python
async with pool.acquire() as conn:
    async with conn.transaction():
        user_id = await repo.create_user(...)   # INSERT users (balance_li=0)
        if settings.signup_gift_li > 0:
            await ledger.record(
                conn, user_id, +settings.signup_gift_li,
                'signup_gift', None, None, {},
            )  # INSERT ledger + UPDATE users.balance_li
```

任一环节抛错,整事务回滚。

---

## §5 一致性 / 错误处理

### 5.1 ledger.record() 事务模式

```python
async def record(
    self, conn, user_id, amount_li, kind, ref_type, ref_id, meta,
) -> int:
    """返 balance_after。要求外层已开 transaction(便于跟 register 组合事务)。"""
    # 1. SELECT FOR UPDATE 锁 users 行
    cur = await conn.fetchval(
        "SELECT balance_li FROM users WHERE id=$1 FOR UPDATE", user_id,
    )
    if cur is None:
        raise LedgerError("user_not_found")
    new_balance = cur + amount_li
    if new_balance < 0:
        raise LedgerError("insufficient_balance")
    # 2. INSERT ledger
    ledger_id = await conn.fetchval(
        "INSERT INTO ledger (user_id,amount_li,kind,ref_type,ref_id,"
        "balance_after,meta) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id",
        user_id, amount_li, kind, ref_type, ref_id, new_balance, meta,
    )
    # 3. UPDATE users.balance_li
    await conn.execute("UPDATE users SET balance_li=$1 WHERE id=$2",
                       new_balance, user_id)
    return new_balance
```

**关键不变量**:
- 锁顺序:永远先锁 users 行(单行),不存在循环死锁
- balance_after 由后端算,不接受 client 上送
- amount_li 为 0 允许(no-op 但记录,便于审计)
- meta 是 dict → JSONB,asyncpg 自动 jsonable

### 5.2 profile upsert(动态 SET clause)

**语义**(对应 §4.4):
| 输入 | 处理 |
|------|------|
| 字段在 body 里缺失 | 不进 SET clause,DB 不动 |
| `"x": null` | 同上,不进 SET clause |
| `"x": ""` | handler 转 NULL,**进** SET clause(实现「清空」) |
| `"x": "value"` | 进 SET clause,长度校验过则存,否则 400 |

Handler 伪码:
```python
FIELDS = ('research_field','affiliation','expertise_level','projects','custom_intro')
MAX = {'research_field':256,'affiliation':256,'expertise_level':256,
       'projects':2000,'custom_intro':2000}
to_set = {}
for k in FIELDS:
    if k not in body or body[k] is None:
        continue   # 缺失 / null → 不动
    v = body[k]
    if not isinstance(v, str):
        return _json(send, 400, {"error":"field_invalid","field":k})
    if len(v) > MAX[k]:
        return _json(send, 400, {"error":"field_too_long","field":k,"max":MAX[k]})
    to_set[k] = None if v == "" else v   # 空串 → NULL(清空语义)
```

`to_set` 为空 → no-op(连 INSERT 都不发,GET 仍返全 null)。

`to_set` 非空 → 动态 SQL:
```python
cols = ", ".join(to_set.keys())
vals = ", ".join(f"${i+2}" for i in range(len(to_set)))
sets = ", ".join(f"{k} = EXCLUDED.{k}" for k in to_set.keys())
sql = (
  f"INSERT INTO user_profiles (user_id, {cols}, updated_at) "
  f"VALUES ($1, {vals}, now()) "
  f"ON CONFLICT (user_id) DO UPDATE SET {sets}, updated_at = now()"
)
await conn.execute(sql, user_id, *to_set.values())
```

**不**用 COALESCE,因为「缺失字段」根本不进 SET。EXCLUDED.x 必然是 handler 想存的值(可能是真 NULL = 清空)。

### 5.3 401 / 404 / 500 schema 对齐

| 状态 | body |
|------|------|
| 401 未登录 | `{"error":"unauthorized","reason":"未登录"}` |
| 404 用户不存在(soft-deleted etc) | `{"error":"user_not_found","reason":"..."}` |
| 400 字段超长 | `{"error":"field_too_long","field":"...","max":N}` |
| 500 内部 | `{"error":"internal","reason":"..."}`(由 ASGI 顶层 catch) |

### 5.4 realname_verified 计算

```python
# handle_me 内
"realname_verified": bool(row.realname_verified_at),
```

不动 DB schema。M12 admin 实名审核流程时,UPDATE `realname_verified_at = now()` 即可让 bool 翻 true。

### 5.5 balance_yuan 格式

```python
f"{balance_li / 100:.2f}"
```

- `balance_li=0` → `"0.00"`
- `balance_li=10000` → `"100.00"`
- `balance_li=-50` → `"-0.50"`(负值理论可能,前端显示「欠费」)
- 不用 decimal:int 除浮点再 :.2f 已足精度,且 li 单位下分币不丢

---

## §6 测试覆盖(目标新增 ~32 条,pytest 总数 ≥ 1575)

### 6.1 `tests/test_accounting_ledger.py`(~10)
- record_signup_gift_inserts_row_and_updates_balance
- record_consumption_negative_amount
- record_zero_amount_allowed
- record_insufficient_balance_raises
- record_unknown_user_raises
- recent_returns_desc_by_created_at
- recent_limit_20
- recent_empty_for_new_user
- concurrent_records_no_lost_update(asyncio.gather × 5)
- record_meta_json_roundtrip

### 6.2 `tests/test_auth_routes_v2_me.py`(~14)
- me_shape_11_fields(不嵌套)
- me_realname_verified_false_when_at_null
- me_realname_verified_true_when_at_set
- me_balance_yuan_format
- me_balance_returns_recent_20_desc
- me_balance_recent_empty
- me_profile_get_returns_nulls_when_empty
- me_profile_get_returns_values_after_upsert
- me_profile_post_field_too_long_400(每字段一例 = 5 个 sub case)
- me_profile_post_empty_string_clears
- me_profile_post_null_keeps
- me_proposals_stub_empty
- register_grants_signup_gift_li_when_env_10000
- register_no_gift_when_env_0

### 6.3 `tests/test_auth_repository_pg_profile.py`(~5)
- upsert_creates_row_when_absent
- upsert_partial_keeps_existing
- upsert_empty_string_clears
- get_profile_returns_none_when_absent
- get_profile_returns_dict_after_upsert

### 6.4 `tests/test_config_signup_gift.py`(~3)
- default_signup_gift_li_is_10000
- env_override_sets_value
- env_0_means_no_gift

---

## §7 Ship / 回滚

### 7.1 Ship 流程(M9 末尾)

```bash
# 1. 全测过
cd /Volumes/T7/clade-learn/PRAXIS-2
pytest -q tests/ -k "not integration" --ignore=tests/test_skills  # 1571+
ruff check praxis2/ tests/
cd frontend && npm run typecheck && VITE_API_BASE='' npm run build

# 2. staging migration(.53)
ssh zkyd@10.102.106.53 \
  'cd /home/zkyd/PRAXIS-2 && alembic upgrade head'  # → 002

# 3. backend restart
ssh zkyd@10.102.106.53 \
  'tmux send-keys -t praxis2-backend C-c && sleep 2 && \
   tmux send-keys -t praxis2-backend Enter'  # 自动重起 gunicorn(脚本里)

# 4. backend smoke
curl -s http://10.102.106.53:8001/api/info  # service=PRAXIS-2
curl -i http://10.102.106.53:8001/api/me     # 401 unauthorized

# 5. FE rebuild + rsync(后端 ± 30 min)
rsync -avz --delete frontend/dist/ \
  hipeson@10.102.106.40:/home/hipeson/mzy/PRAXIS-2/dist/

# 6. 浏览器手测:登录 → sidebar 用户名 + 余额「¥100.00」+ profile 填一次
open http://10.102.106.40:8080/

# 7. tag
git tag v0.10.0 && git push origin v0.10.0
```

**v1 链路始终不动**(`.40:8088` + `.40:PRAXIS/dist` + `.53:7788`)。

### 7.2 回滚(24h 内任意红牌触发)

| 红牌信号 | 回滚动作 |
|---------|---------|
| pytest 在 ship 后 staging 跑炸 | `alembic downgrade 001` + backend revert v0.9.6 + 重启 |
| FE 余额显示 NaN / 用户名空 | `fetchMe()` unwrap hack 恢复 + dist rebuild rsync |
| ledger 写入失败导致 register 卡 | backend revert + DB 不动(ledger 表空也不影响 register 旧路径) |
| `.40:8080` 反代 502 | `pkill praxis2_proxy.py` + 重起 |

**v1 不受影响**:`.40:8088` + `.53:7788` 全程不参与 M9 ship,回滚天然零风险传染。

### 7.3 估时(SMTP 砍 0.5d 后)

| 子任务 | 估时 |
|---|---|
| 002 migration + repo 4 个方法 + 测试 | 0.5 d |
| accounting/ledger.py + 测试 | 1 d |
| 4 个 /api/me/* handler + 测试 | 1 d |
| Config env + register 接 ledger + 测试 | 0.5 d |
| FE adapter 删除 + rebuild + smoke | 0.5 d |
| staging ship + tag | 0.5 d |
| **合计** | **4 d** |

---

## §8 不在 M9 做的事(避免范围蔓延)

- 不接真 SMTP(env 不配 = DevEmailGateway,dev_code 回显)
- 不改 `praxis2/auth/email.py`
- 不动 brain / agents / scheduler / runtime
- 不加 `quota_md_per_day` / `quota_spawn_concurrent`(M11)
- 不接 `/api/admin/users` / `/api/admin/ledger`(M12)
- 不做 token cost 真定价(M11 spawn/md 才需要)
- 不引入新 chat-stream 路径
- 不删 `/admin/review/*` legacy(老 staging 兼容)
- 不动 v1 任何东西

---

## §9 关联文档

- 上游路线图(repo 内副本):[`PRAXIS-2-计划-v2-完整重写-路线图.md`](../../../PRAXIS-2-计划-v2-完整重写-路线图.md) §5
- 上游路线图(外层 `/Volumes/T7/clade-learn/` 副本同内容,两份同步)
- M13 推迟约束(memory):`project_m13_deferred.md`
- v2.0.1 / v2.0.2 上线状态:`PRAXIS-2/VERSION-STATUS-*.md`
- 后续 milestone:M10 agents/profile + files、M11 spawn/md/HPC、M12 admin v2 + proposals
