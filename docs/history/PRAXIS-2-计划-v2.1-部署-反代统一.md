# PRAXIS-2 v2.1 部署计划 — `.40` 反代统一 + 双轨后台过渡

> 起草:2026-05-24
> 决策上下文:v2.0.1 hotfix(SSE 对齐 + `/api/agents` + admin alias)已落地,但 v2 后端**仍只覆盖 chat + auth + admin/review**,
> 而 `.40:8088` 老 dist 调 v1 后端(`.53:7788`)能跑的 spawn/md/files/proposals/admin-users 全集**未在 v2 重写**。
> 本计划**不是** v2 完整 API parity 路线图(那是 [PRAXIS-2-v1.x-API-parity-移交.md](./PRAXIS-2-v1.x-API-parity-移交.md) 里 M9-M12),
> 是**当下 `.40` 入口统一 + 双后台分流**的 1-2 天工程方案。

---

## §0 现状盘点(probe 实测,2026-05-24)

### 0.1 三台机器/六个进程的真实拓扑

```
                                ┌────────────────────────────────────────┐
                                │  .53  zkyd@10.102.106.53               │
                                │                                        │
浏览器 ──┐                      │  ┌────────────────────────┐            │
         │   :8088 (老入口)     │  │ PRAXIS v1  (pid 28...) │            │
         ├──────────────────────┼─→│ uvicorn :7788          │ ← 在线用户 │
         │                      │  │ /PRAXIS-hou/  v0.1.0   │            │
         │                      │  │ "环境 dev / 真计费"    │            │
         │                      │  └────────────────────────┘            │
         │                      │                                        │
         │   :8080 (新入口)     │  ┌────────────────────────┐            │
         └──────────────────────┼─→│ PRAXIS-2  (gunicorn)   │            │
                                │  │ :8001                  │            │
                                │  │ /PRAXIS-2/  v0.9.0     │            │
                                │  │ "环境 staging"         │            │
                                │  └────────────────────────┘            │
                                └────────────────────────────────────────┘

         ┌────────────────────────────────────────────┐
         │  .40  hipeson@10.102.106.40                │
         │                                            │
         │  :8088   python3 server.py (PRAXIS-proxy/0.2)
         │          dist  = /home/hipeson/mzy/PRAXIS/dist        ← v1 dist (5月17 build)
         │          反代  → http://10.102.106.53:7788  (env)
         │
         │  :8080   python3 praxis2_proxy.py (我刚部署)
         │          dist  = /home/hipeson/mzy/PRAXIS-2/dist       ← v2.0.1 dist (今天 build)
         │          反代  → http://10.102.106.53:8001  (env)
         │
         │  无 nginx / caddy / node / sudo,仅 python 3.8.10
         └────────────────────────────────────────────┘
```

### 0.2 能力覆盖矩阵(以前端 fetch 的 `/api/*` 全集 vs 两个后端真实路由对齐)

