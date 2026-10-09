# Spec:GAP-B-1 子项目1 —— 后端跨会话记忆(SessionStore 接生产)

- **状态**:设计已批准(brainstorm 完成),本文是落地 spec,待用户 review → `writing-plans` → `subagent-driven-development`
- **范围**:**SP1 后端**(持久化 / resume / 端点)。SP2 前端(稳定 session_id + ConversationSidebar 接 `/api/me/sessions` + 切换恢复)作后续独立 spec,依赖 SP1 的 API
- **前序**:反幻觉链路完整(GAP-AH-1/2/3);本轮转跨会话记忆。模式同 GAP-AH——**已实现但未接生产的组件接进 chat 路径**
- **约束**:main 直接干(无 worktree);部署/e2e controller 亲做;commit 只 add 目标文件(工作区有 stray microbiome 文件,绝不 `git add .`);commit 末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## 1. 背景与问题

PRAXIS-2 的对话态在内存 `SessionPool`(LRU 200 × idle TTL 1h):同 `(user_id, session_id)` 跨请求复用服务端 `State`(messages / phase / recovery_attempts / stop_hook 等)。**进程重启即丢全部对话**;换设备 / 重登也无从恢复(FE 历史仅在 `localStorage`,跨设备/无痕丢失,TEST §TC-FE-08)。

`praxis2/memory/session.py` 已实现完整的持久层 `SessionStore`(transcript → blob append-only + UUID 幂等 + `resume()` 编排),**但仅测试引用,server/ 完全未接线**(grep 空)。`app.py:212` 注释已写明设计意图——"驱逐只丢内存副本,**权威态在 store**(§11.8)"——但从未落地。

GAP-B-1 = 兑现该意图:把 `SessionStore` 接进 chat 路径,让对话**跨重启 / 换设备 / 重登持久 + 恢复**。

**架构定位**:`SessionPool` 仍是**内存热缓存**(命中即快);`SessionStore` 是**权威持久层**。pool miss → 从 store resume 重建 `State` → 回填 pool;每轮把新增 entries append 进 store。两层职责正交,缓存丢失不丢数据。

---

## 2. 目标与非目标

### 2.1 SP1 目标(本轮)
1. chat 路径 pool miss 时,从 `SessionStore` resume 历史对话重建 `State`(而非今日的空 `State()`)。
2. 每轮把新增 transcript entries(user / assistant / tool_result)持久化进 PG(经 store blob append-only)。
3. 新增 `GET /api/me/sessions` 端点,列当前用户会话(供 SP2 侧栏)。
4. 后端从 chat body 读 `session_id`(SP2 真传前沿用现有 uuid4 fallback)。
5. **零回归**:无 PG 环境(测试 `FakeAuthRepository` 无 `_pool`)退回今日纯内存态,全量回归零失败。

### 2.2 非目标(SP1 明确不做)
- **SP2 前端**:稳定 session_id 生成/持久(localStorage)、随 chat 传入、ConversationSidebar 接 `/api/me/sessions`、切换会话恢复 UI。SP1 只提供后端 API。
- **不动 `query.py` 内核**:持久化在 chat 路径(query 外层)做 delta diff + append,不侵入 delicate core。
- 不做会话删除 / 改名 / 分享端点(YAGNI,需要时单独立项)。
- 不做跨会话**语义记忆**(检索增强);本 gap 只做**对话 transcript** 的持久与恢复。

---

## 3. 验收标准(映射 TEST §GAP-B-1)

TEST-WEB-BACKEND-FRONTEND.md §GAP-B-1 列 ①-⑤。SP1 认领 **②③④⑤(后端 + 单测)**;① 归 SP2(FE 生成/传 session_id)。

