# GAP-B-1 SP2 前端跨设备会话恢复(渐进混合)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端兑现跨设备会话恢复:`conversation.id` 作 `session_id` 随 chatStream 传(激活 SP1 持久/resume)、启动并入后端独有会话、切换懒填充历史 messages;保留现有前端逻辑(渐进混合)。

**Architecture:** 后端补 `GET /api/me/sessions/{id}` 返回 transcript 的 user/assistant 文本。前端 3 处接入(不改状态模型):chatStream 传 session_id;启动 `fetchSessions` 把后端独有会话并入 `conversations`(`lazy` stub);切到 lazy 会话 `fetchSessionMessages` 懒填充。localStorage/send/retry/edit/runStream/sidebar 全保留。

**Tech Stack:** Python 3.11 + pytest(后端 TDD);React+TS+Vite(前端,**无单测框架** → `tsc --noEmit` 类型门 + controller playwright/手动 e2e)。参考 spec:`docs/superpowers/specs/2026-06-08-gap-b-1-sp2-frontend-session-restore-design.md`。流程:main 直接干,commit 只 add 目标文件(**绝不 `git add .`**——stray `brains/microbiome`),末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `praxis2/server/app.py` | 后端 messages 端点 | Modify(动态路由 dispatch + `_session_messages_mine` handler) |
| `tests/test_gap_b1_session_messages_endpoint.py` | 端点单测 | Create |
| `frontend/src/lib/api.ts` | 前端 API | Modify(加 `fetchSessions`/`fetchSessionMessages`) |
| `frontend/src/types/api.ts` | 类型 | Modify(`Conversation` 加 `lazy?`) |
| `frontend/src/App.tsx` | 前端接入 | Modify(3 处:send session_id / 启动合并 / onSwitch 懒填充) |

**后端测试**:`.venv/bin/python -m pytest <path> -v`;全量 `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml`(解析 junit)。
**前端类型门**:`cd frontend && npx tsc --noEmit`(无类型错误)。

### 关键锚点(ship 后 `144c51c`)
- `app.py:506-510` 动态路由范式(`path.startswith("/api/spawn/get/")` → `scope["path_params"]` → `await handle_x(...)` → `return`);`:431` 静态路由 `("/api/me/sessions","GET"): self._sessions_list_mine`;`:549` `_json`;`_sessions_list_mine` handler(SP1)。动态 startswith 块在静态 dict 匹配**之前**。
- `frontend/src/lib/api.ts:30` `apiFetch`、`:57` `fetchAgents`(GET 范式)、`:109` `ChatStreamBody.session_id`、`:112` chatStream。
- `frontend/src/App.tsx:16` api import、`:73` `newId`、`:225` `updateConv`、`:230` `runStream`(含 `convId`)、`:251-253` chatStream body、`:854-858` `<ConversationSidebar onSwitch={setActiveConvId}>`。
- `frontend/src/types/api.ts:105` `Conversation`。

---

## Task 1: 后端 `GET /api/me/sessions/{id}`(TDD)