| 前端调用                    | v1 `.53:7788` | v2 `.53:8001` | UI 影响 |
|----------------------------|:-------------:|:-------------:|---------|
| `POST /api/chat-stream`     |       ✅       |       ✅       | 主聊天 |
| `GET  /api/info`            |       ✅       |       ✅       | 启动信息 |
| `GET  /api/agents`          |       ✅       |   ⚠ v2.0.1 加 | sidebar 卡片(v2 v0.9.0 没有,v2.0.1 已加) |
| `GET  /api/agents/profile`  |       ✅       |       ❌       | 智能体手册 modal |
| `POST /api/auth/login`      |       ✅       |       ✅       | 登录 |
| `POST /api/auth/register`   |       ✅       |       ✅       | 注册 |
| `POST /api/auth/sms/send-code`/`email/send-code` | ✅ sms | ✅ email | identifier 切换(v1 phone,v2 email) |
| `GET  /api/me`              |       ✅       |       ✅       | 用户信息(返回 shape 不同,v2.0.1 已加 unwrap) |
| `GET  /api/me/balance`      |       ✅       |       ✅       | 余额 |
| `GET  /api/me/profile`      |       ✅       |       ❌       | 个人资料 |
| `GET  /api/me/proposals`    |       ✅       |       ❌       | 我的提案 |
| `DELETE /api/me/account`    |       ✅       |       ✅       | 注销账号 |
| `POST /api/spawn`           |       ✅       |       ❌       | auto 模式后台任务 |
| `GET  /api/spawn/list`      |       ✅       |       ❌       | 任务面板 |
| `GET  /api/spawn/get/{id}`  |       ✅       |       ❌       | 任务详情 |
| `POST /api/md/submit`       |       ✅       |       ❌       | MD 派发 |
| `GET  /api/md/runs`         |       ✅       |       ❌       | MD 任务列表 |
| `GET  /api/md/gpu-pool`     |       ✅       |       ❌       | GPU 状态 |
| `GET  /api/md/jobs/{id}`    |       ✅       |       ❌       | MD 单任务 |
| `POST /api/md/jobs/{id}/cancel` |    ✅       |       ❌       | MD 取消 |
| `GET  /api/files`           |       ✅       |       ❌       | 文件管理 |
| `POST /api/files`           |       ✅       |       ❌       | 文件上传 |
| `DELETE /api/files/{id}`    |       ✅       |       ❌       | 删文件 |
| `GET  /api/files/usage`     |       ✅       |       ❌       | 配额 |
| `POST /api/proposals`       |       ✅       |       ❌       | 提交提案 |
| `GET  /api/admin/users`     |       ✅       |       ❌       | 管理员-用户 |
| `POST /api/admin/users/{id}/{adjust,freeze,unfreeze}` | ✅ | ❌ | 管理员调账 |
| `GET  /api/admin/ledger`    |       ✅       |       ❌       | 流水 |
| `GET  /api/admin/audit-log` |       ✅       |       ❌       | 审计 |
| `GET  /api/admin/stats`     |       ✅       |       ❌       | 统计 |
| `POST /api/admin/reconcile` |       ✅       |       ❌       | 对账 |
| `GET  /api/admin/proposals` |       ✅       |       ❌       | 管理员-提案 |
| `* /api/admin/review/*`     |       ❌       |       ✅       | 大脑评审(v2 独有,M5) |
| `GET  /api/storage/*`       |       ✅       |       ❌       | 存储 tab |

**结论**:**v1 是 35+ endpoint 全集,v2 只覆盖 ~10 个(chat + auth + me 基础 + admin/review)**。
若直接切前端到 v2,UI 的多数面板会空白/破。

---

## §1 目标(v2.1)

1. **`.40:8088` 是唯一对外入口**(老 URL,用户已习惯;关 `:8080` 这条临时辅道)
2. **`.40` 作为分流反代**:
   - chat/auth/me/admin-review/agents → 走 **v2**(`.53:8001`)拿新内核 + SSE 真合约
   - 其余 spawn/md/files/proposals/admin-users → 走 **v1**(`.53:7788`)保留可用功能
3. **前端 dist 用 v2.0.1 的 PRAXIS-2 build**(SSE 名已对齐 + fallback agents)
4. **零数据库迁移**(v1 用户表 ≠ v2 用户表,这一版承认两套独立账号体系并存)
5. **回滚 30 秒能做**(改一个 env 切回 8088 老 dist + 单一反代到 :7788)

---

## §2 方案选型(三选一,本计划选 B)

| 方案 | 入口 | 后端 | 工程量 | 风险 | UI 满血 |
|------|------|------|--------|------|---------|
| A. 维持现状 | `:8088` 老 + `:8080` 新 | v1 + v2 | 0 | 用户记俩 URL | `:8088` 满血,`:8080` 残血 |
| **B. 分流反代** ✅ | `:8088` 单点 | v1 + v2 双轨 | ~1 天 | 中(v2 与 v1 用户系统不同步) | **接近满血** |
| C. v2 完整重写(M9-M12) | `:8088` 单点 | v2 | 4-6 周 | 高 | 满血 |

