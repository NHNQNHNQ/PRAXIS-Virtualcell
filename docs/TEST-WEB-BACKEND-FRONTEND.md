# PRAXIS-2 前后端测试计划（测试 + 审计 + gap 验收）

> **日期**: 2026-06-05 · **base**: v0.18.0（`6167ee2`）· **形态**: 三合一（现状审计 + 可执行测试用例 + 缺失能力验收/路径）
> **审计依据**: 2026-06-05 server/前端审计。本文取代 2026-05-22 的 v0.9.1 旧版（旧版 18 端点、SSE mismatch 等已严重过时）。
> **环境**: 前端/反代 `http://10.102.106.40:8080` → 后端 `http://10.102.106.53:8001`（gunicorn ×2）→ litellm `127.0.0.1:4000`。本地 dev：后端 `uvicorn praxis2.server:make_app --factory --port 8001`，前端 `cd frontend && npm run dev`。
> **图例**: ✅ DONE · ⚠ PARTIAL/风险 · ❌ MISSING · 🔌 实现完整但未接入生产
> **配套**: 智能体框架测试见 `TEST-AGENT-FRAMEWORK.md`

---

## 0. 现状审计速览（重点关切）

- **栈**：后端纯 ASGI（不依赖 FastAPI）`praxis2/server/app.py`；前端 React18 + TS + Vite，dist 已构建版本 **0.17.0**（与 `/api/info` 对齐，历史 dist mismatch 已修）。
- **端点**：旧版 18 个 → 现 **~40+**（spawn/md/files/admin v2/proposals 全新增）。
- **关键 gap（用户最关心）**：
  - **跨会话用户记忆 ❌ MISSING**：SessionPool 是内存（重启丢）；`SessionStore`（`memory/session.py`）实现完整但**未接入生产**；前端对话历史纯 localStorage（换设备/无痕清零）；唯一跨会话持久的是 user_profile（画像，非对话）。**FE 还不传 session_id** → 后端每次 uuid4 fallback，同用户每条消息都是新 session。
  - **ASK 弹窗 UI ⚠ 未实现**：后端发 `control_request`，前端目前仅 StatusStrip 文字提示（`App.tsx` 注释"弹窗待补"）。
  - **多 worker 限流协调 ⚠**：`ratelimit.py` 单进程内存计数，多 worker 配额可被绕过。

---

## 1. HTTP 端点测试（全表 ~40）

> 端点权威来源：`server/app.py:335-379`（`_routes`）+ `auth/routes.py:580-592`（`ROUTES`）。鉴权：cookie `praxis2_sid`（`auth/middleware.py`，HMAC+Redis session）。

### 1.1 Auth（`praxis2/auth/routes.py`）
| 端点 | 方法 | 鉴权 | 测试用例 |
|---|---|---|---|
| `/api/auth/email/send-code` | POST | 否 | TC-EP-01 发码（SMTP 未配走 DevGateway dev_code）|
| `/api/auth/register` | POST | 否 | TC-EP-02 注册 → set-cookie + signup_gift 入账 |
| `/api/auth/login` | POST | 否 | TC-EP-03 登录成功；TC-EP-04 **5 次密码错锁 email、20 次锁 IP**（双维度 `routes.py:259-263`）|
| `/api/auth/logout` / `logout-all` | POST | 否/是 | TC-EP-05 logout-all 杀全 session → 旧 cookie 失效 |
| `/api/me` `/api/me/balance` `/api/me/profile` | GET/POST | 是 | TC-EP-06 me 11 字段；TC-EP-07 profile upsert/get（**唯一跨会话持久的用户数据**）|
| `/api/me/account` | DELETE | 是 | TC-EP-08 软删 |
| `/api/info` | GET | 否 | TC-EP-09 健康检查（version v0.17.0）|

### 1.2 Chat / Permission
| `/api/chat-stream`（+legacy `/chat/stream`）| POST | 是 | TC-EP-10 SSE 主流（见 §2）；无 cookie → 401 |
| `/chat/permission` | POST | 是 | TC-EP-11 ASK 决策回传（见 §2 control_request）|

### 1.3 Agents / Files
| `/api/agents` | GET | 否 | TC-EP-12 13 学科元数据+models+pricing |
| `/api/agents/profile` | GET | 是 | TC-EP-13 |
| `/api/files`（GET 列/POST 上传 multipart）| | 是 | TC-EP-14 上传→列出→`/api/files/{id}/content` 下载→DELETE 软删；`/api/files/usage` 配额 |

### 1.4 Spawn / MD
| `/api/spawn`（POST 提交）`/api/spawn/list` `/api/spawn/get/{id}` `/api/spawn/cancel/{id}` | | 是 | TC-EP-15 见 §4；跨租户 get → 404 |
| `/api/md/submit` `/api/md/runs` `/api/md/gpu-pool` `/api/md/jobs/{id}` `/api/md/jobs/{id}/cancel` | | 是 | TC-EP-16 提交 MD HPC 作业→列→详情→取消 |