| # | 验收 | SP1 范围 | 判据 |
|---|------|---------|------|
| ① | FE 生成并持久化 session_id(localStorage)随 chat 传 | SP2 | —— SP1 只读 `body["session_id"]`,缺省 uuid4 fallback(`test_app_session_id_fallback.py` 不回归) |
| ② | 后端 chat 路径接入 SessionStore,transcript 落 PG | **SP1** | 一轮对话后,`load_transcript(user_id, session_id)` 能读回 user + assistant(+ tool_result)entries |
| ③ | resume:重启 / 换设备 / 重登后凭 session_id 恢复历史 | **SP1**(后端能力) | pool miss + store 有历史 → `resume()` 重建 `State.messages`;controller staging e2e:**重启 gunicorn 后凭同 session_id resume 出历史** |
| ④ | `/api/me/sessions` 端点 | **SP1** | `GET /api/me/sessions` 返回当前用户会话列表(session_id + 末时间 + title/preview) |
| ⑤ | 单测覆盖 append 原子 + resume 不变量 | **SP1** | 复用 `test_memory_session*.py` + 新增 chat-path resume 集成、端点、session_id round-trip、`SessionStore=None` 零回归 |

**整体通过线**:全量回归零失败(`tests/` 除 integration)+ controller staging e2e(重启 resume)+ KPI 无反幻觉回归(GAP-AH 门不受影响)。

---

## 4. 架构总览

```
chat-stream 请求(user_id, session_id, message)
        │
        ▼
  SessionPool.get(user_id, session_id)          ← 内存热缓存
        │
   ┌────┴─────────────┐
 hit│              miss│
   │                  ▼
   │      SessionStore 可用?
   │       ┌──────┴───────┐
   │      是│            否│(无 PG)
   │       ▼              ▼
   │  resume(ss,st,…)   State()        ← 今日行为(零回归)
   │  重建 messages/phase
   │       │
   └───────┴──► pool.put ──► st.messages.append(user) ──► query() ──► 流式 SSE
                                  │                          │
                            append_entry(user)        diff 新增 → append_entry(assistant/tool)
                                  │                          │
                                  └──────► SessionStore(权威持久层,PG blob)◄──┘

GET /api/me/sessions ──► store.meta_list("sessions", user_id) ──► [会话列表]
```

---

## 5. 组件设计

> 五组件忠实"已批准设计"。组件 2 精化为**直接复用 `session.py` 既有 `resume()` 编排**(核对代码后确认:它已打包去重→snip→relink→孤儿配对→中断注入→相位重建,比手动重建更稳、更少出错)。相位**写侧**持久见 §9 开放问题。

### 组件 1:实例化 SessionStore(`_pool` 兜底)
- **位置**:`app.py` `_App.__init__`(@214 `SessionPool` 实例化处旁)。
- **逻辑**(镜像 ledger@237 / files_repo@251 的 `_pool` 兜底):
  ```python
  # deps.repo._pool 存在(PgAuthRepository)→ 用 deps.store(PgStore)构 SessionStore
  # 无 _pool(FakeAuthRepository,测试)→ None,退回纯内存态(零回归)
  self._session_store = (
      SessionStore(self._deps.store)
      if getattr(self._deps.repo, "_pool", None) else None
  )
  ```
- **理由**:`SessionStore(store)` 构造要 `Store` 抽象(prod = `PgStore(pool)`,与 `deps.repo._pool` 同源);用 `_pool` 存在性作开关,与既有两个组件完全一致,测试路径零碰触。

### 组件 2:resume(pool miss)
- **位置**:`app.py:732`(`st = self._session_pool.get(...)`;`if st is None:` 分支)。
- **改动**:
  ```python
  st = self._session_pool.get(user_id, session_id)
  if st is None:
      st = State()
      if self._session_store is not None:
          # session.py 既有完整编排:load → dedup → snip → relink →
          # 孤儿 tool_result 配对 → 中断注入 → rebuild_phase,直接 set st.messages
          await resume(self._session_store, st, user_id=user_id, session_id=session_id)
      self._session_pool.put(user_id, session_id, st)
  ```
