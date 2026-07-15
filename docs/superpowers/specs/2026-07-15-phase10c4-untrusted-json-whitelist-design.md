# P10.C4 未受信 LLM JSON 白名单化 + 溯源契约 设计 spec

**定位**:C3 收口续作(同一失效模式、同一函数、同一批文件)。修 main 上一个活的生产 bug,并把
C3 Task 7 漏掉的那一层根治掉。产出直接服务 D 单元(D 有大量"全覆盖"性质的主张要核验)。

**基线**:main = HEAD = `c050f8a`,分支 `feat/v0.9-phase0-module-core`。

---

## 1. 目标与背景

### 1.1 活 bug(main 上,生产可达,已复现)

```
PYTHONPATH=$PWD .venv/bin/python -c "
from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate
validate_candidate({'species':'human','perturbation_type':'gene','perturbation_targets':['AHR'],
                    'task_type':'predict_delta_expression',
                    'requested_outputs':[['delta_expression']]})"
# → TypeError: unhashable type: 'list'   (元素为 dict 时:unhashable type: 'dict')
```

根因 `run_virtualcell_query.py:57`:`isinstance` 只守了**容器**,没守**元素**;
`o in ALLOWED_OUTPUTS`(ALLOWED_OUTPUTS 是 **set**)对 unhashable 元素抛 TypeError。

### 1.2 这次要根治的失效模式(五次复发,最后一次漏到 main)

| # | 单元 | 谁抓到 | 漏了什么 | 根因层级 |
|---|---|---|---|---|
| 1 | C2 | opus final review | spec §5 predictor 枚举漏 MLBackedPredictorAgent → Gate A 误伤远端真 ML | 手工枚举 **predictor 清单** |
| 2 | C3 | 代码质量审(per-task 两审) | safety_contract 自承"复刻 LLMRouter"、抄时修了漏洞却未回填原件 | **修复未回填** |
| 3 | C3 | opus final review(自行 grep) | spec §2 手工枚举漏 cross_module_reasoner + parse_query | **入口**是手工清单 |
| 4 | C3 | fresh 复审(66 组合枚举) | Task 6 编辑了 validate_candidate 却只修 assumptions,漏 perturbation_targets | **字段**是手工清单 |
| 5 | main(活的) | 无人;本单元勘察复现 | 见 §1.1 + §2.2 | **畸形类型**是手工清单 |

C3 spec §8 修正 4b 的最终教训是"**双层**机械枚举(入口 × 字段)"。**本单元勘察证明双层仍不够**:
Task 7 照做了 11 字段 × 6 畸形 = 66 组合机械枚举,仍漏掉两层 —— 见 §2.3。

---

## 2. 勘察确立的事实地基(全部实测,2026-07-15)

### 2.1 真实基线(订正全仓文档的既有错误)

- **稳定基线 = 850 passed / 40 skipped / 9 deselected / 0 failed**(`-m "not llm"`,实测)。
- 台账 `UPGRADE-PROGRESS.md`、`memory/*`、C3 commit message 全写 **858/40/0 —— 是错的**。根因:858 是某次收官
  会话里 1 条真实网络 LLM 测试 fail 后"按红线扣除"的净值,不是任何一次真实运行的原始输出。
- 仓库有 **9 条 `@pytest.mark.llm` 真实网络测试**(本机 `.env` 有 key → 全真跑,网络挂时是 **FAIL 不是 skip**)。
  故**"看退出码"会给假红**,须靠 `short test summary info` 的测试名区分真红/网络红。
- `memory/phase10-deep-validation.md` 写 main=61709b3,**实际 c050f8a**(以 git 为准)。
- **本单元订正这些数字(Task 0)。**

### 2.2 活 bug 的真实严重性(比"只 500 不破裁决"更重)

崩溃类 2 个(→ `/api/parse` 500);**静默污染类 5 个,全部 `schema_valid=True` 且发明假基因名**:

| 输入 `perturbation_targets` | 输出 normalized | schema_valid |
|---|---|---|
| `[None,'AHR']` | `['NONE','AHR']` ← **凭空发明基因 NONE** | True |
| `[['AHR']]` | `["['AHR']"]` | True |
| `[{'g':'AHR'}]` | `["{'G': 'AHR'}"]` | True |
| `[123]` / `[True]` | `['123']` / `['TRUE']` | True |

