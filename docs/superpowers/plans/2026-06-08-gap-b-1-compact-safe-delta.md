# GAP-B-1 compact-safe delta 追踪 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 chat 路径追踪本轮 transcript delta 的方式从位置索引(`_prev_len`)改为对象身份快照(`_seen_ids`),消除 reactive compact reassign `state.messages` 导致的 tool delta 越界漏持久。

**Architecture:** query 前记 `_seen_ids = {id(m) for m in st.messages}`;query 后 `_append_turn_entries` 遍历 `state.messages`、跳过 `id` 在快照里的(历史 + 已单独持久的 user),持久其余(本轮新 append 的 assistant/tool)。compact 切片保留原对象(id 命中→跳过)、本轮新对象 id 必不在快照(→持久),故不漏。仅改 `praxis2/server/app.py`,不碰 query.py 内核 / session.py。

**Tech Stack:** Python 3.11、pytest + pytest-asyncio。参考 spec:`docs/superpowers/specs/2026-06-08-gap-b-1-compact-safe-delta-design.md`。流程:main 直接干(无 worktree),逐 task TDD。commit 只 `git add` 目标文件(**绝不 `git add .`**——工作区有 stray `brains/microbiome` 文件),末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `praxis2/server/app.py` | chat 路径 delta 追踪 | Modify(3 处:query 前快照 / `_append_turn_entries` 遍历 / 调用传参) |
| `tests/test_gap_b1_persist_turn.py` | compact 回归测试 | Modify(追加 `test_delta_survives_reactive_compact`) |

**测试运行**:`.venv/bin/python -m pytest <path> -v`
**全量回归**:`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?`(解析 `/tmp/r.xml`)

### 关键锚点(当前 ship 后 `98c0914`)
- `app.py:105-108` `_append_turn_entries(ss, state, prev_len: int, *, user_id, session_id, phase_before)`;`:113` `for msg in state.messages[prev_len:]:`;role 处理 `:114-134`(content 检查不变);相位段 `:135-142`(不变)。
- `app.py:829-830` chat 路径 `# GAP-B-1:delta 起点...` + `_prev_len = len(st.messages)`;`:831` `_phase_before`。
- `app.py:866-870` 调用 `await _append_turn_entries(self._session_store, st, _prev_len, ...)`。
- `tests/test_gap_b1_persist_turn.py`:现有 4 测试 + `_make_persistent_app` helper;`tests/_gap_b1_helpers.py` 的 `drive_chat`。

---

## Task 1: compact-safe delta(对象身份追踪)

**Files:**
- Modify: `praxis2/server/app.py`(3 处)
- Test: `tests/test_gap_b1_persist_turn.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/test_gap_b1_persist_turn.py` 末尾追加:
```python
@pytest.mark.asyncio
async def test_delta_survives_reactive_compact(monkeypatch):
    """fake query append 本轮 assistant(tool_use)后模拟 reactive compact 截断
    state.messages(reassign,丢弃前段),本轮 assistant 仍经对象身份 diff 持久。
    旧 _prev_len 位置索引在此会越界空切片漏持久(query 前 len=1,compact 后
    messages[1:]=[]),id 追踪不漏——compact 缺陷的直接回归锚。"""
    from praxis2.server import app as app_module

    store = InMemoryStore()
    deps, app = _make_persistent_app(store)
    cookie = await preseed_session(deps, user_id="u1")

    async def fake_query(
        state, *, client, registry, settings, runner, compactor, **_kw
    ):
        # 本轮 append 一条 assistant(tool_use)——这是要持久的本轮新增
        state.messages.append({"role": "assistant", "content": [
            {"type": "tool_use", "id": "tc1", "name": "x", "input": {}}]})
        # 模拟 reactive compact:reassign 截断,只留尾段(含本轮 assistant);
        # 入口 messages=[user 问](query 前 len=1),此后 messages 变短到 len=1,
        # 使旧 _prev_len=1 的 messages[1:] 成空切片(漏),id-diff 不漏。
        state.messages = state.messages[-1:]
        yield {"type": "end", "reason": "stop"}

    monkeypatch.setattr(app_module, "query", fake_query)

    await drive_chat(app, cookie, message="问", session_id="s1")
    await deps.redis.aclose()
    seq = await app._app._session_store.load_transcript(
        user_id="u1", session_id="s1")
    # 本轮 user "问"(query 前持久,不受 compact 影响)
    assert any(e.type == "user" and e.content == "问" for e in seq), \
        f"user 应持久,实际 {[(e.type, e.content) for e in seq]!r}"
    # 关键:tool_use assistant(本轮新增对象)在 compact 截断后仍被 id-diff 持久
    tool_use_persisted = any(
        e.type == "assistant" and isinstance(e.content, list)
        and any(isinstance(b, dict) and b.get("type") == "tool_use"
                for b in e.content)
        for e in seq)
    assert tool_use_persisted, \
        f"compact 截断后 tool_use assistant 应仍持久,实际 {[(e.type, e.content) for e in seq]!r}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py::test_delta_survives_reactive_compact -v`
