# GAP-B-1 SP1 后端跨会话记忆 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已实现的 `SessionStore`(transcript→PG blob + `resume()`)接进 chat 路径,让对话跨重启/换设备/重登持久 + 恢复,并新增 `GET /api/me/sessions` 端点;无 PG 环境零回归。

**Architecture:** `SessionPool` 仍是内存热缓存,`SessionStore` 是权威持久层。`_App.__init__` 镜像 ledger/files_repo 的 `deps.repo._pool` 兜底实例化 `SessionStore`(无 PG→None)。chat 路径:pool miss → `resume()` 重建 `State`;每轮 user 消息 + query 产出的 assistant/tool delta + 相位变化 append 进 transcript;每轮 `meta_upsert("sessions")` 注册会话元数据供端点列出。**不动 `query.py` 内核与 `session.py`**(只复用)。

**Tech Stack:** Python 3.11、asyncio、ASGI、pytest + pytest-asyncio。参考 spec:`docs/superpowers/specs/2026-06-07-gap-b-1-session-persistence-backend-design.md`。流程:main 直接干(无 worktree),逐 task TDD,fresh subagent/task。commit 只 `git add` 目标文件(**绝不 `git add .`**——工作区有 stray microbiome 文件),末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `praxis2/server/app.py` | chat 路径接 SessionStore + 端点 | Modify(import / `__init__` / chat 路径 / 模块级 helper / handler / 路由表) |
| `praxis2/memory/session.py` | 持久层 | **不改**(复用 `SessionStore` / `SessionEntry` / `resume` / `record_phase_transition`) |
| `tests/_gap_b1_helpers.py` | 测试共享:驱动 chat-stream + fake query | Create |
| `tests/test_gap_b1_session_store_init.py` | 组件1 兜底实例化 | Create |
| `tests/test_gap_b1_resume_wire.py` | 组件2 resume on pool miss | Create |
| `tests/test_gap_b1_persist_turn.py` | 组件3 持久(user/assistant/phase) | Create |
| `tests/test_gap_b1_sessions_endpoint.py` | 组件4 端点 + 隔离 + 无 store | Create |

**测试运行**:`.venv/bin/python -m pytest <path> -v`
**全量回归**:`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?`(汇总行被 sandbox 吞,解析 `/tmp/r.xml`)

### 关键锚点(已核对真实行号/签名)
- `app.py:200` `_App.__init__(self, deps)`;`:214` `self._session_pool = SessionPool(...)`;`:234-253` ledger/files_repo 的 `try: X = Foo(deps.repo._pool) except AttributeError: X = None` 兜底范式。
- `app.py:560` `_chat_stream`;`:571` `user_id = user["user_id"]`;`:595` `session_id = _resolve_session_id(body)`(**组件5 已实现**);`:596` `message = body.get("message", "")`;`:659` `async with acquire_session_lock(...)`;`:732-736` pool.get miss 分支 + user append;`:749` `assistant_text=[]`;`:751-776` query 的 try/except/finally(`finally: await client.aclose()`)。
- `app.py:368` 路由表 `("/api/me/proposals", "GET"): self._proposal_list_mine`;`:549` `async def _json(self, send, status, body)`;`:1003` `_proposal_list_mine` handler 范式(`user = scope.get("user")` → 401 → `user["user_id"]` → `self._json`)。
- `praxis2/memory/session.py`:`SessionEntry(uuid, type, content, user_id, session_id, parent_uuid=None, phase=None, timestamp=)`;`SessionStore(store)` 的 `load_transcript(*, user_id, session_id)` / `append_entry(entry)`;`resume(ss, state, *, user_id, session_id) -> ResumeResult`;`record_phase_transition(ss, *, user_id, session_id, to, uuid_, parent=None)`。
- `praxis2/core/rmcp.py`:`Phase`(INIT/RETRIEVE/...);`get_phase(state)->Phase`(初始 INIT);`set_phase(state, phase)`。
- `praxis2/store/memory.py` `InMemoryStore`:**`meta_upsert` 要 `row["pk"]`(非 `id`)**;`meta_list` 不排序。`praxis2/store/pg.py` `PgStore`:`meta_upsert` 认 `row["id"] or row["pk"]`;`meta_list` 按 DB `created_at`。**→ row 主键统一用 `pk`(两 store 通用),handler 侧按 `updated_at` 排序**。
- 测试范式(照搬 `tests/test_correctness_session_pool_wire.py`):`make_test_app_deps(store=InMemoryStore())` + `preseed_session(deps, user_id=...)` + ASGI drive path `"/chat/stream"` + `monkeypatch.setattr(app_module, "query", fake_query)`;fake_query 签名 `async def fake_query(state, *, client, registry, settings, runner, compactor, **_kw)`。`make_app(deps)` → `app._app` 是 inner `_App`。

