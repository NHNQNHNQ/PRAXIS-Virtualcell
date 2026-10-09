# GAP-AH-1 + GAP-AH-2 反幻觉接生产 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把"检索先行证据门"与"声称执行+零证据 veto 的 stop_hook"接入 PRAXIS-2 chat 生产路径,堵两条幻觉根因路径,不破黄金链路、全量零回归。

**Architecture:** 新增轻量 `RetrieveFirstPermission`(rmcp_op≠None 工具仅"已检索/phase≠INIT"才放行)作为 `app.py` 权限链 base;BrainQuery 真命中经实例属性 + 新 post_hook `advance_phase_on_real_retrieval` 推进相位;新 `make_tool_use_presence_stop_hook` 经 `query(stop_hook=…)` 接入。附带修 `SkillExec.rmcp_op` latent bug + 强化 `AgentTool` 描述。

**Tech Stack:** Python 3.11、pytest、现有 RMCP 相位机(`core/rmcp.py`)、permission seam(`core/seams.py`)、`SerialToolRunner` post_hooks(`tools/runtools.py`)、FakeLLMClient(`tests/_llm_fakes.py`)。

参考 spec:`docs/superpowers/specs/2026-06-06-gap-ah-antihallucination-wiring-design.md`。流程:main 直接干(无 worktree),逐 task TDD 红→绿→commit + 两阶段 review。commit 末尾加 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `praxis2/tools/skill_exec.py` | SkillExec 工具;`rmcp_op` | 改 `"execute"`→`"call_skill"`(对齐 ALLOWED_OPS[EXECUTE]) |
| `praxis2/agents/agent_tool.py` | AgentTool;`description` | 强化描述(不自动 fork/返回非完成) |
| `praxis2/tools/permission.py` | 权限策略 | 新增 `RetrieveFirstPermission` |
| `praxis2/tools/brain_query.py` | BrainQuery 工具 | run() 记 `self.last_retrieval_real_hit` 实例属性 |
| `praxis2/hooks/builtin.py` | PostToolUse/stop hook | 新增 `advance_phase_on_real_retrieval` post_hook + `make_tool_use_presence_stop_hook` + claims 检测助手 |
| `praxis2/core/state.py` | State | 新增 `stop_hook_veto_count: int = 0` |
| `praxis2/server/app.py` | chat 路由接线 | 串 `RetrieveFirstPermission` base + `post_hooks` + `query(stop_hook=…)` |

测试:`tests/test_tools_skill_exec.py`、`tests/test_agent_tool_description.py`(新)、`tests/test_tools_permission.py`、`tests/test_brain_query_retrieval_flag.py`(新)、`tests/test_hooks_retrieve_advance.py`(新)、`tests/test_hooks_tool_evidence.py`(新)、`tests/test_gap_ah_integration.py`(新)。

测试运行约定(全量回归,汇总行被 sandbox 吞,用 junit-xml 取数):
```
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=short
```
单测直接 `.venv/bin/python -m pytest <path>::<name> -v`。

---

## Task 1: 修 SkillExec.rmcp_op latent bug

**Files:**
- Modify: `praxis2/tools/skill_exec.py:107`
- Test: `tests/test_tools_skill_exec.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_tools_skill_exec.py` 末尾追加:
```python
def test_skill_exec_rmcp_op_matches_execute_phase_whitelist():
    """latent bug:rmcp_op 须等于 ALLOWED_OPS[EXECUTE] 的成员(call_skill),
    否则即便相位到 EXECUTE,PhaseAwarePermission 也对不上而拒。"""
    from praxis2.core.rmcp import ALLOWED_OPS, Phase
    from praxis2.tools.skill_exec import SkillExecTool

    assert SkillExecTool.rmcp_op == "call_skill"
    assert SkillExecTool.rmcp_op in ALLOWED_OPS[Phase.EXECUTE]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_tools_skill_exec.py::test_skill_exec_rmcp_op_matches_execute_phase_whitelist -v`