**选 B 理由**:
- 用户主诉「8080 没继承 8088 能力」 → B 直接解
- 老 v1 没生产用户(`.40:8088` 是 staging,不是 prod) → 数据隔离可接受
- 把 chat-stream / admin/review / agents 分到 v2 是真升级(新内核 + SSE event_id 续传 + Cron-style admin)
- M9-M12 真要做也以本方案作为底座(v2 endpoint 一个个补齐时,只需修改 `.40` 路由表把对应 path 从 v1 路由切到 v2)

---

## §3 拓扑详图(目标态)

```
                              ┌─────────────────────────────────────┐
                              │  .53 后台双轨                       │
                              │                                     │
       ┌──────────────────────┼─→  v1  (uvicorn :7788)              │
       │ 路由集 R1            │       PRAXIS-hou v0.1.0             │
       │                      │       完整 35+ /api/*               │
       │                      │                                     │
       │                      │                                     │
       │ 路由集 R2            │       PRAXIS-2 v0.9.0+v2.0.1        │
       └──────────────────────┼─→  v2  (gunicorn :8001)             │
                              │       chat/auth/me/admin-review/    │
                              │       agents                        │
                              └─────────────────────────────────────┘
                                         ↑
                ┌────────────────────────┴───────────────────────────┐
                │  .40   praxis2_proxy_unified.py (本计划新增)        │
                │                                                    │
                │  :8088    分流反代:                                │
                │           R2 = {/api/chat-stream, /api/auth/*,     │
                │                 /api/me, /api/me/balance,          │
                │                 /api/me/account,                   │
                │                 /api/admin/review/*,               │
                │                 /api/agents, /api/info}            │
                │                                                    │
                │           → http://10.102.106.53:8001 (v2)         │
                │                                                    │
                │           R1 = 其余 /api/*                          │
                │           → http://10.102.106.53:7788 (v1)         │
                │                                                    │
                │           静态 SPA → /home/hipeson/mzy/PRAXIS-2-fe/dist
                │                                                    │
                │  :8080   已停                                       │
                │  :8088 上的老 server.py 也已停                      │
                └────────────────────────────────────────────────────┘
                              ↑
                         浏览器 http://10.102.106.40:8088/
```

### 3.1 R2 白名单(走 v2)的精确正则

```python
R2_PATTERNS = [
    r"^/api/chat-stream$",
    r"^/api/info$",
    r"^/api/agents$",
    r"^/api/auth/(login|logout|logout-all|register|email/send-code)$",
    r"^/api/me$",
    r"^/api/me/balance$",
    r"^/api/me/account$",
    r"^/api/admin/review/(pending|approve|reject)$",
    r"^/chat/permission$",   # M5 ASK 回调
]
# 凡 /api/* 不命中 R2,落 R1 (v1 .53:7788)
```

### 3.2 前端 dist 选择

**用 `PRAXIS-2/frontend/` 当前 build**(v2.0.1,`praxis-qian@0.7.15`),因为它:
- SSE 事件名已对齐 v2 协议(`text_delta/final/tool_*`,见 `frontend/src/App.tsx:194-263`)
- `/api/agents` 失败有 fallback 12 学科卡片
- `/api/me` 嵌套 unwrap 适配 v2 shape
- 多数 modal(MD/Spawn/Storage/Proposals)在调用 v1 endpoint 时仍能工作(R1 分流)

**老 `PRAXIS/dist/`(5月17)** 不再用,因为:
- 调 `/api/auth/sms/send-code`(v1 phone-based),与 v2 `email/send-code` 不兼容,登录会回退到 v1 系统,用户数据继续留在 v1 → 与「v2 是主」目标相悖
- SSE 事件名是老的(`meta/status/answer/done`)

---

## §4 实施步骤(估时 1 天)

### Task 1 — 写 unified proxy 脚本(本机,~2 小时)

新文件:`PRAXIS-2/deploy/praxis2_proxy_unified.py`

**关键设计**(对 §0.2 矩阵的代码化):
- 复用现有 `/home/hipeson/mzy/PRAXIS/server.py`(PRAXIS-proxy/0.2)作为骨架(它已有 SPA fallback + Cache-Control + X-Forwarded-For + 流式 forward + 502 错误页),
  **加一层路径正则分流**到两个 upstream。