- **契约**:`resume(ss, state, *, user_id, session_id) -> ResumeResult(messages_count, needs_continue, phase, dropped_lines)`。空 transcript → `messages=[]`(等价新 `State()`,零回归)。
- **注意**:`resume()` 内部 `recover_orphaned_parallel_tool_results` 产出的 messages 格式(`{role, content}`,content 为 str 或 blocks)与 chat 路径 `st.messages.append({"role":"user","content":message})` 一致,直接可续轮。`needs_continue=True` 时已注入 `[resume] 上一轮未完成,请继续`。

### 组件 3:持久化(每轮 delta append)
- **位置**:`app.py` chat 路径——user append(@736)后 + `query()`(@752)结束后。
- **逻辑**:
  1. **user 消息**:`st.messages.append({"role":"user","content":message})` 后,立即 `append_entry(SessionEntry(type="user", content=message, …))`。
  2. **assistant / tool_result**:记录 query 前 `prev_len = len(st.messages)`;query 结束后对 `st.messages[prev_len:]` 逐条映射 → append:
     - `role=="assistant"` → `type="assistant"`,content 原样。
     - `role=="user"` 且 content 含 `tool_result` block → `type="user"`,content 原样(tool 结果回合)。
     - (纯 user 文本已在第 1 步落库,不在 delta 区,不重复。)
- **映射 & 幂等**(plan 阶段 TDD 定清):
  - `State.messages` dict(role/content)↔ `SessionEntry`(type/content/user_id/session_id/uuid)。
  - **每条新 entry 给稳定 uuid**(`uuid4().hex`);`append_entry` 是 O(1) `blob_append` 原子(已修 reviewer M1 C1),**只 append 本轮 delta,绝不重写整盘**。
  - 读侧 `load_transcript` 已按 uuid dedup;append-only + 每条新 uuid → resume 后续轮新消息天然不与历史撞 uuid。
  - `append_entry` 仅接受 `_LEGAL_TYPES`(user/assistant/system/attachment/phase-transition);**progress / 未完成 tool_use 不入库**(type 约束天然保证)。
- **失败隔离**:持久化异常**不得阻塞 chat 流**(try/except 包裹 + 可观测日志,等价"持久失败退化为内存态本轮")。
- **相位持久(§9.1-A 已决策,本组件子项)**:`query()` 结束后比对最终相位 `get_phase(st)` 与轮前相位,变则 `record_phase_transition(ss, …, to=<新相位>, uuid_=<新 uuid>)` 补一条 phase-transition entry(仍在 chat 路径,不动内核)。保证重启 resume 的 `rebuild_phase` 能恢复相位,GAP-AH 检索先行门不误拦 resume 后首轮。

### 组件 4:会话元数据注册 + `GET /api/me/sessions` 端点
- **store 来源**:meta 操作走 `self._deps.store`(`Store` 实例,prod=`PgStore`),统一 gated by `self._session_store is not None`(SessionStore 不暴露 `meta_*`,**不改 session.py**)。
- **注册(每轮 chat 后)**:query 成功后 `self._deps.store.meta_upsert("sessions", {"user_id": user_id, "id": session_id, "preview": <本轮 user 消息截断>, "updated_at": <time.time()>})`。`praxis_meta` 主键 `(table_name, user_id, pk=id)` → 首轮 INSERT、后续轮 `ON CONFLICT DO UPDATE SET row=EXCLUDED.row`(整行覆盖 row);DB `created_at` 列自动记首次时刻、后续 upsert **不覆盖**。**每轮 upsert 即可,无需判断首轮**。
- **端点** `("/api/me/sessions", "GET")` handler:
  - `if self._session_store is None: return []`(无 PG,零回归,测试路径不炸)。
  - `rows = await self._deps.store.meta_list("sessions", user_id)`(`meta_list` 只返 row JSON,SQL 按 DB `created_at` 升序);handler 按 `row["updated_at"]` **降序重排**(最近活动置顶),投影 `[{"session_id": r["id"], "preview": r["preview"], "updated_at": r["updated_at"]}]`。
