# v0.10.0 现状(M9 用户中心 + ledger + profile + signup_gift)

> **锁定**: 2026-05-25 · **base**: v2.0.2(`7c7c835`)→ **HEAD** `955bb27` · **tag**: `v0.10.0`
> **关联文档**:
> - `docs/superpowers/specs/2026-05-24-m9-user-center-design.md`(spec)
> - `docs/superpowers/plans/2026-05-24-m9-user-center.md`(13 task plan)
> - `PRAXIS-2-计划-v2-完整重写-路线图.md`(M9-M12 主线;M13 推迟)
> - `VERSION-STATUS-v2.0.md`(13 brain × 152 skill 全量 real-uplift 现状,本版本**完全继承**)
> **GitHub**: `git@github.com:NHNQNHNQ/PRAXIS-2.git`(`main` + tag `v0.10.0` 已 push)

---

## 1. 一句话定位

**v0.10.0 = v2.0.2(智能体能力完整版)+ M9 用户中心扩展层**。智能体 / 大脑 / skills / SkillExecTool 真跑能力 **0 改动**,只在外层加 user / profile / ledger / signup_gift / admin stub 几条 endpoint。

---

## 2. PRAXIS 智能体真跑能力(继承自 v2.0.x,**v0.10.0 未动**)

> ⚠️ 关键不变约束:M9 全程**不动** `praxis2/core/`、`praxis2/agents/`、`praxis2/brains/`、`praxis2/tools/`、`praxis2/scheduler/`、`praxis2/runtime/`。智能体 152 skill 真跑能力跟 v2.0.2 完全一致。

### 2.1 13 学科 brain 数量盘点(同 v2.0.x)

| brain | cases | rules | workflows | real CLI / N/A | 状态 |
|---|---|---|---|---|---|
| `_common` | — | — | — | — | 通用 prompt + rules |
| `general` | 22 | 44 | 13 | — | general 模式底盘 |
| `dock` | — | — | 12 | 7 real + 5 N/A | vina/gnina/boltz/pyrosetta |
| `drug` | — | — | 12 | 12 real + 2 N/A | admet/aizynth/reinvent/openfe/rdkit/vina |
| `protein` | — | — | 17 | 17 real + 4 N/A | esm/boltz/chai/foldseek/rfdiffusion/proteinmpnn |
| `microbiome` | — | — | 22 | 22 real + 8 N/A | kraken2/humann/dada2/ANCOMBC |
| `omics` | — | — | 13 | 13 real + 4 N/A | scanpy/muon/cooler/mofapy2/cell2location |
| `enzyme` | — | — | 11 | 11 real + 2 N/A | REST + ESM + BioPython |
| `cell` | — | — | 11 | 11 real + 3 N/A | cellpose/skimage/scanpy/scipy |
| `crispr` | — | — | 11 | 11 real + 0 N/A | crispor/cas-offinder/mageck |
| `cryo` | — | — | 11 | 11 N/A(host 缺工具栈) | RELION/cryoSPARC/Warp |
| `immuno` | — | — | 11 | 11 real + 1 N/A | mhcflurry/arcasHLA/optitype/ANARCI/boltz |
| `pharma` | — | — | 11 | 11 real + 1 N/A | scipy 数学 + openFDA REST |
| `md` | — | — | 8 | 8 real + 3 N/A | gmx + vina + nohup |
| `synth`(v2.0.2 新增) | 22 | 44 | 13 | — | 合成生物学 / FBA / antiSMASH / Golden-Gate |

**合计**(继承 v2.0.x):
- **152 skill** 真盘点
- **109 real CLI**(`.53` host 可真跑)
- **41 N/A**(license / web / composite / host 工具缺 / prompt-only)
- **2 hand-written DONE_real**(`dock/vina_gnina_dock` + `enzyme/pyrosetta-stability-scan`)
- `tests/skills/`:**929 passed / 4 skipped / 0 failed**(同 v2.0.x)

### 2.2 v0.10.0 中智能体相关 0 改动列表

