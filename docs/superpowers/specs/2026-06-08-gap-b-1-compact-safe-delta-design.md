# Spec:GAP-B-1 compact-safe delta 追踪(修 `_prev_len` 越界漏持久)

- **状态**:设计已批准(brainstorm 完成),待用户 review → `writing-plans` → `subagent-driven-development`
- **范围**:GAP-B-1 SP1 的 follow-up 缺陷修复(单文件 `app.py`)。SP1 已 ship(`98c0914`,staging 部署 + 真 PG probe e2e 通过)
- **约束**:main 直接干(无 worktree);commit 只 add 目标文件(工作区有 stray `brains/microbiome` 文件,绝不 `git add .`);commit 末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## 1. 背景与问题

GAP-B-1 SP1 的 chat 路径用**位置索引**追踪本轮新增的 transcript delta:

```python
_prev_len = len(st.messages)        # query 前
... query() ...
# query 后:_append_turn_entries 持久 st.messages[_prev_len:]
```

`query()` 内核在 `PROMPT_TOO_LONG` 时会触发 **reactive compact**(`praxis2/core/query.py:118-120`),调 `MinimalCompactor.compact()`(`praxis2/core/seams.py:91-113`),其末尾:

```python
state.messages = msgs[len(msgs) // 2 :]   # reassign,截断为后半段
```

`state.messages` 被 **reassign 截短**后,query 前记录的 `_prev_len`(旧长度,如 10)指向越界位置 → `st.messages[10:]` 为空 → **本轮 assistant/tool delta 被静默漏持久**进 transcript。

**缺陷边界(已核对)**:
- chat 路径调 `query()` **未传 `precompact_gate`** → 主动 compact 路径不激活;只有 reactive compact(超长对话 `PROMPT_TOO_LONG`)会触发。
- `_prev_len` **只追踪 tool_use assistant + tool_result delta**。本轮 **user 消息**(query 前已单独 `append_entry`)和 **assistant 文本答复**(query 后从 `assistant_text` buffer 持久)**都不走 `_prev_len`,不受 compact 影响**。
- 故仅当「超长对话触发 reactive compact」**且**「该轮含 tool_use」同时成立才漏——罕见 **Minor**,但是真实正确性缺口(code review Task 4 / final review 已标记为已知限制)。

---

## 2. 目标与非目标

### 目标
用**对象身份快照**替代位置索引追踪 delta,使本轮新增的 assistant/tool 消息在 reactive compact reassign `state.messages` 后仍被正确持久。

### 非目标
- 不重构 `MinimalCompactor` / `core/compact.py`(M4 AutoCompactor 范围)。
- 不碰 `query.py` 内核 / 内核 hook(延续 SP1「不动 query.py 内核」边界)。
- 不动 `session.py`(复用)。
- 不处理 compact **自身**的语义正确性(如 compact 后 transcript 与 messages 的一致性);只修 delta 追踪不漏。

---

## 3. 设计

**核心洞察**:`_prev_len` 的脆弱性源于「用位置索引追踪 append-only 序列,但 compact 会 reassign 截断它」。改用**对象身份**:compact 删除旧 message 对象、保留的切片仍是**原对象**;本轮 query append 的是**新对象**,其 `id()` 必不在 query 前的快照里。

### 改动(3 处,均在 `praxis2/server/app.py`)

**(a) chat 路径 query 前** —— `_prev_len` 改 `_seen_ids`:
```python
# GAP-B-1:delta 起点用对象身份快照(抗 reactive compact 对 st.messages 的
# reassign 截断;位置索引 _prev_len 会越界漏持久 tool delta)。
_seen_ids = {id(m) for m in st.messages}
_phase_before = get_phase(st).value
```

**(b) `_append_turn_entries`** —— 签名 `prev_len: int` 改 `seen_ids: set[int]`,遍历方式从切片改为 id 过滤(**content 检查 / 相位持久段不变**):
```python
async def _append_turn_entries(
    ss: SessionStore, state: State, seen_ids: set[int],
    *, user_id: str, session_id: str, phase_before: str,
) -> None:
    """...本轮新增 = state.messages 中 id 不在 seen_ids 的(对象身份追踪,抗
    reactive compact 对 state.messages 的 reassign 截断:compact 删旧对象、
    保留切片仍是原对象,本轮新 append 的对象 id 必不在 query 前快照)。"""
    for msg in state.messages:
        if id(msg) in seen_ids:
            continue  # 历史 + 已单独持久的本轮 user → 跳过
        role = msg.get("role")
        if role == "assistant":
            etype = "assistant"
        elif role == "user":
            # (现有 content 检查不变:只持久含 tool_result block 的 user)
            ...
        else:
            continue
        await ss.append_entry(SessionEntry(...))
    # (现有相位持久段不变)
```