Expected: FAIL（`assert "execute" == "call_skill"`）

- [ ] **Step 3: 改实现**

`praxis2/tools/skill_exec.py` 第 107 行:
```python
    rmcp_op = "call_skill"  # §7.3.7:写/执行类显式声明;须 ∈ ALLOWED_OPS[EXECUTE]={"call_skill"}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_tools_skill_exec.py -v`
Expected: PASS（全文件，确认无回归）

- [ ] **Step 5: commit**

```bash
git add praxis2/tools/skill_exec.py tests/test_tools_skill_exec.py
git commit -m "fix(skill_exec): rmcp_op execute→call_skill 对齐 ALLOWED_OPS[EXECUTE]

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 强化 AgentTool 描述(堵风险点①措辞误导)

**Files:**
- Modify: `praxis2/agents/agent_tool.py:48`
- Test: `tests/test_agent_tool_description.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_agent_tool_description.py`:
```python
from praxis2.agents.agent_tool import AgentTool


def test_agent_tool_description_warns_not_auto_fork():
    """风险点①:run() 只构 spawn 描述符恒 ok=True。描述须显式声明
    '只返回描述符/不代表子 agent 已完成',防模型把'已构造'当'已完成分析'转述。"""
    d = AgentTool.description
    assert "不代表" in d and "完成" in d
    assert "描述符" in d
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_agent_tool_description.py -v`
Expected: FAIL（旧描述无这些词）

- [ ] **Step 3: 改实现**

`praxis2/agents/agent_tool.py` 第 48 行:
```python
    description = (
        "fork 一个隔离子 agent 执行受限子任务(身份/上下文/token 三层隔离)。"
        "注意:本工具只返回 spawn 描述符/已提交占位,不代表子 agent 已完成分析或产出最终结论;"
        "勿把本工具返回当作子 agent 的完成结果转述。"
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_agent_tool_description.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add praxis2/agents/agent_tool.py tests/test_agent_tool_description.py
git commit -m "feat(agent_tool): 描述显式声明只返描述符不代表子 agent 完成(反幻觉风险点①)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: RetrieveFirstPermission(检索先行证据门)

**Files:**
- Modify: `praxis2/tools/permission.py`(新增类;import 加 `Phase`)
- Test: `tests/test_tools_permission.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_tools_permission.py` 末尾追加:
```python
def test_retrieve_first_permission_matrix():
    from praxis2.core.rmcp import Phase, set_phase
    from praxis2.core.seams import (
        PermissionDecision, PermissionPolicy, PermissionResult,
    )
    from praxis2.core.state import State
    from praxis2.tools.permission import RetrieveFirstPermission

    class _AllowBase(PermissionPolicy):
        def check(self, *, tool, payload, state):
            return PermissionResult(PermissionDecision.ALLOW)

    class _DenyBase(PermissionPolicy):
        def check(self, *, tool, payload, state):
            return PermissionResult(PermissionDecision.DENY, "base 拒")

    class _ExecTool:
        name = "SkillExec"
        rmcp_op = "call_skill"

    class _ReadTool:
        name = "BrainQuery"
        rmcp_op = None

    pol = RetrieveFirstPermission(_AllowBase())

    # 1) INIT + rmcp_op → DENY
    st = State()
    d = pol.check(tool=_ExecTool(), payload={}, state=st)
    assert d.decision is PermissionDecision.DENY
    assert "检索先行" in (d.reason or "")

    # 2) 已检索(phase!=INIT)+ rmcp_op → ALLOW
    st2 = State()
    set_phase(st2, Phase.RETRIEVE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st2).decision \
        is PermissionDecision.ALLOW

    # 3) rmcp_op=None → 透传 ALLOW(即便 INIT)
    assert pol.check(tool=_ReadTool(), payload={}, state=State()).decision \
        is PermissionDecision.ALLOW

    # 4) base 非 ALLOW(DENY/ASK)优先返回,不进相位判定
    pol_deny = RetrieveFirstPermission(_DenyBase())
    dd = pol_deny.check(tool=_ReadTool(), payload={}, state=State())
    assert dd.decision is PermissionDecision.DENY and dd.reason == "base 拒"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_tools_permission.py::test_retrieve_first_permission_matrix -v`
Expected: FAIL（`ImportError: cannot import name 'RetrieveFirstPermission'`）

- [ ] **Step 3: 改实现**

`praxis2/tools/permission.py` 顶部 import 改为(加 `Phase`):
```python
from praxis2.core.rmcp import ALLOWED_OPS, Phase, get_phase
```

文件末尾追加:
```python
class RetrieveFirstPermission(PermissionPolicy):
    """§7.3.7 chat 生产证据门(检索先行):先过 base(deny/ask 优先);base 放行后,
    rmcp_op != None 的执行/写入类工具仅当本会话已发生成功检索(相位已离开 INIT)才放行,
    否则 DENY 并在 reason 引导模型自补 BrainQuery(不停下问人,§4)。rmcp_op=None 的
    检索/读/编排类工具透传。空/fixture/降级检索不推进相位 → 执行仍被拒(反幻觉不失守)。"""

    def __init__(self, base: PermissionPolicy) -> None:
        self._base = base

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        base = self._base.check(tool=tool, payload=payload, state=state)
        if base.decision is not PermissionDecision.ALLOW:
            return base  # base 层 deny/ask 优先
        op = getattr(tool, "rmcp_op", None)
        if op is None:
            return base  # 检索/读/编排类,不受证据门约束
        if get_phase(state) is Phase.INIT:
            return PermissionResult(
                PermissionDecision.DENY,
                "检索先行:本会话尚无成功的大脑检索(BrainQuery 命中),不能执行/写入。"
                "请先用 BrainQuery 检索相关 cases/rules,命中后再调用"
                "(自行补检索,勿停下问人)。",
            )
        return PermissionResult(PermissionDecision.ALLOW)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_tools_permission.py -v`
Expected: PASS（全文件无回归）

- [ ] **Step 5: commit**

```bash
git add praxis2/tools/permission.py tests/test_tools_permission.py
git commit -m "feat(permission): RetrieveFirstPermission 检索先行证据门(GAP-AH-1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: BrainQuery 记录真命中实例属性

**Files:**
- Modify: `praxis2/tools/brain_query.py`(类属性默认 + run() 末尾置位)
- Test: `tests/test_brain_query_retrieval_flag.py`(新)

**说明**:tools 的 `run(payload)` 不接 state,post_hook 收到的是字符串化 result(无结构化 value 且可能被 budget 截断)。故由 BrainQuery 在**自身实例**上记结构化判定 `last_retrieval_real_hit`,Task 5 的 post_hook 在同一 `tool` 实例上读取(run_turn 里 `tool.run()` 后紧接同一 `tool` 调 post_hook,必可读)。

- [ ] **Step 1: 写失败测试**

新建 `tests/test_brain_query_retrieval_flag.py`:
```python
from praxis2.tools.brain_query import BrainQueryTool


def _make_tool():
    return BrainQueryTool()


async def test_real_hit_sets_flag_true():
    tool = _make_tool()
    # enzyme 真盘有 cases;查命中词
    res = await tool.run({"brain": "enzyme", "query": "thermostability", "top_k": 3})
    assert res.ok
    if res.value.get("source") == "filesystem" and res.value.get("hits"):
        assert tool.last_retrieval_real_hit is True


async def test_unknown_brain_flag_false():
    tool = _make_tool()
    res = await tool.run({"brain": "no_such_brain_xyz", "query": "x"})
    assert not res.ok  # 未知 brain
    assert tool.last_retrieval_real_hit is False


async def test_empty_query_keeps_flag_false():
    tool = _make_tool()
    await tool.run({"brain": "enzyme", "query": ""})
    assert tool.last_retrieval_real_hit is False
```
（注:文件需 `pytest.ini`/`conftest` 已开 asyncio_mode=auto;参照同目录现有 async 测试。若未开,函数加 `@pytest.mark.asyncio`。先看 `tests/test_tools_brain_query*.py` 或 `tests/conftest.py` 确认。）

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_brain_query_retrieval_flag.py -v`
Expected: FAIL（`AttributeError: ... last_retrieval_real_hit` 或属性不存在）

- [ ] **Step 3: 改实现**

`praxis2/tools/brain_query.py`:在类体(`rmcp_op = None` 附近,约 47 行)加类属性默认:
```python
    last_retrieval_real_hit = False  # GAP-AH-1:本工具最近一次是否真命中(非 fixture/空/降级)
```
在 `run()` 的成功 `return ToolResult(...)`(约 150 行)**之前**置位:
```python
        self.last_retrieval_real_hit = (
            source == "filesystem"
            and not result.degraded_to_bare
            and bool(hits_view)
        )
        return ToolResult(
            ok=True,
            value={
                ...（保持原有 value 不变）
            },
        )
```
（错误/缺参的早 return 路径不动:类属性默认 False 即"未发生真命中"。）

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_brain_query_retrieval_flag.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add praxis2/tools/brain_query.py tests/test_brain_query_retrieval_flag.py
git commit -m "feat(brain_query): 记录 last_retrieval_real_hit 供检索先行门推进相位(GAP-AH-1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: advance_phase_on_real_retrieval post_hook

**Files:**
- Modify: `praxis2/hooks/builtin.py`(新增函数)
- Test: `tests/test_hooks_retrieve_advance.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_hooks_retrieve_advance.py`:
```python
from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.state import State
from praxis2.hooks.builtin import advance_phase_on_real_retrieval


class _BrainQueryReal:
    name = "BrainQuery"
    last_retrieval_real_hit = True


class _BrainQueryFixture:
    name = "BrainQuery"
    last_retrieval_real_hit = False


def _ok(tid="t"):
    return {"type": "tool_result", "tool_use_id": tid, "is_error": False, "content": "x"}


def test_real_hit_advances_init_to_retrieve():
    st = State()  # INIT
    out = advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, _ok(), st)
    assert out is None  # 永不替换 result
    assert get_phase(st) is Phase.RETRIEVE


def test_fixture_hit_does_not_advance():
    st = State()
    advance_phase_on_real_retrieval(_BrainQueryFixture(), {"id": "t"}, _ok(), st)
    assert get_phase(st) is Phase.INIT


def test_idempotent_no_double_advance_no_phaseerror():
    st = State()
    advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, _ok(), st)
    advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, _ok(), st)  # 再来不报错
    assert get_phase(st) is Phase.RETRIEVE


def test_error_result_does_not_advance():
    st = State()
    err = {"type": "tool_result", "tool_use_id": "t", "is_error": True, "content": "boom"}
    advance_phase_on_real_retrieval(_BrainQueryReal(), {"id": "t"}, err, st)
    assert get_phase(st) is Phase.INIT
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_hooks_retrieve_advance.py -v`
Expected: FAIL（`ImportError: cannot import name 'advance_phase_on_real_retrieval'`）

- [ ] **Step 3: 改实现**

`praxis2/hooks/builtin.py` 追加（文件顶部已 import `Phase, advance_phase, get_phase`）:
```python
def advance_phase_on_real_retrieval(
    tool: Any, blk: dict, result: dict, state: State
) -> dict | None:
    """GAP-AH-1 检索先行接线(chat):BrainQuery 真命中(tool.last_retrieval_real_hit)
    且当前 INIT → 推进 RETRIEVE。fixture/空/降级/错误结果不推进(执行仍被证据门拒)。
    幂等:已非 INIT 不动(守 S7 无 RETRIEVE→RETRIEVE 边,避 PhaseError)。永不替换 result。"""
    if result.get("is_error"):
        return None
    if getattr(tool, "last_retrieval_real_hit", False) and get_phase(state) is Phase.INIT:
        advance_phase(state, Phase.RETRIEVE)
    return None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_hooks_retrieve_advance.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add praxis2/hooks/builtin.py tests/test_hooks_retrieve_advance.py
git commit -m "feat(hooks): advance_phase_on_real_retrieval post_hook(BrainQuery 真命中推进相位)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: tool_use_presence stop_hook + 防循环计数

**Files:**
- Modify: `praxis2/core/state.py`(加 `stop_hook_veto_count`)
- Modify: `praxis2/hooks/builtin.py`(claims 检测 + stop_hook 工厂)
- Test: `tests/test_hooks_tool_evidence.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_hooks_tool_evidence.py`:
```python
from praxis2.core.state import State
from praxis2.hooks.builtin import make_tool_use_presence_stop_hook


def _state_with_final(text, *, tool_ok=False):
    st = State()
    st.messages = [{"role": "user", "content": "请帮我对接"}]
    if tool_ok:
        st.messages.append(
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": False,
                 "content": "ok"}]}
        )
    st.messages.append(
        {"role": "assistant", "content": [{"type": "text", "text": text}]}
    )
    return st


