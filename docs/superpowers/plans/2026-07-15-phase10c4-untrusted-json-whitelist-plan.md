# P10.C4 未受信 LLM JSON 白名单化 + 溯源契约 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修掉 main 上 `validate_candidate` 的元素级畸形 bug(`/api/parse` 500 + 5 个静默污染 `schema_valid=True` 发明假基因名),并用"白名单实现 + 输出侧溯源契约"根治"畸形类型/后果类型是手工清单"这一层失效模式。

**Architecture:** 跟随仓库里两个既有正确先例 —— `llm_router.py:44` 的**值白名单**(`if a in candidates`)与 `safety_contract.py:54-65` 的**整段 try fail-closed**。核心是把 `str(t)` 强转改成 `isinstance(t, str)` **元素级白名单**(其余丢弃),配**输出侧溯源契约**断言(`schema_valid=True ⟹ set(normalized) ⊆ 输入的 str 元素`)—— 不枚举输入侧畸形类型。**不引入任何新依赖、不新建抽象层。**

**Tech Stack:** Python 3.13 / pytest(现有栈)。**不引入 hypothesis**(用户 2026-07-15 拍板,理由见 spec §5.1)。

**Spec:** `docs/superpowers/specs/2026-07-15-phase10c4-untrusted-json-whitelist-design.md`(commit `a8c7f97`,用户已批)

**基线:** main = HEAD = `a8c7f97`(spec commit,父 `c050f8a`),分支 `feat/v0.9-phase0-module-core`

---

## 全局约束(每个 task 都适用,不可破)

1. **测试口径显式**:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`,**绝不裸跑 `pytest`**。稳定基线加 `-m "not llm"`。
2. **9 条 `@pytest.mark.llm` 是真实网络测试**,网络挂时 **FAIL 不是 skip** → **"看退出码"会给假红**,必须读 `short test summary info` 的测试名区分真红/网络红。
3. **红线**:核心内核(`core/message.py`/`bus.py`/`agent.py`)+ 仓库根 `tests/` **零触碰**;`agents/reliability.py`/`agents/critic.py` 裁决逻辑与数值**零改**。
4. **前端 WIP 全程隔离**:`praxis_vc_react/src/styles/{base,fonts,themes,tokens}.css`(M)+ `.claude/`、`.playwright-mcp/`、`string.jpeg`(??)**绝不 stage/touch/revert**。**每次 `git add` 只显式列本 task 的文件,禁止 `git add -A` / `git add .`**。
5. **不 push**。commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`(用户 2026-07-15 复核确认)。
6. **开工先 `git log --oneline -3` 确认 HEAD**(C2 出过 agent 未确认 HEAD 就 `--amend` 折叠进他人 commit 的事故)。**绝不 `--amend` 不属于本 task 的 commit。**
7. **诚实不伪造**:实际行为与预期不符 → **先报告,不得为凑绿弱化断言**。挡下本计划的错误极有价值(C3 里 implementer 连续挡下两个控制器错误)。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py` | C4 全部测试(溯源契约 / 崩溃类 / 发明类 / fail-closed / 零回归 / 边界 try / 姊妹 6 处 / 字节等价) | **Create**(Task 1) |
| `praxis_virtualcell/workflows/run_virtualcell_query.py` | `validate_candidate` 元素级白名单(:54/:57/:61)+ 边界 try | **Modify**(Task 1、2) |
| `praxis_virtualcell/agents_llm/llm_critic.py` | notes/flags 元素级过滤(:39-40) | **Modify**(Task 3) |
| `praxis_virtualcell/agents_llm/llm_router.py` | risk_flags 元素级过滤(:49)。**`recommended/excluded_agents`(:44-47)不动**——已是值白名单天然安全 | **Modify**(Task 3) |
| `praxis_virtualcell/llm_orchestration/cross_module_reasoner.py` | notes/flags 元素级过滤(:45-46) | **Modify**(Task 3) |
| `praxis_virtualcell/llm_orchestration/safety_contract.py` | risk_flags 元素级过滤(:62) | **Modify**(Task 3) |
| `docs/superpowers/plans/UPGRADE-PROGRESS.md` | 台账:订正 858→850 + C4 勾账 | **Modify**(Task 0、4) |

**不新建文件**(除测试)。**不建 sanitize 公共模块** —— spec §3 明列不做(回归面大,且层1 仍无法机械根治)。

---

## Task 0:前置验证 + 基线固化 + 台账数字订正

**Files:**
- Modify: `docs/superpowers/plans/UPGRADE-PROGRESS.md`

- [ ] **Step 1: 确认 HEAD**

```bash
cd /Volumes/T7/PRAXIS-virtualcell && git log --oneline -3 && git status --short
```
Expected: HEAD = `a8c7f97`(spec commit)。工作树只有前端 WIP(4 个 css + `.claude/` + `.playwright-mcp/` + `string.jpeg`)。

- [ ] **Step 2: 跑真实稳定基线并记录**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -m "not llm" 2>&1 | tail -3
```
Expected: `850 passed, 40 skipped, 9 deselected, 1 warning in ~10s`
**若数字不是 850/40/9 → 停,报告实际值**(不要照本计划的预期去查一个不存在的回归)。

- [ ] **Step 3: 前置验证 spec §5.2 —— assumptions 收紧是否破既有测试**

```bash
grep -rn "assumptions" --include="*.py" praxis_virtualcell/tests praxis_vc_api praxis_vc_web | grep -v "\.pyc"
```
判据:**是否有任何测试/生产代码依赖 `assumptions` 含非 str 元素**(dict/list/int)。
Expected: 全部用例的 assumptions 都是 `list[str]`(如 `["deterministic keyword parse"]`)→ 收紧安全。
**若发现依赖非 str assumptions → 停,报告**(spec §4.1 的 assumptions 收紧需重新评估)。

- [ ] **Step 4: 台账订正 858 → 850**

在 `docs/superpowers/plans/UPGRADE-PROGRESS.md` 里找到 C3 段所有 `858/40/0` 与 `858 passed`,改为如实表述。**逐处替换,不要漏**:

```bash
grep -n "858" docs/superpowers/plans/UPGRADE-PROGRESS.md
```