---

## Task 0(前置):测试共享 helper

**Files:**
- Create: `tests/_gap_b1_helpers.py`

- [ ] **Step 1: 创建 helper 文件**

```python
"""GAP-B-1 测试共享:驱动 /chat/stream(ASGI)+ fake query 注入。

照搬 tests/test_correctness_session_pool_wire.py 的 drive 范式,抽出复用。"""
from __future__ import annotations

import json as _json


async def drive_chat(app, cookie, *, message, session_id="s1"):
    """走 ASGI 驱动一次 /chat/stream;返回收到的 body frames(bytes 列表)。"""
    arrivals: list[bytes] = []
    started = {"v": False}

    async def receive():
        return {
            "type": "http.request",
            "body": _json.dumps(
                {"message": message, "session_id": session_id}
            ).encode(),
            "more_body": False,
        }

    async def send(msg):
        if msg["type"] == "http.response.start":
            started["v"] = True
        elif msg["type"] == "http.response.body" and msg.get("body"):
            arrivals.append(msg["body"])

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat/stream",
        "headers": [(b"cookie", cookie.encode())],
        "query_string": b"",
    }
    await app(scope, receive, send)
    assert started["v"], "http.response.start 未发送"
    return arrivals


def install_capture_query(monkeypatch, captured, *, assistant_text="ok"):
    """fake query:把本请求开始时(已 append user)的 state.messages 快照进
    captured,再 append 一条 assistant,正常终答。模拟 query 内核真实路径。"""
    from praxis2.server import app as app_module

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        captured.append({"messages": list(state.messages)})
        state.messages.append({"role": "assistant", "content": assistant_text})
        yield {"type": "text", "text": assistant_text}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)
```

- [ ] **Step 2: 验证可导入**

Run: `.venv/bin/python -c "from tests._gap_b1_helpers import drive_chat, install_capture_query; print('ok')"`
Expected: 打印 `ok`(无 ImportError)

- [ ] **Step 3: Commit**

```bash
git add tests/_gap_b1_helpers.py
git commit -m "test(gap-b-1): chat-stream 驱动 + fake query 测试 helper

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 1: 组件1 — `_App.__init__` 实例化 SessionStore(`_pool` 兜底)

**Files:**
- Modify: `praxis2/server/app.py`(顶部 import + `__init__` `:214` 后)
- Test: `tests/test_gap_b1_session_store_init.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_gap_b1_session_store_init.py`:
```python
"""GAP-B-1 Task 1:_App.__init__ 实例化 SessionStore,镜像 ledger/files_repo
的 deps.repo._pool 兜底——无 PG(FakeAuthRepo 无 _pool,测试)→ None,零回归。"""
from __future__ import annotations

import pytest

from praxis2.memory.session import SessionStore
from praxis2.server.app import make_app
from tests._auth_test_helpers import make_test_app_deps


@pytest.mark.asyncio
async def test_no_pg_session_store_is_none():
    """FakeAuthRepository 无 _pool → _session_store=None(退回纯内存态)。"""
    deps = make_test_app_deps()
    app = make_app(deps)
    assert app._app._session_store is None
    await deps.redis.aclose()