- env:
  - `PRAXIS_V2_UPSTREAM` 默认 `http://10.102.106.53:8001`
  - `PRAXIS_V1_UPSTREAM` 默认 `http://10.102.106.53:7788`
  - `PRAXIS_PROXY_PORT`  默认 `8088`
  - `PRAXIS_PROXY_DIST`  默认 `/home/hipeson/mzy/PRAXIS-2-fe/dist`
- 日志结构化(JSON line)写 `/tmp/praxis2-proxy.log`:
  ```json
  {"ts":"...","method":"POST","path":"/api/chat-stream","upstream":"v2","status":200,"dur_ms":1820}
  ```
- 健康检查:`GET /__proxy/healthz` 返 `{v1:OK|FAIL, v2:OK|FAIL, ts:...}`(同步 ping 两端的 `/api/info`)

### Task 2 — 部署目录布局(.40,~30 分钟)

```bash
# 在 .40 上建一个独立目录,不污染老 PRAXIS/
ssh hipeson@10.102.106.40 'mkdir -p /home/hipeson/mzy/PRAXIS-2-fe'

# 推 dist
rsync -avz --delete frontend/dist/ \
  hipeson@10.102.106.40:/home/hipeson/mzy/PRAXIS-2-fe/dist/

# 推 unified proxy
scp deploy/praxis2_proxy_unified.py \
  hipeson@10.102.106.40:/home/hipeson/mzy/PRAXIS-2-fe/server.py
```

最终 `.40` 目录:
```
/home/hipeson/mzy/
├── PRAXIS/             ← v1 deployment(留作 fallback,不动)
│   ├── server.py
│   └── dist/
├── PRAXIS-2/           ← 本机源码 + 旧 :8080 部署(可删 :8080 后清理)
│   └── dist/
└── PRAXIS-2-fe/        ← v2.1 新部署(本计划目标)
    ├── server.py       ← praxis2_proxy_unified.py
    └── dist/
```

### Task 3 — 切流量(.40,~5 分钟)

```bash
# 1. 停 :8080 临时辅道
ssh hipeson@10.102.106.40 'pkill -f praxis2_proxy.py'

# 2. 停 :8088 老 server.py(分流脚本要占用此 port)
ssh hipeson@10.102.106.40 'cat /home/hipeson/mzy/PRAXIS/server.pid \
    | xargs -r kill 2>/dev/null; pkill -f "PRAXIS/server.py"'

# 3. 起 unified
ssh -f hipeson@10.102.106.40 \
    'cd /home/hipeson/mzy/PRAXIS-2-fe && \
     exec python3 server.py > /tmp/praxis2-proxy.log 2>&1'

# 4. 验
curl -s http://10.102.106.40:8088/__proxy/healthz
```

### Task 4 — 验收 smoke(~30 分钟)

完整跑下面 9 条 curl,**全过 = ship**;有任意红停 = §6 回滚:

```bash
BASE=http://10.102.106.40:8088
EMAIL="test$(date +%s)@example.com"

# T4.1  /healthz 含 v1,v2 状态
curl -s $BASE/__proxy/healthz

# T4.2  /api/info 命中 v2
curl -s $BASE/api/info | grep -q '"service": "PRAXIS-2"' && echo OK || echo FAIL

# T4.3  /api/me 命中 v2(无 cookie 返 401 JSON,非 SPA HTML)
curl -s -i $BASE/api/me | head -3

# T4.4  /api/spawn/list 命中 v1(无 cookie 返 v1 风格 401)
curl -s -i $BASE/api/spawn/list | head -3

# T4.5  /api/agents 命中 v2(v2.0.1 已实现,返 12 学科 JSON)
curl -s $BASE/api/agents | python3 -c "import sys,json;print(len(json.load(sys.stdin)['agents']))"
# → 12

# T4.6  CORS preflight 同 origin 无 CORS 头(预期)
curl -s -i -X OPTIONS $BASE/api/chat-stream \
  -H 'Origin: http://10.102.106.40:8088' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' | head -5

# T4.7  v2 注册闭环
curl -s -c /tmp/cj -X POST $BASE/api/auth/email/send-code \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"purpose\":\"register\"}"
# 注意 dev_code 在 dev_note 里,生产 SMTP 接好后此项失效

# T4.8  SSE chat-stream (v2 真合约) 至少 5 帧
N=$(curl -sN -X POST $BASE/api/chat-stream \
  -b /tmp/cj -H 'Content-Type: application/json' \
  -d '{"agent":"general","message":"hello"}' | grep -c '^event: ')
[ "$N" -ge 5 ] && echo "SSE OK($N events)" || echo "SSE FAIL($N)"

# T4.9  浏览器真打开
open http://10.102.106.40:8088/   # 或在内网机器手测
```