每处改成(按上下文调整措辞,核心事实必须含):
```
850 passed / 40 skipped / 9 deselected / 0 failed(`-m "not llm"` 稳定基线)
```
并在 C3 段落末尾加一句订正说明:
```markdown
> ⚠️ **基线数字订正(P10.C4 勘察 2026-07-15 实测)**:本段原写 `858/40/0` —— **是错的**。
> 真实稳定基线 = `-m "not llm"` → **850 passed / 40 skipped / 9 deselected / 0 failed**。
> 根因:858 是某次收官会话里 1 条真实网络 LLM 测试 fail 后"按红线扣除"的净值,
> **非任何一次真实运行的原始输出**。仓库有 9 条 `@pytest.mark.llm` 真实网络测试
> (本机 `.env` 有 key → 全真跑,**网络挂时是 FAIL 不是 skip**),故数字随网络浮动、
> **"看退出码"会给假红**,须靠 `short test summary info` 的测试名区分真红/网络红。
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/UPGRADE-PROGRESS.md
git commit -F - <<'EOF'
docs(phase10c4): Task 0 台账基线数字订正 —— 858/40/0 是错的,真实稳定基线 850/40/9deselected/0

C4 勘察实测坐实:858 是某次收官按红线扣除 1 条网络 LLM fail 的净值,非任何一次
真实运行的原始输出。真实稳定基线 = -m "not llm" → 850 passed/40 skipped/9 deselected/0 failed。
仓库 9 条 @pytest.mark.llm 是真实网络测试(网络挂时 FAIL 不 skip)→ 看退出码会给假红。

前置验证(spec §5.2):assumptions 收紧为"只接受 str 元素"不破既有用例。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```
Expected: 只有 `UPGRADE-PROGRESS.md` 一个文件。**无前端 WIP。**

---

## Task 1:溯源契约 + `validate_candidate` 元素级白名单(核心)

**Files:**
- Create: `praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py`
- Modify: `praxis_virtualcell/workflows/run_virtualcell_query.py:54,57,61`

- [ ] **Step 1: 确认 HEAD**

```bash
git log --oneline -3
```
Expected: HEAD = Task 0 的 commit。

- [ ] **Step 2: 写失败测试**

创建 `praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py`:

```python
"""P10.C4 未受信 LLM JSON 白名单化 + 溯源契约 测试。

本文件的判据是**输出侧**的 —— 不枚举输入侧畸形类型。理由(spec §2.3):输入侧枚举是
无底递归(入口→字段→畸形类型→后果类型),C3 Task 7 照"双层机械枚举"教训做了
11 字段 × 6 畸形 = 66 组合,仍漏了层3(6 种畸形全是容器级、无一元素级)与层4
(判据只有"崩溃/字符拆"、没有"零发明")。溯源契约只问"输出有没有凭空多出东西",
故一条断言同时覆盖字符拆/发明/嵌套/崩溃四类后果。

诚实边界(spec §8,收官文档/paper 引用须照此表述):
- **溯源契约仅适用 `perturbation_targets`**(有溯源语义的字段);`requested_outputs` 是
  **值白名单**(输出 ⊆ ALLOWED_OUTPUTS,更强)、`assumptions` 是**类型过滤**(元素恒 str)
  —— 三者判据不同,**不得统称"溯源契约"**。
- 本文件**不覆盖"哪些函数消费未受信 LLM JSON"**(层1 无机械判据:`.complete(` 恰漏
  `safety_contract.py`、`json.loads` 混进 20+ 读本地数据集的无关文件)——属残余风险,
  **不得声称"全覆盖"**。
"""
import json

import pytest

from praxis_virtualcell.workflows.run_virtualcell_query import ALLOWED_OUTPUTS, validate_candidate

_BASE = {"species": "human", "perturbation_type": "gene",
         "task_type": "predict_delta_expression"}


def _norm(s: str) -> str:
    """声明的归一化(与 validate_candidate:54+77-80 一致):strip,gene/ligand 大写。"""
    return s.strip().upper()


# 已知畸形全集(勘察实测):含 C3 #4 的字符拆与本单元的活 bug。
# 注意:本清单是**证据留档**(证明修复对已知实例有效),**不是判据来源** ——
# 判据是下面的溯源契约(输出侧),不依赖本清单穷尽输入侧畸形。
_TARGETS_CASES = [
    ("C3#4 字符拆:LLM 单基因返标量(自然错误,非对抗构造)", "AHR"),
    ("发明:None → 'NONE'(层4,66 组合枚举漏掉的)", [None, "AHR"]),
    ("嵌套 list(层3,66 组合枚举漏掉的)", [["AHR"]]),
    ("元素 dict", [{"g": "AHR"}]),
    ("元素 int", [123]),
    ("元素 bool", [True]),
    ("合法输入(零回归)", ["AHR"]),
    ("合法输入需归一(零回归)", ["ahr", " TP53 "]),
]


@pytest.mark.parametrize("desc,raw", _TARGETS_CASES, ids=[c[0] for c in _TARGETS_CASES])
def test_provenance_contract_targets_never_invented(desc, raw):
    """**溯源契约(本单元核心贡献)**:对任意输入,若 schema_valid=True,则 normalized 的
    每个 target 必须溯源自输入 list 里的某个 str 元素(经声明归一化)。

    形式化:set(normalized_targets) ⊆ {_norm(s) for s in raw if isinstance(s, str)}

    为何一条覆盖四类后果:
    - 字符拆:"AHR" 是 str 不是 list → src=∅ → 若放行 ['A','H','R'] 则 ⊄ ∅ → 红
    - 发明:'NONE' 不溯源自 None → ⊄ {'AHR'} → 红
    - 嵌套:"['AHR']" 不溯源自 ['AHR'](那是 list 不是 str)→ ⊄ ∅ → 红
    - 崩溃:契约求值前先抛 TypeError → 红
    """
    v = validate_candidate({**_BASE, "perturbation_targets": raw})
    if not v["schema_valid"]:
        assert v["normalized"] is None, "fail-closed 时不得返回 normalized"
        return
    src = {_norm(s) for s in raw if isinstance(s, str)} if isinstance(raw, list) else set()
    got = set(v["normalized"]["perturbation_targets"])
    assert got <= src, f"发明了输入里不存在的 target:{got - src}(输入可溯源集={src})"


@pytest.mark.parametrize("raw", [
    [["delta_expression"]],          # main 活 bug:TypeError: unhashable type: 'list'
    [{"a": 1}],                      # main 活 bug:TypeError: unhashable type: 'dict'
    [None, "delta_expression"],
    [123, "growth"],
], ids=["嵌套list(活bug)", "元素dict(活bug)", "元素None", "元素int"])
def test_requested_outputs_malformed_element_does_not_crash(raw):
    """**main 活 bug**:`o in ALLOWED_OUTPUTS`(ALLOWED_OUTPUTS 是 **set**)对 unhashable
    元素抛 TypeError。生产可达(实测,非构造):/api/parse → runtime_service.parse_query
    → validate_candidate,全链无 try/except,且 validate_candidate 在 parse_query 的 try 块
    **外面**(:147)→ FastAPI 500。LLM 返嵌套数组是自然错误。

    判据 = **值白名单**(非溯源契约):修复后元素级 isinstance 短路在 `in set` 之前,
    畸形元素丢弃、合法元素保留。
    """
    v = validate_candidate({**_BASE, "perturbation_targets": ["AHR"],
                            "requested_outputs": raw})
    kept = v["normalized"]["metadata"]["requested_outputs"]
    assert all(isinstance(o, str) for o in kept)
    assert set(kept) <= ALLOWED_OUTPUTS
    # 合法元素不得被误伤
    assert [o for o in raw if isinstance(o, str) and o in ALLOWED_OUTPUTS] == kept


def test_targets_all_elements_malformed_fails_closed():
    """全部元素畸形 → targets=[] → 既有 missing 校验触发 → schema_valid=False。
    与 C3 Task 7 对 "AHR" 的既有语义一致(不静默放行污染数据)。"""
    v = validate_candidate({**_BASE, "perturbation_targets": [["AHR"], {"g": "TP53"}, 123]})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "perturbation_targets" in v["missing_fields"]


def test_targets_partial_malformed_keeps_legit_drops_garbage():
    """**"部分丢弃"语义(spec §4.1 设计决策)**:保留合法元素、丢弃畸形元素,而非整体 fail。
    ①满足溯源契约(既不发明 'NONE'、也不丢真数据 'AHR');②与 llm_router:44 的
    `if a in candidates` 语义完全一致(静默丢弃越界元素、不报错)—— 跟随既有先例。"""
    v = validate_candidate({**_BASE, "perturbation_targets": [None, "AHR", ["x"], 7]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR"]
    assert "NONE" not in v["normalized"]["perturbation_targets"]   # 层4:不发明


def test_assumptions_non_str_elements_dropped():
    """assumptions 判据 = **类型过滤**(元素恒 str),**非溯源契约**。
    收紧:现状 `list(x)` 元素任意 → dict/list 元素原样进 normalized.metadata。"""
    v = validate_candidate({**_BASE, "perturbation_targets": ["AHR"],
                            "assumptions": ["ok", {"evil": 1}, ["nested"], None, 42]})
    assert v["normalized"]["metadata"]["assumptions"] == ["ok"]


def test_legit_input_zero_regression():
    """白名单对合法输入**恒等** —— OFFLINE 字节等价的基础
    (_deterministic_parse 产物恒 list[str] → 白名单对其恒等)。"""
    v = validate_candidate({**_BASE, "perturbation_targets": ["ahr", " TP53 "],
                            "requested_outputs": ["delta_expression", "growth"],
                            "assumptions": ["deterministic keyword parse"]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR", "TP53"]
    assert v["normalized"]["metadata"]["requested_outputs"] == ["delta_expression", "growth"]
    assert v["normalized"]["metadata"]["assumptions"] == ["deterministic keyword parse"]


def test_offline_deterministic_parse_products_pass_through_unchanged():
    """OFFLINE 路径字节等价:_deterministic_parse 产物(恒 list[str])过白名单恒等,
    同请求多跑结果一致。"""
    cand = {"species": "human", "perturbation_type": "gene",
            "perturbation_targets": ["AHR", "TP53"],
            "task_type": "predict_delta_expression",
            "assumptions": ["deterministic keyword parse"]}
    a = validate_candidate(dict(cand))
    b = validate_candidate(dict(cand))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["normalized"]["perturbation_targets"] == ["AHR", "TP53"]
```

- [ ] **Step 3: 跑测试确认失败(红)**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider 2>&1 | tail -15
```
Expected: **多条 FAIL**,其中必须包含:
- `test_requested_outputs_malformed_element_does_not_crash[嵌套list(活bug)]` → `TypeError: unhashable type: 'list'`
- `test_requested_outputs_malformed_element_does_not_crash[元素dict(活bug)]` → `TypeError: unhashable type: 'dict'`
- `test_provenance_contract_targets_never_invented[发明:None → 'NONE'...]` → 断言失败,`{'NONE'}` 不可溯源
- `test_provenance_contract_targets_never_invented[嵌套 list...]` → `{"['AHR']"}` 不可溯源
- `test_targets_partial_malformed_keeps_legit_drops_garbage`、`test_assumptions_non_str_elements_dropped`

**若上述任何一条修复前就绿 → 停,报告**(说明该断言是空壳/没有牙)。

- [ ] **Step 4: 实现元素级白名单**

修改 `praxis_virtualcell/workflows/run_virtualcell_query.py`。

**替换 `:51-61`** 的三处(注意保留 `_perturbation` 的既有 dict 守卫):

```python
    targets = d.get("perturbation_targets")
    if targets is None and _perturbation:
        targets = _perturbation.get("targets")
    # C4 元素级白名单:容器级 isinstance 只守了"targets 是不是 list",没守元素 ——
    # 原 `str(t).strip()` 对**任何**对象都成功,把 [None,'AHR'] 变成 ['NONE','AHR']
    # (凭空发明基因 NONE)、[['AHR']] 变成 ["['AHR']"],且带 schema_valid=True 返给前端,
    # 用户确认后内核真按假基因名跑。**try/except 兜不住这一类**(str() 不抛异常)。
    # 修法跟随 llm_router.py:44 的值白名单先例:只接受契约内类型(str),其余丢弃 ——
    # 畸形类型全集无需枚举,因为"其余"是补集。
    targets = ([t.strip() for t in targets if isinstance(t, str) and t.strip()]
               if isinstance(targets, list) else [])
    task = str(d.get("task_type") or d.get("task", "")).strip().lower() or "predict_delta_expression"
    _raw_outputs = d.get("requested_outputs")
    # C4:`o in ALLOWED_OUTPUTS`(set)对 unhashable 元素抛 TypeError → /api/parse 500
    # (main 活 bug)。isinstance 短路在 `in` 之前 → 元素级畸形不再崩;值白名单同时保证
    # 输出 ⊆ ALLOWED_OUTPUTS。
    outputs = ([o for o in _raw_outputs if isinstance(o, str) and o in ALLOWED_OUTPUTS]
               if isinstance(_raw_outputs, list) else [])
    # C4:元素级类型过滤(原 list(x) 元素任意 → dict/list 原样进 normalized.metadata)。
    _raw_assumptions = d.get("assumptions")
    assumptions = ([a for a in _raw_assumptions if isinstance(a, str)]
                   if isinstance(_raw_assumptions, list) else [])
```

- [ ] **Step 5: 跑测试确认通过(绿)**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider 2>&1 | tail -3
```
Expected: 全部 passed。

- [ ] **Step 6: 复现活 bug 已消失(生产路径实证)**

```bash
PYTHONPATH=$PWD .venv/bin/python -c "
from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate
r = validate_candidate({'species':'human','perturbation_type':'gene','perturbation_targets':['AHR'],
                        'task_type':'predict_delta_expression',
                        'requested_outputs':[['delta_expression']]})
print('活bug(嵌套):NO CRASH, schema_valid=%s outputs=%r' % (r['schema_valid'], r['normalized']['metadata']['requested_outputs']))
r2 = validate_candidate({'species':'human','perturbation_type':'gene',
                         'perturbation_targets':[None,'AHR'],'task_type':'predict_delta_expression'})
print('发明类:targets=%r (NONE 必须不在里面)' % r2['normalized']['perturbation_targets'])
"
```
Expected:
```
活bug(嵌套):NO CRASH, schema_valid=True outputs=[]
发明类:targets=['AHR'] (NONE 必须不在里面)
```

- [ ] **Step 7: 变异证伪(证明测试有牙,不是空壳)**

把 `isinstance(t, str) and ` 从 targets 那行**临时删掉**(退回 `str(t).strip()` 语义),跑测试:
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider 2>&1 | tail -3
```
Expected: **FAIL**(溯源契约 + 部分丢弃 + fail-closed 多条红)。
**然后把变异改回来**,重跑确认绿。**若变异后仍全绿 → 停,报告断言是空壳。**

- [ ] **Step 8: 全量回归**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -m "not llm" 2>&1 | tail -3
```
Expected: `867 passed, 40 skipped, 9 deselected, 0 failed`(850 基线 + 本 task 新增 **17** 条:
溯源契约 8 参数化 + 崩溃类 4 参数化 + fail-closed/部分丢弃/assumptions/零回归/字节等价 各 1)。
**⚠️ 别把这里的数字与 858 搞混 —— 858 是全仓那个错误数字(Task 0 刚订正掉),不是任何预期值。**
**若 passed 数对不上 → 先自己数实际新增条数再判断;若有既有测试变红 → 停,报告是哪条、为什么**(不得改既有测试凑绿)。

- [ ] **Step 9: Commit**

```bash
git add praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py praxis_virtualcell/workflows/run_virtualcell_query.py
git commit -F - <<'EOF'
feat(phase10c4): Task 1 validate_candidate 元素级白名单 + 溯源契约 —— 修 main 活 bug(/api/parse 500)+ 根治发明假基因名

main 活 bug(生产可达,已复现):requested_outputs 元素 unhashable → `o in ALLOWED_OUTPUTS`
(set)抛 TypeError → /api/parse 无 try/except → 500。同函数另有 5 个静默污染变体
schema_valid=True 且发明假基因名([None,'AHR'] → ['NONE','AHR']、[['AHR']] → ["['AHR']"]),
与 C3 #4 字符拆同性质的诚实性缺陷 —— 根因 str(t) 对任何对象都成功,故 try/except 兜不住。

修法跟随仓库两个既有正确先例(不引新抽象):llm_router:44 值白名单 / safety_contract
整段 try。元素级只接受 str,其余丢弃 —— 畸形类型全集无需枚举("其余"是补集)。

核心:输出侧溯源契约替代无底的输入侧枚举 —— schema_valid=True ⟹
set(normalized_targets) ⊆ {norm(s) for s in raw if isinstance(s,str)}。一条断言覆盖
字符拆/发明/嵌套/崩溃四类后果。变异证伪:删掉 isinstance 守卫则多条红。

诚实边界:溯源契约仅适用 perturbation_targets;requested_outputs 是值白名单、
assumptions 是类型过滤,判据不同不得统称。层1(哪些函数消费未受信 JSON)无机械判据,
不得声称"全覆盖"。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```
Expected: 只有 2 个文件(测试 + `run_virtualcell_query.py`)。**无前端 WIP。**

---

## Task 2:边界 try(defense-in-depth,须先证可达)

> **本 task 可能以"不做"收尾** —— 若 Step 2 证明 except 分支不可达,则**不加 try**(避免死码),
> 在报告里如实说明,由控制器记入 spec §8.5。**这是允许的结果,不是失败。**

**Files:**
- Modify: `praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py`
- Modify: `praxis_virtualcell/workflows/run_virtualcell_query.py:39-92`

- [ ] **Step 1: 确认 HEAD**

```bash
git log --oneline -3
```
Expected: HEAD = Task 1 的 commit。

- [ ] **Step 2: 先证 except 分支真实可达(不可达就不加)**

```bash
PYTHONPATH=$PWD .venv/bin/python -c "
import json
# validate_candidate:83 的 json.dumps(d, sort_keys=True) —— d 含混合类型 key 时:
try:
    json.dumps({1: 'a', 'b': 2}, sort_keys=True)
    print('不可达 → 本 task 不加 try,如实报告')
except TypeError as e:
    print('可达 → TypeError:', e)
from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate
try:
    validate_candidate({1: 'a', 'species': 'human', 'perturbation_type': 'gene',
                        'perturbation_targets': ['AHR'], 'task_type': 'predict_delta_expression'})
    print('validate_candidate 未崩 → 重新评估')
except Exception as e:
    print('validate_candidate 崩:', type(e).__name__, '->', e)
"
```
Expected:
```
可达 → TypeError: '<' not supported between instances of 'str' and 'int'
validate_candidate 崩: TypeError -> '<' not supported between instances of 'str' and 'int'
```
**若显示"不可达"或 validate_candidate 未崩 → 停,跳过本 task 并报告**(spec §4.3 已授权此结果)。

- [ ] **Step 3: 写失败测试**

追加到 `test_t10_7_untrusted_json_whitelist.py`:

```python
def test_boundary_try_non_str_key_returns_invalid_not_raises():
    """**边界 try(defense-in-depth,非死码 —— 可达路径已实测)**:validate_candidate 是
    public 函数,有 2 个非测试消费点(/api/parse 与 praxis_vc_web/app.py:75),
    非 JSON 来源的 dict 可含非 str key,而 :83 的 json.dumps(d, sort_keys=True) 对混合
    类型 key 抛 TypeError: '<' not supported between instances of 'str' and 'int'。

    语义:public 函数**绝不把未预见异常透给端点** → 返回 schema_valid=False 而非抛。
    这是防御性 fail-closed(同 C1/C2 的类不变量断言),诚实披露为"罕触发"即可 ——
    但它**有真实可达路径**,不是永真空壳(C3 T10.6 的教训)。
    """
    v = validate_candidate({1: "a", "species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "candidate_malformed" in v["errors"]


def test_boundary_try_does_not_swallow_legit_results():
    """边界 try 不得吞掉正常路径(变异对照:若 try 把一切都变成 invalid,本条会红)。"""
    v = validate_candidate({"species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR"]
```

- [ ] **Step 4: 跑测试确认失败(红)**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider -k boundary_try 2>&1 | tail -8
```
Expected: `test_boundary_try_non_str_key_returns_invalid_not_raises` FAIL,`TypeError: '<' not supported...`。
`test_boundary_try_does_not_swallow_legit_results` 应 PASS(它是对照)。

- [ ] **Step 5: 实现边界 try**

把 `validate_candidate` 的函数体**整体**包进 try。改法:把现有函数体重命名为内部实现,外层加薄壳。

替换 `run_virtualcell_query.py` 的 `def validate_candidate(cand: dict) -> dict:` 那一行 + docstring 为:

```python
def validate_candidate(cand: dict) -> dict:
    """确定性校验 + 归一。返回 {schema_valid, missing_fields, errors, normalized}。

    **C4 边界 try(defense-in-depth)**:本函数是 public 入口,有 2 个非测试消费点
    (`/api/parse` → parse_query:147,与 `praxis_vc_web/app.py:75`),二者链路均无
    try/except → 未捕获异常 = FastAPI 500。元素级白名单(见 `_validate_candidate_impl`)
    已消灭已知崩溃类,本层只兜**未预见**异常(如非 JSON 来源 dict 的混合类型 key 使
    `json.dumps(sort_keys=True)` 抛 TypeError —— 实测可达,非死码)。
    fail-closed:任何异常 → schema_valid=False + errors=["candidate_malformed"]。
    """
    try:
        return _validate_candidate_impl(cand)
    except (TypeError, AttributeError, ValueError):
        return {"schema_valid": False, "missing_fields": [],
                "errors": ["candidate_malformed"], "normalized": None}


def _validate_candidate_impl(cand: dict) -> dict:
    """validate_candidate 的实现体(异常由外层边界 try 兜,见其 docstring)。"""
```

**其余函数体(`errors, missing = [], []` 起至 `return {...}` 止)保持不变、缩进不变。**

- [ ] **Step 6: 跑测试确认通过(绿)**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider 2>&1 | tail -3
```
Expected: 全部 passed。

- [ ] **Step 7: 变异证伪**

把 except 子句临时改成 `except ():`(捕获空元组 = 不捕获任何异常),跑:
```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider -k boundary_try 2>&1 | tail -3
```
Expected: `test_boundary_try_non_str_key_returns_invalid_not_raises` **FAIL**(证明它真的在测 except 分支)。
**改回来**,重跑确认绿。

- [ ] **Step 8: 全量回归 + Commit**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -m "not llm" 2>&1 | tail -3
git add praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py praxis_virtualcell/workflows/run_virtualcell_query.py
git commit -F - <<'EOF'
feat(phase10c4): Task 2 validate_candidate 边界 try —— public 入口绝不把未预见异常透给 /api/parse

元素级白名单(Task 1)已消灭已知崩溃类;本层兜未预见异常。**非死码,可达路径已实测**:
validate_candidate 是 public 函数(2 个非测试消费点:/api/parse 与 praxis_vc_web/app.py:75),
非 JSON 来源 dict 的混合类型 key 使 :83 的 json.dumps(sort_keys=True) 抛
TypeError: '<' not supported between instances of 'str' and 'int'。

fail-closed:任何 TypeError/AttributeError/ValueError → schema_valid=False +
errors=["candidate_malformed"],绝不抛给端点。变异证伪:except 改成不捕获则测试红
(证明不是永真空壳 —— C3 T10.6 教训)。对照测试钉住"不吞正常路径"。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```
Expected: 2 个文件。**无前端 WIP。**

---

## Task 3:姊妹 6 处同型缺口(用户拍板一起修)

> 形状 predicate:`list(x) if isinstance(x, list) else []` —— 容器守了、元素没守。
> 后果:元素级畸形原样进 **provenance**(不崩、**不碰裁决**)。影响面小但 provenance 是
> paper 要引用的审计产物。**C3 教训 #2 正是"同型缺口未回填"**(safety_contract 抄 llm_router
> 时修了漏洞却没回填原件)。

**Files:**
- Modify: `praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py`
- Modify: `praxis_virtualcell/agents_llm/llm_critic.py:39-40`
- Modify: `praxis_virtualcell/agents_llm/llm_router.py:49`
- Modify: `praxis_virtualcell/llm_orchestration/cross_module_reasoner.py:45-46`
- Modify: `praxis_virtualcell/llm_orchestration/safety_contract.py:62`

- [ ] **Step 1: 确认 HEAD + 机械枚举确认 6 处未多未少**

```bash
git log --oneline -3
grep -rn "list(.*) if isinstance(.*, *list) else \[\]" --include="*.py" praxis_virtualcell | grep -v "/tests/"
```
Expected: **恰好 6 处**(llm_router:49 / llm_critic:39,40 / cross_module_reasoner:45,46 / safety_contract:62)。
**若数量对不上 → 停,报告实际清单**(本计划的清单可能已过时)。

- [ ] **Step 2: 写失败测试**

追加到 `test_t10_7_untrusted_json_whitelist.py`(注意新增 import 放到文件顶部 import 块):

```python
# --- 顶部 import 块追加 ---
from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC
from praxis_virtualcell.llm_orchestration.cross_module_reasoner import CrossModuleReasonerAgent
```

```python
# ---------------------------------------------------------------------------
# 姊妹 6 处同型缺口(spec §2.6):`list(x) if isinstance(x, list) else []`
# —— 容器守了、元素没守。产物只进 provenance、不碰裁决,但 provenance 是 paper 要
# 引用的审计产物。C3 教训 #2 正是"同型缺口未回填"。
# ---------------------------------------------------------------------------

_GARBAGE = ["ok_flag", {"evil": 1}, ["nested"], None, 42]      # 合法 str + 4 类畸形元素


class _StubClient:
    """返回指定 content 的假 LLMClient(不需 API key)。同 test_t10_6 的既有模式。"""

    def __init__(self, content) -> None:
        self._c = content

    def complete(self, messages, **kw) -> dict:
        return {"content": self._c}


def _critic_notes(content) -> dict:
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMCriticAgent(_StubClient(content)).handle(
        AgentMessage("m1", "Report", "LLMCritic", "llm_review", {"report": {"abstain": False}},
                     "t1"), bus)
    return bus.latest("llm_critic_notes").payload


def _xmod_notes(content) -> dict:
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    CrossModuleReasonerAgent(_StubClient(content)).handle(
        AgentMessage("m1", "ModuleRouter", "LLMCrossModuleReasoner", "llm_cross_module",
                     {"module_plan": {"primary": "gene_hub", "entries": []}}, "t1"), bus)
    return bus.latest("llm_cross_module_notes").payload


def _route_suggestion(content) -> dict:
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMRouterAgent(_StubClient(content)).handle(
        AgentMessage("m1", "ModelApplicability", "LLMRouter", "llm_route",
                     {"applicable": ["MockPredictor"], "rejected_candidates": [],
                      "request": {"species": "human"}}, "t1"), bus)
    return bus.latest("llm_route_suggestion").payload["suggestion"]


def test_sibling_critic_notes_flags_drop_non_str_elements():
    """llm_critic.py:39-40 —— 元素级畸形不得原样进 provenance。"""
    out = _critic_notes(json.dumps({"notes": _GARBAGE, "flags": _GARBAGE}))
    assert out["notes"] == ["ok_flag"]
    assert out["flags"] == ["ok_flag"]


def test_sibling_xmod_notes_flags_drop_non_str_elements():
    """cross_module_reasoner.py:45-46 —— 同型(经 core/runtime.py::_dispatch_collect 同步调用)。"""
    out = _xmod_notes(json.dumps({"notes": _GARBAGE, "flags": _GARBAGE}))
    assert out["notes"] == ["ok_flag"]
    assert out["flags"] == ["ok_flag"]


def test_sibling_router_risk_flags_drop_non_str_elements():
    """llm_router.py:49 risk_flags —— 元素级。
    注意:recommended/excluded_agents(:44-47)**不在本 task 范围** —— 它们已是
    值白名单(`if a in candidates`,candidates 是 list → `in` 用 == 不需 hash),天然安全。"""
    sug = _route_suggestion(json.dumps({"recommended_agents": ["MockPredictor"],
                                        "excluded_agents": [], "reasoning_summary": "x",
                                        "risk_flags": _GARBAGE}))
    assert sug["risk_flags"] == ["ok_flag"]
    assert sug["recommended_agents"] == ["MockPredictor"]      # 值白名单零回归


def test_sibling_router_value_whitelist_still_natively_safe():
    """钉住 spec §2.5 的架构证据:值白名单对元素级畸形**天然安全**(不崩、不放行)。
    本条修复前后都应绿 —— 它是**架构不变量的文档化**,不是回归测试。"""
    sug = _route_suggestion(json.dumps({"recommended_agents": [["nested"], {"d": 1}, None],
                                        "excluded_agents": [], "reasoning_summary": "",
                                        "risk_flags": []}))
    assert sug["recommended_agents"] == []


def test_sibling_safety_contract_risk_flags_drop_non_str_elements():
    """safety_contract.py:62 risk_flags —— 实测修复前 [{'evil':1},['nested'],None] 原样透传。"""
    out = SC.sanitize_llm_plan(
        json.dumps({"selected_modules": ["gene_hub"], "risk_flags": _GARBAGE}),
        ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["ok_flag"]
    assert out["selected_modules"] == ["gene_hub"]             # 零回归


def test_sibling_sanitize_llm_plan_still_fail_closed_on_element_malformed():
    """钉住 spec §2.5 的另一条架构证据:整段 try 对元素级畸形 fail-closed 保 primary
    (作者从未枚举过该畸形 —— except 不需要知道畸形长什么样)。修复前后都应绿。"""
    out = SC.sanitize_llm_plan(json.dumps({"selected_modules": [["gene_hub"]]}),
                               ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["llm_parse_failed"]
    assert out["selected_modules"] == ["gene_hub"]
```

- [ ] **Step 3: 跑测试确认失败(红)**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider -k sibling 2>&1 | tail -12
```
Expected: **4 条 FAIL**(critic / xmod / router risk_flags / safety_contract),各显示 `_GARBAGE` 元素原样透传。
**2 条架构不变量测试(`..._natively_safe` / `..._still_fail_closed...`)应 PASS** —— 它们钉的是既有正确行为。
**若那 2 条红 → 停,报告**(说明 spec §2.5 的架构证据不成立)。

- [ ] **Step 4: 实现 —— 4 个文件各改元素级过滤**

`praxis_virtualcell/agents_llm/llm_critic.py:39-40` 替换为:
```python
                # C4 元素级白名单:C3 只守了容器(notes 是不是 list),没守元素 ——
                # [{'evil':1},['nested'],None] 原样进 provenance。只接受 str,其余丢弃。
                out["notes"] = [n for n in notes if isinstance(n, str)] if isinstance(notes, list) else []
                out["flags"] = [f for f in flags if isinstance(f, str)] if isinstance(flags, list) else []
```

`praxis_virtualcell/llm_orchestration/cross_module_reasoner.py:45-46` 替换为:
```python
                # C4 元素级白名单(同 llm_critic.py:39-40):容器守了、元素没守。
                out["notes"] = [n for n in notes if isinstance(n, str)] if isinstance(notes, list) else []
                out["flags"] = [f for f in flags if isinstance(f, str)] if isinstance(flags, list) else []
```

`praxis_virtualcell/agents_llm/llm_router.py:49` 替换为:
```python
                # C4 元素级白名单(recommended/excluded_agents 无需改 —— `if a in candidates`
                # 是值白名单,candidates 是 list → `in` 用 == 不需 hash,天然安全)。
                sug["risk_flags"] = [f for f in rf if isinstance(f, str)] if isinstance(rf, list) else []
```

`praxis_virtualcell/llm_orchestration/safety_contract.py:62` 替换为:
```python
        # C4 元素级白名单:只接受 str 元素(原 list(rf) 元素任意 → 畸形原样进 provenance)。
        out["risk_flags"] = [f for f in rf if isinstance(f, str)] if isinstance(rf, list) else []
```

- [ ] **Step 5: 跑测试确认通过(绿)+ 变异证伪**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider 2>&1 | tail -3
```
Expected: 全部 passed。

变异:把 `llm_critic.py` 的元素级过滤临时改回 `list(notes)`,跑 `-k sibling_critic` → 必须 **FAIL**。改回来。

- [ ] **Step 6: 确认无遗漏(机械复核)**

```bash
grep -rn "list(.*) if isinstance(.*, *list) else \[\]" --include="*.py" praxis_virtualcell | grep -v "/tests/"
```
Expected: **0 处**(6 处全部改完)。

- [ ] **Step 7: 全量回归 + Commit**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -m "not llm" 2>&1 | tail -3
git add praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py praxis_virtualcell/agents_llm/llm_critic.py praxis_virtualcell/agents_llm/llm_router.py praxis_virtualcell/llm_orchestration/cross_module_reasoner.py praxis_virtualcell/llm_orchestration/safety_contract.py
git commit -F - <<'EOF'
feat(phase10c4): Task 3 姊妹 6 处同型缺口元素级白名单回填 —— 畸形不再原样进 provenance

形状 predicate 机械枚举(非手工清单)`list(x) if isinstance(x, list) else []` = 恰好 6 处:
llm_router:49 risk_flags / llm_critic:39-40 notes+flags / cross_module_reasoner:45-46
notes+flags / safety_contract:62 risk_flags。C3 只守了容器、没守元素 → 实测
[{'evil':1},['nested'],None] 原样透传进 provenance(不崩、不碰裁决,但 provenance 是
paper 要引用的审计产物)。用户拍板本单元一起修 —— C3 教训 #2 正是"同型缺口未回填"。

llm_router 的 recommended/excluded_agents 有意不改:`if a in candidates` 是值白名单
(candidates 是 list → `in` 用 == 不需 hash),天然安全 —— 已加测试钉住该架构不变量。
同样钉住 sanitize_llm_plan 整段 try 对元素级畸形 fail-closed 保 primary。

改后机械复核该形状 predicate 全仓 0 处残留。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```
Expected: 5 个文件(测试 + 4 个实现)。**无前端 WIP。**

---

## Task 4:端到端实证 + 收官核验

**Files:**
- Modify: `praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py`

- [ ] **Step 1: 确认 HEAD**

```bash
git log --oneline -4
```
Expected: HEAD = Task 3 的 commit;能看到 Task 0/1/2/3 四个 commit 链完整。

- [ ] **Step 2: 写端到端测试(钉住生产路径 /api/parse 不再 500)**

追加到 `test_t10_7_untrusted_json_whitelist.py`(顶部 import 块追加 `from praxis_virtualcell.agents_llm import llm_client as _llmc` 与 `from praxis_virtualcell.core.config import Mode, RuntimeConfig`、`from praxis_virtualcell.workflows.run_virtualcell_query import parse_query`):

```python
def test_e2e_parse_query_llm_malformed_outputs_does_not_500(monkeypatch):
    """**生产路径端到端**:/api/parse → runtime_service.parse_query → validate_candidate。
    全链无 try/except 且 validate_candidate 在 parse_query 的 try 块外(:147)→
    修复前 LLM 返 requested_outputs=[["delta_expression"]](自然错误)会 FastAPI 500。
    修复后:不抛,正常返回解析结果。"""
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "task_type": "predict_delta_expression",
        "requested_outputs": [["delta_expression"]],       # 嵌套数组 = LLM 自然错误
    })))
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True)
    out = parse_query("human AHR 敲低", config=cfg)         # 修复前:TypeError → 500
    assert out["schema_valid"] is True
    assert out["candidate_request"]["metadata"]["requested_outputs"] == []


def test_e2e_parse_query_llm_invents_no_gene_names(monkeypatch):
    """**溯源契约的端到端形态**:LLM 返 [None,'AHR'] → 前端**不得**收到发明的 'NONE'。
    修复前:candidate_request.perturbation_targets = ['NONE','AHR'] 且 schema_valid=True,
    用户确认后内核真按假基因名 NONE 跑。"""
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene",
        "perturbation_targets": [None, "AHR"],
        "task_type": "predict_delta_expression",
    })))
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True)
    out = parse_query("human AHR 敲低", config=cfg)
    assert out["candidate_request"]["perturbation_targets"] == ["AHR"]
    assert "NONE" not in out["candidate_request"]["perturbation_targets"]
```

- [ ] **Step 3: 跑测试(绿)**

```bash
PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py -p no:cacheprovider 2>&1 | tail -3
```
Expected: 全部 passed。
**注意**:若 `RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True)` 触发 `assert_llm_boundaries` 报错 → **停,报告**(parse_query:114 有该守卫;可能需按 test_t10_6:344-370 的既有做法构造 cfg)。

- [ ] **Step 4: OFFLINE 字节等价实证(红线 §6.4)**

```bash
PYTHONPATH=$PWD .venv/bin/python -c "
import json
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query
req = {'request_id':'c4-det','species':'human','perturbation_type':'gene',
       'perturbation_targets':['AHR'],'input_modality':'scRNA',
       'output_modality':'delta_expression','task_type':'predict_delta_expression'}
cfg = RuntimeConfig(mode=Mode.OFFLINE)
outs = [json.dumps(run_query(dict(req), config=cfg)['structured_report'], sort_keys=True, default=str) for _ in range(3)]
print('OFFLINE 三跑字节等价:', 'PASS' if len(set(outs)) == 1 else '*** FAIL')
print('llm_used_for_prediction 恒 False:', run_query(dict(req), config=cfg)['llm_used_for_prediction'] is False)
"
```
Expected:
```
OFFLINE 三跑字节等价: PASS
llm_used_for_prediction 恒 False: True
```
**若 FAIL → 停,报告**(白名单改动破了确定性红线)。

- [ ] **Step 5: 红线自核(逐条实证,不靠自述)**

```bash
echo "=== 核心内核 + 根 tests/ 零触碰 ===" && git diff --name-only c050f8a..HEAD | grep -E "^tests/|core/(message|bus|agent)\.py" && echo "*** 违红线!" || echo "OK"
echo "=== reliability/critic 裁决零改 ===" && git diff --name-only c050f8a..HEAD | grep -E "agents/(reliability|critic)\.py" && echo "*** 违红线!" || echo "OK"
echo "=== 前端 WIP 零触碰 ===" && git diff --name-only c050f8a..HEAD | grep -E "praxis_vc_react|\.claude|playwright|string\.jpeg" && echo "*** 违红线!" || echo "OK"
echo "=== 本单元全部改动文件 ===" && git diff --name-only c050f8a..HEAD
echo "=== 未 push 核实 ===" && git rev-list --count origin/main..main
```
Expected: 三个 OK;改动文件只有 spec + plan + UPGRADE-PROGRESS + test_t10_7 + `run_virtualcell_query.py` + 4 个姊妹文件。

- [ ] **Step 6: 全量回归(真实基线 + 含 llm 的完整跑)**

```bash
echo "=== 稳定基线 ===" && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -m "not llm" 2>&1 | tail -3
echo "=== 含 llm 完整跑(9 条真实网络测试,FAIL 须逐条辨真红/网络红)===" && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -12
```
Expected: 稳定基线 = 850 + 本单元新增条数,0 failed。
**含 llm 跑若有 FAIL:必须逐条读 `short test summary info` 的测试名判定** —— 只有 `@pytest.mark.llm` 的网络测试失败才可归因网络;**任何非 llm 测试失败 = 真红 → 停,报告。**

- [ ] **Step 7: Commit**

```bash
git add praxis_virtualcell/tests/phase10/test_t10_7_untrusted_json_whitelist.py
git commit -F - <<'EOF'
test(phase10c4): Task 4 端到端实证 —— /api/parse 生产路径不再 500 + 溯源契约端到端形态

钉住生产链路(/api/parse → parse_query → validate_candidate,全链无 try/except):
LLM 返 requested_outputs=[["delta_expression"]](自然错误)修复前 500,现正常返回;
LLM 返 perturbation_targets=[None,"AHR"] 修复前前端收到发明的 'NONE' 且 schema_valid=True
(用户确认后内核真按假基因名跑),现只收到 ['AHR']。

OFFLINE 三跑字节等价实证 PASS、llm_used_for_prediction 恒 False。
红线自核:核心内核/根 tests/reliability/critic/前端 WIP 全零触碰。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
git show --stat HEAD
```

---

## 收官(控制器执行,不派 subagent)

- [ ] **opus final review**(fresh、只读)—— 带上血泪教训:**final review 也会漏**(#5 就是它漏的),
  重点审:①跨 task 接缝(Task 1 的白名单 vs Task 2 的边界 try 是否互相掩盖);
  ②是否有**新的过度声称**(尤其"全覆盖"类表述);③变异证伪是否真做了;
  ④是否有测试是永真空壳;⑤**自行机械枚举**核对姊妹 6 处是否真的全改、是否有第 7 处。
- [ ] **控制器勾账**:台账 `UPGRADE-PROGRESS.md` + `memory/phase10-deep-validation.md` + `memory/MEMORY.md`,
  含 spec §8 的诚实边界六条(**不得声称"全覆盖"**)。
- [ ] **暂停 AskUserQuestion** 问是否 FF 合并 main(合则 `git branch -f main HEAD`、**不 push**、保留分支)。

---

## Self-Review

**1. Spec 覆盖**(逐节核对):
- §3 做①白名单+溯源契约 → **Task 1**;②姊妹 6 处 → **Task 3**;③订正基线数字 → **Task 0**(台账)+ 控制器已订正 memory。
- §4.1 白名单三处(:54/:57/:61)→ Task 1 Step 4(三处全含)。
- §4.2 溯源契约 → Task 1 Step 2 `test_provenance_contract_targets_never_invented`;§4.2 的"三者判据不同"→ 测试 docstring 已分别标注(溯源契约/值白名单/类型过滤)。
- §4.3 边界 try + **可达性判据 + 不可达则不加** → Task 2(Step 2 是前置门,授权"不做"收尾)。
- §4.4 姊妹 6 处 + `recommended/excluded_agents` 不动 → Task 3(含钉住值白名单天然安全的测试)。
- §4.5 字节等价 / llm_used_for_prediction → Task 4 Step 4。
- §5.2 assumptions 收紧前置验证 → Task 0 Step 3。
- §6 红线 → 全局约束 + Task 4 Step 5 逐条实证自核。
- §7 八类测试 → 1️⃣溯源契约 T1 / 2️⃣崩溃类 T1 / 3️⃣发明类 T1 / 4️⃣fail-closed T1 / 5️⃣零回归 T1 / 6️⃣边界 try 有牙 T2 / 7️⃣姊妹 6 处 T3 / 8️⃣字节等价 T1(单元)+T4(端到端)。**§7 变异要求 → T1 Step 7、T2 Step 7、T3 Step 5 各含。**
- §8 诚实边界 → 测试文件 docstring(层1 无机械判据/三者判据不同)+ 收官勾账项。
- **Gap 检查:无未覆盖项。**

**2. 占位符扫描**:无 TBD/TODO;每个代码步骤都有完整可跑代码;每个命令都有预期输出;Task 2 的"可能不做"有明确判据(Step 2 实测)而非模糊授权。

**3. 类型一致性**:
- 测试文件名全程 `test_t10_7_untrusted_json_whitelist.py`(不占用 D 的 `t10_3`)。
- `_StubClient` 在 Task 3 Step 2 定义,Task 4 Step 2 复用 —— **同名同签名**,一致。
- `_GARBAGE` 在 Task 3 定义并只在 Task 3 用。
- `validate_candidate` / `_validate_candidate_impl` 的拆分在 Task 2 Step 5 定义,Task 1 的实现体(Step 4)成为 impl 的一部分 —— **Task 2 明确要求"其余函数体保持不变、缩进不变"**,无签名冲突。
- `ALLOWED_OUTPUTS` 从 `run_virtualcell_query` import(Task 1 Step 2 顶部),Task 1 断言使用 —— 一致。