**Files:**
- Modify: `praxis2/server/app.py`(动态路由 dispatch + handler)
- Test: `tests/test_gap_b1_session_messages_endpoint.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_gap_b1_session_messages_endpoint.py`:
```python
"""GAP-B-1 SP2:GET /api/me/sessions/{id} 返回 transcript user/assistant 文本。"""
from __future__ import annotations

import json as _json

import pytest

from praxis2.core.rmcp import Phase
from praxis2.memory.session import SessionEntry, SessionStore, record_phase_transition
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session


async def _get_messages(app, cookie, session_id):
    arrivals: list[bytes] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.body" and msg.get("body"):
            arrivals.append(msg["body"])

    scope = {
        "type": "http", "method": "GET",
        "path": f"/api/me/sessions/{session_id}",
        "headers": [(b"cookie", cookie.encode())], "query_string": b"",
    }
    await app(scope, receive, send)
    return _json.loads(b"".join(arrivals))


async def _seed(ss, sid, uid="u1"):
    await ss.append_entry(SessionEntry(
        uuid="m1", type="user", content="问题", user_id=uid, session_id=sid))
    await ss.append_entry(SessionEntry(
        uuid="m2", type="assistant", content="答复", user_id=uid, session_id=sid))
    # tool_use assistant + tool_result user(content 是 list)+ phase → 应被过滤
    await ss.append_entry(SessionEntry(
        uuid="m3", type="assistant",
        content=[{"type": "tool_use", "id": "t", "name": "x", "input": {}}],
        user_id=uid, session_id=sid))
    await ss.append_entry(SessionEntry(
        uuid="m4", type="user",
        content=[{"type": "tool_result", "tool_use_id": "t", "content": "r"}],
        user_id=uid, session_id=sid))
    await record_phase_transition(
        ss, user_id=uid, session_id=sid, to=Phase.RETRIEVE, uuid_="ph")


@pytest.mark.asyncio
async def test_returns_text_filters_tool_and_phase(monkeypatch):
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    ss = SessionStore(store)
    app._app._session_store = ss
    await _seed(ss, "s1")
    out = await _get_messages(app, cookie, "s1")
    await deps.redis.aclose()
    # 只返纯文本 user/assistant;tool_use/tool_result/phase 过滤
    assert [(m["role"], m["text"]) for m in out["messages"]] == [
        ("user", "问题"), ("assistant", "答复"),
    ], f"实际 {out['messages']!r}"
    assert all("ts" in m for m in out["messages"])


@pytest.mark.asyncio
async def test_tenant_isolation(monkeypatch):
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    c1 = await preseed_session(deps, user_id="u1", email="u1@t.com")
    c2 = await preseed_session(deps, user_id="u2", email="u2@t.com")
    app = make_app(deps)
    ss = SessionStore(store)
    app._app._session_store = ss
    await _seed(ss, "s1", uid="u1")
    out2 = await _get_messages(app, c2, "s1")  # u2 读 u1 的 session
    await deps.redis.aclose()
    assert out2["messages"] == [], f"u2 不应读到 u1 的会话,实际 {out2!r}"


@pytest.mark.asyncio
async def test_no_store_empty():
    deps = make_test_app_deps()  # 默认无 _pool → _session_store None
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    assert app._app._session_store is None
    out = await _get_messages(app, cookie, "whatever")
    await deps.redis.aclose()
    assert out == {"messages": []}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_session_messages_endpoint.py -v`
Expected: FAIL(路由不存在 → 返回 404/SPA HTML,`out["messages"]` KeyError)

- [ ] **Step 3: 实现**

**(3a)** 在 `app.py` 动态路由块,紧接 spawn 的 `if path.startswith("/api/spawn/cancel/")...return` 之后(`:515` 后)插入:
```python
        # GAP-B-1 SP2:GET /api/me/sessions/{id} 动态路由(带尾斜杠,不撞列表端点
        # /api/me/sessions)。返回该会话 transcript 的 user/assistant 文本 messages。
        if path.startswith("/api/me/sessions/") and method == "GET":
            scope["path_params"] = {"session_id": path[len("/api/me/sessions/"):]}
            await self._session_messages_mine(scope, receive, send)
            return
```

**(3b)** 在 `_sessions_list_mine` handler 之后(`_App` 类内)加 handler:
```python
    async def _session_messages_mine(self, scope, receive, send) -> None:
        """GAP-B-1 SP2:GET /api/me/sessions/{id} —— 返回该会话 transcript 的
        user/assistant 纯文本 messages(供前端懒填充历史显示)。tool_use/
        tool_result(content 是 list)与 phase-transition 跳过。"""
        user = scope.get("user")
        if not user:
            await self._json(
                send, 401, {"error": "unauthorized", "reason": "未登录"}
            )
            return
        if self._session_store is None:
            await self._json(send, 200, {"messages": []})  # 无 PG,零回归
            return
        session_id = scope.get("path_params", {}).get("session_id", "")
        seq = await self._session_store.load_transcript(
            user_id=user["user_id"], session_id=session_id)
        messages = [
            {"role": e.type, "text": e.content, "ts": e.timestamp}
            for e in seq
            if e.type in ("user", "assistant") and isinstance(e.content, str)
        ]
        await self._json(send, 200, {"messages": messages})
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_session_messages_endpoint.py -v`
Expected: 3 passed