@pytest.mark.asyncio
async def test_with_pool_session_store_built():
    """deps.repo 有 _pool(模拟 PgAuthRepository)→ 建 SessionStore(deps.store)。"""
    deps = make_test_app_deps()
    deps.repo._pool = object()  # FakeAuthRepository 是普通类,可 setattr
    app = make_app(deps)
    assert isinstance(app._app._session_store, SessionStore)
    await deps.redis.aclose()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_session_store_init.py -v`
Expected: FAIL（`AttributeError: '_App' object has no attribute '_session_store'`）

- [ ] **Step 3: 实现**

在 `app.py` 顶部 import 区(与其他 `from praxis2...` import 同处)加:
```python
from praxis2.memory.session import (
    SessionEntry,
    SessionStore,
    record_phase_transition,
    resume,
)
```
（后续 task 用到 `SessionEntry`/`resume`/`record_phase_transition`,一次 import 齐避免反复改顶部。）

在 `__init__` 中 `self._session_pool = SessionPool(max_size=200, idle_ttl_s=3600.0)`（`:214`）之后插入:
```python
        # GAP-B-1 SP1:SessionStore 权威持久层(transcript→store blob)。
        # 镜像 ledger/files_repo 兜底:deps.repo._pool 不存在(FakeAuthRepo,
        # 测试)→ AttributeError → None,退回纯内存态(SessionPool 单层),零回归。
        try:
            _ = deps.repo._pool  # 仅探测存在性;真 IO 走 deps.store
            self._session_store: SessionStore | None = SessionStore(deps.store)
        except AttributeError:
            self._session_store = None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_session_store_init.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_gap_b1_session_store_init.py
git commit -m "feat(gap-b-1): _App 实例化 SessionStore,_pool 兜底零回归

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 组件2 — chat 路径 pool miss → `resume()` 重建 State

**Files:**
- Modify: `praxis2/server/app.py`(`:732-735` pool miss 分支)
- Test: `tests/test_gap_b1_resume_wire.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_gap_b1_resume_wire.py`:
```python
"""GAP-B-1 Task 2:chat 路径 pool miss + 持久层可用 → resume 历史 transcript。"""
from __future__ import annotations

import pytest

from praxis2.memory.session import SessionEntry, SessionStore
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._gap_b1_helpers import drive_chat, install_capture_query


@pytest.mark.asyncio
async def test_pool_miss_resumes_transcript(monkeypatch):
    """pool 无此 session,SessionStore 有历史 → resume 重建 messages;
    fake_query 看到的 state.messages 含历史 user/assistant + 本轮 user。"""
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    ss = SessionStore(store)
    app._app._session_store = ss  # 注入可用持久层(默认 FakeAuthRepo→None)
    # 预置历史 transcript(上一会话两条)
    await ss.append_entry(SessionEntry(
        uuid="h1", type="user", content="历史问题",
        user_id="u1", session_id="s1"))
    await ss.append_entry(SessionEntry(
        uuid="h2", type="assistant", content="历史回答",
        user_id="u1", session_id="s1"))
    captured: list = []
    install_capture_query(monkeypatch, captured)

    await drive_chat(app, cookie, message="新问题", session_id="s1")
    await deps.redis.aclose()

    assert captured[0]["messages"] == [
        {"role": "user", "content": "历史问题"},
        {"role": "assistant", "content": "历史回答"},
        {"role": "user", "content": "新问题"},
    ], f"resume 应重建历史 + 本轮 user,实际 {captured[0]['messages']!r}"


@pytest.mark.asyncio
async def test_no_store_empty_state_no_regression(monkeypatch):
    """SessionStore=None(默认无 PG)→ pool miss 走空 State(),仅本轮 user(零回归)。"""
    deps = make_test_app_deps()
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    assert app._app._session_store is None
    captured: list = []
    install_capture_query(monkeypatch, captured)
    await drive_chat(app, cookie, message="hi", session_id="s-new")
    await deps.redis.aclose()
    assert captured[0]["messages"] == [{"role": "user", "content": "hi"}]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_resume_wire.py -v`