def test_claims_execution_zero_tools_vetoes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("我已对接完成,最佳亲和力 -9.2 kcal/mol。")
    dec = hook(st)
    assert dec.veto is True
    assert st.stop_hook_veto_count == 1


def test_claims_but_has_successful_tool_use_passes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("我已对接完成,得分 -9.2。", tool_ok=True)
    assert hook(st).veto is False


def test_no_claims_passes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("你可以用 AutoDock Vina 方法来做对接,大致流程是……")
    assert hook(st).veto is False


def test_veto_capped_once():
    hook = make_tool_use_presence_stop_hook(max_veto=1)
    st = _state_with_final("我已对接完成,得分 -9.2。")
    assert hook(st).veto is True   # 第一次 veto
    assert hook(st).veto is False  # 计数到顶,不再 veto(防循环)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_hooks_tool_evidence.py -v`
Expected: FAIL（`ImportError` make_tool_use_presence_stop_hook / `AttributeError` stop_hook_veto_count）

- [ ] **Step 3a: 加 State 字段**

`praxis2/core/state.py`,在 `pending_stop_reasons` 字段附近(约 49 行后)加:
```python
    stop_hook_veto_count: int = 0  # GAP-AH-2:tool_use_presence stop_hook 已 veto 次数(防循环)
```