污染类与 C3 #4(`"AHR"`→`['A','H','R']`)**同性质**:系统声称解析成功但实际解析错了,产物带
`schema_valid=True` 返前端,用户确认后内核真按假基因名跑。**这不是 500,是诚实性缺陷。**
根因 `:54` 的 `str(t)` —— 对**任何**对象都成功,所以 **try/except 兜不住污染类**,必须元素级类型守卫。

### 2.3 层级递归:双层不够,实际有四层

- 层1 **入口**(#3 漏)→ 层2 **字段**(#4 漏)→ 层3 **畸形类型**(#5 漏)→ 层4 **后果类型**(至今活着)

Task 7 的 66 组合枚举了 11 字段 × 6 畸形,但:
- **6 种畸形类型是手工挑的** → 全是**容器级**(`"AHR"` / `123` / 非 dict),**无一个元素级**(list 里装 list/dict/None)→ 漏层3。
- **判据是手工挑的** → 只有"零崩溃"和"零字符拆"两种后果,**没有"零发明"** → 漏层4。
  所以 `[None,'AHR']→['NONE','AHR']` 穿过了 66 组合、19 组合复验、opus final review、850 全绿,活到今天。

**教训升级(D 单元必带)**:枚举**输入侧**(入口×字段×畸形类型)是无底递归 —— 每加一层,下一层立刻成为新漏点。
**出路是换到输出侧写契约**,见 §4.2。

### 2.4 生产可达性(prompt 只列了一个消费点,实测有两个)

`validate_candidate` 的**非测试**消费点:
1. `praxis_vc_api/main.py:37` `@app.post("/api/parse")` → `runtime_service.py:44 parse_query()` → `validate_candidate()`。
   全链无 try/except;且 `validate_candidate(cand)` 在 parse_query 的 try 块**外面**(`:147`)→ **FastAPI 500**。
2. `praxis_vc_web/app.py:75-76`(Streamlit 界面,`praxis-vc web` 可启)。

**触发条件**:`mode=llm_assisted` 且有 key(`config_for()` :31-34)→ `llm_enabled=True` → `cand = json.loads(LLM 响应)`。
**OFFLINE 恒安全**(cand 由 `_deterministic_parse` 内部构造)。LLM 返嵌套数组是自然错误,非对抗构造。

### 2.5 决定性架构证据:同一畸形,三个消费点命运不同

| 消费点 | 机制 | 元素级畸形结果 |
|---|---|---|
| `llm_router.py:44` | `if a in candidates`(**值白名单**,candidates 是 **list** → `in` 用 `==` 不需 hash) | **天然安全** |
| `safety_contract.py:54-65` `sanitize_llm_plan` | **整段 try 捕获 TypeError** | **天然安全**,fail-closed 保 primary |
| `validate_candidate` | 逐字段 `isinstance` 黑名单 + **无 try** | 崩 + 污染 |

**对照实验(实测)**:同型畸形喂 `sanitize_llm_plan` → `risk_flags=['llm_parse_failed']` 保 primary,不崩;
裸调它内部的 `filter_to_supported_modules([['gene_hub']], cands)` → `TypeError: unhashable type: 'list'`。
**崩点真实存在,只是被 try 兜住了。** 且 `sanitize_llm_plan` 的作者**从未枚举过"元素是 list"这种畸形**
(注释只写了"非可迭代标量(如 123)")—— **except 不需要知道畸形长什么样**。

**结论**:黑名单思维(挡已知坏的)→ 必然递归手工清单;白名单思维(只收契约内的,其余全丢)→
畸形类型全集**根本不需要枚举**,因为"其余"是补集。**项目里已有两个正确先例,本单元跟随它们,不引入新抽象。**

### 2.6 姊妹缺口(层2 机械枚举,形状 predicate 精确)

`list(x) if isinstance(x, list) else []` —— 容器守了、元素没守。**6 处同型**:

| # | 位置 | 字段 | 实测 |
|---|---|---|---|
| 1 | `llm_router.py:49` | risk_flags | 元素任意 |
| 2-3 | `llm_critic.py:39-40` | notes / flags | 元素任意 |
| 4-5 | `cross_module_reasoner.py:45-46` | notes / flags | 元素任意 |
| 6 | `safety_contract.py:62` | risk_flags | 实测 `[{'evil':1},['nested'],None]` 原样透传 |

后果:元素级畸形原样进 **provenance**(不崩、**不碰裁决**、per-call hash 仍确定性)。
影响面小,但 provenance 是 paper 要引用的审计产物 → 用户 2026-07-15 拍板**本单元一起修**
(理由:C3 教训 #2 正是"同型缺口未回填")。

### 2.7 层1 无机械判据(残余风险,必须诚实标注)

三个独立 predicate 交叉枚举,**没有一个能单独找全**:

| predicate | 漏掉 | 噪声 |
|---|---|---|
| `\.complete\(` | **`safety_contract.py`**(接收 raw_content 参数,不自己调 LLM) | 无 |
| `json\.loads\(` | 无 | 20+ 个读**本地数据集**的无关文件(predictors/job_store/registry…) |
| `isinstance\(.*list\)` | `module_planner` / `llm_report` | `core/request.py` / `registry.py` 等 |

`.complete(` 恰恰漏掉 `safety_contract.py` —— 而那正是 sanitize 正确实现的所在地。
**"哪些函数消费未受信 LLM JSON"是语义问题,无机械判据。** 本单元的入口集由三 predicate 并集 + 人工判断确定,
**这是残余风险,收官文档/paper 不得声称"全覆盖"**(表述见 §8)。

**这也是"登记表 + scan 比对"方案被否决的根因的独立复证**:scan predicate 会编码错误假设
(`.complete(` 编码了"入口 = LLM client 调用点"),而该假设不在登记表里 —— 变绿反而获得权威外观。

### 2.8 无自动执行面(核实属实)

`.github/workflows/ci.yml` 触发条件 `on: [push, pull_request]`,而红线是**不 push**;
`origin/main` 停在 `7fc4aa5`(v0.8),`origin/main..main = 304` —— **最近 304 个 commit 从未触发过 CI**;
且该 workflow 跑的正是被禁的裸 `pytest`。`.git/hooks` 下无自定义 hook。
**唯一执行面 = 收官前的本地全量回归。** 本单元**不新建 hook/CI**(那是独立决策,不在本单元范围)。

---

## 3. 范围(用户 2026-07-15 三拍板)

**做**:
1. **白名单重写 `validate_candidate` + 溯源契约**(拍板1)—— 元素级只接受 `str`,其余丢弃(**不 `str()` 强转**);
   配"不发明数据"溯源契约断言。同时消灭崩溃类 + 污染类。
2. **姊妹 6 处同型缺口一起修**(拍板3)。
3. **订正基线数字**(台账 + memory + 本 spec)。

**不做(明列)**:
- **不引入 hypothesis / 不建生成式 fuzz 工程**(拍板2)。理由见 §5.1。
- **不做全仓 sanitize 层重构**(回归面大,且层1 仍无法机械根治)。
- **不新建 hook/CI 执行面**(§2.8;独立决策)。
- **不动 #1(predictor 域)、#2(修复未回填)、#3(入口清单)** —— 本单元只根治 #4/#5 所在的层2/3/4。

---

## 4. 架构设计

### 4.1 白名单实现(跟随 §2.5 的两个既有先例)

`validate_candidate` 三处改元素级白名单:

```python
# targets:只接受 str,其余丢弃 —— 不 str() 强转(强转 = 发明数据)
targets = [t.strip() for t in targets if isinstance(t, str) and t.strip()] if isinstance(targets, list) else []
# outputs:元素级类型守 + 值白名单(isinstance 短路在 `o in set` 之前 → unhashable 不再崩)
outputs = [o for o in _raw_outputs if isinstance(o, str) and o in ALLOWED_OUTPUTS] if isinstance(_raw_outputs, list) else []
# assumptions:只接受 str 元素(收紧:现状 list(x) 元素任意)
assumptions = [a for a in _raw_assumptions if isinstance(a, str)] if isinstance(_raw_assumptions, list) else []
```

**原型已验证 7/7 已知实例**(实测):`"AHR"`→`[]`、`[None,'AHR']`→`['AHR']`、`[['AHR']]`→`[]`、
`[{'g':'AHR'}]`→`[]`、`[123]`→`[]`、`[True]`→`[]`、`['AHR']`→`['AHR']`(合法零回归);
两个崩溃实例均 NO CRASH。

**"部分丢弃"语义(设计决策)**:`[None,'AHR']` → `['AHR']`(保留合法元素、丢弃畸形元素),而非整体 fail。
理由:①满足溯源契约(既不发明 `'NONE'`、也不丢真数据 `'AHR'`);②全部元素被丢时 `targets=[]` →
既有 `missing.append("perturbation_targets")` 校验触发 → `schema_valid=False` → **fail-closed**,
与 Task 7 对 `"AHR"` 的既有语义一致;③**与 `llm_router:44` 的 `if a in candidates` 语义完全一致**
(静默丢弃越界元素、不报错)—— 跟随既有先例。

### 4.2 溯源契约(输出侧,不枚举输入侧)——本单元的核心贡献

```
契约:validate_candidate 对任意输入,若 schema_valid=True,
     则 normalized["perturbation_targets"] 的每个元素,
     必须溯源自输入 list 里的某个 str 元素(经声明的归一化:strip + 大小写)。
     形式化:set(normalized_targets) ⊆ {norm(s) for s in raw if isinstance(s, str)}
```

**为什么这一条能替代无底的输入侧枚举**:它是**输出侧**断言 —— 不问"输入可能有多畸形",
只问"输出有没有凭空多出东西"。一个断言同时覆盖已知全部四类后果:

| 后果 | 实例 | 契约为何抓得到 |
|---|---|---|
| 字符拆(C3 #4) | `"AHR"`→`['A','H','R']` | `'A'` 不溯源自任何输入 str 元素 |
| 发明(层4,现存) | `[None,'AHR']`→`['NONE','AHR']` | `'NONE'` 不溯源自 `None` |
| 嵌套(层3,现存) | `[['AHR']]`→`["['AHR']"]` | `"['AHR']"` 不溯源自 `['AHR']`(那是 list 不是 str) |
| 崩溃(#5) | `[['x']]` in set | 契约求值前先崩 → 测试红 |

**诚实边界**:契约只适用于**有溯源语义的字段**(`perturbation_targets`)。
`requested_outputs` 是**值白名单**(输出 ⊆ ALLOWED_OUTPUTS,更强);`assumptions` 是**类型过滤**(元素恒 str)。
三者判据不同,不得统称"溯源契约"。

### 4.3 边界 try(defense-in-depth,**非死码**)

`validate_candidate` 整体包一层 try,捕获 `(TypeError, AttributeError, ValueError)` → 返回
`schema_valid=False` + `errors=["candidate_malformed"]`,**绝不让 public 函数把未预见异常透给 `/api/parse`**。

**它不是空壳,有真实可达路径(实测)**:`:83` 的 `json.dumps(d, sort_keys=True, ...)` 对**混合类型 key**
抛 `TypeError: '<' not supported between instances of 'str' and 'int'` ——
实测 `json.dumps({1:'a','b':2}, sort_keys=True)` 确实抛。`validate_candidate` 是 public 函数(2 个消费点),
非 JSON 来源的 dict 可含非 str key。**Task 必须为此写一条真触发 except 分支的测试**;
若 TDD 阶段证明不可达 → **不加 try**(避免死码),并在 §8 如实记录。

### 4.4 姊妹 6 处(§2.6)

统一改 `[x for x in v if isinstance(x, str)] if isinstance(v, list) else []`。
**只收紧结构、不改语义**:产物只进 provenance,不碰裁决;`llm_router:44-47` 的 `recommended/excluded_agents`
**不动**(已是值白名单,天然安全)。

### 4.5 为什么不违红线

- 只改**输入侧结构守卫**,`reliability.py` / `critic.py` 裁决逻辑与数值**零改**;核心内核 + 根 `tests/` **零触碰**。
- OFFLINE 路径 cand 由 `_deterministic_parse` 内部构造(恒 `list[str]`)→ 白名单对其**恒等** → **字节等价不变**。
- 合法输入零回归(§4.1 原型实证 `['AHR']`→`['AHR']`)。
- `llm_used_for_prediction` 是 `run_query` 返回键(`:188`)恒 False,本单元不碰。

---

## 5. 关键风险与前置验证

### 5.1 风险:本单元被证伪(勘察挡下无收益工程是本项目传统)

用户拍板**不引入 hypothesis**,三条理由已勘察证成:
1. **白名单实现后 fuzz 主价值贬值** —— 没有"畸形类型全集"要找了(§2.5)。
2. **property 本身是手工的(层4)** —— fuzz 找到 #5 只因"不崩"是免费 property;它找不到"发明数据",
   除非人先想到写那个 property。**fuzz 把手工清单推后一层,正是本单元诊断的失效模式本身。**
3. 未装 = 新依赖;随机性与 OFFLINE 确定性红线有张力(`derandomize` 会退化成固定用例集,反而失去自动探索价值)。

### 5.2 风险:改 `assumptions` 为"只接受 str"是行为收紧

现状 `list(_raw_assumptions)` 元素任意。收紧后 dict/list 元素被丢。
**前置验证(Task 0)**:全量回归确认无既有测试依赖非 str assumptions。

### 5.3 风险:层1 残余(§2.7)

无法消除。**缓解**:三 predicate 并集 + 人工判断 + §8 诚实标注。**不得声称"全覆盖"。**

---

## 6. 红线(全程不可破)

1. 核心内核(`core/message.py`/`bus.py`/`agent.py`)+ 仓库根 `tests/` **零触碰**。
2. `agents/reliability.py` / `agents/critic.py` 裁决逻辑与数值**零改**。
3. 测试口径显式:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`,
   **绝不裸跑 pytest**。稳定基线用 `-m "not llm"`。新测试落 `praxis_virtualcell/tests/phase10/`。
4. OFFLINE 确定性字节等价(同请求多跑一致)。
5. 诚实不伪造:能力边界须在代码 docstring + spec 如实标注;**不得为凑绿弱化断言**(实际行为与预期不符 → 先报告)。
6. **不 push**;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
7. **前端 WIP 全程隔离**:`praxis_vc_react/src/styles/{base,fonts,themes,tokens}.css`(M)+ `.claude/`、
   `.playwright-mcp/`、`string.jpeg`(??)**绝不 stage/touch/revert**。每次 `git add` 只显式列本 task 的后端文件。

---

## 7. 测试(落 `praxis_virtualcell/tests/phase10/test_t10_7.py`)

> `test_t10_{1,2,4,5,6}.py` 已存在;`t10_3` 是 D 的交付物,**本单元不占用** → 用 `t10_7`。
> (若 D 的 playwright e2e 也想叫 T10.7,收官时在台账注明本文件是 C4 的,由 D 另取名。)

1. **溯源契约**(§4.2)—— 参数化跑过全部 7 个已知实例 + 合法输入,断言
   `schema_valid=True ⟹ set(normalized_targets) ⊆ {norm(s) for s in raw if isinstance(s,str)}`。
2. **崩溃类**:`requested_outputs=[['delta_expression']]` / `[{'a':1}]` → 不抛异常(**修复前红**)。
3. **发明类**:`perturbation_targets=[None,'AHR']` → `'NONE'` **不得**出现在 normalized(**修复前红**)。
4. **fail-closed**:全部元素畸形 → `targets=[]` → `schema_valid=False` + `missing_fields` 含 `perturbation_targets`。
5. **合法零回归**:`['AHR']`→`['AHR']`、`requested_outputs=['delta_expression']` 原样保留。
6. **边界 try 有牙**(§4.3):构造真触发 except 的输入,断言返回 `schema_valid=False` 而非抛异常。
7. **姊妹 6 处**:各断言元素级畸形被丢弃、合法元素保留(§4.4)。
8. **OFFLINE 字节等价**:同请求多跑一致(白名单对 `_deterministic_parse` 产物恒等)。

**变异要求**:每条断言须证"有牙"(改坏实现会红)。**永真断言 = 空壳,必须变异证伪**(C3 T10.6 的教训)。

---

## 8. 诚实边界(收官文档 / paper 引用须照此表述,不得夸大)

1. **不得声称"全覆盖未受信 LLM JSON 消费点"**。层1(哪些函数消费未受信输入)**无机械判据**(§2.7):
   `.complete(` 漏 `safety_contract`,`json.loads` 混进 20+ 无关文件,`isinstance` 漏 `module_planner`/`llm_report`。
   本单元入口集 = **三 predicate 并集 + 人工判断**,属残余风险。
2. **溯源契约只适用于 `perturbation_targets`**(有溯源语义的字段);`requested_outputs` 是值白名单、
   `assumptions` 是类型过滤 —— 三者判据不同,**不得统称"溯源契约"**(§4.2)。
3. **本单元不解决 #1/#2/#3**(predictor 域枚举 / 修复未回填 / 入口清单),只根治 #4/#5 所在的层2/3/4。
   **五次失效里本单元覆盖两次。**
4. **"850/40/0"是 `-m "not llm"` 的稳定基线**;含 9 条真实网络 LLM 测试时数字随网络浮动。
   **858/40/0 是全仓既有错误**(按红线扣除的净值,非任何一次真实运行输出),本单元订正。
5. 边界 try(§4.3)属**防御性 fail-closed**,若 TDD 证明不可达则不加 —— 收官须如实记录实际做法。
6. **`str()` 强转是本类 bug 的通用根因**:它对任何对象都成功,所以 **try/except 兜不住污染类**。
   凡"用 isinstance 守住了未受信输入"的主张,须区分**容器级**与**元素级**。

---

## 9. Self-Review(占位符/一致性/范围/歧义)

- **占位符**:无 TBD/TODO。§4.3 的 try 去留有明确判据(TDD 可达性)+ §8.5 兜底记录要求。
- **一致性**:§4.1"部分丢弃"与 §4.2 溯源契约一致(丢畸形元素不违反"不发明");
  §4.5 字节等价与 §6.4 红线一致;§3"不引入 hypothesis"与 §5.1 三条理由一致;
  §7 用 `t10_7` 与 §7 脚注(不占用 D 的 t10_3)一致。
- **范围**:聚焦用户三拍板;fuzz/全仓重构/新建 CI 执行面/#1#2#3 明列不做。
- **歧义**:§4.2 明确"溯源契约"仅指 `perturbation_targets`,另两字段判据已分别命名;
  §2.7 明确"层1 无机械判据"是残余风险而非可消除项。

---

## 10. 执行期修正(以本节为准 —— 上文 §4.2/§7/§8 的原文已被这些发现取代)

Task 1 实现后由**两轮**代码质量审(第一轮 2 条 Important;复核轮 1 条 Important + 2 条 Minor,
其中一条 Minor 坐实为**第二个活的生产 500**)抓到,implementer 逐条独立变异/实跑复核确认属实。
**本节优先于上文;收官文档 / paper 引用一律照本节表述。**
修正 1 经**两轮**订正(第一轮的订正本身仍是 conflate,见下);修正 5/6 为复核轮新增。

### 修正 1:§4.2"一条断言覆盖四类后果"是**过度声称**(实测:溯源契约 2/4)

§4.2 原写"一个断言同时覆盖已知全部四类后果",**不成立**。逐类变异实证(删掉 targets 的
`isinstance(t, str)` 守卫、退回 `str(t).strip()`)归属如下:

| 后果 | 实际由谁覆盖 | 是本单元判据吗 | 实证 |
|---|---|---|---|
| 发明(`[None,'AHR']`→`'NONE'`) | **溯源契约** | ✅ 本单元新增 | 变异 → 红 |
| 嵌套(`[['AHR']]`→`"['AHR']"`) | **溯源契约** | ✅ 本单元新增 | 变异 → 红 |
| 崩溃 | **`requested_outputs` 的值白名单**(`o in ALLOWED_OUTPUTS`,机制完全不同) | ✅ 本单元新增 | targets 路径**根本不会崩**:`str()`/`isinstance()` 对 JSON 可产生的全部元素类型(null/int/float/bool/str/list/dict)均不抛 |
| 字符拆(`"AHR"`→`['A','H','R']`) | **C3 既有的容器级 `isinstance(targets, list)`** | ❌ **非本单元贡献** | 同变异 → **仍绿**(C3 守卫先返 `[]` → fail-closed 早退);反向变异(只删 C3 容器守卫、留元素级)→ 字符拆**红** → 证实元素级 `isinstance(t,str)` 对字符拆毫无防护(拆出的字符本身就是 str),契约仅提供**回归防护** |

**⚠️ 第一轮的订正表述"跨字段的三种判据(溯源契约/值白名单/类型过滤)合计覆盖四类后果"
仍是 conflate,第二次被抓,一并作废** —— 复核审按上表**自己的归属列**逐行核:
只有 3 行落在本单元三处收紧内,**第 4 行(字符拆)落在三者之外**。
且**「类型过滤」(assumptions)对这四类贡献 0 类**(实测:修复前 `list(x)` 元素**原样透传、
不经 `str()`** → 无发明;不字符串化 → 非嵌套;`metadata.assumptions` 无 `in set` 消费点,
且 `ParseOut.candidate_request: dict[str, Any]` 无 pydantic 约束 → 不崩;容器守卫 C3 已有
→ 非字符拆)—— 它是**正当的纵深加固**,却被算进"合计覆盖四类"的分子。

**真实账目**:溯源契约 **2/4**(发明、嵌套)· 值白名单 **1/4**(崩溃)· 类型过滤 **0/4**
(独立加固,防非 str 元素进 metadata,不属四类)· C3 既有容器守卫(**非本单元判据**)
**1/4**(字符拆),本单元契约仅对其提供**回归防护**。

**唯一正确表述(按贡献直说,去掉"三种"这类凑数量词)**:

> 本单元三处收紧中,**溯源契约贡献「发明」「嵌套」两类、值白名单贡献「崩溃」一类、
> 类型过滤不对应这四类中任何一类**(独立加固)。第四类「字符拆」由 **C3 既有容器级守卫**
> 覆盖,本单元的溯源契约仅对其提供**回归防护**,非新覆盖。

**收官文档/paper 不得再写"一条断言覆盖四类",亦不得写"三种判据合计覆盖四类"。**

**§4.2 表格末行"崩溃(#5)|`[['x']]` in set|契约求值前先崩 → 测试红"一并作废** ——
审查者指出它只在"任何未捕获异常都会让任何 pytest 测试红"这个**平凡意义**上成立,
**不是 ⊆ 契约本身的性质**,是空洞断言。

### 修正 2:§4.2/§8 未披露 `got ⊆ src` 的**不对称性**

⊆ **只禁"多出"(发明)、不禁"少掉"(丢真数据)**:丢掉部分合法元素 → `schema_valid=True`
→ 契约恒 PASS;且 `∅ ⊆ src` 恒真 → 全丢亦 PASS。审查者搜遍全套测试
(`test_run_virtualcell_query.py` / `test_negative_cases.py` / `test_t10_6_llm_guard.py` /
`test_t10_7_*.py`)**无一条 3+ 合法混畸形用例** → 未来"丢一个合法 target"的 bug 会穿过整套。

**已补** `test_targets_no_silent_partial_loss`(3+ 合法混畸形,**精确相等**断言,不多不少保序)
从反侧覆盖;全丢那侧由既有 `test_targets_all_elements_malformed_fails_closed` 从
`missing_fields` 兜住。**当前实现无此 bug**(per-element 独立 filter,已核实),本条属**防回归**。

**实证佐证(implementer 补做)**:把 filter 变异成 `[:1]`(丢真数据)→ **溯源契约的 8 条参数化
测试全部保持绿**,只有新增的精确相等条 + 2 条零回归条变红 → **独立坐实 ⊆ 抓不到"少掉"**。

**paper 引用溯源契约时须同时说明它是单向的(只保证"不发明",不保证"不丢失")。**

**另记残余风险(审查者提)**:**静默丢弃无信号** —— 部分元素被丢弃时调用方/前端收不到
任何信号(与"用户本来就传得少"无法区分)。这是"部分丢弃"设计(跟随 `llm_router` 先例)的
已知代价,非 bug,但 D 单元若做用户可见性表述须计入。

### 修正 3:§8 残余风险清单**漏了同函数内 4 个零守卫标量字段**

`validate_candidate` 内 `request_id` / `cell_type` / `input_modality` / `output_modality`
**完全无类型守卫**(比本 task 修的三处更彻底地无保护)。端到端实测(控制器 + implementer
双方独立复核):

- **不崩溃**:`cell_type` 下游 `supported_cell_types` 是 **list**(实证:
  `brains/virtualcell/human/model_applicability.yaml:13` `[K562, A549, MCF7, HEK293T]`,
  YAML 加载后 `type=list`)→ `in` 用 `==` 比较**不需 hash** → unhashable 值不崩,
  恒不匹配 → **fail-closed abstain=True**(与 `requested_outputs` 的 set 命运相反 —— 正是
  §2.5"同一畸形三个消费点命运不同"的又一实例)。
- **不发明数据**:4 处**原样透传、不经 `str()` 强转**(实测 `cell_type=['evil']` → 输出仍是
  `['evil']` 而非 `"['evil']"`)。

→ **不构成本单元的两类失效模式**(崩溃 / 发明),故本单元不修;**但 D 单元若要对
`validate_candidate` 做"全覆盖"表述,须把这 4 处计入残余风险。**

### 修正 4(Minor):测试文件 `_norm` 的 scope 限制

`_norm` 硬编码 `.strip().upper()`,只对应实现的 `gene`/`gene_combination`/`ligand` 分支;
本文件全部用例均为 `perturbation_type: "gene"` → **`drug` 分支(归一小写)未覆盖**。已在
`_norm` docstring 标注。**非同义反复**(审查者实测证伪该风险):把实现的 `.upper()` 变异成
`.lower()` → 测试红 6 条 → `_norm` 是**独立 oracle**,不是跟着实现走的空壳。

### 修正 5(复核轮 —— **第七次复发,发生在"我声称机械枚举"的那句话上**)

**§2.6 写的"6 处同型"是错的,实际 7 处** —— 漏掉 `run_virtualcell_query.py:151`
(`parse_query` 内独立的一处 `list(raw_assumptions)`,**不是** `validate_candidate` 的那处)。

**§2.6 声称"这 6 处是精确形状 predicate 能机械找全的(不是语义猜测)"是不实表述**:
控制器当时**根本没跑那个 predicate**,是手工从 `grep "isinstance(.*, *list)"` 的结果里挑的,
并把 `:151` 误归类成了"validate_candidate 的一部分"。

**implementer 复核轮实跑 predicate(命令与输出照贴,不再只声称)**:

```bash
grep -rnE 'list\(.*\) if isinstance\(.*, *list\) else \[\]' \
     praxis_virtualcell/ praxis_vc_api/ --include="*.py" | grep -v "/tests/"
```
```
run_virtualcell_query.py:151   ← §2.6 的"6 处"清单漏了这个
agents_llm/llm_router.py:49
agents_llm/llm_critic.py:39
agents_llm/llm_critic.py:40
llm_orchestration/cross_module_reasoner.py:45
llm_orchestration/cross_module_reasoner.py:46
llm_orchestration/safety_contract.py:62
```
**命中 = 7**。另在 spec 写作时的树(`7fb70e5`)上实跑:该文件当时命中 **2 处**(`:61` + `:140`)
→ 全仓 **8 处**,减去 Task 1 自身范围内的 `:61` = **7 处姊妹**,spec 却写 6 —— 漏的正是
`:140`(Task 1 加注释行后现为 `:151`)。**算术与归属双向对得上,清单错误坐实。**

**漏掉的这处是第二个活的生产 500**(端到端实测,与 main 活 bug 同类、路径不同):
`parse_query:151` `list(raw_assumptions)` 元素级无守卫 → `:169` 原样返回
(**注意:返的是 `parse_query` 自己的 `assumptions`,不是 `validate_candidate` 的
`normalized.metadata.assumptions` → Task 1 的收紧保护不到这条路径**)→
`praxis_vc_api/models/api_schema.py:23 ParseOut.assumptions: list[str]` → pydantic 对
**dict/list/None/int 四种元素全抛 ValidationError** → **HTTP 500**。
自然触发例:LLM 把 assumption 写成对象 `['单基因敲低', {'note':'...'}]`。
`:152` 的 `try` **捕不到**(`list()` 对 list 不抛;ValidationError 发生在 `parse_query`
**返回之后**)。**仅 llm_assisted 模式可达**(实证:`:119` `_deterministic_parse` 恒产
`["deterministic keyword parse"]` → OFFLINE 不可达)。

**修复归属 Task 3**(姊妹处,在用户已拍板"一起修"的范围内 —— 它本就是同一形状 predicate
的一员,只是清单漏了)。**Task 3 的清单须用上面实跑的 7 处,不得再用 §2.6 的 6 处。**

**教训(本单元第七次复发,且这次发生在元层面)**:**"机械枚举"这个词本身也会被当成挡箭牌
—— 声称机械枚举 ≠ 真跑了 predicate。** 凡写"已机械枚举全集",须在文档里**贴出实际跑的
命令与输出**(如本节),否则与手工清单无异,且因带着"机械"二字而更具误导性。

### 修正 6(复核轮 Minor):契约的**归一化盲区**未披露

**契约是相对于「声明的归一化」而言的,不校验归一化规则本身是否无损。** `src` 是**用
`_norm` 定义的**,故任何**本身就在损毁数据的归一化**都在盲区 —— 实测:实现改成
`t.strip().upper()[:3]`、`_norm` 同步改 → `'TP53'`→`'TP5'`(数据已损毁)**照样 PASS**。

修正 4 记的 `.upper()`→`.lower()` 变异只证伪了**单侧漂移**(实现改、oracle 没改 → 红 6 条,
证明 `_norm` 是独立 oracle),**挡不住协同修改**。

**paper 若写"溯源契约保证 target 可溯源",读者会过读成"保证归一化无损" → 必须一并披露
该盲区。** 已在测试文件 docstring 诚实边界补记。