- [ ] **Step 4.5: ruff gate**

Run: `.venv/bin/ruff check praxis2/server/app.py tests/test_gap_b1_session_messages_endpoint.py`
Expected: `All checks passed!`(不 clean 则 `--fix` 再查)

- [ ] **Step 5: 全量回归 + Commit**

Run:
```bash
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?
.venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/r.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print('tests=%s failures=%s errors=%s'%(s.get('tests'), s.get('failures'), s.get('errors')))"
```
Expected: `failures=0 errors=0`。

```bash
git add praxis2/server/app.py tests/test_gap_b1_session_messages_endpoint.py
git commit -m "feat(gap-b-1): GET /api/me/sessions/{id} 返回会话历史 messages(SP2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 前端 api.ts + Conversation.lazy

**Files:**
- Modify: `frontend/src/lib/api.ts`(加 2 个 fetch)
- Modify: `frontend/src/types/api.ts`(`Conversation` 加 `lazy?`)

- [ ] **Step 1: 加类型字段**

`frontend/src/types/api.ts` 的 `Conversation` interface(`:105`)加 `lazy?: boolean`:
```typescript
export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  lazy?: boolean;  // GAP-B-1 SP2:后端独有、messages 未懒填充的 stub 标记
}
```

- [ ] **Step 2: 加 api 函数**

`frontend/src/lib/api.ts` 在 `fetchBalance`(`:87`)之后加:
```typescript
// GAP-B-1 SP2 — 跨设备会话恢复:会话列表 + 单会话历史 messages。
export interface SessionMeta { session_id: string; preview: string; updated_at: number }
export const fetchSessions = () =>
  apiFetch<{ sessions: SessionMeta[] }>('/api/me/sessions');

export interface SessionMessage { role: 'user' | 'assistant'; text: string; ts: number }
export const fetchSessionMessages = (sessionId: string) =>
  apiFetch<{ messages: SessionMessage[] }>(
    '/api/me/sessions/' + encodeURIComponent(sessionId),
  );