- **鉴权**:走 `/api/me/*` 鉴权中间件,`user_id` 从认证态取(**不信任 body**);多租户隔离由 `meta_list` 的 `user_id` 过滤 + `Namespace` 保证。

### 组件 5:session_id from body
- **位置**:chat-stream 路由解析 body 处。
- **逻辑**:`session_id = body.get("session_id") or <现有 uuid4 fallback>`。FE `lib/api.ts` 已有 `session_id?` 字段(SP2 才真传)。
- **零回归**:`test_app_session_id_fallback.py`——不传 session_id 仍 uuid4 兜底,行为不变。

---

## 6. 数据流(端到端)

**写**:chat(session_id) → `pool.get` miss → `resume()` 重建 `State` → `pool.put` → user append + `append_entry(user)` → `query()` 流式 → diff 新增 → `append_entry(assistant/tool)` → `meta_upsert("sessions")`(每轮刷新 preview/updated_at)。

**读(resume)**:重启后 pool 空 → 同 session_id 再来 → `pool.get` miss → `resume()` 从 PG blob `load_transcript` → 重建 messages/phase → 续轮。

**列**:`GET /api/me/sessions` → `meta_list("sessions", user_id)` → 重排投影 → 用户会话列表。

---

## 7. 关键实现约束(给 writing-plans)

1. **复用 `resume()`,不手写重建**:`session.py` 既有 `resume(ss, state, *, user_id, session_id)` 已是完整编排;接线直接调,不要在 app.py 里手动 `load_transcript` + 拼 messages + `rebuild_phase`。
2. **delta append,非整盘重写**:`append_entry` O(1) 原子;每轮只追加本轮新增 entries。
3. **不动 query.py 内核**:持久化全部在 chat 路径(query 外层)。messages delta 从 `st.messages[prev_len:]` 取。
4. **uuid 策略 TDD 定清**:每条新 entry 稳定 uuid;读侧已 dedup;验证 resume 后续轮不产生重复 entry。
5. **兜底镜像既有模式**:`SessionStore=None` 开关用 `getattr(deps.repo, "_pool", None)`,与 ledger/files_repo 字面一致。
6. **持久失败不阻塞流**:try/except + 日志,降级内存态。

---

## 8. 边界与零回归

| 场景 | 处理 |
|------|------|
| 无 PG(测试 FakeAuthRepo 无 `_pool`) | `SessionStore=None` → resume/append/端点全短路 → 今日纯内存态(**零回归**) |
| 大 transcript resume | 现有 compaction / `apply_snip_removals` / `apply_preserved_segment_relinks` 处理 |
| 并发 append | `blob_append` 原子(已有,reviewer M1 C1 修复),无丢失 |
| resume 重复 entry | 读侧 `load_transcript` uuid dedup |
| 中断轮(末条 assistant 有 tool_use 无 result) | `recover_orphaned_parallel_tool_results` → `needs_continue` → 注入续跑提示 |
| 损坏 transcript 行 | `load_transcript` 跳过损坏行(`dropped_lines` 计数),不整会话失败 |
| 持久化异常 | try/except 包裹,不阻塞 chat 流,降级内存态 |

---

## 9. 风险与开放问题(**需用户 review 决策**)

### 9.1 相位(phase)写侧持久 ⚠ 关键