### Task 5 — 文档同步(~30 分钟)

更新以下文件:
- [PRAXIS-2/TEST-WEB-BACKEND-FRONTEND.md](./PRAXIS-2/TEST-WEB-BACKEND-FRONTEND.md):
  - §1 表里 staging 入口改为 `.40:8088`(同 origin,不再写跨域 origin)
  - §2.2 表加列「分流到 v1/v2」
  - §3 用例:CORS preflight 用例改为「同 origin,无 ACAO 头是预期」
- [PRAXIS-2/VERSION-STATUS-v2.0.md](./PRAXIS-2/VERSION-STATUS-v2.0.md):末尾加 v2.1 节
- 删除 [PRAXIS-2/deploy/praxis2_proxy.py](./PRAXIS-2/deploy/praxis2_proxy.py)(被 unified 取代)
- 不动 [PRAXIS-2-v1.x-API-parity-移交.md](./PRAXIS-2-v1.x-API-parity-移交.md)(它仍是 M9-M12 远期路线图,与本计划互补)

---

## §5 回归矩阵(每次推 v2.1 后必跑)

| 类别 | 命令 | 期望 |
|---|---|---|
| 后端单元测 | `pytest -q tests/ -k "not integration" --ignore=tests/test_skills` | 1543 pass(基线) |
| FE typecheck | `cd frontend && npm run typecheck` | 0 error |
| FE build | `cd frontend && VITE_API_BASE='' npm run build` | dist/ 含 index-*.js |
| dist 校验 | `grep -oE '"text_delta"\|"final"' dist/assets/index-*.js` | 两条都在 |
| dist 不漏 base | `grep -oE '10\.102\.106\.53' dist/assets/index-*.js` | **空**(VITE_API_BASE='' 才对) |
| .40 smoke | §4 Task 4 九条 | 全过 |

---

## §6 回滚预案(30 秒)

```bash
# 1. 停 unified
ssh hipeson@10.102.106.40 'pkill -f PRAXIS-2-fe/server.py'

# 2. 起回老 server.py + 老 dist(它还在原位)
ssh -f hipeson@10.102.106.40 \
    'cd /home/hipeson/mzy/PRAXIS && exec python3 server.py --port 8088'

# 3. 验 8088 回到 v1 dist 调 v1 后端
curl -s http://10.102.106.40:8088/api/info | grep PRAXIS-hou
```

判据触发回滚:
- §4 T4.2 / T4.4 / T4.8 任一失败
- 用户报告主聊天断流且看 backend log 无错(说明 unified 反代 SSE buffer 出问题)
- `/tmp/praxis2-proxy.log` JSON line 持续 502 v1 upstream

---

## §7 已知不变与已知偏差

### 7.1 仍然不动的
- `.53:7788` 老 v1 后端(D2 边界:不动 v1 后端,在线用户原话来自移交文档 §2)
- 老 PRAXIS dist(留作 fallback,但默认不再 serve)
- v1 后端的用户表(不迁移,v2 是独立账号体系)

### 7.2 主动接受的偏差
- **v1 v2 用户互不可见**:用户在 v2 注册的账号(email-based)不会出现在 v1 admin/users 列表里(后者读 v1 PG 表)。
  这一版承认这个偏差,在 admin 面板里看到的「用户列表」就是 v1 用户表,要看 v2 用户需通过 v2 自己的 admin/review 通道(暂无)。
