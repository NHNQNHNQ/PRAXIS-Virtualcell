# Spec:GAP-B-1 SP2 前端跨设备会话恢复(渐进混合)

- **状态**:设计已批准(brainstorm 完成;架构经 plan-前 explore 由"后端权威"调整为"渐进混合",见 §2),待用户 review → `writing-plans` → `subagent-driven-development`
- **范围**:GAP-B-1 全栈的前端部分 + 一个支撑后端端点。SP1 后端已 ship(`98c0914`/`144c51c`,staging 部署 + 真 PG probe e2e)
- **约束**:main 直接干(无 worktree);commit 只 add 目标文件(工作区有 stray `brains/microbiome` 文件,绝不 `git add .`);commit 末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`;部署/e2e controller 亲做

---

## 1. 背景与问题

SP1 把 `SessionStore` 接进 chat 路径(resume / 每轮持久 / `GET /api/me/sessions`)。但 explore 揭示:

- `frontend/src/App.tsx:252` chatStream body = `{agent, message, model, mode}`,**无 `session_id`** → 后端 `_resolve_session_id` 每请求 `uuid4` fallback → **SP1 的 resume/持久在当前前端下从未生效**(每次新 session)。
- 前端对话历史全在 **localStorage**(`praxis-split:conversations:{user.id}`,`Conversation.messages`);后端 transcript 无端点返回 messages 给前端显示(`GET /api/me/sessions` 只返元数据)。

SP2 = 让前端真正兑现跨会话记忆:换设备/重登能看到历史对话内容。

---

## 2. 目标与非目标

### 架构决策(渐进混合)
plan-前 explore 发现 App.tsx 的 `conversations[].messages` 模型**深度耦合**(send/retry/editAndResend/runStream/渲染/sidebar 全基于它)。"后端权威 + localStorage 弃用"需整体重构该模型(风险中-高,前端无单测)。**改用渐进混合**:同样达成完整跨设备恢复 UX,但保留现有 `conversations[].messages` + localStorage,风险低。

### 目标
1. `Conversation.id` 即 `session_id`(已是稳定 id)→ 随 chatStream 传 → 激活 SP1 持久/resume。
2. 启动时 `fetchSessions()` → 把**后端独有**(本地 localStorage 没有)的会话并入列表(lazy stub,messages 空)。
3. 切换到 lazy 会话 → `fetchSessionMessages(id)` 懒填充 messages 显示。
4. 换设备/重登:新设备 localStorage 空 → `fetchSessions` 出全部历史会话 → 切换懒填充内容。

### 非目标
- **不重构 App.tsx 状态模型**:保留 `conversations[].messages` + localStorage(缓存)+ send/retry/editAndResend/runStream/渲染逻辑不动。
- **删除会话**:需后端 store `blob_delete/meta_delete` + `DELETE` 端点(现无)→ 留 follow-up;sidebar 现有删除/清空按钮**保留**(只删本地 localStorage 副本,后端 transcript 不删——可接受:下次 fetchSessions 又会并回 lazy stub,行为=隐藏本地副本;真删留 follow-up)。
- **历史 per-message agent/model**:transcript 只存 role/content/ts → 懒填充的历史 message agent 用默认 `•`/空 model。
- **历史 tool 过程**:简洁文本(user/assistant 气泡),tool_use/tool_result 不回显。

---

## 3. 设计

**架构**:`conversation.id = session_id`(稳定)。前端保留 `conversations[].messages` 模型 + localStorage 缓存(后端是跨设备权威,本地是缓存/离线)。三处接入:① chatStream 传 session_id;② 启动 `fetchSessions` 合并后端独有会话(lazy stub);③ 切到 lazy 会话懒填充。send/retry/edit/runStream/sidebar **不变**。

### 组件 1:后端 `GET /api/me/sessions/{session_id}`(新端点)
- **路由**:照搬动态路由范式(app.py:506 `path.startswith("/api/spawn/get/")` → `scope["path_params"]`)。加 `if path.startswith("/api/me/sessions/") and method == "GET": scope["path_params"]={"session_id": path[len("/api/me/sessions/"):]}` → 派发 `_session_messages_mine`。带尾斜杠的 `/api/me/sessions/` 前缀不撞列表端点 `/api/me/sessions`。
- **handler `_session_messages_mine`**:
  - `user = scope.get("user")`;无 → 401。
  - `if self._session_store is None: {"messages": []}`(无 PG,零回归)。
  - `seq = await self._session_store.load_transcript(user_id=user["user_id"], session_id=<path_params>)`。
  - 映射:遍历 entries,只取 `type in ("user","assistant")` 且 `isinstance(e.content, str)`(纯文本;tool_use assistant / tool_result user 的 content 是 list → 跳过;phase-transition → 跳过)→ `{"role": e.type, "text": e.content, "ts": e.timestamp}`。
  - `await self._json(send, 200, {"messages": [...]})`。隔离由 `load_transcript` 的 user_id namespace 保证。

### 组件 2:前端 `api.ts`
- `ChatStreamBody.session_id` 已有字段;App 传入。
- 新 `fetchSessions(): Promise<{sessions: {session_id: string; preview: string; updated_at: number}[]}>` = `apiFetch('/api/me/sessions')`。
- 新 `fetchSessionMessages(sessionId): Promise<{messages: {role: 'user'|'assistant'; text: string; ts: number}[]}>` = `apiFetch('/api/me/sessions/' + encodeURIComponent(sessionId))`。

### 组件 3:前端 `App.tsx`(最小侵入)
- **`Conversation` 类型**(`types/api.ts`):加 `lazy?: boolean`(后端独有、messages 未拉的 stub 标记)。
- **send 传 session_id**(:252):`chatStream({agent, message, model, mode, session_id: conv.id}, ...)`。`conv.id` 即 session_id。
- **启动合并**(新 useEffect,mount 时):`fetchSessions()` → 对每个后端 `session_id`,若本地 `conversations` 无同 id → 追加 stub `{id: session_id, title: preview, createdAt: updated_at*1000, updatedAt: updated_at*1000, messages: [], lazy: true}`;本地有则保留(已有 messages)。合并进 `setConversations`。失败静默(不阻塞)。
- **切换懒填充**:`onSwitch(id)` 包一层 → `setActiveConvId(id)`;若目标 conv `lazy && messages.length===0` → `fetchSessionMessages(id)` → 映射 `{id: newId(), role, agent: activeAgent, model: '', text, ts: ts*1000}[]` → `updateConv(id, c => ({...c, messages, lazy: false}))`。失败 → 标记非 lazy 避免重复拉(显示空 + 可重发)。
- **保留**:`conversations`/localStorage(`saveConversations`)/`activeConvId`/`ensureConv`/`updateConv`/`runStream`/`send`/`retry`/`editAndResend`/渲染逻辑全不动。

### 组件 4:前端 `ConversationSidebar.tsx`
- **基本不变**(仍 `conversations: Conversation[]`)。合并/懒填充逻辑全在 App,sidebar 只渲染。
- 唯一可选微调:lazy 会话的标题用 `preview`(已在 stub 的 `title`),emoji 行对空 messages 容错(现有 `c.messages.map` 对空数组安全 → 无 emoji,OK)。

---

## 4. 数据流

- **启动**:localStorage `conversations`(缓存)即时显示 → `fetchSessions()` 异步并入后端独有 lazy stub。
- **切换会话**:onSwitch(id) → 若 lazy → `fetchSessionMessages` 填充 → 显示;否则直接显示本地 messages。
- **发消息**:`chatStream(session_id=conv.id)` → 后端持久(SP1)+ 前端 conversations[conv].messages 实时更新(现有 runStream)+ localStorage 缓存。
- **跨设备/重登**:新设备 localStorage 空 → `fetchSessions` 出全部历史会话(lazy)→ 切换懒填充内容(真正兑现)。

---

## 5. 边界与容错

| 场景 | 处理 |
|------|------|
| 无 PG(dev) | `/api/me/sessions` 返 `[]`、`/{id}` 返 `{messages:[]}` → 仅本地 localStorage,容错不崩 |
| fetchSessions 失败 | 静默,仅显示本地 conversations(降级) |
| lazy 填充失败 | 标记 `lazy:false` 防重复拉,显示空(用户可继续发消息) |
| 本地 + 后端同 id | 本地优先(已有完整 messages),不覆盖 |
| 新对话未发消息 | 本地 stub,后端无 meta(未注册),其他设备看不到(正常) |
| session_id 特殊字符 | `encodeURIComponent`(前端)+ 后端 path 解码 |
| 历史 message 无 agent | 默认 `•`/空 model |

---

## 6. 测试

### 后端(单测)
`tests/test_gap_b1_session_messages_endpoint.py`(新):
- `GET /api/me/sessions/{id}` 返回 user/assistant 文本 messages(过滤 tool_use/tool_result/phase 的 list-content)。
- tool 轮 transcript → 只返纯文本对话。
- 多租户隔离(A 读不到 B);无 store → `{messages: []}`;401 无 user。
- 全量回归零失败 + ruff clean。

### 前端
无单测框架 → **controller playwright/手动 e2e**(staging 部署 + 凭证):登录 → 发消息(传 session_id,网络面板确认)→ 清 localStorage 模拟换设备 → 刷新 → fetchSessions 出会话 → 切换懒填充出历史内容。FE dist rebuild 部署。

---

## 7. 雷区

- **commit 只 add 目标文件**:工作区 stray `brains/microbiome/...`,绝不 `git add .`。
- 后端端点鉴权从 `scope["user"]`;`load_transcript` user_id namespace 保证隔离。
- 动态路由 `/api/me/sessions/` **带尾斜杠**,不撞列表端点。
- 渐进混合**保留现有逻辑**:不动 send/retry/editAndResend/runStream/渲染;只加 session_id 传参 + fetchSessions 合并 + onSwitch 懒填充 3 处。
- 后端 meta `updated_at` 是秒(`time.time()`);前端 `Conversation.updatedAt` 是毫秒(`Date.now()`)→ 合并 stub 时 `*1000` 对齐。
- FE dist rebuild 部署(版本/缓存,参考 v0.16.2)。
- delicate core(app.py 路由 dispatch)+ App.tsx 改动 controller 细审。

---

## 8. 代码锚点

- `praxis2/server/app.py`:`_resolve_session_id`(:78)· 动态路由 :506-508(spawn/get)· `("/api/me/sessions","GET"): self._sessions_list_mine` + handler(SP1)· `_json`(:549)· `load_transcript`(`praxis2/memory/session.py`,SessionEntry type/content/timestamp)。
- `frontend/src/lib/api.ts`:`ChatStreamBody.session_id`(:109)、`chatStream`(:112)、`apiFetch`(:30)。
- `frontend/src/App.tsx`:chatStream 调用 :251-253(补 session_id=conv.id)· `conversations`/localStorage :116-120/182 · `ensureConv`/`updateConv` :217/225 · `send` :423 · `activeConv` 渲染 :657 · `<ConversationSidebar onSwitch={setActiveConvId}>` :854-858(包懒填充)· `newConv`/`newId` :74。
- `frontend/src/types/api.ts`:`Conversation`(:105,加 `lazy?`)、`ChatMessage`(:80)。
</content>