- [ ] **Step 3b: 加 claims 检测 + stop_hook 工厂**

`praxis2/hooks/builtin.py` 追加（顶部已 import `re`、`StopDecision`、`State`、`Callable`）:
```python
# GAP-AH-2:声称"已执行/已分析/有结果"的中英特征(v1 小而精,精度优先,可后扩)
_CLAIM_PATTERNS = re.compile(
    r"已(运行|执行|对接|折叠|计算|跑完|完成对接|完成折叠|完成分析|得到结果)"
    r"|结果(显示|为|如下|是)"
    r"|(最佳|预测)?(亲和力|结合能|打分|得分|plddt|rmsd)"
    r"|docked|folded|computed|executed|ran the|results?\s+show|affinity\s+is",
    re.IGNORECASE,
)


def _last_assistant_text(state: State) -> str:
    for m in reversed(state.messages):
        if m.get("role") == "assistant":
            c = m.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return " ".join(
                    b.get("text", "")
                    for b in c
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            return ""
    return ""


def _has_successful_tool_use(state: State) -> bool:
    """历史里有无成功(非 is_error)的 tool_result(任何工具均算证据)。"""
    for m in state.messages:
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if (
                    isinstance(b, dict)
                    and b.get("type") == "tool_result"
                    and not b.get("is_error", False)
                ):
                    return True
    return False


def make_tool_use_presence_stop_hook(
    max_veto: int = 1,
) -> "Callable[[State], StopDecision]":
    """GAP-AH-2 终答证据门:终答声称做过执行/分析,但本会话零成功 tool_use → veto
    一次、注入纠正、强制再走(§5④#3)。保守(零工具证据才 veto),几乎不误杀纯概念问答。
    防循环:state.stop_hook_veto_count >= max_veto 不再 veto(maxTurns/recovery 兜底)。"""

    def _hook(state: State) -> StopDecision:
        if state.stop_hook_veto_count >= max_veto:
            return StopDecision(veto=False)
        text = _last_assistant_text(state)
        claims = bool(_CLAIM_PATTERNS.search(text))
        if claims and not _has_successful_tool_use(state):
            state.stop_hook_veto_count += 1
            return StopDecision(
                veto=True,
                message=(
                    "[反幻觉否决] 你声称已执行/分析并给出了结果,但本会话未真正调用任何工具"
                    "拿到这些结果。请先用 BrainQuery 检索、再用 SkillExec 等真正执行,"
                    "拿到真实数据后再作答;不要凭空给出执行结论。"
                ),
            )
        return StopDecision(veto=False)

    return _hook
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_hooks_tool_evidence.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add praxis2/core/state.py praxis2/hooks/builtin.py tests/test_hooks_tool_evidence.py
git commit -m "feat(hooks): tool_use_presence stop_hook 声称执行+零证据 veto(GAP-AH-2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: 集成测试 — 门+推进+stop_hook 经真 query() 端到端

**Files:**
- Test: `tests/test_gap_ah_integration.py`(新)

**说明**:模仿 `tests/test_rmcp_invariants.py` + `tests/test_core_query_stophook.py`,用真 `SerialToolRunner`(permission=RetrieveFirstPermission + post_hooks=[advance_phase_on_real_retrieval])+ 脚本化 `FakeLLMClient` 跑 `query()`,证明三件套组合正确:裸 execute 被拒 → 检索推进 → execute 放行;以及"声称无证据"终答被 veto。

- [ ] **Step 1: 写测试(本任务无实现改动,直接验组合;先红后绿靠前序任务已落地)**

新建 `tests/test_gap_ah_integration.py`:
```python
from praxis2.core.query import query
from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.seams import MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import (
    advance_phase_on_real_retrieval,
    make_tool_use_presence_stop_hook,
)
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.bash_policy import BashCommandPolicy
from praxis2.tools.permission import RetrieveFirstPermission
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import FakeLLMClient


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2
    return S()


