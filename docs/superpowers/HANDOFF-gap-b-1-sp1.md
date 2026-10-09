# 接续提示词:GAP-B-1 子项目1(后端跨会话记忆)— 设计已批准,下一步写 spec

> 新对话直接读本文件起步。**brainstorm 已完成、SP1 后端设计已用户批准**;下一步 = 写 spec → 用户 review → writing-plans → subagent-driven-development。**不要重新 brainstorm / 重新探索**(关键发现都在下面)。

## 一句话
PRAXIS-2 智能体每会话从零开始。`SessionStore`(transcript→PG + resume)**实现完整但未接生产**(同 GAP-AH 模式)。GAP-B-1 = 把它接进 chat 路径让对话**跨重启/换设备/重登持久+恢复**。全栈功能已拆分:**SP1 后端(本轮)** + SP2 前端(后续)。

## 先读 + orientation
```
cd /Volumes/T7/clade-learn/PRAXIS-2 && git log --oneline -8
cat docs/superpowers/HANDOFF-gap-b-1-sp1.md   # 本文件
sed -n '/GAP-B-1/,/GAP-/p' TEST-WEB-BACKEND-FRONTEND.md | head -40   # 审计的验收(=spec 基础)
```
- main HEAD 含本会话工作(见下"本会话已做");memory:`~/.claude/projects/-Volumes-T7-clade-learn/memory/`(MEMORY.md + project_gap_ah_antihallucination.md 等)。

## 本会话已做(背景,均已 commit+push main)
- **GAP-E2E ops backlog**:DONE_real 12→20(rfdiffusion/covalent/redock/admet/da/boltz/de_novo/symmetric;`6e939da`)。T7 durable LD 前置尝试→回退(破 gnina cuDNN)。
- **GAP-AH-1/2**:反幻觉两道门接生产(`RetrieveFirstPermission` 检索先行证据门 + `tool_use_presence` stop_hook;`63839fb`)。
- **GAP-AH-3**:ship 前门 `scripts/ship_gate.py`(全量 pytest + KPI best-of-2;`8ed6f23`/`7558586`/`74eac51`/`38851bd`),全门实跑端到端绿。
- **反幻觉链路至此完整**。本轮转 GAP-B-1 跨会话记忆,brainstorm 完成,SP1 设计已批准。
- 已 spawn 未做:eval `executed_ok` S-FAIL 误判修复(chip)。

## 已批准的 SP1 设计(后端;**勿改动,直接落 spec**)
**拆分**:完整 GAP-B-1 → **SP1 后端**(持久化/resume/端点,本轮)+ **SP2 前端**(稳定 session_id + ConversationSidebar 接 /api/me/sessions + 切换恢复,后续独立 spec)。SP2 依赖 SP1 的 API。

**SP1 架构**:把已实现的 `SessionStore`(`praxis2/memory/session.py`:transcript→PgStore,append-only,resume)接进 chat 路径。`SessionPool` 仍是内存热缓存,`SessionStore` 是权威持久层(兑现 `app.py:212` 注释"权威态在 store")。pool miss → 从 SessionStore 加载+重建 State;每轮 append 新 entries。

**组件**:
1. **app.py 实例化 SessionStore**(`PgStore` 用 `deps.repo._pool`)。无 PG(测试 FakeAuthRepo,无 `_pool`)→ SessionStore=None → 退回今日纯内存态(**零回归**,镜像现有 ledger/files_repo 的 `_pool` 兜底模式)。
2. **resume(pool miss,app.py ~732 `self._session_pool.get`)**:miss 且 SessionStore 可用 → `await load_transcript(user_id, session_id)` → 重建 State(messages from entries + `rebuild_phase(ss, state, ...)`)→ put 入 pool。否则新 State(今日行为)。
3. **持久(每轮)**:user 消息 + query() 产出的 assistant/tool result → `append_entry`(blob_append 原子)。**关键实现细节(plan 阶段定清)**:State.messages ↔ SessionEntry 映射(type/content/role)+ **uuid dedup 防 resume 后重复 append**(load_transcript 读侧已按 uuid dedup,写侧给稳定 uuid)。只 append 本轮新增,别重写整盘。
4. **`/api/me/sessions` 端点**:GET,列当前用户会话(session_id + 末时间 + title/preview)。经 `Store.meta_list(table, user_id)`(会话首次创建时注册一行到 meta 表)。返回给 SP2 侧栏。
5. **session_id from chat body**:后端读 `body["session_id"]`(FE `lib/api.ts` 已有 `session_id?` 字段;SP2 会真传)。在此之前沿用现有 uuid4 fallback(`test_app_session_id_fallback.py`)。

**数据流**:chat(session_id)→ pool.get miss → load_transcript → 重建 State → 处理轮 → append 新 entries;`/api/me/sessions` → meta_list → 用户会话。