### 1.5 Admin v2 / Proposals
| `/api/admin/review/{pending,approve,reject}` | | admin | TC-EP-17 审核流 |
| `/api/admin/users` `/users/{id}/adjust` `/freeze` `/unfreeze` | | admin | TC-EP-18 用户管理+调账+冻结 |
| `/api/admin/{reconcile,ledger,audit-log,stats}` | | admin | TC-EP-19 对账/总账/审计日志/统计 |
| `/api/proposals` `/api/me/proposals` `/api/admin/proposals` `/api/admin/proposals/{id}/decide` | | 是/admin | TC-EP-20 提案提交→审核 |

**TC-EP-AUTH-BOUNDARY 权限边界（必测）**：所有 `是` 端点无 cookie → 401；所有 admin 端点 non-admin → 403。

---

## 2. SSE 协议测试（14 事件类型）

> 权威：`server/sse.py:14-18` + `_map_kernel_event()`。前端消费 `frontend/src/App.tsx:255-389`（已对齐，v2.0.1 修了旧 meta/status/answer/done mismatch）。

| SSE event | 触发 | 关键字段 |
|---|---|---|
| `text_delta` | 模型吐字 | text |
| `tool_start` / `tool_end` / `tool_progress` | 工具生命周期 | tool_use_id/name/input、is_error/content、message |
| `thinking_delta` | reasoning 流 | text（FE 暂不独立渲染）|
| `phase_change` | RMCP 相位切换 | to |
| `compact_boundary` | 上下文压缩 | reason |
| `control_request` / `control_cancel_request` | ASK 确认/取消 | request_id/tool/description |
| `auth_status` | 会话过期 | status:"expired" |
| `queue_position` | 限流排队 | position/eta_s |
| `final` / `error` | 正常/异常结束 | reason、message |
| `stream_event` | 内核事件包装（含 spawn）| original.type（spawn_started/spawn_skipped/agent_route_warning）|

**测试用例**：
- **TC-SSE-01** text_delta 累积成完整文本；event_id 单调递增。
- **TC-SSE-02** tool_start/tool_end 成对，is_error 正确（接框架文档 §2）。
- **TC-SSE-03** control_request → 前端能渲染（⚠ 当前仅 StatusStrip 文字，弹窗见 GAP-B-2）→ `/chat/permission` 回传 → 流继续。
- **TC-SSE-04** queue_position 背压（接 §1 限流）。
- **TC-SSE-05** final reason ∈ {stop,max_turns,escalated}；error 带 message 不裸 500。
- **TC-SSE-06** stream_event.original.type=spawn_started 触发前端轮询（§4）。

---

## 3. Auth 全链路 + 安全

**TC-FLOW-AUTH（端到端）**：send-code → register（cookie + balance 流水）→ `/api/me` → profile upsert → profile get → logout-all → 再访 `/api/me` 返 401（cookie 失效）。
**安全**：
- TC-SEC-01 登录失败锁：同 email 错 5 次锁、同 IP 错 20 次锁（独立 Redis key）。
- TC-SEC-02 cookie 属性：HttpOnly、SameSite（staging Lax）、Secure（生产开）。
- TC-SEC-03 session TTL：`session_ttl_days` 后失效。
- TC-SEC-04 跨租户隔离：A 的 cookie 访问 B 的 `/api/spawn/get/{id}` / `/api/files/{id}` → 404/403。

---

## 4. Spawn auto 全链路

> `spawn/handlers.py` + `App.tsx:317-388`。spawn task 落 PG `spawn_tasks`（重启不丢记录，但 running 的 asyncio task 重启不自动恢复）。

**TC-SPAWN-01 auto 模式回填**：mode=auto 发消息 → chat 完成 end_reason=stop → 后端 `parse_executable_spec` → `create_spawn_task` → SSE `stream_event.original.type=spawn_started`（带 task_id）→ 前端每 2s GET `/api/spawn/get/{taskId}` → status=done → answer 回填同一气泡（"📤 任务完成 · Ns"）。
**TC-SPAWN-02** `/api/spawn/list` 含该任务；`/api/spawn/cancel/{id}` 可取消。
**TC-SPAWN-03** 手动 POST `/api/spawn`（FE SpawnModal）独立路径。
**TC-SPAWN-04 安全网**：前端轮询 30min×900 次超时停跟踪。
**TC-SPAWN-05（gap 说明）**：进程重启后 running 任务 DB 记录停在 running/pending，不自动续跑（见 GAP-B-4）。

---

## 5. 前端测试

> React18+TS+Vite，无路由库（单页 + state 切 AdminPanel）。`frontend/src/`。