Expected: `test_pool_miss_resumes_transcript` FAIL(messages 只有 `[{"role":"user","content":"新问题"}]`,历史未 resume);`test_no_store_empty_state_no_regression` 可能已 PASS（零回归基线）

- [ ] **Step 3: 实现**

把 `app.py` `:732-735` 的:
```python
                st = self._session_pool.get(user_id, session_id)
                if st is None:
                    st = State()
                    self._session_pool.put(user_id, session_id, st)
```
替换为:
```python
                st = self._session_pool.get(user_id, session_id)
                if st is None:
                    st = State()
                    # GAP-B-1:pool miss + 持久层可用 → 从 transcript resume 历史。
                    # resume() 完整编排(dedup→snip→relink→孤儿配对→中断注入→
                    # rebuild_phase);空 transcript → messages=[](等价新 State,零回归)。
                    if self._session_store is not None:
                        try:
                            await resume(
                                self._session_store, st,
                                user_id=user_id, session_id=session_id,
                            )
                        except Exception:  # noqa: BLE001
                            pass  # 持久层异常不阻塞 chat,降级空 State(今日行为)
                    self._session_pool.put(user_id, session_id, st)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_resume_wire.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_gap_b1_resume_wire.py
git commit -m "feat(gap-b-1): chat 路径 pool miss 复用 resume() 重建 State

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 组件3a — user 消息持久化

**Files:**
- Modify: `praxis2/server/app.py`(`:736` user append 之后)
- Test: `tests/test_gap_b1_persist_turn.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_gap_b1_persist_turn.py`:
```python
"""GAP-B-1 Task 3-5:每轮把 user / assistant delta / 相位变化落 transcript。"""
from __future__ import annotations

import pytest

from praxis2.memory.session import SessionStore
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._gap_b1_helpers import drive_chat, install_capture_query


def _make_persistent_app(store):
    deps = make_test_app_deps(store=store)
    app = make_app(deps)
    app._app._session_store = SessionStore(store)
    return deps, app