class _FakeBrainQuery(Tool):
    name = "BrainQuery"
    rmcp_op = None
    last_retrieval_real_hit = False

    def input_schema(self):
        return {"type": "object"}

    async def run(self, payload):
        self.last_retrieval_real_hit = True  # 模拟真命中
        return ToolResult(ok=True, value={"hits": [{"slug": "x"}], "source": "filesystem"})


class _FakeSkill(Tool):
    name = "SkillExec"
    rmcp_op = "call_skill"

    def input_schema(self):
        return {"type": "object"}

    async def run(self, payload):
        return ToolResult(ok=True, value={"result": "docked"})


def _turn_tool_use(tid, name):
    return [
        {"type": "text", "text": ""},
        {"type": "tool_use", "id": tid, "name": name, "input": {}},
        {"type": "message_stop", "stop_reason": "tool_use", "usage": {}},
    ]


def _turn_final(text):
    return [
        {"type": "text", "text": text},
        {"type": "message_stop", "stop_reason": "end_turn", "usage": {}},
    ]


def _runner():
    reg = ToolRegistry()
    reg.register(_FakeBrainQuery())
    reg.register(_FakeSkill())
    perm = RetrieveFirstPermission(BashCommandPolicy())
    runner = SerialToolRunner(
        reg, recovery_budget=3, permission=perm,
        post_hooks=[advance_phase_on_real_retrieval],
    )
    return reg, runner