> **【已决策 · 用户 review 通过:方案 A —— 相位持久纳入 SP1】** 每轮 `query()` 后在 chat 路径(不动内核)比对最终相位,变则补 phase-transition entry。见组件 3 子项。
- **现象**:GAP-AH-1 让 chat 驱动相位机(`advance_phase_on_real_retrieval` post_hook 推进 `st.phase`),相位活在内存 `State`。`resume()` 内部 `rebuild_phase` 从 transcript **最后一条 `phase-transition` entry** 恢复相位——但**组件 3 只 append user/assistant/tool,从不 append `phase-transition`**。
- **后果**:重启后 resume,transcript 无 phase-transition → `rebuild_phase` no-op → 相位回退默认(INIT)。叠加 GAP-AH 检索先行门:**resume 后第一轮可能被门重新要求"检索先行"**,破坏会话连续体验。
- **HANDOFF 五组件未含相位持久**(忠实已批准范围,故列为开放问题而非擅自加组件)。
- **选项**:
  - **(A) 纳入 SP1**:每轮 `query()` 结束后,在 chat 路径(**不动内核**)比对最终相位 `get_phase(st)` 与轮前相位,变则 `record_phase_transition` 补一条 phase-transition entry。`rebuild_phase` 只取最后一条,故记录最终相位即足。resume 体验完整,GAP-AH 门不误拦。**推荐**——否则 resume 名义恢复、相位却丢,与 GAP-AH 直接打架。
  - (B) 拆为 SP1.1 follow-up:SP1 先只持久 messages,相位持久单独立项。范围更小,但留已知缺口。
- **建议**:选 (A),作为组件 3 的子项。请用户 review 时拍板。

### 9.2 会话列表排序 / 时间戳

> **【已决策 · 确认】** row 自存 `updated_at` + handler 降序重排。
- `praxis_meta` 只有 DB `created_at` 列(首次创建,`ON CONFLICT` upsert 不覆盖),**无 `updated_at` 列**;`meta_list` 仅返回 row JSON(不含 DB 列)。故"末活动时间 + 最近置顶"由 **row 内自存 `updated_at`** + handler 降序重排实现(已纳入组件 4)。确认无异议即可。

### 9.3 会话列表显示文案:preview(最近)还是 title(首条)

> **【已决策 · 方案 b】** preview = 最近一条 user 消息截断,每轮 upsert 覆盖。
- **推荐 (b) preview = 最近一条 user 消息截断**(每轮 upsert 覆盖):单次 upsert 无额外读,符合 IM 侧栏"显示最近消息 + 最近活动置顶",正好匹配 HANDOFF"末时间 + preview"。多模态/空消息截断边界 plan 处理。
- 备选 (a) title = 首条消息(稳定不变):需每轮 `meta_get` 读旧 title 再合并 upsert(多一次读),换取标题稳定。
- 本 spec 按 (b) 落组件 4。请 review 时确认。

---

## 10. 测试策略

### 10.1 复用既有(回归不破)
`test_memory_session.py` / `test_memory_session_resume.py` / `test_session_append_atomic.py` / `test_correctness_session_pool_wire.py` / `test_runtime_session_pool.py` / `test_app_session_id_fallback.py`。

### 10.2 新增
1. **chat-path resume 集成**:pool miss → `resume()` → State.messages 含历史(用内存 store 或 fake 注入,验证接线)。
2. **`/api/me/sessions` 端点**:注册 + 列出 + 多租户隔离(A 用户看不到 B)+ 无 store 返 `[]`。
3. **session_id round-trip**:body 传 session_id → 同 session_id resume 出同会话。
4. **delta append 正确性**:一轮后 transcript 含 user+assistant(+tool),无重复 uuid;resume 后再一轮不重复历史。
5. **`SessionStore=None` 零回归**:无 `_pool` 时 resume/append/端点全短路,行为等价今日。
6. **相位持久(§9.1-A 已决策)**:相位跃迁落 phase-transition;resume 后 `rebuild_phase` 恢复相位;**与 GAP-AH 门交互**——resume 后首轮不被检索先行门误拦。

### 10.3 全量回归
```
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?
```
解析 junit(汇总行被 sandbox 吞)。**零失败**。

### 10.4 controller 亲做 staging e2e
重启 gunicorn 后凭固定 session_id 直打 `/api/chat-stream`,验证历史 resume 出来(验收③后端能力);`GET /api/me/sessions` 返回该会话。ship 前可跑 `scripts/ship_gate.py`(需 `PRAXIS_EVAL_EMAIL/PASSWORD`,问用户取)。