下面这些跟 v2.0.x **逐字节相同**(rsync 一致):
- `praxis2/core/query.py`(Claude Code-style 主循环)
- `praxis2/agents/loader.py`(5 模式 agent 路由:discipline / general / one-above-all / yourself / bare)
- `praxis2/brains/`(13 大脑文件树,含 prompts/cases/rules/skills/workflows)
- `praxis2/tools/`(ToolRegistry / SerialToolRunner / Permission)
- `praxis2/scheduler/`(ResourceGate / quota / hpc_submit / TaskState 状态机)
- `praxis2/runtime/`(session_pool / pubsub / tasks)
- `praxis2/llm/`(AnthropicClient / 反代 litellm 协议)
- `praxis2/server/permission_bridge.py`(ASK 流)
- `praxis2/server/sse.py`(SSE 协议名 + event_id replay)

**SkillExecTool**(brain `skills/workflows/<x>/run.py` 真跑)仍走 `.53` host 的 conda env / 系统 binary,M9 未触碰。

### 2.3 用户面看到的智能体能力(v0.10.0 实际可用)

登录后:
- **chat** `/api/chat-stream`:13 学科 brain 全可选(`agent: 'synth' | 'md' | ... | 'general' | 'bare' | 'yourself' | 'one-above-all'`),走 Claude Code-style query.py,SSE 真流式
- **agents 卡片** `/api/agents`:13 学科 sidebar 真渲染(slug / emoji / desc / examples)
- **permission ASK 流**:`/chat/permission` 双向(SSE control_request → POST 决策)
- **5 模式真路由**:discipline / general / one-above-all / yourself / bare 全工作

**未变**:agent 调用真跑 skill 的能力(SkillExecTool ssh `.53` host) — staging 跟 v2.0.x 一样真接 conda env。

---

## 3. v0.10.0 真正改了什么(M9 = 用户中心扩展)

### 3.1 新 API endpoint(共 10 条,M9 主线 + M9.1 hotfix)

#### M9 主线(用户中心)

| Endpoint | Method | Shape | 说明 |
|---|---|---|---|
| `/api/me` | GET | **11 字段平铺**(取消 `{user:{}}`嵌套) | id/phone/email/display_name/role/plan/status/balance_li/balance_yuan/realname_verified/created_at |
| `/api/me/balance` | GET | `{balance_li, balance_yuan, recent: LedgerEntry[]}` | recent 固定 20 条 DESC |
| `/api/me/profile` | GET | 5 字段 + updated_at | 未填过返全 null |
| `/api/me/profile` | POST | 同 GET(upsert 后) | null/缺失=不动 / `""`=清空 / 各字段独立长度上限 |
| `/api/me/proposals` | GET | `{proposals:[], total:0}` | M9 stub;M12 接真 |

#### M9.1 hotfix(staging 真测发现 FE 漏调)

| Endpoint | Method | Shape | 说明 |
|---|---|---|---|
| `/api/admin/stats` | GET | `{users, balance, runs, consumption}` 全 0 | admin role guard |
| `/api/admin/users` | GET | `{users:[], total, page, limit}` | 同上 |
| `/api/admin/ledger` | GET | `{rows:[], total, page, limit}` | 同上 |
| `/api/admin/audit-log` | GET | `{rows:[], total, page, limit}` | 同上 |
| `/api/admin/proposals` | GET | `{proposals:[], total, page, limit}` | 同上 |
| `/api/files/usage` | GET | `{used_bytes:0, quota_bytes:5GB, max_per_file:100MB, files_count:0}` | 全用户(M10 真接) |

#### 已有 endpoint shape 修正

| Endpoint | 改动 |
|---|---|
| `POST /api/auth/register` | response `balance_li` 0 → `settings.signup_gift_li`(默认 10000) |
| `GET /api/info` | `version: "v0.9.0"` → `"v0.10.0"`;`default_model` 由 env `PRAXIS_MODEL` 决定 |
| `GET /api/agents` | 同上 default_model / models 字段 |

### 3.2 DB schema(`002_user_profile_billing.py`)

