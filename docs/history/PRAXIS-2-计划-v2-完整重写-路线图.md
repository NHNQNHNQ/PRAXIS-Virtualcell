# PRAXIS-2 v2 完整重写路线图 — M9 → M13(单 backend / Claude Code-style PRAXIS 框架基底)

> 起草:2026-05-24
> 决策上下文:用户已选 **方案 C(PRAXIS-2 完整重写,关停 v1)**,**先单 backend 实例**(不做 .53A/.53B 双活),
> 公网上云是 v3 远期(腾讯云 CLB + 多机集群)。
> 后端**沿用基于 Claude Code 设计的 PRAXIS framework**(`core/query.py` 主循环 + tools/registry + ASK 流 + brain memory),
> M9-M13 主要是**把 v1 那 25+ 个 `/api/*` endpoint 在 PRAXIS-2 内重新实现**,而**不是**改 agent 内核。
> 替代:[PRAXIS-2-计划-v2.1-部署-反代统一.md](./PRAXIS-2-计划-v2.1-部署-反代统一.md)(那个是方案 B,留作退路)
> 兼容:[PRAXIS-2-v1.x-API-parity-移交.md](./PRAXIS-2-v1.x-API-parity-移交.md)(它的 M9-M12 大纲就是本文的展开)

---

## §0 决策摘要