---

## 11. 雷区

- **commit 只 add 目标文件**:工作区常驻 stray `brains/microbiome/skills/workflows/cooccurrence_network_real/run.py`(modified)+ 未跟踪 `brains/microbiome/memory/cases/microbiome-01{4,5,6,7}-*.md`、`rules/14-*.md`、`skills/workflows/{cross_feeding_gem,phage_host_link}/`——**绝不 `git add .`/`-A`**。
- **无 PG 测试路径**(FakeAuthRepo 无 `_pool`)→ `SessionStore` 必须可为 None,否则破全量回归。
- **subagent 给完整 task 文本**(别让它读 plan 文件);delicate core(query.py/app.py)改动 controller 细审 diff——本 spec 已约束**不动 query.py 内核**。
- resume 重建 messages 格式须与 chat 续轮 append 一致(均 `{role, content}`),否则 query 内核拼接报错。
- 持久失败务必 try/except,绝不阻塞用户对话流。

---

## 12. 代码锚点附录(核对后真实签名/行号)

### `praxis2/memory/session.py`
- `SessionEntry(uuid, type, content, user_id, session_id, parent_uuid=None, phase=None, timestamp=)` + `to_dict()/from_dict()`。`_LEGAL_TYPES = {user, assistant, system, attachment, phase-transition}`。
- `SessionStore(store)`:`load_transcript(*, user_id, session_id) -> list[SessionEntry]`(blob_get + 逐行 parse + uuid dedup + 跳损坏行);`append_entry(entry)`(type 校验 → `blob_append` O(1) 原子)。
- `resume(ss, state, *, user_id, session_id) -> ResumeResult(messages_count, needs_continue, phase, dropped_lines)` ← **接线主入口**。
- `rebuild_phase(ss, state, *, user_id, session_id)`(从最后 phase-transition 恢复相位);`record_phase_transition(ss, *, user_id, session_id, to, uuid_, parent=None)`。
- `apply_snip_removals` / `apply_preserved_segment_relinks` / `recover_orphaned_parallel_tool_results`(resume 内部调用)。

### `praxis2/store/base.py` + `store/pg.py`
- `Store` ABC:`blob_get/put/append(ns, key, …)` + `meta_upsert(table, row)` / `meta_get(table, user_id, pk)` / `meta_list(table, user_id) -> list[dict]`。`Namespace(user_id, scope)` 多租户隔离。
- PG:`praxis_meta`(table_name + user_id + pk → JSONB row,`CREATE TABLE IF NOT EXISTS`,**无需建 schema**)。`meta_upsert` row 需含 `user_id` + `id`/`pk`;`meta_list` `ORDER BY created_at`。`SessionStore` 经 `blob_*` 落 `praxis_blob`。

### `praxis2/server/app.py`
- `_App.__init__`:`SessionPool(max_size=200, idle_ttl_s=3600.0)` @214(注释 @212"权威态在 store §11.8"=本 spec 落地)。ledger 兜底 @237、files_repo 兜底 @251(`deps.repo._pool` 镜像模式)。
- chat-stream 路由:`pool.get` @732 / `if st is None: State() + put` @733-735(**resume 接线点**)/ user append @736 / `query()` @752。
- `_ensure_init` @1171:prod `store=PgStore(pool)` @1185、`repo=PgAuthRepository(pool)` @1188(同 pool)。
- `SessionStore` 在 server/ **未接线**;无 `/api/me/sessions` 端点。

### FE(SP2 用,不在 SP1 范围)
- `frontend/src/lib/api.ts`(已有 `session_id?` 字段 + `chatStream`)、`components/ConversationSidebar.tsx`、`lib/storage.ts`(`praxis-split:conversations:{user.id}`)、`App.tsx:251-253`(补 session_id 处)。
</content>
</invoke>