@pytest.mark.asyncio
async def test_user_message_persisted(monkeypatch):
    """一轮 chat 后,transcript 含本轮 user entry。"""
    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")
    install_capture_query(monkeypatch, [])
    await drive_chat(app, cookie, message="记住我", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    assert any(e.type == "user" and e.content == "记住我" for e in seq), \
        f"user 消息应落库,实际 {[(e.type, e.content) for e in seq]!r}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py -v`
Expected: FAIL(transcript 空,user 未落库)

- [ ] **Step 3: 实现**

把 `app.py` `:736` 的:
```python
                st.messages.append({"role": "user", "content": message})
```
替换为:
```python
                st.messages.append({"role": "user", "content": message})
                # GAP-B-1:user 消息落 transcript(持久层可用时);失败不阻塞 chat。
                if self._session_store is not None:
                    try:
                        await self._session_store.append_entry(SessionEntry(
                            uuid=uuid.uuid4().hex, type="user", content=message,
                            user_id=user_id, session_id=session_id,
                        ))
                    except Exception:  # noqa: BLE001
                        pass
```
（`uuid` 模块 app.py 顶部已 import——`_resolve_session_id` 用 `uuid.uuid4().hex`,无需新增。）

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_gap_b1_persist_turn.py
git commit -m "feat(gap-b-1): user 消息每轮落 transcript

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: 组件3b — assistant/tool delta 持久化(`_append_turn_entries` helper)

**Files:**
- Modify: `praxis2/server/app.py`(模块级新增 `_append_turn_entries`;chat 路径 query 前记 `_prev_len`、query 后调 helper)
- Test: `tests/test_gap_b1_persist_turn.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/test_gap_b1_persist_turn.py` 追加:
```python
@pytest.mark.asyncio
async def test_assistant_delta_persisted(monkeypatch):
    """query 产出的 assistant 消息(state.messages[prev_len:])落库,无重复 uuid。"""
    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")
    install_capture_query(monkeypatch, [])  # fake_query append assistant "ok"
    await drive_chat(app, cookie, message="问", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    assert [e.type for e in seq] == ["user", "assistant"], \
        f"应含 user+assistant,实际 {[(e.type, e.content) for e in seq]!r}"
    assert seq[1].content == "ok"
    uuids = [e.uuid for e in seq]
    assert len(uuids) == len(set(uuids)), "uuid 不能重复"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py::test_assistant_delta_persisted -v`
Expected: FAIL(transcript 只有 `["user"]`,assistant delta 未落库)

- [ ] **Step 3: 实现**

在 `app.py` 模块级(`_chat_stream` 方法之外,例如紧接 `_resolve_session_id` / `_read_body` 等 helper 之后)新增:
```python
async def _append_turn_entries(
    ss, state, prev_len: int, *, user_id: str, session_id: str,
) -> None:
    """GAP-B-1:把本轮 query() 新增(state.messages[prev_len:])的 assistant /
    tool_result 消息 append 进 transcript(只 delta,不重写整盘)。每条新 uuid;
    读侧 load_transcript 已按 uuid dedup。user 纯文本已在 chat 路径单独落库,
    不在 delta 区(prev_len 取自 user append 之后)。"""
    for msg in state.messages[prev_len:]:
        role = msg.get("role")
        if role == "assistant":
            etype = "assistant"
        elif role == "user":
            etype = "user"  # tool_result 回合(content 含 tool_result blocks)
        else:
            continue  # 其他 role 不入库
        await ss.append_entry(SessionEntry(
            uuid=uuid.uuid4().hex, type=etype, content=msg.get("content"),
            user_id=user_id, session_id=session_id,
        ))
```

在 chat 路径 query 调用之前(`:749` 附近,`assistant_text: list[str] = []` 一行之前)插入:
```python
                # GAP-B-1:delta 起点(已含本轮 user)——query 后据此 append 新增 assistant/tool。
                _prev_len = len(st.messages)
```

在 query 的 `try/except/finally` 块结束之后(`finally: await client.aclose()` 之后、v0.15.0 auto-spawn 注释之前)插入:
```python
                # GAP-B-1:本轮 query 新增的 assistant/tool delta 落 transcript;失败不阻塞。
                if self._session_store is not None:
                    try:
                        await _append_turn_entries(
                            self._session_store, st, _prev_len,
                            user_id=user_id, session_id=session_id,
                        )
                    except Exception:  # noqa: BLE001
                        pass
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_gap_b1_persist_turn.py
git commit -m "feat(gap-b-1): query 后 assistant/tool delta 落 transcript

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: 组件3c / §9.1-A — 相位持久(phase-transition)

**Files:**
- Modify: `praxis2/server/app.py`(顶部 import `get_phase`;`_append_turn_entries` 加 `phase_before` 参数 + 相位 append;chat 路径记 `_phase_before` + 调用传参)
- Test: `tests/test_gap_b1_persist_turn.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/test_gap_b1_persist_turn.py` 追加:
```python
@pytest.mark.asyncio
async def test_phase_transition_persisted_and_resumed(monkeypatch):
    """query 推进相位 → 落 phase-transition;新 State resume 后 rebuild_phase 恢复。"""
    from praxis2.core.rmcp import Phase, get_phase, set_phase
    from praxis2.core.state import State
    from praxis2.memory.session import resume
    from praxis2.server import app as app_module

    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        set_phase(state, Phase.RETRIEVE)  # 模拟相位推进(初始 INIT → RETRIEVE)
        yield {"type": "text", "text": "ok"}
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    await drive_chat(app, cookie, message="问", session_id="s1")
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    assert any(
        e.type == "phase-transition" and e.phase == Phase.RETRIEVE.value
        for e in seq
    ), f"应落 phase-transition=retrieve,实际 {[(e.type, e.phase) for e in seq]!r}"

    # 新 State resume → 相位恢复 RETRIEVE(不再回退 INIT)
    st2 = State()
    await resume(app._app._session_store, st2, user_id="u1", session_id="s1")
    assert get_phase(st2) == Phase.RETRIEVE
    await deps.redis.aclose()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py::test_phase_transition_persisted_and_resumed -v`
Expected: FAIL（无 phase-transition entry;resume 后 `get_phase(st2)` 仍 INIT）

- [ ] **Step 3: 实现**

在 `app.py` 顶部 import 区加(若尚未 import）:
```python
from praxis2.core.rmcp import get_phase
```

把 `_append_turn_entries` 的签名与函数体改为(加 `phase_before` 参数 + 末尾相位 append）:
```python
async def _append_turn_entries(
    ss, state, prev_len: int, *, user_id: str, session_id: str,
    phase_before: str,
) -> None:
    """GAP-B-1:把本轮 query() 新增(state.messages[prev_len:])的 assistant /
    tool_result 消息 append 进 transcript(只 delta,不重写整盘)。每条新 uuid;
    读侧 load_transcript 已按 uuid dedup。user 纯文本已在 chat 路径单独落库,
    不在 delta 区(prev_len 取自 user append 之后)。

    §9.1-A:最终相位≠轮前 → 补 phase-transition,保证重启 resume 的
    rebuild_phase 能恢复相位(GAP-AH 检索先行门不误拦 resume 后首轮)。"""
    for msg in state.messages[prev_len:]:
        role = msg.get("role")
        if role == "assistant":
            etype = "assistant"
        elif role == "user":
            etype = "user"  # tool_result 回合(content 含 tool_result blocks)
        else:
            continue  # 其他 role 不入库
        await ss.append_entry(SessionEntry(
            uuid=uuid.uuid4().hex, type=etype, content=msg.get("content"),
            user_id=user_id, session_id=session_id,
        ))
    phase_after = get_phase(state)
    if phase_after.value != phase_before:
        await record_phase_transition(
            ss, user_id=user_id, session_id=session_id,
            to=phase_after, uuid_=uuid.uuid4().hex,
        )
```

在 chat 路径 Task 4 加的 `_prev_len = len(st.messages)` 一行**之后**加:
```python
                _phase_before = get_phase(st).value  # GAP-B-1 §9.1-A:轮前相位
```

把 Task 4 加的 query 后调用改为传 `phase_before`:
```python
                # GAP-B-1:本轮 query 新增的 assistant/tool delta + 相位变化落 transcript;失败不阻塞。
                if self._session_store is not None:
                    try:
                        await _append_turn_entries(
                            self._session_store, st, _prev_len,
                            user_id=user_id, session_id=session_id,
                            phase_before=_phase_before,
                        )
                    except Exception:  # noqa: BLE001
                        pass
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_gap_b1_persist_turn.py
git commit -m "feat(gap-b-1): 相位变化落 phase-transition,resume 恢复相位(§9.1-A)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: 组件4 — 会话元数据注册 + `GET /api/me/sessions` 端点

**Files:**
- Modify: `praxis2/server/app.py`(顶部确认 `import time`;chat 路径 query 后 `meta_upsert`;新增 `_sessions_list_mine` handler;路由表 `:368` 旁注册)
- Test: `tests/test_gap_b1_sessions_endpoint.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_gap_b1_sessions_endpoint.py`:
```python
"""GAP-B-1 Task 6:GET /api/me/sessions 列当前用户会话 + 多租户隔离 + 无 store。"""
from __future__ import annotations

import json as _json

import pytest

from praxis2.memory.session import SessionStore
from praxis2.server.app import make_app
from praxis2.store.memory import InMemoryStore
from tests._auth_test_helpers import make_test_app_deps, preseed_session
from tests._gap_b1_helpers import drive_chat, install_capture_query


async def _get_sessions(app, cookie):
    arrivals: list[bytes] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.body" and msg.get("body"):
            arrivals.append(msg["body"])

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/me/sessions",
        "headers": [(b"cookie", cookie.encode())],
        "query_string": b"",
    }
    await app(scope, receive, send)
    return _json.loads(b"".join(arrivals))


@pytest.mark.asyncio
async def test_lists_user_sessions(monkeypatch):
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    app._app._session_store = SessionStore(store)
    install_capture_query(monkeypatch, [])
    await drive_chat(app, cookie, message="会话A首条", session_id="sa")
    await drive_chat(app, cookie, message="会话B首条", session_id="sb")
    out = await _get_sessions(app, cookie)
    await deps.redis.aclose()
    sids = {s["session_id"] for s in out["sessions"]}
    assert sids == {"sa", "sb"}, f"应列出两会话,实际 {out['sessions']!r}"
    previews = {s["preview"] for s in out["sessions"]}
    assert "会话A首条" in previews and "会话B首条" in previews


@pytest.mark.asyncio
async def test_tenant_isolation(monkeypatch):
    store = InMemoryStore()
    deps = make_test_app_deps(store=store)
    c1 = await preseed_session(deps, user_id="u1", email="u1@t.com")
    c2 = await preseed_session(deps, user_id="u2", email="u2@t.com")
    app = make_app(deps)
    app._app._session_store = SessionStore(store)
    install_capture_query(monkeypatch, [])
    await drive_chat(app, c1, message="u1的会话", session_id="s1")
    out2 = await _get_sessions(app, c2)  # u2 查
    await deps.redis.aclose()
    assert out2["sessions"] == [], f"u2 不应看到 u1 的会话,实际 {out2['sessions']!r}"


@pytest.mark.asyncio
async def test_no_store_returns_empty():
    deps = make_test_app_deps()  # 默认无 _pool → _session_store None
    cookie = await preseed_session(deps, user_id="u1")
    app = make_app(deps)
    assert app._app._session_store is None
    out = await _get_sessions(app, cookie)
    await deps.redis.aclose()
    assert out == {"sessions": []}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_sessions_endpoint.py -v`
Expected: FAIL（路由 404 → `_json.loads` 解析 `{"error":"not found"}` 后 `out["sessions"]` KeyError,或 `test_no_store_returns_empty` 也 404）

- [ ] **Step 3: 实现**

确认 `app.py` 顶部已 `import time`;若无,在标准库 import 区加 `import time`。
（核对:`grep -n "^import time" praxis2/server/app.py`,无输出则加。）

在 chat 路径 Task 5 的 delta 持久块之后插入会话元数据 upsert:
```python
                # GAP-B-1:会话元数据 upsert(preview=本轮 user 消息截断 + updated_at),
                # 供 GET /api/me/sessions。pk=session_id(InMemoryStore/PgStore 通用主键)。
                if self._session_store is not None:
                    try:
                        await self._deps.store.meta_upsert("sessions", {
                            "user_id": user_id, "pk": session_id,
                            "preview": (message or "")[:40],
                            "updated_at": time.time(),
                        })
                    except Exception:  # noqa: BLE001
                        pass
```

在 `_proposal_list_mine`(`:1003`)附近新增 handler 方法:
```python
    async def _sessions_list_mine(self, scope, receive, send) -> None:
        """GAP-B-1:GET /api/me/sessions —— 当前用户会话列表(最近活动置顶)。"""
        user = scope.get("user")
        if not user:
            await self._json(
                send, 401, {"error": "unauthorized", "reason": "未登录"}
            )
            return
        if self._session_store is None:
            await self._json(send, 200, {"sessions": []})  # 无 PG,零回归
            return
        rows = await self._deps.store.meta_list("sessions", user["user_id"])
        rows.sort(key=lambda r: r.get("updated_at", 0.0), reverse=True)
        await self._json(send, 200, {"sessions": [
            {"session_id": r.get("pk"), "preview": r.get("preview", ""),
             "updated_at": r.get("updated_at", 0.0)}
            for r in rows
        ]})
```

在路由表(`:368` `("/api/me/proposals", "GET"): self._proposal_list_mine,` 一行旁)加:
```python
            ("/api/me/sessions", "GET"): self._sessions_list_mine,
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_sessions_endpoint.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_gap_b1_sessions_endpoint.py
git commit -m "feat(gap-b-1): meta 注册 + GET /api/me/sessions 端点

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: 组件5 验证(round-trip)+ 全量回归收尾

**Files:**
- Test: `tests/test_gap_b1_resume_wire.py`(追加 round-trip)
- 无新实现(组件5 `_resolve_session_id` 已存在)

- [ ] **Step 1: 写 round-trip 测试(模拟重启)**

在 `tests/test_gap_b1_resume_wire.py` 追加:
```python
@pytest.mark.asyncio
async def test_restart_resume_roundtrip(monkeypatch):
    """模拟重启:同一 store(权威持久层)新 app(pool 全新为空)→ 凭 session_id
    resume 出上一进程的历史。验收③后端能力 + 组件5 session_id round-trip。"""
    store = InMemoryStore()

    # 第一进程:一轮对话
    deps1 = make_test_app_deps(store=store)
    cookie1 = await preseed_session(deps1, user_id="u1")
    app1 = make_app(deps1)
    app1._app._session_store = SessionStore(store)
    install_capture_query(monkeypatch, [])
    await drive_chat(app1, cookie1, message="第一轮", session_id="s1")
    await deps1.redis.aclose()

    # "重启":新 deps/app 共享同一 store,pool 为空(SessionPool 不持久)
    deps2 = make_test_app_deps(store=store)
    cookie2 = await preseed_session(deps2, user_id="u1")
    app2 = make_app(deps2)
    app2._app._session_store = SessionStore(store)
    captured2: list = []
    install_capture_query(monkeypatch, captured2)
    await drive_chat(app2, cookie2, message="第二轮", session_id="s1")
    await deps2.redis.aclose()

    assert captured2[0]["messages"] == [
        {"role": "user", "content": "第一轮"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "第二轮"},
    ], f"重启后应凭 session_id resume 历史,实际 {captured2[0]['messages']!r}"
```

- [ ] **Step 2: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_resume_wire.py -v`
Expected: 3 passed（含新 round-trip)