```sql
CREATE TABLE user_profiles (
  user_id        UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  research_field VARCHAR(256),
  affiliation    VARCHAR(256),
  expertise_level VARCHAR(256),
  projects       VARCHAR(2000),
  custom_intro   VARCHAR(2000),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ledger (
  id            BIGSERIAL PRIMARY KEY,
  user_id       UUID NOT NULL REFERENCES users(id),
  amount_li     BIGINT NOT NULL,             -- 正=入账 / 负=消费
  kind          VARCHAR(32) NOT NULL,        -- signup_gift|topup|chat_in|chat_out|md_run|admin_adjust
  ref_type      VARCHAR(32),
  ref_id        VARCHAR(64),
  balance_after BIGINT NOT NULL,             -- 冗余,便于审计 + reconcile
  meta          JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ledger_user_created ON ledger(user_id, created_at DESC);
```

**001 表保留**:`users` / `email_codes` / `audit_log` 不动。`users.realname_verified_at` 仍 `TIMESTAMPTZ`,handler 算 `bool(...)` 返 FE(M9 决策点 #2)。

### 3.3 新代码模块

| 路径 | 责任 | 行数 |
|---|---|---|
| `praxis2/accounting/__init__.py` | 包初始化 | 0 |
| `praxis2/accounting/ledger.py` | `Ledger.record()` + `Ledger.recent()` + `LedgerError` | 93 |
| `migrations/versions/002_user_profile_billing.py` | DDL upgrade/downgrade | 52 |

### 3.4 扩展的现有模块

| 路径 | 改动 |
|---|---|
| `praxis2/auth/repository.py` | `UserRow` 加 `realname_verified_at`;`AuthRepository` Protocol + `FakeAuthRepository` 加 4 个 profile/balance 方法 |
| `praxis2/auth/repository_pg.py` | 3 个 SELECT 加 `realname_verified_at` 列;`_row_to_user` 映射;新 `get_user_profile` / `upsert_user_profile`(动态 SET clause)/ `get_user_with_balance` / `get_balance_li` |
| `praxis2/auth/routes.py` | `handle_me` 重写 11 字段平铺;`handle_me_balance` 接 ledger;新 5 个 handler(profile GET/POST + proposals stub + 5 admin stub + files/usage stub);`handle_register` 末尾接 `ledger.record(signup_gift)`;`/api/info` version bump |
| `praxis2/server/app.py` | `_App.__init__` 构造 `Ledger` 加进 `auth_deps`(`PgAuthRepository._pool` 时;`FakeAuthRepository` 测试路径 None) |
| `praxis2/config.py` | 加 `signup_gift_li: int = 10000` + env `PRAXIS_SIGNUP_GIFT_LI` |
| `frontend/src/lib/api.ts` | `fetchMe()` 删 unwrap hack(16 行 → 3 行),直返 `MeResponse` |
| `frontend/package.json` | version `0.7.15` → `0.10.0`(vite 注入 `__APP_VERSION__`) |

### 3.5 测试新增 / 修

| 测试文件 | 用途 | 数 |
|---|---|---|
| `tests/test_config_signup_gift.py` | env 默认 / override / 0 | 3 |
| `tests/test_accounting_ledger.py` | record / recent / 并发不丢更新 / meta JSONB | 10(integration) |
| `tests/test_auth_repository_pg_profile.py` | profile CRUD / balance 一致 | 5(integration) |
| `tests/test_auth_routes_v2_me.py` | 4 新 endpoint × 状态机 + 长度参数化 | 20 |
| `tests/test_auth_repository.py` | UserRow realname_verified_at 字段 | 2 |

**T12 顺手补 5 处之前 task review 漏的 test 修复**(`_TestSettings`/`_S`/`_Settings` 加 `signup_gift_li=0` 默认 + 2 处 shape 断言扁平化)。

**pytest 结果**:1570 passed / 18 skipped / 26 xfailed / 0 failed(基线 1543 + 27 新增,与目标 1575+ 略差因部分参数化测试合并计数)。

### 3.6 不动的 4 件事

1. **智能体内核**(`core/` / `agents/` / `brains/` / `tools/` / `scheduler/` / `runtime/` 全 0 改)
2. **SkillExecTool 真跑 host** (.53 conda env / 系统 binary)
3. **v1 链路**(`.40:8088` + `.53:7788` + `PRAXIS/dist` 全程冻结)
4. **chat-stream / permission_bridge / SSE 协议**(M0-M8 内核合约不动)

---

## 4. 部署拓扑(2026-05-25 实测)

```
┌──────────────────────── .40 (hipeson@10.102.106.40) ────────────────────────┐
│                                                                              │
│  :8088   python3 server.py (PRAXIS-proxy/0.2)            v1 PRAXIS-hou       │
│          dist  = /home/hipeson/mzy/PRAXIS/dist (老 5月17 build)              │
│          反代  → http://10.102.106.53:7788  (v1 backend, M13-deferred)       │
│                                                                              │
│  :8080   python3 server.py                               v2 PRAXIS-2 M9      │
│          dist  = /home/hipeson/mzy/PRAXIS-2-fe/dist                          │
│                  (index-BPoG7EB4.js, v0.10.0 build 2026-05-25)               │
│          反代  → http://10.102.106.53:8001                                   │
│                                                                              │
│  :8090   uvicorn backend.main:app (Scientist-Genome)     4 scientists,       │
│          dist  = /home/hipeson/mzy/Scientist-Genome/frontend/                deepseek    │
│          (本次从 8088 迁过来,sed 修 CRLF + remote_launch.sh PORT=8090)        │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────── .53 (zkyd@10.102.106.53) ────────────────────────────┐
│                                                                              │
│  :7788   uvicorn PRAXIS-hou v0.1.0                       v1 后端(在线用户)   │
│          /home/zkyd/PRAXIS-hou/                                              │
│                                                                              │
│  :8001   gunicorn praxis2.server.app:make_app_default    v2 backend          │
│          /home/zkyd/data1/mzy/PRAXIS-2/                                      │
│          conda env: /home/zkyd/software/miniconda3/envs/praxis2/             │
│          env file:  /home/zkyd/praxis2.env                                   │
│          tmux:      session 10, window "praxis2-be"                          │
│                                                                              │
│  PG      docker praxis2-pg:5432                          users / email_codes │
│          DB: praxis2  user: praxis2                       / audit_log /      │
│                                                          user_profiles /     │
│                                                          ledger              │
│                                                                              │
│  Redis   docker praxis2-redis:6379                       session 缓存 +      │
│                                                          rate_limit          │
│                                                                              │
│  litellm :4000                                           Anthropic→DeepSeek  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### env 配置点

`.53:/home/zkyd/praxis2.env`(本次新增 / 改的关键 var):
- `PRAXIS_MODEL='deepseek-chat'`(本次由 `claude-3-5-sonnet-20241022` 改成)
- `DEEPSEEK_API_KEY=sk-...`(litellm 路由用)
- `PRAXIS_SIGNUP_GIFT_LI=10000`(默认值,等同于不设)
- `PRAXIS_DB_URL=postgresql://praxis2:...@127.0.0.1:5432/praxis2`

---

## 5. v0.10.0 SHIP 流程(13 task + hotfix 实测产物)

> 走 `superpowers:brainstorming → writing-plans → subagent-driven-development` 链路。

| 阶段 | 产出 | commit |
|---|---|---|
| Brainstorming | 10 决策点锁定 + spec 草稿 | `aadf56d` |
| Spec 自审 | 3 处 inline 修(upsert 语义 / 测试数 / 链接) | `66a7d81` |
| Plan 写完 | 2001 行,13 task TDD 红绿步骤 | `024535c` |
| T1 config env | + 1 lint fix | `d05ad1c` + `4f8bfbe` |
| T2 002 migration | DDL + downgrade | `83f1971` |
| T3 ledger 模块 | record/recent + 10 integration tests | `120442e` |
| T4 UserRow realname | 字段加 + 3 SELECT 扩 | `b935e53` |
| T5 repo 4 方法 | profile + balance + Protocol + Fake mirror | `4caacbb` |
| T6 handle_me 11 平铺 | 取消 {user:{}} 嵌套 | `bf5ed3c` |
| T7 balance + Ledger 注入 | 接真 ledger.recent | `d01fe41` |
| T8 profile GET/POST | + 1 field_invalid 测试补 | `8d35cdf` + `2373b18` |
| T9 proposals stub | M12 carry 占位 | `ecc62ad` |
| T10 register signup_gift | ledger.record(+10000)+ 弱原子 | `bd3b08c` |
| T11 FE adapter 删 | 16 行 → 3 行,typecheck + build 通 | `df4fe04` |
| T12 全测自审 | 1570 pass + 5 处漏修补 | `924710a` |
| T13 staging 部署 | alembic + backend restart + FE rsync + admin balance backfill | — |
| **M9.1 hotfix** | 6 stub + version + deepseek | `d4e03b4` |
| **merge → main + tag** | merge commit + v0.10.0 tag push origin | `955bb27` |

**总**: 15 个 dev commit + 1 merge commit = 16 commits on `feat/m9-user-center`,push GitHub `main` + tag `v0.10.0`。

---

## 6. 已知妥协 / carry(明确记录,M10-M12 处理)

| # | 妥协 | 触发条件 | 修在哪 |
|---|---|---|---|
| 1 | `handle_register` + `ledger.record` 跨 conn,**非原子** | create_user 成功但 ledger 失败 → user 已落 + balance=0 + 漏 signup_gift 入账 | M12 `/api/admin/reconcile` 检测 drift + 修 |
| 2 | `/api/admin/{stats,users,ledger,audit-log,proposals}` 全 stub | admin 面板看到全 0 数据 | M12 真接 |
| 3 | `/api/files/usage` stub(全用户固定值) | 配额数字不真实 | M10 真接 files/repo + 配额 |
| 4 | `/api/me/proposals` stub | 提案 tab 空 | M12 真接 proposals/repo |
| 5 | 没有真 SMTP,DevEmailGateway 默认 | 注册验证码在响应体 `dev_code` 回显 | 用户 demo 阶段决策 SMTP 提供商 |
| 6 | M9 部署前注册的老 admin balance=0 | 不享受 signup_gift | M9.1 已手动 ledger 补 +10000 给当前 admin;后续手动一次性补别人 |
| 7 | `FakeAuthRepository`(单测)无 `_pool` → Ledger 为 None | 单测 balance handler 返空 recent | 单测路径降级,生产无影响 |
| 8 | v1 注释「1 li = 0.001 RMB」(v1 = 1000li/元),v2 改「1 li = 0.01 RMB」(v2 = 100li/元) | 单位 ×10 差 | M12 v1→v2 用户迁移工具(若做)需换算 ×10 |
| 9 | tmux session 名实际是 `10:praxis2-be`,非路线图说的 `praxis2-backend` | 重启脚本要用真名 | 文档已记录(本文 §4) |

---

## 7. 升级路径(v2.0.2 → v0.10.0 in-place)

> Staging 已按此步骤 ship,**生产**(若有)走同样流程。

```bash
# 1. 拉新代码
cd /home/zkyd/data1/mzy/PRAXIS-2
# (无 git on .53,本机 rsync push,见 deploy/push_backend.sh)

# 2. PG migration
source /home/zkyd/praxis2.env  # 提供 PRAXIS_DB_URL
alembic upgrade head            # → 002_user_profile_billing

# 3. backend restart(tmux)
tmux send-keys -t 10:praxis2-be C-c
sleep 2
tmux send-keys -t 10:praxis2-be \
    "cd /home/zkyd/data1/mzy/PRAXIS-2 && source /home/zkyd/praxis2.env && \
     /home/zkyd/software/miniconda3/envs/praxis2/bin/gunicorn \
       -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default" Enter

# 4. FE rebuild + rsync
cd PRAXIS-2/frontend
VITE_API_BASE='' npm run build
rsync -avz --delete --exclude '._*' dist/ \
    hipeson@10.102.106.40:/home/hipeson/mzy/PRAXIS-2-fe/dist/

# 5. smoke
curl -s http://10.102.106.40:8080/api/info  # 应见 v0.10.0 + deepseek-chat
```

---

## 8. 回滚预案(24h 内任意红牌触发)

```bash
# A. 数据库:撤 002
ssh zkyd@10.102.106.53 'cd /home/zkyd/data1/mzy/PRAXIS-2 && \
    source /home/zkyd/praxis2.env && alembic downgrade -1'
# → DROP TABLE ledger + user_profiles(M9 新建,丢这些表数据)
# → 001 用户表 + audit 不动,zero 损失

# B. 代码:revert merge commit
git checkout main
git revert -m 1 955bb27   # revert merge,留 history
git push origin main

# C. backend restart 同 §7 step 3

# D. FE 旧 dist(v2.0.2 build 还在 .40 上):
ssh hipeson@10.102.106.40 \
    'ls /home/hipeson/mzy/PRAXIS-2-fe/dist.bak.* 2>/dev/null'
# 若有备份,mv 回来 dist;否则跑老 commit 重 build

# E. env 还原 PRAXIS_MODEL → claude-3-5-sonnet-20241022(若 deepseek 出现兼容问题)
ssh zkyd@10.102.106.53 \
    "sed -i 's/^export PRAXIS_MODEL=.*/export PRAXIS_MODEL=\"claude-3-5-sonnet-20241022\"/' /home/zkyd/praxis2.env"
# 再 restart backend
```

**v1 链路全程不受影响**(`.40:8088` + `.53:7788` 不参与 M9 ship 流程,不需要回滚)。

---

## 9. 路线图位置(本版本 = M9 ship,下一步 M10)

> 同 `PRAXIS-2-计划-v2-完整重写-路线图.md`

| Milestone | 内容 | 工作天 | 状态 |
|---|---|---|---|
| M9 用户中心 + SMTP | profile + balance + signup_gift + ledger | 4.5 d | ✅ **本版本** |
| M10 agents/profile + files | brain 完整资料卡 + 文件管理 + 配额 | 5 d | 待开 |
| M11 spawn + md + HPC | 后台任务 + MD 真接 .53 HPC | 9 d | — |
| M12 admin v2 + proposals | admin 面板真接 + 提案 ship pipeline | 7 d | — |
| ~~M13 切换 + 关 v1~~ | dist 归档 + 8088 切单 upstream | 2.5 d | **DEFERRED**(用户 2026-05-24 决策,无 ETA) |

---

## 10. 附录:GitHub 状态

```
repo:    git@github.com:NHNQNHNQ/PRAXIS-2.git
branch:  main (synced)
tag:     v0.10.0 (synced)         955bb27 merge commit
         feat/m9-user-center (远端保留,15 commit 历史)
```

最近 6 个 commit on main:
```
955bb27 merge(M9): 用户中心 + ledger + profile + signup_gift → main
d4e03b4 fix(M9.1): admin/files stubs + version bump v0.9.0→v0.10.0 + deepseek
924710a fix(M9/T12): 补 T6/T1 漏修的 3 处 test fixture + 2 处 shape 断言
df4fe04 feat(M9/T11): FE fetchMe() 删 unwrap hack,直返后端 MeResponse
bd3b08c feat(M9/T10): register 末尾接 signup_gift ledger.record
ecc62ad feat(M9/T9): /api/me/proposals stub 返 {proposals:[], total:0}
```

完整 commit 列表见 `git log --oneline 7c7c835..955bb27`(从 v2.0.2 base 到 v0.10.0 共 16 commits)。

---

## 11. 一句话风险告知

- **新用户体验**: 注册得 100 元(`signup_gift_li=10000`),立即可以聊。Chat 真路由到 deepseek 而非 claude。
- **老 admin 体验**: 余额是 0(M9 前注册),已手动补 +¥100(`2370309934@qq.com`,ledger id=2)。其他 M9 前注册用户**未补**,可用 SQL `INSERT ledger + UPDATE users.balance_li` 一次性 backfill。
- **admin 面板**: 打开不再报 "got HTML"(M9.1 已修),但显示全 0 数据(M12 接真聚合查询)。
- **MD/Spawn/Files/Proposals 面板**: M9 仍未实装(M10-M12),用户点了会进空状态。
- **PRAXIS 13 学科真跑能力**: 完整保留,跟 v2.0.2 等同;`.53` host 上 109 个 real CLI + 2 hand-written 可经 chat 真触发(staging 已验)。