- **v2 注册的用户没有 spawn/md/files 访问权**:因为这些 endpoint 反代到 v1,v1 检查 v1 session cookie,
  v2 颁的 cookie 在 v1 不识别 → 401。**期望体验**:用户用 v2 账号登录 → 主聊天可用,
  打开 MD/Spawn/文件管理 modal 会 401 提示「权限不足或需要单独的 v1 账号」。
- **Cookie 名冲突**:v1 用 `praxis_session=`,v2 也用 `praxis2_sid=`,name 不冲突,但浏览器同 origin 会都带上,
  后端各取所需,不会互相污染。

### 7.3 留给 v2 完整 parity 的接口
- 任意时点,只需把 §3.1 R2_PATTERNS 加一条新 path(比如 v2 实现了 `/api/spawn/list`),
  下次推 unified server.py 自动切。**无前端变动**,**无第二个 dist**,**无 CORS 改动**。
- 这就是 [移交.md §1 「v2.0 切换判据」](./PRAXIS-2-v1.x-API-parity-移交.md) 的本计划改写版:
  从 "全切换 .40 的 BACKEND_URL 一个 env" 变成 "R2_PATTERNS 表里加一条"。

---

## §8 时间表

| 当日 | 0.5 d | Task 1 unified.py 编码 + 单元自测 |
| 当日 | 0.2 d | Task 2 部署目录 + rsync |
| 当日 | 0.05 d | Task 3 切流量 |
| 当日 | 0.2 d | Task 4 smoke 9 条 |
| 次日 | 0.5 d | Task 5 文档同步 + 观察 24h |
| **总** | **~1.5 d** | v2.1 ship |

---

## §9 关键开关 / 文件清单

| 项 | 位置 | 谁动 |
|---|---|---|
| unified proxy 源码 | `PRAXIS-2/deploy/praxis2_proxy_unified.py`(待写) | 本机 |
| unified proxy 部署点 | `.40:/home/hipeson/mzy/PRAXIS-2-fe/server.py` | scp |
| 新 dist | `.40:/home/hipeson/mzy/PRAXIS-2-fe/dist/` | rsync |
| R2 路由表 | unified proxy 顶部常量 `R2_PATTERNS` | 改后重启 server.py |
| v1 backend URL | env `PRAXIS_V1_UPSTREAM` | 系统环境变量 |
| v2 backend URL | env `PRAXIS_V2_UPSTREAM` | 系统环境变量 |
| 日志 | `.40:/tmp/praxis2-proxy.log` | tail -f |
| 健康检查 | `http://10.102.106.40:8088/__proxy/healthz` | 任意 curl |

---

## §10 后续路线(本计划完成后)

1. **v2.2** — 在 v2 backend 实现 `/api/me/profile` + `/api/me/proposals` + `/api/proposals`(轻量,2 天),
   R2_PATTERNS 加 3 条,从 v1 摘下来
2. **v2.3** — v2 backend 接 ResourceGate + `/api/spawn{,/list,/get}`(M7 carry 已 prepped),~1 周
3. **v2.4** — v2 backend 真接 `/api/md/*`(需 .53 GPU 池 ssh 通道,~1-2 周)
4. **v2.5** — v2 backend admin/users + ledger + audit(读 v2 PG,需要先做 v1→v2 用户迁移工具),~1-2 周
5. **v3.0** — v1 后端 `:7788` 关停,unified proxy 简化为单一 upstream → `:8001`,删 R1/R2 分流

每个里程碑只动 unified server.py 顶部 `R2_PATTERNS` 一行 + 重启,前端零改动。

---

---

## §11 未来:云上反代 + 多后端集群(v3+ 前瞻)

> 用户已确认:本计划是过渡;**v3 起 `.40` 这个反代角色要迁到腾讯云,后台也是多服务器**。
> 本节定 v2.1 设计中**哪些不能挡 v3 路**的约束,让从 stdlib python server.py 升级到云上 CLB/nginx
> 时**配置可平移、不需要重写前端**。

### 11.1 v3 目标拓扑