async def test_premature_execute_denied_then_retrieve_unlocks():
    reg, runner = _runner()
    # 轮1:直接 SkillExec(未检索)→ 门 DENY(回喂 is_error)
    # 轮2:BrainQuery(真命中)→ post_hook 推进 RETRIEVE
    # 轮3:再 SkillExec → 放行
    # 轮4:终答
    client = FakeLLMClient(turns=[
        _turn_tool_use("tu1", "SkillExec"),
        _turn_tool_use("tu2", "BrainQuery"),
        _turn_tool_use("tu3", "SkillExec"),
        _turn_final("完成"),
    ])
    st = State()
    st.messages = [{"role": "user", "content": "对接 imatinib 到 1iep"}]
    events = [e async for e in query(
        st, client=client, registry=reg, settings=_settings(),
        runner=runner, compactor=MinimalCompactor(),
    )]
    # 轮1 SkillExec 被门拒(tool_result is_error 含"检索先行")
    tool_results = [e for e in events if e.get("type") == "tool_result"]
    assert any(
        e.get("is_error") and "检索先行" in (e.get("content") or "")
        for e in tool_results
    ), "未检索的 SkillExec 应被证据门拒"
    # 检索后相位推进 + 轮3 SkillExec 成功(非 is_error)
    assert get_phase(st) is not Phase.INIT
    assert any(not e.get("is_error") for e in tool_results), "检索后 SkillExec 应放行"