Expected: FAIL —— 当前 `_prev_len` 实现:query 前 `_prev_len=1`,fake compact 后 `st.messages` 截到 len=1,`st.messages[1:]` 为空切片 → tool_use assistant 未持久 → `tool_use_persisted` 断言失败。

- [ ] **Step 3: 实现(3 处 Edit)**

**(3a)** 把 `app.py:829-830` 的:
```python
                # GAP-B-1:delta 起点(已含本轮 user)——query 后据此 append 新增 assistant/tool。
                _prev_len = len(st.messages)
```
替换为:
```python
                # GAP-B-1:delta 起点用对象身份快照(抗 reactive compact 对 st.messages
                # 的 reassign 截断;位置索引 _prev_len 会越界漏持久 tool delta,见
                # compact-safe spec)。本轮 user 已单独持久,其 id 在快照内 → 不重复。
                _seen_ids = {id(m) for m in st.messages}
```

**(3b)** 把 `app.py:105-113` 的(签名 + docstring + for 行):
```python
async def _append_turn_entries(
    ss: SessionStore, state: State, prev_len: int,
    *, user_id: str, session_id: str, phase_before: str,
) -> None:
    """GAP-B-1:把本轮 query() 新增(state.messages[prev_len:])的 assistant /
    tool_result 消息 append 进 transcript(只 delta,不重写整盘)。每条新 uuid;
    读侧 load_transcript 已按 uuid dedup。user 纯文本已在 chat 路径单独落库,
    不在 delta 区(prev_len 取自 user append 之后)。"""
    for msg in state.messages[prev_len:]:
```
替换为:
```python
async def _append_turn_entries(
    ss: SessionStore, state: State, seen_ids: set[int],
    *, user_id: str, session_id: str, phase_before: str,
) -> None:
    """GAP-B-1:把本轮 query() 新增(state.messages 中 id 不在 seen_ids 的)
    assistant / tool_result 消息 append 进 transcript(只 delta,不重写整盘)。
    每条新 uuid;读侧 load_transcript 已按 uuid dedup。user 纯文本已在 chat 路径
    单独落库,其 id 在 seen_ids → 跳过,不重复。

    对象身份(id)追踪而非位置索引:抗 reactive compact 对 state.messages 的
    reassign 截断——compact 删旧对象、保留切片仍是原对象(id 命中→跳过),本轮
    新 append 的对象 id 必不在 query 前快照(→持久)。id 在 query 期间被 messages
    持有不被 GC,故稳定不复用。"""
    for msg in state.messages:
        if id(msg) in seen_ids:
            continue  # 历史 + 已单独持久的本轮 user → 跳过
```
(注:`for` 循环体内的 role 处理 `if role == "assistant": ... elif role == "user": ...(content 检查)... else: continue` 与 `await ss.append_entry(...)`,以及其后的相位持久段,**全部保持不变**。)

**(3c)** 把 `app.py:866-867` 调用的:
```python
                        await _append_turn_entries(
                            self._session_store, st, _prev_len,
```
替换为:
```python
                        await _append_turn_entries(
                            self._session_store, st, _seen_ids,
```

- [ ] **Step 4: 跑测试确认通过 + 现有回归**

Run: `.venv/bin/python -m pytest tests/test_gap_b1_persist_turn.py -v`
Expected: 5 passed(现有 4 + 新 `test_delta_survives_reactive_compact`)。现有 4 测试在正常无 compact 轮下,对象身份等价位置索引,不回归。

- [ ] **Step 4.5: ruff gate**

Run: `.venv/bin/ruff check praxis2/server/app.py tests/test_gap_b1_persist_turn.py`
Expected: `All checks passed!`。不 clean 则 `ruff check --fix` 后再查。

- [ ] **Step 5: 全量回归 + Commit**

Run:
```bash
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?
.venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/r.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print('tests=%s failures=%s errors=%s'%(s.get('tests'), s.get('failures'), s.get('errors')))"
```
Expected: `failures=0 errors=0`。

Then:
```bash
git add praxis2/server/app.py tests/test_gap_b1_persist_turn.py
git commit -m "fix(gap-b-1): delta 改对象身份追踪,抗 reactive compact 漏持久

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## 雷区(提醒 subagent)
- commit 只 `git add` 列出的 2 文件,**绝不 `git add .`/`-A`**(stray `brains/microbiome`)。
- `_seen_ids` 必须在原 `_prev_len` 同位置(user `append_entry` 之后、query 之前)捕获——保证本轮 user 的 id 在快照,delta 跳过不重复。
- `_append_turn_entries` **只改遍历起点**(`state.messages[prev_len:]` → `for ...: if id(msg) in seen_ids: continue`),签名 `prev_len: int` → `seen_ids: set[int]`;role 处理 / content 检查 / 相位持久段**保持不变**(前序 review 修过)。
- delicate core(`app.py` chat 路径)diff controller 细审。
</content>