```

- [ ] **Step 3: 类型门**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误(新增类型/函数自洽)。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/types/api.ts
git commit -m "feat(gap-b-1): 前端 fetchSessions/fetchSessionMessages + Conversation.lazy(SP2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 前端 App.tsx 3 处接入

**Files:**
- Modify: `frontend/src/App.tsx`(import + send session_id + 启动合并 + onSwitch 懒填充)

> 无单测框架 → 验证 = `tsc --noEmit` 类型门 + controller staging e2e。保留 send/retry/editAndResend/runStream/渲染/localStorage 不动。

- [ ] **Step 1: import 2 个 fetch**

把 `App.tsx:16` 的 import 行:
```typescript
import { chatStream, fetchAgents, fetchInfo, fetchMe, API_BASE, APP_VERSION, BUILD_TIME } from '@/lib/api';
```
改为(加 `fetchSessions, fetchSessionMessages`):
```typescript
import { chatStream, fetchAgents, fetchInfo, fetchMe, fetchSessions, fetchSessionMessages, API_BASE, APP_VERSION, BUILD_TIME } from '@/lib/api';
```

- [ ] **Step 2: send 传 session_id**

把 `App.tsx:251-253` 的 chatStream 调用:
```typescript
      for await (const ev of chatStream(
        { agent, message: prompt, model, mode: activeMode },
        ctrl.signal,
      )) {
```
改为(加 `session_id: convId` —— `convId` 是 `runStream` 第一参,即 conversation.id):
```typescript
      for await (const ev of chatStream(
        { agent, message: prompt, model, mode: activeMode, session_id: convId },
        ctrl.signal,
      )) {
```

- [ ] **Step 3: 启动 fetchSessions 合并(新 useEffect)**

在 `App.tsx` 现有"启动 effects"区(`saveConversations` effect `:182` 附近)之后加一个 mount-only useEffect:
```typescript
  // GAP-B-1 SP2:启动并入后端独有会话(本地 localStorage 没有的 → lazy stub)。
  // 后端 updated_at 是秒,前端 updatedAt 是毫秒 → *1000 对齐。失败静默降级。
  useEffect(() => {
    let cancelled = false;
    fetchSessions()
      .then(({ sessions }) => {
        if (cancelled) return;
        setConversations((cs) => {
          const have = new Set(cs.map((c) => c.id));
          const stubs: Conversation[] = sessions
            .filter((s) => !have.has(s.session_id))
            .map((s) => ({
              id: s.session_id,
              title: s.preview || '历史对话',
              createdAt: s.updated_at * 1000,
              updatedAt: s.updated_at * 1000,
              messages: [],
              lazy: true,
            }));
          return stubs.length ? [...cs, ...stubs] : cs;
        });
      })
      .catch(() => { /* 静默:仅本地 conversations */ });
    return () => { cancelled = true; };
  }, []);
```

- [ ] **Step 4: onSwitch 懒填充**

在 `App.tsx` `updateConv`(`:225`)之后加 `handleSwitch`:
```typescript
  // GAP-B-1 SP2:切换会话;若是 lazy stub(后端独有、未拉 messages)→ 懒填充历史。
  const handleSwitch = useCallback((id: string) => {
    setActiveConvId(id);
    const conv = conversations.find((c) => c.id === id);
    if (conv?.lazy && conv.messages.length === 0) {
      fetchSessionMessages(id)
        .then(({ messages }) => {
          updateConv(id, (c) => ({
            ...c,
            lazy: false,
            messages: messages.map((m) => ({
              id: newId(), role: m.role, agent: activeAgent, model: '',
              text: m.text, ts: m.ts * 1000,
            })),
          }));
        })
        .catch(() => updateConv(id, (c) => ({ ...c, lazy: false })));  // 防重复拉
    }
  }, [conversations, updateConv, activeAgent]);
```
然后把 `<ConversationSidebar>` 的 `onSwitch={setActiveConvId}`(`:858`)改为 `onSwitch={handleSwitch}`。

- [ ] **Step 5: 类型门**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(gap-b-1): App 接入 session_id + 启动合并 + 切换懒填充(SP2 渐进混合)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 完成后(controller 亲做,不在 subagent task 内)
- FE `npm run build`(dist rebuild)+ rsync staging + 后端 app.py rsync + HUP reload。
- staging e2e(playwright/手动):登录 → 发消息(网络面板确认 body 含 session_id)→ 列表出现 → 清 localStorage 模拟换设备 → 刷新 → fetchSessions 出会话 → 切换懒填充出历史内容。
- 删除会话(真删)留 follow-up。

## 雷区(提醒 subagent)
- commit 只 `git add` 列出文件,**绝不 `git add .`/`-A`**(stray `brains/microbiome`)。
- 动态路由 `/api/me/sessions/` **带尾斜杠**,插在 spawn 动态块后、静态 dict 匹配前;不撞列表端点 `/api/me/sessions`。
- handler 鉴权从 `scope["user"]`;`load_transcript` user_id namespace 隔离;映射只取 `isinstance(content, str)` 的 user/assistant(过滤 tool/phase 的 list-content)。
- 前端 `updated_at`(秒)→ `*1000`;`ts`(秒)→ `*1000`。
- 前端无单测 → 每个前端 task 必跑 `npx tsc --noEmit` 类型门;真行为靠 controller staging e2e。
- 保留现有 send/retry/editAndResend/runStream/渲染/localStorage 逻辑不动(只 3 处接入)。
- delicate core(app.py 路由)+ App.tsx controller 细审 diff。
</content>