```
                                                         ┌─────────────┐
                                                         │  .53A       │ ← v2 backend 主
                                                         │  :8001      │
                                                         └─────────────┘
公网入口                                                  ┌─────────────┐
                ┌────────────────┐                       │  .53B       │ ← v2 backend 备(可 active-active)
domain.com ────→│  腾讯云 CLB    │── upstream pool v2 ──→│  :8001      │
                │  (或 nginx /   │                       └─────────────┘
                │  Caddy on TX)  │                       ┌─────────────┐
                │                │── upstream pool v1 ──→│  .53 (旧)   │ ← v1 backend 保留态(可被 v3.0 弃用)
                │                │                       │  :7788      │
                │                │                       └─────────────┘
                │                │                       ┌─────────────┐
                │                │── static (SPA dist) ─→│  COS bucket │ ← 静态站托管(不再 SimpleHTTPServer)
                └────────────────┘                       └─────────────┘
                       │
                       ├── HTTPS termination (Let's Encrypt / 腾讯云证书)
                       ├── HTTP→HTTPS 强转
                       ├── WAF / DDoS basic
                       └── 健康检查 /api/info + /__proxy/healthz
```

### 11.2 v2.1 设计中哪些不能挡 v3 路(硬约束)

| 决策 | v2.1 做法 | v3 平移路径 | 约束 |
|---|---|---|---|
| **路由表表达式** | `R2_PATTERNS` 是 Python 正则常量 | 翻译到 nginx `location ~ ^/api/(chat-stream\|info)` block / 腾讯云 CLB 监听规则 / Caddy `@match path_regexp` | 正则**用 nginx-PCRE 兼容子集**(不用 Python 独有的 `(?P<name>)` 命名组、`\A`/`\Z` 等),保平移可逐条 sed |
| **upstream 表达** | 两个 env(`PRAXIS_V1_UPSTREAM`/`PRAXIS_V2_UPSTREAM`)各一个 host:port | nginx `upstream v2_pool { server .53A:8001; server .53B:8001 backup; }` | env 名留出**复数可能**:`PRAXIS_V2_UPSTREAMS`(逗号分隔)→ Python 端实现 round-robin。v3 直接迁到 LB 的 server pool 字段 |
| **流式 forward** | 用 stdlib `http.client` 4KB 读 + flush | nginx `proxy_buffering off; proxy_request_buffering off; proxy_read_timeout 1800s;` | **绝不**在 v2.1 引入 buffering,以免 v3 切 nginx 时 SSE 突然出 1KB chunk 才 flush |
| **Cookie 域** | 同 origin(`.40:8088` 一个 host) | 公网域名(如 `praxis.example.com`),v1/v2 cookie 仍走同 host | v2.1 不设 `Domain=` attribute,继承默认 host-only。v3 加 `Domain=.example.com` 时需保证 v1+v2 后端的 `cookie_domain` 配置同步改 |
| **CORS** | 同 origin 不发 CORS 头 | 公网域名仍同 origin(SPA + API 同 domain) | **不靠 CORS** 跨 host 工作。若 v3 真要 SPA / API 分 domain(`app.example.com` + `api.example.com`),CORS 头必须由 LB/nginx 加,**v2 后端的 `allowed_origins` 也要相应扩** |
| **HTTPS** | v2.1 全 HTTP(局域网 staging) | v3 强 HTTPS;v2/v1 后端仍 HTTP,LB 终止 TLS | 后端**信任 `X-Forwarded-Proto`** 决定 cookie `Secure` flag(`praxis2/config.py:cookie_secure` 已是 settings 字段,v3 只改 env) |
| **健康检查 path** | `/__proxy/healthz` 同步 ping v1/v2 `/api/info` | 腾讯云 CLB 健康检查指 `/__proxy/healthz`,200 = OK | v2.1 实现就用此 path,v3 直接复用 |
| **日志** | stdin JSON line 写 `/tmp/praxis2-proxy.log` | 腾讯云 CLB 自带访问日志 + 应用层 nginx access_log JSON | v2.1 JSON shape 提前定:`{ts, method, path, upstream(v1\|v2\|static), status, dur_ms, user_id?}` → v3 同 schema 可入 CLS/ES |
| **跨机 session** | v2.1 单机 fakeredis OK;但 v2 真后端用 `make_redis_client` 已是真 Redis | v3 多 backend 实例 → Redis 必须**共享**(腾讯云 Redis 实例,VPC 内网) | M9 `auth/middleware.py` 已用 Redis 存 session,**不在进程内**,这条已天然满足 |
| **DB pool** | v2.1 后端 PG 单实例 | v3 主从 / Pooler(pgbouncer 或腾讯云 TDSQL) | `make_pg_pool(db_url)` 已是 asyncpg pool,把 url 切 pooler 不动代码 |