- **TC-FE-01 typecheck + build**：`cd frontend && npm run build` 零错误，产物到 `dist/`。
- **TC-FE-02 版本同步**：`package.json` version ↔ `/api/info` version ↔ UserBar 显示一致（历史 mismatch 已修，回归保护）。
- **TC-FE-03 启动容错**：`/api/agents` 失败/返 HTML → 用 FALLBACK_AGENTS，不 bootErr（`App.tsx`）。
- **TC-FE-04 发消息**：`chatStream()` POST `/api/chat-stream` body `{agent,message,model,mode}` → text_delta 渲染。**注意 ⚠ 当前不传 session_id**（见 GAP-B-1）。
- **TC-FE-05 工具可见**：tool_start/tool_end → StatusStrip 展示（让用户看到"真在调工具"，反幻觉 UX）。
- **TC-FE-06 ASK**：control_request → ⚠ 当前仅文字提示，**弹窗未实现**（GAP-B-2）。
- **TC-FE-07 spawn 回填**：见 §4。
- **TC-FE-08 对话历史**：localStorage `praxis-split:conversations:{user.id}`（`lib/storage.ts`）→ ⚠ 换设备/无痕丢失（GAP-B-1）。
- **TC-FE-09 dogfood**：`gstack` 跑登录→选学科→发消息→看工具调用→截图。

---

## 6. 故障注入

| 场景 | 期望降级 |
|---|---|
| TC-FAULT-01 PG 挂 | 读写失败优雅报错，不 500 风暴 |
| TC-FAULT-02 Redis 挂（session）| 鉴权失败明确（401/503），不挂全站 |
| TC-FAULT-03 litellm 挂 | chat-stream 返 error 事件 + 友好 message |
| TC-FAULT-04 MCP server 挂 | 工具不注册/调用 ok=False，chat 不 500（接框架 TC-MCP-02）|
| TC-FAULT-05 spawn worker 异常 | 任务 status=error，前端轮询读到不卡死 |

---

## 7. gap 验收

**GAP-B-1 跨会话用户记忆**（❌ MISSING，用户明确问，**doc B 核心 gap**）
- 现状：SessionPool 内存（重启丢）；SessionStore（`memory/session.py`，🔌 实现完整含 blob_append→PgStore + resume()，仅测试引用未接生产）；FE 不传 session_id。
- 验收：① FE 生成并持久化 session_id（localStorage）随每次 chat 传入；② 后端 chat 路径接入 SessionStore，对话 transcript 落 PG；③ resume：重启 gunicorn / 换设备 / 重登后，凭 session_id（或用户最近会话列表）能恢复历史对话；④ 提供"我的会话列表"端点（`/api/me/sessions`）；⑤ 单测覆盖 append 原子性 + resume 不变量（已有 `test_memory_session*.py` 可复用）。
- 路径：`app.py` chat 路径在 SessionPool 之外接 SessionStore 落库；FE `App.tsx:251-253` 补 session_id；新增会话列表端点。优先级：高（用户核心诉求，虽本轮多选未勾，仍是 doc B 头号 gap）。

**GAP-B-2 ASK 弹窗 UI**（⚠ 未实现）
- 验收：control_request → 前端弹窗（工具名/描述/参数）→ 用户允许/拒绝 → POST `/chat/permission` 回传 request_id+decision → 流继续；超时（control_cancel_request）UI 复位。
- 路径：`App.tsx` 补 ASK 弹窗组件 + 决策回传；后端 bridge 已就绪（`permission_bridge.py`）。优先级：中（影响灰区命令/敏感操作的人审体验）。

**GAP-B-3 多 worker 限流协调**（⚠）
- 验收：多 gunicorn worker 下并发/QPS/inflight 配额经 Redis 原子计数协调，不被绕过。
- 路径：`ratelimit.py:86` 接口位换 Redis 实现。优先级：中。

**GAP-B-4 spawn 重启续跑**（⚠）
- 验收：进程重启后扫 PG 中 running/pending 任务 → 重新入队或标记 failed-需重试，不留僵尸。
- 路径：lifespan 启动时 spawn 恢复扫描。优先级：低。

---

## 8. 执行与通过线

### 8.1 怎么跑
- 后端单测：`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --junit-xml=/tmp/r.xml`。
- 端点 smoke：`curl -i`（看响应头/cookie，`-c /tmp/cj` 写 cookie jar）；SSE 用 `curl -N --no-buffer`。
- 前端：`cd frontend && npm run build`（typecheck+build）+ `gstack` 无头 dogfood。
- staging：经 `ssh zkyd@10.102.106.53` 看 gunicorn log（`tail /tmp/p.log`）。

### 8.2 通过线
| 维度 | 通过线 |
|---|---|
| 端点 | 全表 2xx/预期错误码 + 鉴权边界 401/403 全过 |
| SSE | 14 事件协议正确，event_id 单调，final/error 不裸 500 |
| Auth 安全 | 锁定/TTL/跨租户隔离全过 |
| Spawn | auto 全链路回填 + list/cancel |
| 前端 | build 零错 + 版本同步 + dogfood 主流程通 |
| 故障注入 | 全部优雅降级不 500 风暴 |

### 8.3 本轮重点 gap
1. **GAP-B-1 跨会话记忆**（接 SessionStore + FE session_id + 会话列表）——doc B 头号。
2. GAP-B-2 ASK 弹窗 UI。
3. GAP-B-3 多 worker 限流 Redis 协调。
- （框架侧 gap 见 `TEST-AGENT-FRAMEWORK.md`：相位门/stop_hook 接线、109 TODO skill 真验、MCP 生态+装 CC skills/mcp。）