- [ ] **Step 3: 跑组件5 既有回归(确认 session_id fallback 未破)**

Run: `.venv/bin/python -m pytest tests/test_app_session_id_fallback.py tests/test_correctness_session_pool_wire.py -v`
Expected: 全 passed（组件5 现状 + SessionPool 既有行为零回归)

- [ ] **Step 4: 全量回归零失败**

Run:
```bash
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?
.venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/r.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print('tests=%s failures=%s errors=%s'%(s.get('tests'), s.get('failures'), s.get('errors')))"
```
Expected: `failures=0 errors=0`（汇总行被 sandbox 吞,故解析 junit)

- [ ] **Step 5: Commit**

```bash
git add tests/test_gap_b1_resume_wire.py
git commit -m "test(gap-b-1): 重启 resume round-trip + 全量回归收尾

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 完成后(controller 亲做,不在 subagent task 内)
- staging 部署 + e2e:重启 gunicorn 后凭固定 session_id 直打 `/chat/stream`,验证历史 resume;`GET /api/me/sessions` 返回会话(spec §10.4)。
- ship 前可跑 `scripts/ship_gate.py`(需 `PRAXIS_EVAL_EMAIL/PASSWORD`,问用户取)。
- SP2 前端(稳定 session_id + ConversationSidebar 接 `/api/me/sessions`)作后续独立 spec。

## 雷区(每 task 提醒 subagent)
- commit 只 `git add` 列出的目标文件,**绝不 `git add .`/`-A`**(工作区 stray microbiome 文件)。
- 持久化全部 `try/except` 包裹,**绝不阻塞 chat 流**。
- `_prev_len` 必须在 user `append_entry` 之后、`query()` 之前记录(否则 delta 含 user → 重复)。
- meta row 主键用 **`pk`**(不是 `id`),否则 `InMemoryStore.meta_upsert` 抛 ValueError。
- 不改 `praxis2/memory/session.py` 与 `query.py` 内核(只复用/外层接线)。
- delicate core(`app.py` chat 路径)diff 由 controller 细审。