async def test_claim_without_tools_vetoed_then_stops():
    reg, runner = _runner()
    # 轮1:直接给"已对接出分"终答(零工具)→ stop_hook veto → 轮2 再终答(计数到顶放行)
    client = FakeLLMClient(turns=[
        _turn_final("我已对接完成,最佳亲和力 -9.2 kcal/mol。"),
        _turn_final("我已对接完成,最佳亲和力 -9.2 kcal/mol。"),
    ])
    st = State()
    st.messages = [{"role": "user", "content": "对接并给分"}]
    events = [e async for e in query(
        st, client=client, registry=reg, settings=_settings(),
        runner=runner, compactor=MinimalCompactor(),
        stop_hook=make_tool_use_presence_stop_hook(),
    )]
    assert st.stop_hook_veto_count == 1, "应 veto 一次"
    # 注入了纠正 user 消息
    assert any(
        m["role"] == "user" and "反幻觉否决" in str(m.get("content", ""))
        for m in st.messages
    )
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
```

- [ ] **Step 2: 跑测试**

Run: `.venv/bin/python -m pytest tests/test_gap_ah_integration.py -v`
Expected: PASS（前序 Task 3/5/6 已落地;若红，定位是组合接线问题而非占位）
注:`ToolRegistry.register` 与 `BashCommandPolicy` 构造方式以仓库现有用法为准（见 `tests/test_rmcp_invariants.py`、`praxis2/server/app.py:707`）；若签名不符按实际调整 `_runner()`。

- [ ] **Step 3: commit**

```bash
git add tests/test_gap_ah_integration.py
git commit -m "test(gap-ah): query 级集成 — 检索先行门+推进+stop_hook 组合

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: 接入 app.py chat 生产路径

**Files:**
- Modify: `praxis2/server/app.py`（约 707、716、741）
- Test: 全量回归 + staging e2e（controller 亲做）

**说明**:三处接线。组件正确性由 Task 3/5/6 单测 + Task 7 集成测试覆盖;app.py 接线由全量 server 测试零回归 + staging e2e 验证(本项目 server 接线惯例如 BashTool/MCP 均 staging e2e 验)。

- [ ] **Step 1: 改 import**

`praxis2/server/app.py` 顶部加(与现有 import 同区):
```python
from praxis2.hooks.builtin import (
    advance_phase_on_real_retrieval,
    make_tool_use_presence_stop_hook,
)
from praxis2.tools.permission import RetrieveFirstPermission
```

- [ ] **Step 2: 串证据门 base(约 707 行)**

```python
                # v0.17 子项目2:base 换 BashCommandPolicy(非 Bash 透传 ALLOW)。
                # GAP-AH-1:外裹 RetrieveFirstPermission(rmcp_op≠None 工具须已检索)。
                base_perm = RetrieveFirstPermission(BashCommandPolicy())
```