**边界**:无 PG → SessionStore=None → 内存态零回归;大 transcript resume → 现有 compaction/`apply_snip_removals` 处理;并发 append → blob_append 原子(已有);resume 重复 → uuid dedup。

**测试**:复用 `tests/test_memory_session.py` / `test_memory_session_resume.py` / `test_session_append_atomic.py` / `test_correctness_session_pool_wire.py` / `test_runtime_session_pool.py` / `test_app_session_id_fallback.py`;新增 chat-path resume 集成(pool miss→load→rebuild)、`/api/me/sessions` 端点、session_id round-trip、SessionStore=None 退回内存态(零回归)。全量回归零失败 + controller 亲做 staging e2e(重启 gunicorn 后凭 session_id resume 出历史)。

## 关键探索发现(代码锚点,**勿重复探索**)
- **`praxis2/memory/session.py`**:`SessionEntry`(字段 `uuid/type/content/user_id/session_id/parent_uuid/phase/timestamp`)· `SessionStore(store)`:`load_transcript(*,user_id,session_id)->list[SessionEntry]`(blob_get+逐行parse+uuid dedup)、`append_entry(entry)`(blob_append O(1) 原子)· `record_phase_transition(...)`、`rebuild_phase(ss,state,*,user_id,session_id)`(从 transcript 重建 State.phase)、`apply_snip_removals`。
- **`praxis2/store/base.py`**:`Store` ABC(`kv_put/get/delete` + `blob_put/get/append` + ttl + `meta_list(table,user_id)`)· `Namespace(user_id, scope)` 多租户隔离。后端 `store/{memory,redis,pg}.py`;`store/pg.py` 有 `PgStore, make_pg_pool`。
- **`praxis2/server/app.py`**:`SessionPool(max_size=200, idle_ttl_s=3600)` @214(注释 212"驱逐只丢内存副本,权威态在 store §11.8"=设计意图未落地)· pool `.get/.put` @732/735(**resume 接线点**)· `deps.repo._pool`(PG pool,PgAuthRepo 有/FakeAuthRepo 无)· `from praxis2.store.pg import PgStore` @1176(make_app_default)· chat-stream 路由 @~640-760(query() 调用、`st.messages.append` user 消息 @729)。
- **SessionStore 在 server/ 完全未接线**(grep 空)· 无 `/api/me/sessions` 端点。
- **GAP-B-1 验收(审计 TEST-WEB-BACKEND-FRONTEND.md §GAP-B-1,= spec 基础)**:① FE session_id(localStorage)随 chat 传 ② chat 路径接 SessionStore、transcript 落 PG ③ resume(重启/换设备/重登恢复历史)④ `/api/me/sessions` 端点 ⑤ 单测(append 原子 + resume 不变量)。
- **FE(SP2 用,React+TS+Vite,在 `frontend/`)**:`src/components/ConversationSidebar.tsx`(已有对话侧栏)· `src/lib/api.ts`(已有 `session_id?` 字段 + `chatStream`)· `src/lib/storage.ts`(localStorage 对话历史 `praxis-split:conversations:{user.id}`)。

## 流程(superpowers,严格)
brainstorm **已完成、SP1 设计已批准** → **下一步:写 spec** 到 `docs/superpowers/specs/2026-06-07-gap-b-1-session-persistence-backend-design.md`(把上面"已批准的 SP1 设计"成文 + 自审)→ **用户 review spec** → `writing-plans`(逐 task TDD,落 `docs/superpowers/plans/`)→ `subagent-driven-development`(fresh subagent/task,红→绿→commit + 两阶段 review:spec 合规→code quality,final review)。**main 直接干(用户既定,无 worktree)**。部署/e2e/收尾 controller 亲做。commit 末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

## 雷区(本系列踩过)
- **commit 只 add 目标文件**:工作区常驻无关 stray `brains/microbiome/skills/workflows/cooccurrence_network_real/run.py`(modified)+ 未跟踪 `brains/microbiome/memory/cases/microbiome-01{4,5,6,7}-*.md`、`rules/14-*.md`、`skills/workflows/{cross_feeding_gem,phage_host_link}/` —— **绝不 `git add .`/`-A`**。
- 无 PG 的测试路径(FakeAuthRepo 无 `_pool`)→ SessionStore 必须可为 None 退回内存态,否则破全量回归。
- 全量回归:`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?` 然后解析 junit(汇总行被 sandbox 吞)。
- ship 前可跑 `scripts/ship_gate.py`(需 `PRAXIS_EVAL_EMAIL/PASSWORD`,问用户取)。
- subagent 给完整 task 文本(别让它读 plan 文件);delicate core(query.py/app.py)改动 controller 细审 diff。