**(c) 调用处** —— 传 `_seen_ids`:
```python
await _append_turn_entries(
    self._session_store, st, _seen_ids,
    user_id=user_id, session_id=session_id, phase_before=_phase_before,
)
```

---

## 4. 正确性论证

| 场景 | 行为 |
|------|------|
| **正常轮(无 compact)** | `seen_ids` = query 前 messages 的 id;query append assistant/tool(新对象,id 不在 `seen_ids`)→ delta = 新增。**等价旧 `_prev_len`**,零回归。 |
| **compact 轮** | `state.messages = msgs[half:]`(切片)→ 保留原对象(id 在 `seen_ids` → 跳过);本轮 append 的新对象(id 不在 `seen_ids` → 持久)。compact 删除的旧对象已不在 messages,自然不持久(本就不该)。**不漏。** |
| **顺序** | `for msg in state.messages` 按 messages 顺序遍历,跳过旧的,新增按序持久 → transcript 顺序正确。 |

**id 安全性**:
- query 期间所有 message 对象被 `state.messages`(或 compact 的 `keep` 切片)持有引用,**不被 GC** → `id` 不被新对象复用 → query 前的 `_seen_ids`(id 值)在 query 后仍唯一指向同对象。
- `_seen_ids` 是 chat 请求内局部变量,**不跨请求**,无 id 跨调用复用问题。
- query 不**替换**已有 message dict(只 `append` 新 + compact `reassign list`,元素 dict 是切片复用的原对象)→ 无「同位置新对象 id 撞旧 id」风险。

---

## 5. 测试策略

### 新增(缺陷回归锚)
`test_delta_survives_reactive_compact`:fake query 内 append 一条 assistant(tool_use)后,模拟 reactive compact —— `state.messages = state.messages[len//2:]`(reassign 截断),确保 append 的 assistant 落在保留段末尾;断言该 assistant 仍被持久进 transcript。**旧 `_prev_len` 机制此处会漏(空切片),id 追踪不漏**——这是缺陷的直接回归。

### 回归
- 现有 4 个 `test_gap_b1_persist_turn.py` 测试(正常无 compact 轮,对象身份 ≡ 位置索引)。
- 全量回归零失败:`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=no --junit-xml=/tmp/r.xml`(解析 junit)。
- ruff clean(`praxis2/server/app.py`)。

### e2e(controller)
缺陷罕见(超长 + tool 轮),staging 难自然触发;单测的 compact 模拟 + 全量回归已是充分证据,**不强制 staging HTTP e2e**。若部署,沿 SP1 SOP(rsync app.py + HUP reload)。

---

## 6. 雷区

- **commit 只 add `app.py` + 测试文件**;工作区常驻 stray `brains/microbiome/...`,绝不 `git add .`。
- `_seen_ids` 必须在 user `append_entry` **之后**、query **之前**捕获(与原 `_prev_len` 同位置)——保证本轮 user 的 id 在 `seen_ids`(已单独持久,delta 跳过,不重复)。
- 改 `_append_turn_entries` 时**只动遍历起点**(切片→id 过滤),content 检查 / 相位持久段保持不变(它们是前序 review 修过的)。
- delicate core(`app.py` chat 路径)diff controller 细审。

---

## 7. 代码锚点(GAP-B-1 ship 后 `98c0914`)

- `praxis2/server/app.py`:`_append_turn_entries`(模块级,`_resolve_session_id` 之后);chat 路径 `_prev_len = len(st.messages)` + `_phase_before`(query 前);`await _append_turn_entries(...)`(query try/finally 之后)。
- `praxis2/core/query.py:118-120`:reactive compact 触发(`PROMPT_TOO_LONG` → `compactor.compact(state)`)。chat 路径 `query()` 调用未传 `precompact_gate`(主动 compact 不激活)。
- `praxis2/core/seams.py:91-113`:`MinimalCompactor.compact()`,末尾 `state.messages = keep`(reassign 截断)。
- `tests/test_gap_b1_persist_turn.py`:现有 4 测试 + `tests/_gap_b1_helpers.py`(`install_capture_query` 忠实内核 fake)。
</content>
</invoke>