| 维度 | 决策 |
|---|---|
| **路径** | C 完整重写(PRAXIS-2 backend 自身扩到 v1 全集) |
| **实例** | PRAXIS-2 backend 在 `.53:8001`;**v1 `.53:7788` 保留运行**(M13 关停**无限期推迟**,需「完整测试 + 显式用户决策」才触发) |
| **入口** | **双端口并存**:`.40:8088` 维持 v1 入口(老 server.py → `.53:7788`),`.40:8080` 维持 v2 入口(praxis2_proxy.py → `.53:8001`)。M13 触发前**不夺端口、不切单 upstream**。 |
| **前端 dist** | PRAXIS-2 `frontend/` v2.0.1 build,**逐版迭代**(每个 M 加 1 个 UI 校准);v1 dist 不动 |
| **agent 内核** | **不动** Claude Code-style `core/query.py` + `agents/loader.py` + `brains/`;新 endpoint 是 CRUD + 调度,不是新 agent 模式 |
| **数据库** | 单 PG `.53`,**v2 自己的库**;v1 库继续承载在线用户(M13 触发前**不迁移**) |
| **节奏** | M9-M12 共 ~25.5 工作日(~5 周)到 v2 完整 parity;M13(关 v1)**不在本路线时间窗内**,触发条件见 §9 |
| **上云** | v3+ 才做,本路线只留**腾讯云迁移钩子**(同 [v2.1 §11](./PRAXIS-2-计划-v2.1-部署-反代统一.md#§11-未来:云上反代-+-多后端集群(v3+-前瞻))) |

---

## §1 v1 → v2 API gap 矩阵(目标态:全部命中 v2)

> 来源:对 `.40:8088` 老 dist `index-ygWsFD2p.js` 的 `grep -oE '"/api/[^"]+"'` 全集 + v1 后端 `/api/info` 探测。
> 同 [v2.1 §0.2](./PRAXIS-2-计划-v2.1-部署-反代统一.md#02-能力覆盖矩阵)。

| 类目 | endpoint | v1 ✅ | v2 现状 | 落在哪个 M | PRAXIS 框架钩点 |
|------|----------|:----:|:------:|:---------:|----------------|
| **chat** | `POST /api/chat-stream` | ✅ | ✅ | — | `core/query.py` + `server/app._chat_stream` |
| | `POST /chat/permission` | ✅ | ✅ | — | `server/permission_bridge.PendingPermissionRegistry` |
| **info/agents** | `GET /api/info` | ✅ | ✅ | M10 校 schema | `auth/routes.handle_info` |
| | `GET /api/agents` | ✅ | ✅(v2.0.1) | M10 校 examples | `server/app._api_agents` |
| | `GET /api/agents/profile` | ✅ | ❌ | **M10** | brains 索引 + system_prompt 摘要 |
| **auth** | `POST /api/auth/login` | ✅ | ✅ | — | `auth/routes.handle_login` |
| | `POST /api/auth/register` | ✅ | ✅ | — | 同 |
| | `POST /api/auth/logout` `/logout-all` | ✅ | ✅ | — | 同 |
| | `POST /api/auth/email/send-code` | ✅(sms) | ✅(email) | M9 真 SMTP | `auth/email.SmtpEmailGateway`(M9 接) |
| **me** | `GET /api/me` | ✅ | ⚠ shape 偏差 | **M9** | `auth/routes.handle_me`(扩 balance/plan/status) |
| | `GET /api/me/balance` | ✅ | ✅ stub | **M9** | 新 `accounting/ledger.py` |
| | `GET /api/me/profile` `POST /api/me/profile` | ✅ | ❌ | **M9** | 新 `auth/profile.py` |
| | `GET /api/me/proposals` | ✅ | ❌ | M12 | 新 `proposals/repo.py` |
| | `DELETE /api/me/account` | ✅ | ✅ | — | — |
| **spawn**(后台任务) | `POST /api/spawn` | ✅ | ❌ | **M11** | `runtime/tasks.TaskState` + `runtime/parallel` + 新 `tasks/store.py` |
| | `GET /api/spawn/list` | ✅ | ❌ | M11 | 同 |
| | `GET /api/spawn/get/{id}` | ✅ | ❌ | M11 | 同 |
| **md**(分子动力学) | `POST /api/md/submit` | ✅ | ❌ | **M11** | `scheduler/hpc_submit.py` + brain `md` skills |
| | `GET /api/md/runs` | ✅ | ❌ | M11 | 同 |
| | `GET /api/md/jobs/{id}` | ✅ | ❌ | M11 | 同 |
| | `POST /api/md/jobs/{id}/cancel` | ✅ | ❌ | M11 | 同 |
| | `GET /api/md/jobs/{id}/children` | ✅ | ❌ | M11 | 同(replicas) |
| | `GET /api/md/gpu-pool` | ✅ | ❌ | M11 | 新 `scheduler/gpu_pool.py`(nvidia-smi over ssh) |
| **files** | `GET /api/files` `POST /api/files` `DELETE /api/files/{id}` | ✅ | ❌ | **M10** | 新 `files/repo.py` + 本地 fs / S3 抽象 |
| | `GET /api/files/usage` | ✅ | ❌ | M10 | 同 |
| **proposals** | `POST /api/proposals` `GET /api/proposals` | ✅ | ❌ | **M12** | 新 `proposals/` 子包 + admin 决策流 |
| | `GET /api/admin/proposals` `POST /api/admin/proposals/{id}/decide` | ✅ | ❌ | M12 | 同 + brain ship_to 路由 |
| **admin v2** | `GET /api/admin/users` | ✅ | ❌ | **M12** | `auth/repository_pg.py` 已 list_users 接口位 |
| | `POST /api/admin/users/{id}/{adjust,freeze,unfreeze}` | ✅ | ❌ | M12 | 同 + `accounting/ledger` |
| | `GET /api/admin/ledger` `GET /api/admin/audit-log` | ✅ | ❌ | M12 | 同 |
| | `GET /api/admin/stats` `POST /api/admin/reconcile` | ✅ | ❌ | M12 | 同 |
| | `* /api/admin/review/*` | ❌ | ✅ | — | M5 已有,**v1 独缺** |
| **storage** | `GET /api/storage/biggest` `GET /api/storage/trajectories` | ✅ | ❌ | M11 | files + md 派生 view |

**统计**:已实现 10 / 待实现 25 / v2 独有 4(admin/review × 3 + agents)。

---

## §2 PRAXIS Claude Code-style 框架现状(给所有 milestone 用)

> M9-M13 都跑在这个框架之上,新 endpoint **绝不**改下面的核心,只**调用 / 扩展**它们。

### 2.1 Claude Code-style 主循环(`praxis2/core/query.py`)

```
state(messages, phase, recovery_attempts, ...)
    │
    ├─ client.stream_messages(model, system, tools)   ← Anthropic-like streaming
    │       │
    │       ├─ yield {type:"text", text:"..."}          → SSE text_delta
    │       ├─ yield {type:"tool_use", id, name, input} → SSE tool_start
    │       └─ yield {type:"message_stop", stop_reason}
    │
    ├─ runner.run_tools(tool_use_blocks)               ← SerialToolRunner + Permission
    │       │
    │       ├─ permission.check_or_ask()                → SSE control_request / 等回包
    │       └─ tool.execute()                           → yield tool_result → SSE tool_end
    │
    ├─ append assistant + tool_result 到 state.messages
    └─ 回到顶,直到 message_stop=end_turn or recovery_budget 耗尽
```

**关键**(已在 v2.0.1 验证):
- SSE 事件名 = `text_delta/tool_start/tool_end/tool_progress/phase_change/compact_boundary/control_request/control_cancel_request/auth_status/final/error/queue_position/stream_event`
- event_id 单调递增(`runtime/pubsub.InMemoryEventBus` 维护,Redis 版接口位 M11 落地)
- replay 支持 Last-Event-ID(M6 已落)

### 2.2 5 模式 agent 路由(`praxis2/agents/loader.py`)

```python
spec → AgentSelection(mode, brain_slugs, is_discipline, readonly, max_turns)

discipline      → 12 学科之一,brain_slugs=[_common, <slug>],is_discipline=True(禁递归 AgentTool)
general         → brain_slugs=[_common, general]
one-above-all   → 关键词打分选 1 个 + _common(max_turns≤5)
yourself        → 多个相关 brain + _common,readonly(不写回)
bare            → 仅 _common
```

**对新 endpoint 的影响**:
- `/api/spawn` 接受 `agent` 字段时仍走 `resolve_agent(spec)`,**异步**调 `query()`(下文 §7.3)
- `/api/md/submit` **不走 agent 路由**(它是直接调度 MD job,与 chat 是平行通道),但其 spec 在 chat 模式由 brain `md` 的 skill 推荐
- `/api/agents/profile` 直接读 brain 索引(case_count/rule_count/skill_workflows),不调 query

### 2.3 brains 大脑结构(每学科)

```
brains/<slug>/
├── PRAXIS-<X>-AGENT-PROMPT.md    ← runtime system prompt(被 build_chat_system_prompt 装进)
├── memory/
│   ├── cases/                    ← 正例(BM25+vector 检索)
│   ├── neg_cases/                ← 反例(避坑)
│   └── rules/                    ← 硬/软规则
├── skills/workflows/<x>/         ← 真可执行能力
│   ├── SKILL.md                  ← 必须有(枚举到 ToolRegistry)
│   └── run.py                    ← 真 CLI/真 API(无 run.py = N/A,prompt-only)
└── schemas/                      ← 输入输出 JSON Schema
```

**`/api/agents/profile` 的数据来源**(M10 实现):
- 直接 `os.walk brains/<slug>/`,read SKILL.md frontmatter
- 不查 PG,纯文件系统
- 缓存 60s(brains 不常变,改了会重启)

### 2.4 Permission ASK 流(`praxis2/server/permission_bridge.py`)

```
tool.execute() → permission.check() → 默认 ALLOW
                                     → ASK: emit_sse control_request → 阻塞等 /chat/permission POST → resume
                                     → DENY/forbidden(tenant 不匹配,M9 已锁)
```

**对新 endpoint 的影响**:
- `/api/spawn` 后台任务**默认 ALLOW**(用户已显式 spawn,不需要再 ASK)
- 但若用户在 `/api/spawn` 配置里要求 strict,可注入 BridgePermissionAdapter,**结果落到 task table 的 `pending_permission` 字段**(无 SSE 通道,需要前端轮询)

### 2.5 SessionPool + State(`praxis2/runtime/session_pool.py`)

- 同 `(user_id, session_id)` 复用一个 State(messages 跨请求保留)
- LRU + idle_ttl 自动驱逐
- **/api/spawn 不复用此池**(spawn 是独立 task,跑完即销),M11 引入独立 `task_pool`

### 2.6 ResourceGate 5 分支(`praxis2/scheduler/resource_gate.py`)

```python
class GateBehavior:
    SUBMIT_NOW     # 配额 + 资源都够
    ENQUEUE        # 放队列(返 ETA)
    DOWNSCALE      # 给降配建议
    CPU_FALLBACK   # GPU→CPU
    REJECT         # 全队列满 + 不可退
```

**对新 endpoint 的影响**:
- `/api/md/submit` **必经** ResourceGate(M11 接 GPU pool 状态)
- `/api/spawn` 走轻量 gate(只查 max_concurrent_per_user)

### 2.7 已有的 Task 状态机(`praxis2/runtime/tasks.py`)

```
pending → queued → submitted(M7 重算力)→ running → completed/failed/killed/timeout
```

**M11 直接复用**:`SpawnTask` 与 `MdJob` 都是这个状态机的实例,只是 metadata 不同。

### 2.8 HPC 提交端(`praxis2/scheduler/hpc_submit.py`)

- `InMemoryHPCBackend`:dev/test
- `AsyncSSHBackend`:接口位,需 asyncssh,**M11 真接通**到 `bio000070`
- `HPCAccount` StrEnum:`SCW6CHB`(GPU 包月)/`scw6chb`(CPU 按需) **严区分大小写**(总纲 §11.7)

### 2.9 配额(`praxis2/scheduler/quota.py`)

- 全局并发 / 全局队列长度 / 每用户重算力配额
- **M11 接 /api/md/submit 时此值要可调**(从 PG users 表的 `quota_*` 列读,M9 加列)

---

## §3 部署目标拓扑(单 backend,本路线终态)

> ⚠️ 本拓扑是 **M13 完成后**的终态。**M9-M12 期间 v1 链路全程冻结**:
> `.40:8088`(老 `PRAXIS/server.py`)+ `.40:/home/hipeson/mzy/PRAXIS/dist` +
> `.53:7788`(PRAXIS-hou v0.1.0)整条链路**不动**,在线用户继续走 v1。
> v2 改动只在 `.40:8080` + `PRAXIS-2/dist` + `.53:8001` 上做(本机源码 → 推 dist + 推 proxy)。
> **M13 才执行**:v1 PG snapshot → 关 `.53:7788` 进程 → 反代切单 upstream → 夺 `.40:8088` 端口 →
> 老 dist 改名归档(详见 §9.1 checklist)。

```
公网 / 内网

┌──────────────────────────────────────────────────────────────────┐
│  .40  hipeson@10.102.106.40                                      │
│                                                                  │
│  :8088  python3 server.py (PRAXIS-proxy/0.3)                     │
│         dist  = /home/hipeson/mzy/PRAXIS-2-fe/dist               │
│         反代   /api/*  /chat/permission  → http://10.102.106.53:8001
│         (静态 SPA fallback for 其余 GET)                          │
│                                                                  │
│  (老 :8080 / 老 PRAXIS/server.py 都已停)                          │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│  .53  zkyd@10.102.106.53                                         │
│                                                                  │
│  :8001  gunicorn praxis2.server.app:make_app_default             │
│         workers = 2  (per CPU 数,M8 已基线)                      │
│         tmux session: praxis2-backend                            │
│                                                                  │
│  postgres  docker praxis2-pg:5432                                │
│            DB: praxis2  user: praxis2                            │
│            表:users / sessions / email_codes / audit_log         │
│                + spawn_tasks / md_jobs / files / proposals       │
│                + ledger / user_profiles  (M9-M12 新增)            │
│                                                                  │
│  redis     docker praxis2-redis:6379                             │
│            DB 0: session 缓存 + rate_limit 计数                   │
│            DB 1: EventBus pubsub(M11 替换内存版)                  │
│            DB 2: spawn task progress 缓存                         │
│                                                                  │
│  litellm   :4000(已部署),proxy 到 AWS Claude / DeepSeek        │
│                                                                  │
│  (v1 :7788 在 M9 完成 + 数据迁移决策后**关停**;tmux session 杀;  │
│   /home/zkyd/PRAXIS-hou/ 留 6 个月归档)                           │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ↓
┌──────────────────────────────────────────────────────────────────┐
│  HPC bio000070(M11 接通)                                         │
│   AsyncSSHBackend over asyncssh                                  │
│   提账户:SCW6CHB (GPU 包月) / scw6chb (CPU 按需)                  │
│   作业脚本生成走 brains/md/skills/workflows/gmx_simulate/run.py   │
└──────────────────────────────────────────────────────────────────┘
```

**单 backend 即终态**(本路线范围内):
- 不做 .53A/.53B 主备 / active-active
- 不做 nginx / HAProxy(`.40` 仍是 stdlib python server.py)
- 不做 systemd unit(tmux 已足够 staging)

---

## §4 数据模型(PG schema 完整建模)

> 命名:tables 复数 / 字段 snake_case / 主键 uuid / 时间戳带时区 / 软删 deleted_at。
> Migration:`alembic` revision 自 001 接续。

### 4.1 已有(001_initial_auth.py 已落)

```sql
users (
  id            uuid PK,
  email         text unique NOT NULL,
  phone         text,
  password_hash bytea NOT NULL,
  display_name  text,
  role          text NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
  status        text NOT NULL DEFAULT 'active', -- 'active' | 'frozen' | 'deleted'
  balance_li    bigint NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_login_at timestamptz,
  deleted_at    timestamptz
);
email_codes (id, email, code, purpose, expires_at, used_at, attempts);
audit_log (id, user_id, actor, action, resource, resource_id, ip, ua, meta jsonb, created_at);
```

### 4.2 M9 新增 — 用户中心 / 计费

```sql
-- 002_user_profile_billing.py
ALTER TABLE users ADD COLUMN plan text NOT NULL DEFAULT 'free';   -- 'free' | 'pro'
ALTER TABLE users ADD COLUMN realname_verified bool NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN quota_md_per_day int NOT NULL DEFAULT 3;
ALTER TABLE users ADD COLUMN quota_spawn_concurrent int NOT NULL DEFAULT 2;

CREATE TABLE user_profiles (
  user_id        uuid PK REFERENCES users(id) ON DELETE CASCADE,
  research_field text,
  affiliation    text,
  expertise_level text,
  projects       text,
  custom_intro   text,
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ledger (
  id            bigserial PK,
  user_id       uuid NOT NULL REFERENCES users(id),
  amount_li     bigint NOT NULL,                  -- 正=入账,负=消费
  kind          text NOT NULL,                    -- 'signup_gift' | 'topup' | 'chat_in' | 'chat_out' | 'md_run' | 'admin_adjust'
  ref_type      text,                             -- 'spawn_task' | 'md_job' | 'chat_session'
  ref_id        text,
  balance_after bigint NOT NULL,
  meta          jsonb,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_ledger_user_created ON ledger(user_id, created_at DESC);
```

### 4.3 M10 新增 — 文件管理

```sql
-- 003_files.py
CREATE TABLE files (
  id          uuid PK DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id),
  filename    text NOT NULL,
  size_bytes  bigint NOT NULL,
  mime        text,
  purpose     text,                                -- 'pdb' | 'config' | 'report' | 'other'
  storage_key text NOT NULL,                       -- 本地 fs path 或 S3 key
  created_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);
CREATE INDEX ix_files_user_purpose ON files(user_id, purpose) WHERE deleted_at IS NULL;
```

### 4.4 M11 新增 — spawn 任务 + MD 作业

```sql
-- 004_tasks_md.py
CREATE TABLE spawn_tasks (
  id            uuid PK DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES users(id),
  agent         text NOT NULL,                     -- 'general' | <discipline> | ...
  model         text NOT NULL,
  label         text,
  message       text NOT NULL,
  status        text NOT NULL DEFAULT 'starting', -- starting|running|done|error|timeout|cancelled
  answer        text DEFAULT '',
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  exit_code     int,
  in_tokens     bigint DEFAULT 0,
  out_tokens    bigint DEFAULT 0,
  timeout_s     int NOT NULL DEFAULT 1800,
  cost_li       bigint DEFAULT 0,
  meta          jsonb
);
CREATE INDEX ix_spawn_user_started ON spawn_tasks(user_id, started_at DESC);

CREATE TABLE md_jobs (
  id                uuid PK DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id),
  parent_id         uuid REFERENCES md_jobs(id),       -- replicas/ensemble 父子
  replica_index     int,
  n_replicas        int,
  dispatch_strategy text NOT NULL DEFAULT 'single',    -- single|replicas|remd|fep|ensemble
  simulation_type   text NOT NULL DEFAULT 'standard',  -- standard|cg_martini|smd_pulling|metadynamics|umbrella
  structure         text NOT NULL,                     -- PDB id 或 file id
  force_field       text NOT NULL,
  water_model       text NOT NULL,
  ensemble          text NOT NULL,                     -- NPT | NVT
  temperature_k     real NOT NULL,
  time_ns           real NOT NULL,
  timestep_fs       real NOT NULL,
  notes             text,
  status            text NOT NULL DEFAULT 'queued',    -- 同 TaskState
  hpc_account       text,                              -- 'SCW6CHB' | 'scw6chb'
  hpc_job_id        text,
  gpu_host          text,
  gpu_id            int,
  progress          real DEFAULT 0,
  artifacts         jsonb,                             -- [{name,size_bytes,remote_path,remote_host}]
  cost_li           bigint DEFAULT 0,
  error             text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  started_at        timestamptz,
  finished_at       timestamptz
);
CREATE INDEX ix_md_user_created ON md_jobs(user_id, created_at DESC);
CREATE INDEX ix_md_parent ON md_jobs(parent_id) WHERE parent_id IS NOT NULL;
```

### 4.5 M12 新增 — 提案 / 审计补充

```sql
-- 005_proposals.py
CREATE TABLE proposals (
  id             uuid PK DEFAULT gen_random_uuid(),
  user_id        uuid NOT NULL REFERENCES users(id),
  kind           text NOT NULL,                     -- 'case' | 'rule' | 'skill' | 'fix' | 'feature'
  title          text NOT NULL,
  body           text NOT NULL,                     -- markdown
  status         text NOT NULL DEFAULT 'pending',   -- pending|approved|rejected|shipped|hold
  admin_verdict  text,
  admin_scores   jsonb,                             -- {accuracy: 5, novelty: 4, ...}
  shipped_to     text,                              -- brain slug:case_id
  decision_note  text,
  decided_at     timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_proposals_user_created ON proposals(user_id, created_at DESC);
CREATE INDEX ix_proposals_status ON proposals(status, created_at DESC);
```

---

## §5 M9 — 用户中心扩展 + 真 SMTP(~1.5 周)

### 5.1 范围

| Endpoint | Method | 行为 | 备注 |
|---|---|---|---|
| `/api/me` | GET | 扩 plan/status/balance_yuan/realname_verified/created_at 字段 | shape 对齐 FE `MeResponse`(去掉 v2.0.1 适配 hack) |
| `/api/me/balance` | GET | 返 balance_li/balance_yuan + 最近 20 条 ledger | 已 stub,M9 接真 ledger |
| `/api/me/profile` | GET | 返 user_profiles 一行 | 新表 |
| `/api/me/profile` | POST | upsert user_profiles | 同 |
| `/api/auth/email/send-code` | POST | 真 SMTP 发码,关 DevGateway dev_code 回显 | env: `PRAXIS_SMTP_*` 全配 |

### 5.2 实现要点

- **`auth/repository_pg.py` 扩**:
  - `get_user_with_balance(user_id) → UserWithBalance`(JOIN ledger 取 sum 或读 cached balance_li)
  - `list_user_profile(user_id)` / `upsert_user_profile(user_id, **fields)`
- **`accounting/ledger.py`**(新):
  - `record(user_id, amount_li, kind, ref_type, ref_id, meta) → balance_after`
  - 写 ledger 原子 + 更新 users.balance_li(单事务)
  - 注册赠送:M9 加 `signup_gift_li=5000` 在 register 末尾 record
- **`auth/email.py` 扩**:
  - `SmtpEmailGateway` 已是接口位,M9 完整化:`aiosmtplib` async 发,模板用 `string.Template`
  - 配错时 dev fallback(env `PRAXIS_SMTP_HOST=""` → 仍走 DevGateway)
- **`/api/me/profile` handler**:
  - 字段 5 列全选填,前端期望 string|null,**不允许** schema 偏差
- **删** v2.0.1 在 `frontend/src/lib/api.ts:fetchMe()` 里的 unwrap hack(M9 后端真返平铺 shape)

### 5.3 测试

```
tests/test_auth_routes_v2_me.py          ← 4 个新 case:me_shape / balance_ledger / profile_get_post / signup_gift
tests/test_accounting_ledger.py          ← record() 单元,事务原子,balance_after 一致
tests/test_auth_email_smtp.py            ← 接 fake smtp,模板渲染,失败 fallback
tests/integration/test_m9_smtp_real.py   ← 标 @pytest.mark.integration,需 PRAXIS_INTEGRATION=1 + 真 SMTP
```

### 5.4 上线判据

- pytest 全过(基线 1543 + 新增 ~30,**1570+**)
- staging 真 SMTP 验:`curl -X POST /api/auth/email/send-code -d '{"email":"...","purpose":"register"}'` → 真邮件到达
- `/api/me` 不再嵌套(FE adapter 删掉 typecheck 仍过 = 验通)

### 5.5 时间表

| 子任务 | 估时 |
|---|---|
| 002 migration + repo 扩 | 0.5 d |
| accounting/ledger.py + 测试 | 1 d |
| /api/me + /api/me/balance + /api/me/profile | 1 d |
| SmtpEmailGateway + 测试 | 1 d |
| FE adapter 删除 + 验证 | 0.5 d |
| staging 上线 + smoke | 0.5 d |
| **合计** | **4.5 d** |

---

## §6 M10 — agents/profile + 文件管理(~1 周)

### 6.1 范围

| Endpoint | Method | 行为 |
|---|---|---|
| `/api/agents/profile` | GET | 返 12 学科 brain 的完整资料卡(name/desc/cases/rules/workflows/sample_cases) |
| `/api/files` | GET | 当前用户的文件列表(可按 purpose 过滤) |
| `/api/files` | POST | 上传(multipart/form-data),返 file id |
| `/api/files/{id}` | DELETE | 软删 |
| `/api/files/usage` | GET | 已用空间 / 配额 / max_per_file |

### 6.2 实现要点

- **`brains/store.py` 扩**:`load_agent_profile(slug) → dict`(walk brains/<slug>/,统计 cases/rules/skills,读 sample_cases 标题)
  - 60s 内存缓存(brains 不常变,改了重启 backend)
- **`files/repo.py`**(新):CRUD against `files` 表 + 真存储
  - 默认本地 fs:`PRAXIS_FILES_ROOT=/home/zkyd/data1/praxis2-files/<user_id>/<file_id>`
  - 配额每用户默认 5 GB(env `PRAXIS_FILES_QUOTA_BYTES`),max_per_file 100 MB
  - S3 接口位预留(`files/store_s3.py` stub,v3 接腾讯云 COS)
- **multipart 处理**:用 stdlib `email.parser.BytesParser` + `cgi.FieldStorage`(虽 deprecated 但 stdlib),或 `python-multipart` 包 — **倾向后者**(asgi 生态标准,M10 加依赖)
- **流式上传**:不 buffer 整个文件到内存,5 GB upload 真过(老 v1 上限是 5 GB,M10 对齐)

### 6.3 安全

- 文件名 `secure_filename`(去 path traversal `..`,只留 `[A-Za-z0-9._-]`)
- mime 由后端 sniff(`python-magic` 或简单魔数表),不信任 client 上送
- 下载 url 走 `/api/files/{id}/content`(M10.5 carry,先用 storage_key 直读 fs)

### 6.4 测试

```
tests/test_brains_profile_loader.py        ← 12 学科 profile 全返,字段完整,case_count 正确
tests/test_files_repo.py                   ← CRUD + 配额 + soft_delete
tests/test_files_routes.py                 ← upload 1 KB / 1 MB / 100 MB 三档,配额拒
tests/test_files_security.py               ← path traversal 试探 / mime sniff
```

### 6.5 时间表

| 子任务 | 估时 |
|---|---|
| 003 migration + files/repo.py | 1 d |
| files routes + multipart 处理 | 1.5 d |
| /api/agents/profile + brain loader | 1 d |
| 配额 / 安全 / 测试 | 1.5 d |
| **合计** | **5 d** |

---

## §7 M11 — spawn 后台任务 + MD 重算力闭环(~2 周)

### 7.1 范围 — spawn

| Endpoint | Method | 行为 |
|---|---|---|
| `/api/spawn` | POST | 派发后台 chat 任务,立返 task_id |
| `/api/spawn/list` | GET | 当前用户的 spawn 任务列表(最近 50) |
| `/api/spawn/get/{id}` | GET | 单任务详情 |

### 7.2 范围 — MD

| Endpoint | Method | 行为 |
|---|---|---|
| `/api/md/submit` | POST | 派发 MD 作业,经 ResourceGate + AsyncSSHBackend |
| `/api/md/runs` | GET | 当前用户的 md_jobs 列表 |
| `/api/md/jobs/{id}` | GET | 单作业详情(含 artifacts 列表) |
| `/api/md/jobs/{id}/cancel` | POST | scancel + 状态切 killed |
| `/api/md/jobs/{id}/children` | GET | replicas 子任务 |
| `/api/md/gpu-pool` | GET | 实时 GPU 占用(ssh nvidia-smi) |

### 7.3 spawn 实现要点(重点)

**Spawn 在 PRAXIS framework 上的钩入方式**:

```python
# praxis2/server/routes/spawn.py
async def handle_spawn_submit(scope, receive, send, deps):
    user = scope["user"]
    body = await _read_body(receive)

    # 1. ResourceGate 闸 (light path, 不查 GPU)
    decision = light_gate.acquire(user["user_id"], cost=ResourceCost.LIGHT)
    if decision is REJECT:
        return _json(send, 429, {"error": "quota_exceeded"})

    # 2. 入 PG → spawn_tasks 状态 = starting
    task = await deps.repo.create_spawn_task(
        user_id=user["user_id"],
        agent=body["agent"], model=body.get("model"),
        message=body["message"], label=body.get("label"),
        timeout_s=body.get("timeout", 1800),
    )

    # 3. 起异步 task,**不等结果**返 task_id
    asyncio.create_task(_run_spawn(task.id, body, deps))
    return _json(send, 200, {
        "task_id": str(task.id), "status": "starting", "label": task.label,
    })


async def _run_spawn(task_id, body, deps):
    """后台运行,reuse Claude Code-style query()。"""
    try:
        await deps.repo.update_spawn_status(task_id, "running")
        selection = resolve_agent(body["agent"], user_query=body["message"])
        st = State()  # spawn 不复用 SessionPool(独立短命任务)
        st.messages.append({"role": "user", "content": body["message"]})

        reg = build_chat_registry(selection=selection)
        runner = SerialToolRunner(reg, recovery_budget=3,
                                  permission=AllowAllPermission())   # spawn 默认 ALLOW
        client = AnthropicClient(api_key=deps.api_key, base_url=deps.base_url)
        system = build_chat_system_prompt(selection, body["message"])

        answer_buf = []
        in_tok = out_tok = 0
        async for ev in query(st, client=client, registry=reg, settings=deps.settings,
                              runner=runner, compactor=MinimalCompactor(),
                              system=system or None):
            if ev["type"] == "text":
                answer_buf.append(ev["text"])
                out_tok += len(ev["text"]) // 4   # rough,精确接 tokenizer
                # 每 10 chunk 写一次 DB,前端轮询拿到 partial answer
                if len(answer_buf) % 10 == 0:
                    await deps.repo.update_spawn_answer(task_id, "".join(answer_buf))

        final_answer = "".join(answer_buf)
        await deps.repo.complete_spawn_task(task_id,
            answer=final_answer, status="done", in_tokens=in_tok, out_tokens=out_tok)

        # 计费:消费 ledger
        cost_li = _calc_cost(in_tok, out_tok, deps.settings.pricing)
        await deps.ledger.record(task.user_id, amount_li=-cost_li,
            kind="chat_out", ref_type="spawn_task", ref_id=str(task_id))
    except asyncio.TimeoutError:
        await deps.repo.complete_spawn_task(task_id, status="timeout")
    except Exception as e:
        await deps.repo.complete_spawn_task(task_id, status="error", error=repr(e))
```

**关键约束**:
- spawn task 在**同一 backend 进程**异步跑(用 `asyncio.create_task`),**不**开 subprocess(避免 v1 的 ~1 GB/req 内存模型)
- 长任务靠 redis lock 或 PG row lock 防双 worker 抢同 task(M11.2 carry,先单 worker)
- timeout 由 `asyncio.wait_for(..., timeout=task.timeout_s)` 包住 query()
- progress 不发 SSE(spawn 无 SSE 通道),前端**轮询** `/api/spawn/get/{id}` (默认 2s)

### 7.4 MD 实现要点

**MD 在 PRAXIS framework 上的钩入方式**:

```python
# praxis2/server/routes/md.py
async def handle_md_submit(scope, receive, send, deps):
    user = scope["user"]
    body = await _read_body(receive)

    # 1. 资源闸:重算力 path
    cost = ResourceCost(gpu_hours=body["time_ns"] * 0.01, cpu_cores=4, ram_gb=16)
    decision = deps.resource_gate.acquire(user["user_id"], cost=cost)
    if decision.behavior == GateBehavior.REJECT:
        return _json(send, 429, {"error": "global_queue_full"})
    if decision.behavior == GateBehavior.DOWNSCALE:
        return _json(send, 409, {"error": "downscale_required",
                                  "suggestion": decision.suggestion})

    # 2. 入 PG → md_jobs 状态 = queued
    job = await deps.repo.create_md_job(
        user_id=user["user_id"],
        **body,
        status="queued", hpc_account=body.get("hpc_account", "SCW6CHB"),
    )

    # 3. 后台真投 HPC(asyncio.create_task)
    asyncio.create_task(_dispatch_md(job.id, body, deps))
    return _json(send, 200, {
        "id": str(job.id), "status": "queued", "created_at": job.created_at.isoformat(),
        "dispatch_strategy": body.get("dispatch_strategy", "single"),
        "n_replicas": body.get("n_replicas", 1),
    })


async def _dispatch_md(job_id, body, deps):
    """跑 brains/md/skills/workflows/gmx_simulate 的 run.py 远端。"""
    # 1. 渲染脚本 (jinja-like, 在 brain 自带 SKILL.md schema)
    script = render_md_script(body, brain=deps.brains.md)

    # 2. 上 bio000070 (asyncssh)
    backend = deps.hpc_backend   # AsyncSSHBackend
    handle = await backend.submit(
        account=HPCAccount(body["hpc_account"]),
        script=script,
        user_id=body["user_id"],
    )
    await deps.repo.update_md_job(job_id, hpc_job_id=handle.job_id, status="submitted")

    # 3. 轮询 SLURM 状态 (60s/次)
    while True:
        st = await backend.poll(handle)
        await deps.repo.update_md_job_progress(job_id, st.progress, st.state)
        if st.state in {TaskState.COMPLETED, TaskState.FAILED, TaskState.KILLED, TaskState.TIMEOUT}:
            break
        await asyncio.sleep(60)

    # 4. 收 artifacts(扫远端目录,记元数据,不下载)
    artifacts = await backend.list_artifacts(handle)
    await deps.repo.complete_md_job(job_id, artifacts=artifacts, status=st.state.value)

    # 5. 计费(GPU 小时数)
    cost_li = _calc_md_cost(handle.actual_gpu_hours, deps.settings.pricing)
    await deps.ledger.record(body["user_id"], amount_li=-cost_li,
        kind="md_run", ref_type="md_job", ref_id=str(job_id))
```

**关键约束**:
- **不下载** trajectory 到 backend 机器(磁盘吃不住,~1-10 GB/job)。`artifacts` 字段只记 `remote_host` + `remote_path`,前端通过 `/api/storage/trajectories` 走 ssh-cat 下载(M11.5 carry,先返路径,FE 显示「在 hipeson:/home/.../<job_id>/ 查看」)
- replicas 用 parent_id 串起来,`/api/md/jobs/{parent}/children` 直接 `WHERE parent_id = $1`
- cancel:发 `scancel <hpc_job_id>` + DB 改 status,**不等远端确认**

### 7.5 GPU pool 状态

```python
# praxis2/scheduler/gpu_pool.py (新)
async def fetch_gpu_status(ssh_pool) -> GpuPoolStatus:
    """ssh nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv"""
    hosts = ["bio000070", "bio000071"]   # 配置在 env
    gpus = []
    for h in hosts:
        out = await ssh_pool.run(h, "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits")
        for line in out.splitlines():
            idx, name, mem_used, mem_total, util = line.split(", ")
            gpus.append({"host": h, "gpu_id": int(idx), "name": name,
                         "mem_mb": f"{mem_used}/{mem_total}", "util_pct": int(util),
                         "busy": int(util) > 50, "busy_label": None})
    # busy_label 关联到当前 md_jobs(running 态的 gpu_host + gpu_id 查 user)
    ...
    return GpuPoolStatus(total_slots=len(gpus), busy_slots=..., gpus=gpus, hosts=hosts)
```

- 30s 缓存(防 ssh nvidia-smi 风暴)
- 用 asyncssh 长连接池(`asyncssh.connect()` 复用)

### 7.6 测试

```
tests/test_spawn_routes.py                 ← submit / list / get,异步任务跑完写 DB
tests/test_spawn_lifecycle.py              ← starting→running→done 真状态机
tests/test_md_routes.py                    ← submit / runs / cancel,接 InMemoryHPCBackend
tests/test_md_replicas.py                  ← parent + n_replicas=3 → 3 child rows
tests/test_gpu_pool.py                     ← fake nvidia-smi 输出解析
tests/integration/test_md_real_hpc.py      ← @integration,真投 bio000070,跑 1 ns 烟测
```

### 7.7 时间表

| 子任务 | 估时 |
|---|---|
| 004 migration + spawn/repo + md/repo | 1.5 d |
| spawn routes + 异步执行 + 计费 | 2 d |
| md routes + ResourceGate 接入 | 1.5 d |
| AsyncSSHBackend 完整化(submit/poll/cancel/artifacts) | 2 d |
| GPU pool + 缓存 | 1 d |
| 集成 / 真 HPC 烟测 | 1 d |
| **合计** | **9 d** |

---

## §8 M12 — 提案 + admin v2(~1.5 周)

### 8.1 范围

| Endpoint | Method | 行为 |
|---|---|---|
| `/api/proposals` | POST | 用户提交提案(kind/title/body) |
| `/api/me/proposals` | GET | 我的提案列表 |
| `/api/admin/proposals` | GET | 管理员查所有,支持 status 过滤 |
| `/api/admin/proposals/{id}/decide` | POST | ship/promote/hold/reject + admin_scores |
| `/api/admin/users` | GET | 用户列表(分页 + q 模糊搜邮箱) |
| `/api/admin/users/{id}/adjust` | POST | 调账:amount_yuan/note → 写 ledger |
| `/api/admin/users/{id}/freeze` | POST | 冻结(status=frozen) |
| `/api/admin/users/{id}/unfreeze` | POST | 解冻 |
| `/api/admin/ledger` | GET | 流水(分页 + user_id/kind 过滤) |
| `/api/admin/audit-log` | GET | 审计日志(分页 + user_id/action 过滤) |
| `/api/admin/stats` | GET | dashboard 数字(users/balance/runs/consumption) |
| `/api/admin/reconcile` | POST | 对账:ledger sum vs users.balance_li,返 mismatches |

### 8.2 实现要点

- **`proposals/repo.py`**(新):CRUD + decide 链
- **`proposals/ship.py`**(新):approved → write 大脑(brain `<slug>/memory/cases/<case_id>.md`),走 review pipeline(已有 admin/review 模块复用)
- **`auth/repository_pg.py` 扩**:
  - `list_users(q, page, limit, role?, status?)`
  - `update_user_status(user_id, status)`
- **`accounting/ledger.py` 扩**:
  - `list_ledger(filters, page, limit)`
  - `reconcile() → ReconcileReport`:校验 sum(ledger.amount_li per user) == users.balance_li,记 mismatches
- **`admin/stats.py`**(新):聚合查询
  - `users`:total/active/frozen/deleted
  - `balance`:sum(balance_li) 出账总余
  - `runs`:spawn_tasks + md_jobs 总数 / done / failed
  - `consumption`:abs(sum(amount_li WHERE amount_li<0))
  - 缓存 5 min

### 8.3 权限

- 所有 admin 路由强 `_require_admin(scope, send)`(已有,M9 校准)
- 写操作(adjust/freeze/decide)**强 audit**:每条调用 `audit_log.insert(actor=user_id, action="admin_adjust", resource="user", resource_id=target_id, meta={...})`

### 8.4 测试

```
tests/test_proposals_routes.py             ← submit / list / decide,ship 真写到 brains/<slug>/memory/
tests/test_admin_users_routes.py           ← list / adjust / freeze / unfreeze
tests/test_admin_ledger_audit.py           ← list 分页 + 过滤
tests/test_admin_stats.py                  ← 4 个数字与 db 真值一致
tests/test_admin_reconcile.py              ← 造 ledger drift → reconcile 报错列
tests/test_audit_on_admin_writes.py        ← 每个写操作必有 audit_log row
```

### 8.5 时间表

| 子任务 | 估时 |
|---|---|
| 005 migration + proposals/repo | 1 d |
| proposals routes + ship pipeline | 1.5 d |
| admin/users + audit | 1.5 d |
| admin/ledger + stats + reconcile | 2 d |
| 测试 + staging 验证 | 1 d |
| **合计** | **7 d** |

---

## §9 M13 — 切换 + 关 v1(**无限期推迟**,~0.5 周)

> **状态:DEFERRED**(2026-05-24 用户决策)。M9-M12 完成后**不自动**进入 M13。
>
> **触发前提**(全部满足才能开 M13):
> 1. M9-M12 全部 ship 且 staging 跑满 ≥ 2 周无红牌
> 2. 用户主导一轮「完整测试」(13 学科 brain + 全部 25+ endpoint + 13 个 FE 面板真跑)
> 3. v1 在线用户 retention / 流量 / 投诉日志确认可以承受切换
> 4. **用户显式说「开 M13」**,本路线不自动调度
>
> 在那之前,v1 整条链路(`.40:8088` + 老 server.py + `.53:7788` PRAXIS-hou)**保持运行**,
> v2 仅在 `.40:8080` + `.53:8001` 双端口并存形态下迭代。**不夺端口、不切单 upstream、不归档老 dist**。

### 9.1 切换 checklist(只在用户开 M13 时执行)

```
[ ] M9-M12 全部 ship 到 staging,pytest 全过
[ ] frontend rebuild (VITE_API_BASE='')
[ ] dist rsync 到 .40:/home/hipeson/mzy/PRAXIS-2-fe/dist/
[ ] .40 反代 server.py 已只指 :8001(不再分流,因 v2 全集已有)
[ ] /api/info 验 v2 命中
[ ] 所有 FE modal 走一遍(MD/Spawn/Files/Admin/Proposals)真跑 + 截图
[ ] v1 用户库快照(`pg_dump -h .53 -p 5432 -U praxis_v1 praxis_hou > praxis-v1-snapshot-2026MMDD.sql`)
[ ] v1 backend 进程停(`tmux send-keys -t praxis-hou C-c`)
[ ] v1 dist 改名归档(`mv /home/hipeson/mzy/PRAXIS /home/hipeson/mzy/PRAXIS.archived.2026MMDD`)
[ ] 24h 观察 + 用户回报
[ ] 7d 后清 v1 PG 实例(若无回滚需求)
```

### 9.2 反代代码瘦身

```python
# praxis2_proxy_unified.py → 简化版,只反代到 v2
PROXY_PREFIXES = ("/api/", "/chat/permission")
UPSTREAM = "http://10.102.106.53:8001"   # 单一 upstream
# 删除 R1/R2 分流逻辑
```

### 9.3 数据迁移决策(用户)

**默认**:不迁移。v1 关停后,v1 用户在新 v2 系统里没有账号,需重新注册。理由:
- staging 数据非生产,损失可接受
- v1 用 phone+password,v2 用 email+password,iden 切换无法 1:1 平移
- v1 余额 ledger 与 v2 ledger 表结构不同(v1 PRAXIS-hou 自定义)

**可选**:写一个 `scripts/migrate_v1_users.py`(已有同名 stub,扩展之),手动跑一次。**仅限管理员账号迁移**(`mzy` / 其他 admin),不大批量迁移用户。
工作量:0.5 d。决策点 — M9 末尾问用户。

### 9.4 时间表

| 子任务 | 估时 |
|---|---|
| 反代瘦身 + 切单 upstream | 0.2 d |
| 完整 smoke(13 个 FE 面板) | 0.5 d |
| v1 snapshot + 关停 | 0.2 d |
| 24h 观察 | 1 d(背景) |
| 文档 wrap up(v3.0 tag,README 更新) | 0.5 d |
| **合计** | **2.5 d** |

---

## §10 v3 上云钩子(本路线不实现,只保留)

> 沿用 [v2.1 §11](./PRAXIS-2-计划-v2.1-部署-反代统一.md#§11-未来:云上反代-+-多后端集群(v3+-前瞻)) 的硬约束,本路线在 M9-M13 实现时**遵守**:

| 约束 | 在哪个 M 落 | 验证方法 |
|---|---|---|
| R2_PATTERNS 用 nginx-PCRE 兼容 | M13 反代瘦身后单一,无 R2 概念,但 location regex 风格保持 | `pcretest` 离线验 |
| upstream env 可接 LIST | M13 server.py `PRAXIS_V2_UPSTREAMS="host1:8001,host2:8001"` | 单值也接 |
| SSE proxy_buffering = OFF | 从 M9 起每个 handler 流式输出不带 Content-Length | curl --no-buffer 实测 |
| cookie 全 host-only | M9 不引入 `Domain=` 设置 | 浏览器 devtools 校验 |
| 后端读 X-Forwarded-Proto | M9 配 settings.cookie_secure 从 env 切 | nginx X-F-P=https 时 cookie 带 Secure |
| `/__proxy/healthz` 实现 | M13 反代瘦身一并加 | curl 返 `{v2:OK,ts}` |
| 日志 JSON line | 每个 M 写 route 时用同 schema(已有 `audit_log.insert`,扩 access log) | grep schema |
| Session/Redis 进程外 | 已是,M11 spawn 复用 | M11 多 worker 测 |
| DB pool 用 asyncpg | 已是 | — |

---

## §11 风险登记表 + 回滚预案

### 11.1 已识别风险

| # | 风险 | 概率 | 影响 | 缓解 |
|---|------|:----:|:----:|------|
| R1 | M11 真接 HPC 时 asyncssh 在 staging 不通 | 中 | 高(MD 全挂) | 用 InMemoryHPCBackend 兜底,M11.5 carry 真接 |
| R2 | M12 admin 改账号余额时 ledger 不一致 | 中 | 高(财务对账失败) | 强事务 + reconcile 端点;每改一次必跑 reconcile |
| R3 | v1 关停后有用户反馈缺失 | 中 | 中(口碑) | snapshot 留 6 月,需要时单独捞 |
| R4 | 单 backend 实例挂(无 .53A/.53B) | 低 | 高(全站挂) | tmux + 自动重启;v3 上云解决 |
| R5 | M11 spawn 在同 backend 进程跑久驻 → 内存膨胀 | 中 | 中 | 每任务 finally 释放;监控 RSS;timeout 强杀 |
| R6 | M10 文件上传到 fs,磁盘满 | 中 | 中 | 配额硬限;`df` 告警(v3 接监控);单文件 100 MB 上限 |
| R7 | PG schema 改动有现网用户时阻塞 | 低 | 中 | 每 migration 写 reversible upgrade/downgrade;先 staging 跑 alembic upgrade head |
| R8 | FE typecheck 由于 MeResponse adapter 删除而炸 | 低 | 低 | M9 末尾 typecheck + build 全跑 |

### 11.2 回滚预案(per milestone)

| Milestone | 回滚命令 |
|-----------|---------|
| M9 ship | `alembic downgrade -1`(撤 002)+ revert FE adapter + 重启 gunicorn |
| M10 | `alembic downgrade -1`(撤 003)+ files/ 子包代码 revert |
| M11 | 同上 + spawn/md routes 注释掉(或 returns 503) |
| M12 | 同上 |
| M13 (切换 + 关 v1) | `tmux send-keys -t praxis-hou` 重启老 v1 进程 + 反代切回 R1/R2 分流(v2.1 备案) |

**24 小时回滚窗**:每个 M ship 后 24h 内若发现红牌(SSE 不出帧 / 余额错乱 / SMTP 退信),立刻按表回。

---

## §12 总时间表

| Milestone | 工作天 | 累计 | 周次 |
|-----------|:------:|:----:|:----:|
| M9 用户中心 + SMTP | 4.5 d | 4.5 d | W1+W2 上半 |
| M10 agents/profile + files | 5 d | 9.5 d | W2 下半 + W3 |
| M11 spawn + md + HPC | 9 d | 18.5 d | W4 + W5 |
| M12 admin v2 + proposals | 7 d | 25.5 d | W6 + W7 上半 |
| **本路线合计** | **~25.5 工作日 / ~5 周** | | M12 末尾 = v2 完整 parity |
| ~~M13 切换 + 关 v1~~ | ~~2.5 d~~ | — | **DEFERRED**(§9 前提满足 + 用户显式触发,无 ETA) |

**进度展示**(不含 M13):
```
W1  [M9 ──────────]
W2        [M9──][M10 ────]
W3            [M10 ───────]
W4                  [M11 ───────────]
W5                              [M11 ────]
W6                                  [M12 ──────]
W7                                          [M12─][M13]
```

---

## §13 实施过程的工作流(沿用 superpowers)

每个 milestone 实施:

1. **Brainstorm**(`/superpowers:brainstorming`):跟用户对齐范围,确认 P0/P1/carry 边界
2. **Write plan**(`/superpowers:writing-plans`):写 M<N> 具体 plan 文件 `PRAXIS-2-计划-M<N>-*.md`(2000-3000 行,体例同 M0-M8)
3. **TDD execute**(`/superpowers:executing-plans` + `subagent-driven-development`):
   - 每 Task:**先写测试** → 跑红 → 实现 → 跑绿 → commit
   - commit 尾必须 `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`
4. **Review**(`/superpowers:requesting-code-review`):合 PR 前自审 + ruff + pytest 全过
5. **Verify**(`/superpowers:verification-before-completion`):跑回归矩阵 + staging smoke
6. **Ship**:tag `v0.<M>.0`(M9 → v0.10.0,M10 → v0.11.0,M11 → v0.12.0,M12 → v0.13.0 = **v2 完整 parity**;M13 推迟,v0.14.0 / v3.0-pre 留待 §9 触发后再 tag)

每个 M 最后 push tag,git log 体例延续 M0-M8。

---

## §14 关键不变约束(全路线必守)

- **不动 Claude Code-style 内核**(query.py / agents/loader.py / brains/)。新 endpoint **调用**这些,不 **改**这些。
- **不引入第二个 chat-stream 路径**(`/chat/stream` legacy alias 已有,M13 可考虑删,但不再新增)
- **不硬编码 prompt 进 string**(走 `Section()` + `core/prompt.py` 单一路径)
- **不在 backend 进程 fork subprocess**(spawn 走 asyncio.create_task 单进程,M11 已说明)
- **不读 `~/.ssh/`**(凭据探测拒)
- **不提交 hpc_submit_account.toml 真账号**(`.gitignore` 已含)
- **不跨 staging/prod 共享 PG**(staging 一个库,prod 一个库,v3 上云时独立 RDS)
- **每次 PR 必跑** `pytest -k "not integration" --ignore=tests/test_skills` + ruff + typecheck + build

---

## §15 文档清单(本路线落地后产出)

| 文件 | 内容 | 落点 |
|------|------|------|
| 本文件 | 路线图总览 | `/Volumes/T7/clade-learn/` |
| `PRAXIS-2-计划-M9-用户中心.md` | M9 详细 plan(W1 写) | 同 |
| `PRAXIS-2-计划-M10-agents-files.md` | M10 详细 plan | 同 |
| `PRAXIS-2-计划-M11-spawn-md-HPC.md` | M11 详细 plan | 同 |
| `PRAXIS-2-计划-M12-admin-proposals.md` | M12 详细 plan | 同 |
| `PRAXIS-2-计划-M13-切换-关v1.md` | M13 详细 plan(短) | 同 |
| `PRAXIS-2/VERSION-STATUS-v3.0.md` | v3.0 release notes(M13 ship 时) | `PRAXIS-2/` |
| `PRAXIS-2/CHANGELOG.md` | 累计变更 | 同 |
| `PRAXIS-2/DEPLOY.md` | 部署指南 v3.0 | 同 |

---

## 附录 A:Claude Code-style 框架在新 endpoint 中的复用清单

| 新 endpoint | 复用的 PRAXIS 模块 | 说明 |
|------------|----------------|------|
| `/api/spawn` | `core/query.py` + `agents/loader` + `tools/runtools` + `brains/system_prompt` | 等价单次 chat 但异步跑 |
| `/api/md/submit` | `scheduler/hpc_submit` + `scheduler/resource_gate` + brain `md/skills/workflows/*` | MD 不走 query.py,直接调度 |
| `/api/agents/profile` | `brains/store` + `brains/system_prompt`(摘要) | 仅读 brain 文件系统 |
| `/api/files` | 无内核依赖 | 纯 CRUD |
| `/api/proposals` | `server/routes/admin/review`(ship 流复用) | decide → ship 走老 review pipeline |
| `/api/admin/*` | `auth/repository_pg` + `accounting/ledger` | 纯 admin CRUD,不调内核 |

## 附录 B:M9-M12 在 git 上的体现(M13 推迟,见 §9)

```
v0.9.4 (M8 baseline) → v0.9.5 (v2.0.1 hotfix) → v0.9.6 (v2.0.2 Synth)
   │
   ├── v0.10.0  (M9 ship) ─ 用户中心扩展 + 真 SMTP
   │
   ├── v0.11.0  (M10 ship) ─ agents/profile + 文件管理
   │
   ├── v0.12.0  (M11 ship) ─ spawn + md + HPC 真接
   │
   └── v0.13.0  (M12 ship) ─ admin v2 + proposals = **v2 完整 parity**
       ↓
       (M12 ship 后:v1/v2 双端口长期并存,等用户在 §9 前提满足后开 M13)

   ── DEFERRED ─────────────────────────────────────────────
   v0.14.0 / v3.0-pre  (M13 ship) ─ v1 关停 + 反代瘦身    │  ← 无 ETA,
   v3.0                (M13 + 7d 无问题 → 上 prod 准入)   │    用户触发
   ─────────────────────────────────────────────────────────
```

## 附录 C:为什么不在本路线引入双实例 / 多机

- **复杂度爆炸**:加 .53A/.53B 后,session(Redis 已外)、SQLite/SQLite-like cache、文件 fs 都得共享存储。Redis + asyncpg pool 已是「天然多机 ready」,但本路线还有 file storage(M10 本地 fs)和 GPU pool 长连接(M11)是单点。
- **资源不到位**:`.53` 已是 staging 单机,prod 双机需要新机器审批 + VLAN 设计,周期超本路线 6 周窗口。
- **v3 一并解决**:腾讯云 CVM × N + COS 文件 + RDS PG + Tencent Redis,届时本路线产生的 v3.0 镜像直接 docker run × N,反代切 CLB,**M9-M13 代码层面不再变**(因 §10 钩子已守)。

## 附录 D:本路线**不**做的事

- 不重写 Claude Code-style 内核(`core/query.py` / `agents/loader.py`)
- 不引入新 agent 模式(仍是 5 种)
- 不替换 LLM client(`llm/client.py:AnthropicClient` 保持 Anthropic 协议)
- 不接 prod-grade 监控(Prometheus/Grafana 是 v3 carry)
- 不接 prod-grade CI/CD(GitHub Actions 已有基本流水,v3 加 deploy job)
- 不做 i18n(中文是 staging 唯一语言,英文 carry 到 v3 国际化)
- 不做 mobile app(SPA 已 responsive,RN/Tauri 是 v4 carry)