### 11.3 v2.1 → v3 迁移点检表(写完 v2.1 时立刻贴在 §6 旁)

```
[ ] R2_PATTERNS 全部 nginx-PCRE 兼容(用 `pcretest` 离线验证)
[ ] upstream env 改成 LIST 风格(逗号分隔),v2.1 单元素也接受
[ ] healthz JSON shape 定稿,v2.1 已按此输出
[ ] 日志 JSON shape 定稿,v2.1 已按此输出
[ ] cookie 全 host-only(no Domain attr),v2 后端验证
[ ] 后端读 X-Forwarded-Proto 决定 Secure 标志,v2 后端验证
[ ] SSE buffering OFF 路径写入 §3 文档,v3 nginx 复刻
[ ] dist 上传到 COS 的 manifest 脚本(deploy/push_dist_cos.sh)预制,v3 一键启用
```

### 11.4 v3 阶段会变更的内容(本计划无需准备)

- HTTPS 证书申请(腾讯云 SSL/Let's Encrypt)
- 域名 + DNS(走腾讯云 DNSPod)
- 公网 ACL(腾讯云安全组)、限流、WAF
- 真 SMTP / 短信(替换 DevEmailGateway)
- 对象存储(COS)直挂 SPA dist,LB 静态路由直接走 COS
- v1 后端是否在 v3 时关停(由 §10 v3.0 决策)
- 多 backend 实例的灰度发布工具(腾讯云 CLB 权重 / nginx upstream weight)

### 11.5 多服务器情境下 v2.1 仍可用的程度

- 如果 v3 之前**先**有需求把 v2 backend 跑 2 个实例(比如 .53A + .53B),
  v2.1 stdlib server.py **只要把 R2 这一个 upstream env 改成 `host:port` 列表**(本计划 §11.2 第二行已要求),
  proxy 加 5 行 round-robin 即可,**不需要等 v3**。
- 但若需要会话粘性(sticky)、健康剔除、慢节点退避 等,stdlib 写不动,直接迁 v3。

---

## 附录 A:与既有文档的关系

| 文档 | 关系 |
|---|---|
| [PRAXIS-2-v1.x-API-parity-移交.md](./PRAXIS-2-v1.x-API-parity-移交.md) | 远期 M9-M12 路线;本计划是其**短期低成本替身** |
| [PRAXIS-2/TEST-WEB-BACKEND-FRONTEND.md](./PRAXIS-2/TEST-WEB-BACKEND-FRONTEND.md) | 测试用例;本计划 §4 Task 4 引用其 §3 体例 |
| [PRAXIS-2-上线清单-v1.0.1.md](./PRAXIS-2-上线清单-v1.0.1.md) | v1 staging 清单;本计划承接其「.40:8088 入口」结论 |
| [PRAXIS-2/deploy/push_frontend.sh](./PRAXIS-2/deploy/push_frontend.sh) | 仅做 rsync;本计划要 scp 多一个 server.py,push_frontend.sh 不变 |

## 附录 B:不在本计划做的事

- **不动 v1 后端**(在线用户)
- **不改前端源码**(v2.0.1 是当前 dist,不为 v2.1 再 patch)
- **不写 nginx config**(.40 没 sudo)
- **不接真 SMTP**(dev_code 仍在响应体回显;生产前 carry)
- **不做用户迁移**(v1 ↔ v2 用户系统并存,见 §7.2)
- **不做监控告警**(只有 stdin log,Grafana/Prometheus 是 v3 carry)