- [ ] **Step 3: 加 post_hooks(约 716 行 SerialToolRunner 构造)**

```python
                runner = SerialToolRunner(
                    reg,
                    recovery_budget=self._deps.settings.recovery_budget,
                    permission=perm,
                    post_hooks=[advance_phase_on_real_retrieval],  # GAP-AH-1 检索→推进相位
                )
```

- [ ] **Step 4: 传 stop_hook(约 741 行 query() 调用)**

```python
                    async for ev in query(
                        st,
                        client=client,
                        registry=reg,
                        settings=self._deps.settings,
                        runner=runner,
                        compactor=MinimalCompactor(),
                        system=system_prompt or None,
                        stop_hook=make_tool_use_presence_stop_hook(),  # GAP-AH-2
                    ):
```

- [ ] **Step 5: 全量回归**

Run:
```
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=short --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?
.venv/bin/python -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/r.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print(s.attrib)"
```
Expected: `failures=0 errors=0`

- [ ] **Step 6: commit**

```bash
git add praxis2/server/app.py
git commit -m "feat(app): 接入 RetrieveFirstPermission + 检索推进 post_hook + stop_hook(GAP-AH-1/2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: staging e2e(controller 亲做,非 subagent)**

rsync 改动文件到 `~/data1/mzy/PRAXIS-2/praxis2/`(逐文件),重启 gunicorn,经 `.40:8080` 真对话验:
1. **黄金链路**:先检索后对接 → call_skill 放行 → 真 JSON(不回归 GAP-E2E)。
2. **裸执行**:诱导未检索直接要对接 → 被门 DENY,模型自补检索后成功。
3. **只说不做**:诱导不调工具直接声称已对接出分 → stop_hook veto → 补调工具。
4. **反幻觉 KPI** `eval_v0160.py`:A+B≥80% / C≤10% / D=0 / S-FAIL=0(对照基线 91%/9%/0%/0)。

---

## Self-Review（计划对 spec 覆盖核对）

- **spec §4.1 RetrieveFirstPermission** → Task 3 ✓
- **spec §4.2 检索推进信号** → Task 4(BrainQuery 标记)+ Task 5(post_hook)+ Task 8 Step 3(接线)✓。*偏差(已在 spec §10 留待 plan):用 `post_hooks` 缝 + 实例属性,替代 spec 设想的 `query(on_tool_results=…)`——更干净、不改 query() 签名、不靠字符串解析(post_hook 收字符串化 result,会被 budget 截断)。*
- **spec §4.3 tool_use_presence stop_hook** → Task 6 ✓(claims 检测 + 零证据 + veto≤1 + State 计数)
- **spec §4.4 SkillExec.rmcp_op** → Task 1 ✓
- **spec §4.5 AgentTool 描述** → Task 2 ✓
- **spec §5 数据流 / §6 边界** → Task 7 集成测试覆盖(裸 execute 拒→检索→放行;声称无证据 veto;fixture 不推进见 Task 5)✓
- **spec §7 测试 / §8 验收** → Task 1-7 单测/集成 + Task 8 全量回归 + staging e2e + KPI ✓
- **占位扫描**:每步均含真代码/真命令/预期输出;Task 7 注明 `ToolRegistry.register`/`BashCommandPolicy` 构造以仓库现有用法为准(防签名漂移),非占位而是显式校验点。
- **类型/命名一致**:`last_retrieval_real_hit`(Task 4 设、Task 5 读、Task 7 fake 用)一致;`stop_hook_veto_count`(Task 6 加、用)一致;`make_tool_use_presence_stop_hook`/`advance_phase_on_real_retrieval`/`RetrieveFirstPermission` 跨 Task 命名一致。

**未决(执行时按仓库实际微调,非占位)**:`ToolRegistry.register` 与 `BashCommandPolicy()` 的确切构造签名(Task 7/8 已标注以现有用法为准);claims 短语集 v1 召回靠 staging KPI 复核迭代。
