# P10.C4 未受信 LLM JSON 白名单化 + 溯源契约 设计 spec

**定位**:C3 收口续作(同一失效模式、同一函数、同一批文件)。修 main 上一个活的生产 bug,并把
C3 Task 7 漏掉的那一层根治掉。产出直接服务 D 单元(D 有大量"全覆盖"性质的主张要核验)。

**基线**:main = HEAD = `c050f8a`,分支 `feat/v0.9-phase0-module-core`。

---

## 0. 当前状态摘要(READ FIRST —— 收官文档 / paper 作者从这里开始)

> **⚠️ 本节是摘要,不是原始记录。**
> - **§1–§9 是原始设计 spec,其中多处已被执行期发现证伪**(§4.2「一条断言覆盖四类」、
>   §7、§8 的部分原文均已被取代)—— **不要直接引用 §1–§9 的结论**。
> - **§10 是 append-only 的审计轨迹**(13 条修正,含 **7 条以上作废链**)——
>   它保留"我们当时错在哪",**逐条读会读到已作废的措辞**。
> - **本节 §0 是唯一"当前为真"的速查面**。与 §1–§9 冲突时以 §0 为准;
>   需要审计"为什么变成这样"时再去 §10。
> - §0 由 §10 修正 13 破例新增(**纯新增区块,不改任何历史文字**)。理由:§10 已 ~750 行、
>   作废链 7+ 条 → **paper 作者引到已作废句的概率接近 1**,该风险高于破坏行数基线的代价。

### 0.1 一句话定位

**P10.C4 = C3 收口续作**:修 main 上**活的生产 bug**(未受信 LLM JSON 未白名单化),
并把"手工清单"这一**反复复发的失效模式**收窄成**可执行的判据 + 规矩**。

### 0.2 当前真相(每条带最硬的那个证据)

| 做了什么 | 当前状态 | 最硬的证据 |
|---|---|---|
| **3 个活的生产 500 路径** | 全修 | ①`requested_outputs` 元素 unhashable → `o in ALLOWED_OUTPUTS` 抛 TypeError;②`parse_query` 的 `assumptions` 元素级无守 → `ParseOut.assumptions: list[str]` pydantic ValidationError;③`:184` `json.loads` 深嵌套 → RecursionError。**三者均 FastAPI TestClient 端到端实测 HTTP 500 → 修后 200** |
| **第六次复发:`app.py:66` 消费侧字符拆** | 修(共享两层守卫 `coerce_str_list`) | HEAD 上实测:`"AHR"` → `','.join(...)` → `'A,H,R'` → 回填 `['A','H','R']` → 用户确认 → **`validate_candidate` 返 schema_valid=True → 内核真按假基因 A/H/R 跑**。修后 `','.join(coerce_str_list("AHR")) == ''` |
| **RecursionError 清单 7 处** | 全捕获 | 机械枚举命令+输出见 §10 修正 11①;5 处回填**逐处变异 → 各自红 5/5** |
| **姊妹 7 处元素级白名单** | 全修 | 清单来自**实跑 predicate**(非手工挑);变异 → 红 |
| **`validate_candidate` 边界 try** | 在(defense-in-depth) | 变异 `except ():` → 红(非空壳);**非生产可达**,对标 C2 Gate B |
| **溯源契约** | 在(仅 `perturbation_targets`) | `[None,'AHR']` → 修前发明 `'NONE'`;端到端 e2e:前端收到 `['AHR']`,`'NONE'` 不在其中 |

### 0.3 可直接引用的表述(照抄,勿改写)

**① 四类后果的账目归属**(经两轮逐类变异实证;**不得**用"三种判据合计覆盖四类"这种凑数量的说法):
> 本单元三处收紧中,**溯源契约贡献「发明」「嵌套」两类、值白名单贡献「崩溃」一类、
> 类型过滤(assumptions)对这四类贡献 0 类**(它是正当的纵深加固,但不属四类中任何一类)。
> 第四类「字符拆」由 **C3 既有的容器级守卫**覆盖,本单元的溯源契约仅对其提供**回归防护**,
> **非新覆盖**。

**② 溯源契约是单向的**:
> `got ⊆ src` **只禁"多出"(发明)、不禁"少掉"(丢真数据)** —— `∅ ⊆ src` 恒真(全丢亦 PASS)。
> 引用溯源契约时**须同时说明它是单向的**;"不丢真数据"由另两条从反侧覆盖。
> 另:契约**不校验归一化规则本身是否无损**(`_norm` 协同修改是盲区)。

**③ 边界 try 的定性**:
> `validate_candidate` 的边界 try 是 **public API 契约防线**(defense-in-depth),
> **捕获已识别的 4 类**(TypeError/AttributeError/ValueError/RecursionError),
> **不声称捕获一切**;**当前生产路径不可达**,价值在防脚本/notebook/直接调用/未来第 3 个调用点,
> 对标 **C2 Gate B**。

**④ RecursionError 的覆盖主张(**唯一许可的写法**)**:
> 经**机械枚举** `json.loads`/`json.dumps` 消费未受信 LLM JSON 的调用点(命令与输出见
> §10 修正 11①),**当前清单 7 处已全部捕获 `RecursionError`**。
> **层1 仍无机械判据**("哪些算未受信 LLM JSON"是语义判断;predicate 只是启发式代理)
> → 残余风险照旧。

**⑤ `parse_query` 的输出契约(极易被过读)**:
> **只有 `schema_valid=True` 分支的产物经过归一 + 白名单**。`schema_valid=False` 时
> **按设计**返回**未归一、未白名单化的原始 LLM dict**(让用户在 UI 上看到 LLM 到底答了什么并
> 修正)→ **守卫的责任在消费侧**,消费者必须调 `coerce_str_list`。

### 0.4 ❌ 不得声称清单(每条都被实证证伪过)

| ❌ 不得写 | 为什么 |
|---|---|
| "**根治**〔第五次复发 / 发明假基因名〕" | 论域=全仓消费未受信 LLM 值的代码点,**无机械枚举** → 判据 A① 不成立。**第六次复发就活在 HEAD 上被 opus 抓到** |
| "`validate_candidate` 已全覆盖" | 同函数内**仍有 4 个零守卫标量字段**(§10 修正 3) |
| "`parse_query` 输出已白名单化" | **只有 True 分支**;False 分支按设计返原始 LLM dict(§0.3⑤) |
| "`/api/parse` 对 RecursionError 无条件安全" | 只能说"**当前清单 7 处已全部捕获**"(§0.3④) |
| 任何对**消费点**的"全覆盖" | 消费点是**语义判断**(层1),**无机械枚举** |
| "LLM unsupported claim = 0"(G2) | C3 支撑不到,须克制 |

### 0.5 已作废措辞黑名单(**必须连「正确写法」一起读** —— 只记禁词会换个同义全称词复发)

| ❌ 已作废 | ✅ 正确写法 |
|---|---|
| "**根治**〔某复发〕" | "修复 **`validate_candidate` 这一处**的字符拆" |
| "**绝不**把异常透给调用方" | "**捕获已识别的 4 类**;`MemoryError`/未知类型在白名单外" |
| "**硬编码** `max_tokens: int = 1024`" | "`max_tokens` 的**函数默认参数**(**可被调用点覆盖**,非结构不变量)" |
| "**可达**"(未限定) | 分开写:"**直接调用可达**"/"**当前生产路径不可达**" |
| "`app.py` 的 cand 是**自产 normalized 拷贝**" | "**只在 `schema_valid=True` 分支**成立;False 分支是未归一原始 LLM JSON" |
| "**三种判据合计覆盖四类**" / "**一条断言覆盖四类**" | 照 §0.3① 的**逐类归属**写 |
| "**无条件成立**" / "**无论…都**〔精确复原〕" | "`setenv` 底层 `setitem` **无条件登记 undo**"(对实现的封闭陈述,非对"任意改写者"的全称) |
| "**6 处**已机械找全" | "**实跑 predicate 命中的 N 处**(命令+输出附后);**predicate 找不找得全是另一回事**" |
| "**表述纪律已守**" | 只有在**同时扫过 commit 标题 / 台账 / 报告**后才可说(判据 A 适用条件 2) |

### 0.6 两个判据(+ 适用条件)

**判据 A —— 全称词能不能用**:
> 全称成立 ⟺ **①论域全覆盖**(存在补集 / else 分支)**∧ ②每个分支的行为各自都满足该性质**。
> - **①要求论域可机械枚举**;论域是**语义判断**(层1)时 ① **永远无法兑现 → 全称不能提**。
> - **A 必须施于 prose**(**commit 标题** / 台账 / paper / 报告),**不止代码分支** ——
>   本单元漏的就是这一步("根治"住在 commit 标题里)。
> - 反例(证明①不够):`data if isinstance(data,list) else list(data)` 是封闭二分,
>   `'AHR'` 照样 → `['A','H','R']`。

**判据 B —— 测试是不是环境依赖的静默空壳**:
> 问 **"这条测试的期望结果,和'它根本没跑'的退化结果,能区分吗?"**
> 不能区分 → 空壳,必须补**只有真跑过才成立**的锚点(如 `llm_metadata.response_hash`)。
> **B 抓"静默未执行",抓不到"机制搞错" → 必须与变异配对使用。**

### 0.7 残余风险(诚实,不加粉饰)

1. **层1 无机械判据**("哪些算未受信 LLM JSON / 谁是消费者"是语义判断)——
   **且已被证明会被当免罪符**:它被写了 4+ 次,却被用来**关闭**分析(app.py 只问 key)
   而不是**打开**分析。**标注风险 ≠ 枚举风险。**
2. **`app.py:66` 无直接测试覆盖**(Streamlit 顶层脚本,import 即执行)——
   被调用的 `coerce_str_list` 有真实覆盖,但若有人把 `:66` 改回直接 `join`,**测试抓不到**。
   (**有意不写"抄一份表达式"的测试** —— 那正是 safety_contract 抄 llm_router 的失效模式。)
3. **React 侧**:`readStr` 用 `String(v)` 使字符拆**走运**安全(**不是设计**);
   但实测 `[{g:'AHR'}]` → `"[object Object]"` —— **仍是发明,只是可见**。(前端 WIP,未修。)
4. **`validate_candidate` 4 个零守卫标量字段**(§10 修正 3)。
5. **`⊆` 单向**(§0.3②)+ **`_norm` 协同修改盲区**。
6. **except 捕获范围过宽无测试兜底**:现有测试能证明"except 真在捕获"(`except ():` → 红),
   **不能证明"范围不过宽"**(改成 `except Exception:` → 全绿)。
7. **`/api/jobs` 的 `detail=str(e)`** 把原始异常文本泄漏给调用方(小瑕疵,记录不修)。
8. **narrative gate**:仅 abstain / 仅浮点 / 不验语境对应 / hedge 词可绕 →
   **不得声称覆盖 §128 hypothesis-写成-conclusion**。

### 0.8 新规矩(本单元用 12 次复发换来的)

1. **prose 里一旦点名某消费者,就必须对它做「字段 × 行」的枚举** —— 不能只问"key 是不是 str"。
   (C4 点名了 `app.py` 却只问 key → 第六次复发活到 final review。)
2. **报数必须显式标口径** —— 858/859/850 与 238/239 两次同型:数字本身没错,**没标口径就是错**。
3. **凡"全覆盖"主张,须双层机械枚举(入口 × 字段)+ 贴出命令与输出** ——
   "声称机械枚举" ≠ "真跑了 predicate"(§10 修正 5)。

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

### 修正 7(Task 2 执行期 —— **§4.3"可达"表述不精确;同一份 spec 对"可达"用了两个标准**)

**§4.3 原写"它不是空壳,有真实可达路径(实测)…… 若 TDD 阶段证明不可达 → 不加 try"**,
其中"可达"**未限定作用域,表述不精确**。实测坐实的是**直接调用 `validate_candidate({1:'a',...})`
会崩**,**不是生产路径可达**。Task 2 implementer 在前置门之外自行勘察两个消费点的调用链,
戳破了这一点(控制器采信并复核确认属实):

- **`/api/parse` → `parse_query`**:`cand` 只可能来自 `json.loads(content)`(**JSON object 的
  key 恒为 str** —— 混合类型 key 在 JSON 里根本不可表示)或 `_deterministic_parse`(固定 str
  key 的字面量构造)。且 `:174` 的 `cand.get`(C3 补的 AttributeError 守卫)已把非 dict 顶层
  值挡回 `_deterministic_parse`。
- **`praxis_vc_web/app.py:75`**:`cand = dict(p["candidate_request"])` —— 是 `validate_candidate`
  **自产的 normalized dict** 的拷贝,key 恒 str。

→ **当前两个已知消费点的正常路径,边界 try 的 except 分支不可达。**

**同一份 spec 里"可达"滑动成了两个标准(本条的核心问题)**:

| 出处 | "可达"的实际含义 | 证据 |
|---|---|---|
| **§2.4 活 bug** | **真·生产路径可达** | LLM 返嵌套数组是**自然错误** → `/api/parse` → 端到端 **500**(已端到端实测) |
| **§4.3 边界 try** | **仅直接调用可达** | `validate_candidate({1:'a',…})` 直接调用会崩;**生产路径到不了** |

**精确定性(收官文档 / paper 一律照此,已同步进 `validate_candidate` docstring 与
`test_boundary_try_non_str_key_returns_invalid_not_raises` docstring)**:

> 边界 try = **public API 契约防线 / 防御性罕触发**。触发需**非 JSON 来源的 dict**(混合类型
> key);**当前两个已知消费点的正常路径不可达**(JSON object key 恒 str)。它防的是脚本 /
> notebook / 直接调用 / **未来第 3 个调用点**,**不是**当前生产 500 的防线 —— 那个由 Task 1
> 的元素级白名单管。定性对标 **C2 的 Gate B**(防御性完整性断言:字段恒由代码构造、正常
> 路径不触发、防未来重构漏挂),**非死码,但也不得说成"生产可达"**。

**"罕触发" ≠ "当前不可达",两词在本项目有实质区别,不得混用**:C1/C2 的 gate 是**罕触发但
理论上生产可达**(违规 module_plan 真会触发 → 真 override abstain);本层是**当前正常路径
根本到不了**。

**保留决策(implementer 判断 + 控制器采信)**:**保留**。依据 = C2 Gate B 先例已确立"正常
路径不触发的防御性断言"是项目接受的模式;`validate_candidate` 是**无下划线前缀的 public 名**、
已被跨包直接 import(`app.py`),契约防线有正当性;成本 = 4 行、正常路径零行为改变
(870 全绿 + 字节等价条恒绿实证)。**但其价值主张必须按上表限定,不得记入"修生产 500"的账。**

### 修正 7b(Task 2 —— 对照组的**已知局限**,implementer 主动实测并披露)

`test_boundary_try_does_not_swallow_legit_results`(对照组)**挡不住"捕获范围过宽"**:
把 except 变异成 `except Exception:`(过度捕获)→ **两条测试均仍绿**(因为正常路径本来就不
抛异常,过度捕获对它无影响)。

**即:当前两条测试能证明"except 真的在捕获"**(反向变异 `except ():` → 上条红,**非永真
空壳**)、**但不能证明"except 的捕获范围不过宽"**。当前实现取 `(TypeError, AttributeError,
ValueError)` 而非 `Exception` 属**人工克制**,**无测试兜底** —— 未来若有人放宽成
`except Exception:`(会吞掉 KeyboardInterrupt 以外的一切,含真 bug),测试套件**不会红**。
已在对照组 docstring 标注。**D 单元若对边界 try 做"测试充分"表述,须计入本条。**

**教训(承修正 5 的元层面教训)**:**"可达"这个词必须限定作用域** —— 生产路径可达 /
直接调用可达 / 理论可达,三者证据强度递减。不限定就会在同一文档内滑动(本条即实例:
§2.4 与 §4.3 同词异义),且**读者会默认取最强的那个含义**。同理适用于"罕触发"
(≠ 不可达)与"非空壳"(≠ 覆盖充分)。

### 修正 8(代码质量审 —— **`RecursionError` fail-open 缺口(已补)+ "绝不"是不可能兑现的主张**)

**Critical(真实缺口,已修)**:代码质量审**逐类枚举 `_validate_candidate_impl` 内可抛异常
的操作**(方法与修正 5 的实跑 predicate 同源:枚举而非手工挑),发现原三元组
`(TypeError, AttributeError, ValueError)` **漏了 `RecursionError`**:

| 异常 | 来源 | 原三元组是否捕获 | 实证 |
|---|---|---|---|
| `TypeError`(混合类型 key) | `json.dumps(d, sort_keys=True)` | ✅ | Task 2 前置门 |
| `ValueError`(循环引用 "Circular reference detected") | 同上 | ✅ | 审查者实测 |
| `UnicodeEncodeError`(孤立代理项,`json.loads('"\ud800"')`) | 同上 | ✅ | **`issubclass(UnicodeEncodeError, ValueError) is True`**(implementer 复核实测) |
| **`RecursionError`(深嵌套非循环 dict)** | 同上 | ❌ **穿透** | `RecursionError.__mro__` = `(RecursionError, **RuntimeError**, Exception, BaseException, object)` —— **不属三元组任一**(implementer 复核实测) |

**已补** `RecursionError` 进白名单(成本 1 个 token,正常路径零行为改变)+ 新增
`test_boundary_try_deep_nested_dict_returns_invalid_not_raises` 钉死。**TDD 红→绿实证**:
补之前该条报 `RecursionError: maximum recursion depth exceeded while encoding a JSON object`;
补之后绿。**变异证伪**:去掉 `RecursionError` → **仅该条红**、另两条边界 try 条仍绿
→ 该条精确钉住这一类,非空壳、无冗余重叠。

**阈值不是稳定常数(implementer 实测订正,spec 不得钉死数字)**:本机(CPython 3.13/macOS)
**8000 层不抛、10000 层抛** —— 审查者给的"约 8000–10000 层"**区间准确**(implementer 初读时
误当成"8000 触发"而声称其数字不准,**当场实测自证其非并收回** —— 又一次"没验证就下结论")。
Python **3.13 按 C 栈指针判定**而非 `recursionlimit` 计数(实测 `sys.getrecursionlimit()==1000`
却需约万层)→ **阈值随栈大小/解释器版本浮动**。故测试取 **20000 层**(远超阈值的余量),
**不写死具体阈值**。

**"绝不把未预见异常透给调用方"是不可能兑现的主张(本条的根本问题,比缺口本身更重要)**:
docstring 原写"**绝不**把未预见异常透给调用方",被 `RecursionError` 直接证伪。但**补上
`RecursionError` 并不能让"绝不"成立** —— 这是量词层面的错配,不是白名单不够全:

- **全称主张 vs 有限枚举**:"绝不"要求对**一切**异常类型成立;`except (A, B, C, D)` 是**枚举**。
  枚举永远兑现不了全称。`MemoryError`(深/大结构序列化时真实可能)、未来代码路径引入的
  未知异常类型,都在白名单外。
- **唯一能兑现"绝不"的写法 `except BaseException` 是坏实践**:会吞掉 `KeyboardInterrupt` /
  `SystemExit`(进程杀不掉)与真 bug(静默)。

→ **表述改为**:"捕获**已识别的 4 类**(`TypeError`/`AttributeError`/`ValueError`[含
`UnicodeEncodeError`]/`RecursionError`),**不声称捕获一切** —— 这是设计上的**有意取舍**,
非遗漏"。已同步进 `validate_candidate` docstring。**收官文档 / paper 一律照此,"绝不"作废。**

**可达性限定(照修正 7 确立的纪律,审查者主动套用)**:`RecursionError` 缺口
**直接调用可达**(脚本/notebook 传深嵌套 dict);**生产路径不可达** ——
`praxis_virtualcell/agents_llm/llm_client.py:23` `max_tokens: int = 1024` → LLM 单次
补全被截断,**物理上产不出触发阈值所需的嵌套深度(约 5–6 万字符)**;`app.py:75` 的 cand 是
浅结构。→ **缺口的可达层级与这个 try 本身的价值主张同级**(都只在"直接调用"层),
**不是新增的生产风险面**,不得记入"修生产 500"的账。

**⚠️ 但两条"生产不可达"的证据强度不同(implementer 复核 `max_tokens` 时发现,审查者与
控制器均未说透 —— 收官文档不得把二者并列成同等强度)**:

| 缺口 | "生产不可达"的依据 | 强度 | 会不会被改动破坏 |
|---|---|---|---|
| 混合类型 key(`TypeError`) | **JSON object 的 key 恒为 str** | **强:JSON 格式的结构性保证** | **不会** —— 除非换掉 `json.loads` 这个数据来源 |
| 深嵌套(`RecursionError`) | `max_tokens` **默认值** 1024 | **弱:可调默认参数,非结构不变量** | **会** —— 调大即可能失效 |

`max_tokens` 是**默认参数**(非常量):实测全仓 `.complete(` 7 个调用点,**唯一覆盖点是
`llm_report.py:29` 的 `max_tokens=800`(更小,且不在本函数路径上)**,`parse_query:172` 用默认
1024 → **当前树上主张成立**。但这是**当前树的事实,不是不变量**:粗算 1024 token ≈ 3–4 千
字符 ÷ 每层约 6 字符(`{"n":` + `}`)≈ **500–600 层**,距阈值约万层有 ~15x 余量;**若未来把
`max_tokens` 调到 128k 级(≈50 万字符 ≈ 8 万层),该余量被吃穿、缺口转为生产可达**。
→ **深嵌套那条的"生产不可达"须表述为"依赖 `max_tokens` 当前默认值",不得写成结构性保证。**
(这也是补 `RecursionError` 的**正当性来源之一**:它把一条"依赖可调配置"的防线变成
无条件成立 —— 成本 1 个 token,不必赌配置不变。)

### 修正 8b(spec 合规审 Minor —— `app.py:75` 那句的适用范围被夸大)

修正 7 与 Task 2 commit 写的"`app.py:75` 的 `cand` 是 `validate_candidate` **自产 normalized
dict 的拷贝**" —— **只在 `schema_valid=True` 分支成立**。`schema_valid=False` 时(**页面 2
专门给用户"补充/修正"的常见路径**)`parse_query` 返的 `candidate_request` 是 `{**cand, ...}`,
即**未经归一的原始 LLM JSON / `_deterministic_parse` 产物**的展开。

**结论方向不变**(`json.loads` 产物与自产 normalized **两者 key 皆恒 str** → except 分支
仍生产不可达),但那句话的适用范围被夸大到了另一分支。**改为**:"`app.py:75` 的 `cand`
来自 `json.loads` 产物或 `validate_candidate` 自产 normalized 二者之一,**两者 key 皆恒 str**"。
已同步进 docstring。

**教训(承修正 5/7 的元层面,本单元第 6 次"未限定作用域的全称词")**:前五次是
**"四类"**(修正 1)· **"三种"**(修正 1 第二轮)· **"机械找全"**(修正 5)· **"可达"**(修正 7)·
**"自产 normalized 的拷贝"**(修正 8b,全称化了只在一个分支成立的事实);这次是 **"绝不"**。

> **凡出现"绝不 / 全部 / 所有 / 一律 / 永不 / 一定"这类全称词,必须能当场给出判据
> (枚举命令 + 输出、或形式化论证),否则一定被反例证伪。** 本单元的经验是:
> **反例总会被下一轮审查找到 —— 六次无一例外。** 更强的做法是**先自问"这是全称还是枚举"**:
> 若实现是枚举(如 except 白名单、手工清单),就**不得用全称词描述它**,应改为
> "已识别的 N 类 + 明示边界"。

### 修正 9(Task 3 收口轮 —— 两轮审查 5 项;含**第 3 个潜在 500** 与**判据自身不完备**)

Task 3 的核心修复(实跑 predicate 命中的 7 处元素级白名单)经 spec 审在父树亲验 **predicate 恰好 7 处
且与改动 1:1 对应**、e2e 500 亲测坐实、6 红 2 绿、全量 879 / phase10 单跑 230 双跑一致、红线全守 ——
**判定合规**。以下 5 项为收口,其中 ②⑥ 是**新发现的真问题**。

#### ①(implementer 自写的过度声称,**本单元第 9 次**)env 泄漏防御的"无论…都"不成立

Task 3 commit 与测试 docstring 写的:

> "monkeypatch.delenv 在此处先'登记'基线,teardown 时**无论期间被谁改写都会精确复原**"

**证伪(审查者读 pytest 源码,implementer 已亲自复核 `_pytest/monkeypatch.py` 确认)**:
`delenv(name, raising=False)` → `delitem`,逻辑是
`if name not in dic: if raising: raise; else: pass`(**key 不存在 → 纯 no-op,不登记任何 undo**);
**只有 key 已存在**才 `self._setitem.append((dic, name, dic.get(name, notset)))`。
对比 `setenv` → `setitem`:**无条件** append undo 记录。

**为什么本地实测"没事"是巧合**:`praxis_virtualcell/tests/conftest.py::pytest_collection_modifyitems`
在**收集阶段**调 `load_env()`,而本仓 `.env` 有 `PRAXIS_VIRTUALCELL_MODE=offline`,`load_env()` 用
`os.environ.setdefault(...)` **预置**了该 key → delenv 恰好命中"已存在"分支。
**纯属环境副作用侥幸,非 delenv 的设计保证。**

**双方独立实验复现真泄漏**(implementer 亲跑,非转述):cwd 换到**无 `.env`** 的目录
(`load_env()` 用**相对路径** `Path(".env")`,找不到即 no-op)、`PYTHONPATH` 指向真实仓库、
`env -u PRAXIS_VIRTUALCELL_MODE`,同一 session 顺序跑 e2e + 泄漏探针 →
**实测 `PRAXIS_VIRTUALCELL_MODE` 残留为 `'llm_assisted'`**。→ **CI / 无 `.env` 环境下会真泄漏。**

**修法(已验)**:`monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")`。
变异证伪:改回 `delenv` → 无 `.env` 环境下探针**红**(泄漏 `'llm_assisted'`);改回 `setenv` → 绿。

**爆炸半径(核实后如实记录,不夸大)**:全仓**只有该条测试**经 API 层调
`config_for("llm_assisted")`(其余 llm_assisted 测试都直接构造 `RuntimeConfig` 不经 `config_for`)
→ **当前无第二个受害者,回归数字未失真**(879/230 双跑一致已亲验)。属**防未来**,非修活 bug。

**订正表述**:删"无论期间被谁改写都会精确复原";改为限定式 ——
"`setenv` 底层 `setitem` **无条件登记 undo**,故 key 之前存不存在都能精确复原"(这是对
`setitem` 实现的**封闭陈述**,非对"任意改写者"的全称主张)。

#### ② 🔴 第 3 个潜在 500:`:184` 的 `json.loads` 同型缺口(**已修**)

**端到端实测(implementer 亲验抛出点)**:stub LLM 返 20000 层嵌套 JSON →
`parse_query(llm_enabled=True)` → **UNCAUGHT RecursionError**,`traceback` 定位抛出点
**`run_virtualcell_query.py:184` 的 `cand = json.loads(content)`**(源码行实测为
`'cand = json.loads(content)'`)→ `/api/parse` **仍 500**,Task 2 在 `validate_candidate` 的边界 try
**根本轮不到执行**。

**根因**:`:184` 所在的 `except (json.JSONDecodeError, TypeError, AttributeError)` **同样不含
RecursionError** —— 与 Task 2 修前的三元组是**同一形状的缺口**(`RecursionError.__mro__` 实测
= RecursionError → RuntimeError → Exception,不含那三者;`json.JSONDecodeError` 是 `ValueError` 子类)。
**这正是 C3 教训 #2「同型缺口未回填」的又一实例**(safety_contract 抄 llm_router 时修了漏洞却没回填原件)。

**阈值实测**(implementer 二分,非转述):`json.loads` 约 **9999 层**(list 形状),落在审查者报的
9835–10140 带内;`json.dumps` 约万层;且 **`json.loads` 程序顺序在先** → 深到能让 dumps 崩的输入,
基本都会先崩在 loads。阈值随栈大小/版本浮动、**非稳定常数**(CPython 3.13 按 **C 栈指针**判定而非
`recursionlimit` 计数)→ 测试取远超阈值的 20000 层,不钉死数字。

**决策**:控制器决定修(审查者建议不修/超范围)。理由:**我们现在已经知道它**,不修就是明知故犯;
成本 1 个 token。TDD:测试先红(实测 500)→ 补 `RecursionError` → 绿 → 变异(去掉它)→ 红 → 改回。

**⚠️ 修后的限定表述(不得越界)**:只能说
> **`json.loads`(:184)与 `validate_candidate` 边界(:75)两处已捕 `RecursionError`**。

**不得声称**"`/api/parse` 对 RecursionError 无条件安全" —— **是否还有第三处未捕,层1 无机械判据**
(这正是本单元反复吃到的教训)。**当前生产可达性**:与 Task 2 同 —— 因 `max_tokens` **默认值** 1024
(**函数默认参数,可被调用点覆盖,非硬编码**)而生产不可达。

#### ③ "封闭二分 vs 枚举"判据**本身不完备**(第 7 次 —— 藏在**用来防过度声称的判据**里)

上一个 implementer 提炼的判据(`isinstance` 是封闭二分 → 可用全称词;`except (A,B,C,D)` 是枚举 →
只能说"已识别 N 类")**方向对,但不完备**。审查者构造反例、implementer **亲跑复现**:

```python
x = data if isinstance(data, list) else list(data)   # 也是封闭二分!两分支都处理了
# 实跑:data='AHR' → ['A','H','R']   ← 恰恰是那条全称禁止的行为
```

**封闭二分只保证"论域全覆盖",不保证全称性质成立。**

**正确判据(以本条为准)**:
> 全称成立 ⟺ **①判据对论域全覆盖**(存在补集 / else 分支)**且 ②每个分支的行为各自都满足该性质**。
> `except (A,B,C,D)` 卡在 ①(无补集;`except BaseException` 是唯一补集且是坏实践)→ 只能写
> "已识别 N 类";`isinstance + else` 过 ①,**必须再验 ②** 才可用全称词。

对照:`[x for x in data if isinstance(x, str)] if isinstance(data, list) else []` —— 实跑
`'AHR'` → `[]`,**else 分支行为本身也满足性质** → ①② 双过 → 才可用全称词。
**照原文进收官文档会授权假全称**(上面那行 `list(data)` 就能通过原判据)。

#### ④ 残留原词已扫(**同一 commit 一边宣布作废、一边新写了它**)

- `test_t10_7_untrusted_json_whitelist.py` 深嵌套那条 docstring(Task 2 那轮**新写**)仍写
  "**硬编码** `max_tokens: int = 1024`" —— 正是那个 commit 宣布作废、改成"**默认值**
  (可调默认参数,非结构不变量)"的词。**已改**。
- 同文件边界 try 那条仍写"`app.py:75` 的 `cand` 是 **validate_candidate 自产 normalized dict 的
  拷贝**" —— 正是修正 8b 判定被夸大的原句。**已改**为分支限定式,并补记
  `app.py:59` 是 `cand = dict(p["candidate_request"])`、`run_virtualcell_query.py:217` 是
  `v["normalized"] or {**cand, ...}`(implementer 实测核对;另:`validate_candidate` 调用点
  实为 **`app.py:76`**,原文写的 `:75` 是 off-by-one)。
- **连带订正修正 8b 自身**:8b 末句"**已同步进 docstring**"**本身未限定作用域** —— 实际只同步了
  `run_virtualcell_query.py` 的生产 docstring,**测试 docstring 两处未动**。应表述为
  "已同步进**生产 docstring**;测试 docstring 遗漏,由修正 9④ 补"。

- **`_norm` 那处的"硬编码"不在本次扫除范围**(implementer 判定并说明):它描述的是**测试自己的
  字面量**(`return s.strip().upper()` 确实是硬编码的独立 oracle)—— **用词准确,非本单元作废的
  那个语境**(作废的是把"函数默认参数"说成"硬编码"从而夸大其不可变性)。

#### ⑤ "15x 余量"须标 **shape-dependent**

6 字符/层是 **dict 形状**(`{"n":` + `}`);**list 形状每层仅 2 字符**(`[`+`]`)。
implementer 亲算:1024 token 粗估 ~3584 字符(~3.5 char/token)→ dict ~597 层(对 ~10000 层阈值
余量 **~16.8x**)、list ~1792 层(余量 **~5.6x**);再叠 BPE 对重复括号的打包,余量继续被吃。
且 `{"x": [[[…]]]}` 这种深 list 嵌在 dict 值里**确实能走到** `json.dumps`。

→ 结论(**当前生产不可达**)**不变**,但"15x"是**最好情况**,应写成
"余量存在但**随嵌套形状变化**(dict ~15x / list ≤5x)",**不是一个稳定常数**。

#### ⑥(**本轮 implementer 新发现,两轮审查均未指出**)e2e 测试**非自足**:无 key 时不再测目标 bug

> ### ⚠️ 本节的「静默」归属**已被修正 10① 判定为错误** —— 读本节必须连带读修正 10①
> 现象(非自足)属实、修法(setenv stub key)有效且已保留;**但"谁在静默"归错了对象**。
> 本节点名的 `test_sibling1_..._e2e_api_not_500` **是吵闹会红的**(敌对环境实测 FAILED);
> **真正静默空过的是本修正 9 自己新造的 `test_parse_query_deep_nested_..._not_500`**
> (敌对环境实测 PASSED),本节**完全没提它**。详见修正 10①。

修 ① 的实验中顺带实测发现:`test_sibling1_parse_query_assumptions_e2e_api_not_500` 经
`config_for("llm_assisted")` → `from_env()`,而
`llm_enabled = (mode in LLM_MODES and bool(key))` —— **无 `DEEPSEEK_API_KEY` 则 llm_enabled=False**
→ 根本不进 LLM 分支、回落 `_deterministic_parse` → `assumptions` 恒
`["deterministic keyword parse"]`。

**【已作废的错句(勿复活;保留原文仅为留审计痕迹,不得作为有效陈述引用)】**:
~~"危害形状与 C3「永真空壳」同类但更隐蔽:在无 `.env` 的 CI 里,本条**不是简单地红** ——
`status_code` 仍 200,它只是静默地不再测它声称要测的那个 500 bug"~~
→ **错**。本条有第二条断言 `assert r.json()["assumptions"] == ["单基因敲低"]`,必然拦下退化值
`["deterministic keyword parse"]` → **红**。该错句与本节自己下一段"实测:修前**红**"**直接自相矛盾**
(**后者才是对的**)。正确归属见修正 10①。

**成立的部分**:今天能测到**纯因为本仓 `.env` 恰好供了真 key**(与 ① 同一个"环境侥幸"根因)——
这一点对本条与那条深嵌套测试**都**成立,故"须显式 setenv"的修法对两条都保留。

**修法**:`monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")` 让本条对环境
**自足**(stub client 已接管 `make_llm_client`,**不发网络请求**;setenv 函数级作用域,teardown 精确
复原;collection 期的 `llm` mark skip 逻辑早已跑完,不受影响)。实测:无 `.env` + `env -u
DEEPSEEK_API_KEY` 环境下,修前**红**(assumptions 落回 deterministic)、修后**绿**。

**教训(与 ① 同源)**:**"测试在本机绿"不等于"测试在测它声称测的东西"** —— 二者都靠仓库 `.env`
的环境副作用侥幸成立。凡测试依赖 `from_env()` 一类**读环境**的构造路径,须显式 setenv 全部相关变量,
否则该测试的有效性**取决于运行环境**而非代码。

### 修正 10(Task 3 收口第二轮 —— **第 10 次过度声称:「静默」归错对象,且放过了真正静默的那条**)

Task 3 收口轮代码经 spec 审独立证实全部落实(敌对环境变异、`traceback.extract_tb` 亲验抛出点
`:184`、二分阈值**不抛=9998 / 抛=9999**)。**但修正 9⑥ 把"静默"归错了对象** —— 形状极讽刺:
它是**修正 9 自己新造的测试**在静默,而 9⑥ 却去点名了另一条**吵闹会红**的测试。

#### ① 「静默」归属订正(implementer 已独立复现,非采信转述)

抽掉两处 stub key 行、在敌对环境(无 `.env` cwd + `env -u PRAXIS_VIRTUALCELL_MODE
-u DEEPSEEK_API_KEY`)实测:

| 测试 | 抽掉 stub key 后 | 与修正 9⑥ 的描述 |
|---|---|---|
| `test_sibling1_..._e2e_api_not_500`(**9⑥ 点名的就是它**) | **FAILED(红,吵闹)** | ❌ 9⑥ 说它"不是简单地红…静默地不再测" |
| `test_parse_query_deep_nested_json_loads_recursionerror_not_500`(**9⑥ 完全没提**) | **PASSED(静默空过!)** | ⚠️ **真正的静默实例,修正 9 没发现** |

**为什么 9⑥ 点名那条不静默**:它有第二条断言 `assert r.json()["assumptions"] == ["单基因敲低"]`
—— 必然拦下退化值 `["deterministic keyword parse"]` → 红。

**为什么修正 9 新造的那条真静默**(implementer 实测打印):
```
status: 200 | fallback_used: True | assumptions: ['deterministic keyword parse']
llm_used: False | llm_metadata: {}
→ 三条断言(status==200 / fallback_used is True / assumptions==deterministic)全 True
→ 静默通过,但 json.loads 根本没被执行过
```
**根因**:该条的**期望结果与"没跑"的退化结果完全同形** → **断言集结构上无法区分"修复生效"与
"测试没跑"**。此前只靠那行 stub key 撑着,而其 docstring **对此只字未提**(解释都写在另一条
不需要的测试上)→ **谁将来删掉那行,它就永远静默绿**。

**修正 9⑥ 自身还自相矛盾**:同一节既写"本条**不是简单地红** —— status 仍 200…**静默地不再测**",
又写"实测:…修前**红**(assumptions 落回 deterministic)"。**后者才是对的。** 同样的错句也进了
测试 docstring,且其上一行刚写"→ assumptions 恒 `['deterministic keyword parse']`",**内部即已矛盾**。
两处均已订正(spec 侧保留原文并加 **【已作废的错句】** 标记,遵循本 spec"已作废措辞(勿复活)"
的既有惯例 —— **删掉会毁掉审计痕迹**,故标作废而非物理删除)。

**最讽刺的一点**:修正 9⑥ 末尾那句教训「**"测试在本机绿"不等于"测试在测它声称测的东西"**」
**完全正确**,而且**恰好精准描述了 9⑥ 自己没发现的那条测试**。

#### ② 新增可区分锚点(结构性修法)+ 变异证据

给 `test_parse_query_deep_nested_json_loads_recursionerror_not_500` 加(**置于三条同形断言之前**):
```python
    assert d["llm_metadata"].get("response_hash")   # 证明 LLM 分支真被走过,而非无 key 退化
```
实测依据(implementer 亲跑):**有 key** → `llm_metadata = {'provider':'deepseek', 'model':
'deepseek-chat', 'prompt_hash':'976107cbf0829ee2', 'response_hash':'31851d9adc33c985', …}`
(`response_hash` 与审查者报的值**逐字一致**);**无 key** → `llm_metadata == {}`。
→ 该条**结构上不可能再静默空过**,不再依赖"stub key 那行还在"。

**变异证伪(即该锚点自身的证据)**:抽掉 stub key 行 + 敌对环境 → **加锚点前 PASSED(静默)、
加锚点后 FAILED**(报错 `LLM 分支未被走过(llm_metadata={})`);加回 stub key → **绿**。

#### ③ 新判据(**比修正 9⑥ 那句教训更可操作**;与修正 9③ 的"①论域全覆盖 ∧ ②每分支行为满足"并列)

> **问:"这条测试的期望结果,和'它根本没跑'的退化结果,能区分吗?"**
> **不能区分 → 它就是环境依赖的静默空壳**,必须补一个**只有真跑过才可能成立**的锚点
> (如 `response_hash`、真实副作用、真实计算产物)。

**与 C3「永真空壳」教训的关系**:C3 那次是**断言在任何输入下恒真**;本次是**断言在"没跑"时恒真**
—— **同一失效族的另一支**,且更隐蔽(它在"跑了"时也真的有区分力,只在退化路径上塌掉)。
**保留修正 9⑥ 那句正确的教训**:"测试在本机绿" ≠ "测试在测它声称测的东西"。

#### ④ 陈旧计数订正(Minor)+ **同型第 2 处(review 未点,implementer 一并扫)**

`_norm` docstring 写"把实现的 `.upper()` 变异成 `.lower()` → 本文件**红 6 条**" —— **陈旧计数**
(Task 3 新增用例后,implementer 亲跑变异实测为 **红 8 条**)。

**同型缺口第 2 处**:**文件级 docstring 里同样写着"红 6 条"**(review 只点了 `_norm` 那处)。
**两处均已改为不钉死数字**("本文件多条红"),避免每次加用例都制造新的陈旧计数 —— 照 C3 教训 #2
「同型缺口未回填」一并回填。

#### ⑤ 本轮未动实现代码(约束核对)

本轮只改**测试断言 + 文档**。Task 1 白名单 / Task 2 边界 try / Task 3 的 7 处 + `:206` 的
`RecursionError` **逐字未动**(`git diff` 对 `run_virtualcell_query.py` 实现部分为空 —— 变异实验
后已干净恢复并验证)。

### 修正 11(末轮 —— RecursionError 同型缺口回填 5 处 + Task 4 收尾 + `:205` 过时表述更新)

用户拍板修。理由 = **C3 教训 #2「同型缺口未回填」**(safety_contract 抄 llm_router 时修了漏洞却
没回填原件)—— 我们**现在已经知道**,不修就是明知故犯;成本 5 个词。

#### ① 机械枚举(**implementer 实跑,命令与输出如下 —— 照修正 5 的要求:声称机械枚举 ≠ 真跑了 predicate**)

```
$ grep -rnE 'json\.loads\((res\["content"\]|res\.get\("content"\)|content|raw_content)\)' \
       praxis_virtualcell/ praxis_vc_api/ praxis_vc_web/ --include="*.py" | grep -v "/tests/"
praxis_virtualcell/workflows/run_virtualcell_query.py:184:      cand = json.loads(content)
praxis_virtualcell/agents_llm/llm_input_interpreter.py:38:      d = json.loads(res["content"])
praxis_virtualcell/agents_llm/llm_router.py:36:                 d = json.loads(res["content"])
praxis_virtualcell/agents_llm/llm_critic.py:33:                 d = json.loads(res["content"])
praxis_virtualcell/llm_orchestration/cross_module_reasoner.py:39: d = json.loads(res["content"])
praxis_virtualcell/llm_orchestration/safety_contract.py:55:     d = json.loads(raw_content)
```
6 处 `json.loads` 消费 LLM 响应 + `validate_candidate` 的 `json.dumps(:136)`/边界 try(`:75`)
= **清单 7 处**。修前状态(实跑 `grep -n "except (" <各文件>`):`:75` 与 `:206` 已含
`RecursionError`(Task 2 / 修正 9),**其余 5 处全缺**。

> **枚举的上游是 50 个 `json.loads`/`json.dumps` 原始命中**(实跑
> `grep -rnE 'json\.(loads|dumps)\('`),其中十几处读本地数据集(predictors/*、
> governance/*、io/job_store 等)—— **"哪些算未受信 LLM JSON"是语义判断**,
> **层1 无机械判据**(此处 predicate 用 `res["content"]|content|raw_content` 作代理,
> **它本身是启发式、不是判据**)。

#### ② 回填的 5 处 + 可达性(照本单元纪律限定作用域,implementer 亲验)

| 位置 | 可达性(实证) |
|---|---|
| `agents_llm/llm_critic.py:43` | 经 `core/runtime.py:44` `agent.handle(...)` —— **该处无 try/except**(亲验) |
| `agents_llm/llm_router.py:52` | 同上 |
| `llm_orchestration/cross_module_reasoner.py:48` | 同上(runtime 同步 `_dispatch_collect`) |
| `llm_orchestration/safety_contract.py:64` | 经 `module_planner:50` 传入 LLM 响应 |
| `agents_llm/llm_input_interpreter.py:53` | **可达性最弱**,见下 |

- 经 `POST /api/jobs`:端点**有** `except Exception`(`praxis_vc_api/main.py:60`)→ 降级 **400**
  (非 500)。**小瑕疵记录不修**:原始异常文本经 `detail=str(e)` 泄漏给调用方。
- 经 **CLI**:`cli.py` **全文无任何 try/except**(实跑 `grep -nE "try:|except" cli.py` **零输出**)
  → **直接崩 Python traceback 给用户**。
- 5 处均同受 `max_tokens` **默认值** 1024 的"当前生产不可达"论证覆盖(**是函数默认参数、
  可被调用点覆盖,不是硬编码**)。

**⚠️ 订正一处措辞(implementer 亲验后不同意原表述)**:控制器称 `llm_input_interpreter`
"**当前未接入任何生产入口**…**近似死码**"。**结论对,机制描述不准**:该 agent **确被注册进
生产 runtime**(`workflows/predict_delta_expression.py:55`)、**也确由生产代码
`core/runtime.py:269` 派发** → **不是"未接入的死码"**。准确说法:**通往它的唯一方法
`runtime.run_workflow_from_text` 当前无任何生产调用点**(实跑 grep:仅
`test_llm_e2e_demo.py`、`test_t10_6_llm_guard.py` 调用;无 API route、无 CLI 子命令)
→ **当前无生产入口可达**。

#### ③ 测试:**5 处全测**(控制器要求"至少 2 处",但 5 处均低成本 → 不取下限)

`_critic_notes` / `_xmod_notes` / `_route_suggestion` 三个 helper 本已存在(Task 3 建),
`safety_contract` 是纯函数,`llm_input_interpreter` 照 `test_t10_6:295` 既有模式 →
**5 处各一条,无一"难以低成本测试"** → **不存在"如实说明未测"的项**。

TDD:5 条**全红**(实际报错 `RecursionError` at `json/decoder.py:361`,穿透 `handle()`)→
补 `RecursionError` → **5 条全绿** → **逐处变异**(**5 个文件各单独去掉 `RecursionError`**)
→ **每处对应测试各自红**(5/5)→ 全部恢复 → 复绿。**每条测试都被证明是承重的。**

#### ④ `:205` 过时表述已更新(**"诚实的不确定" → "已知而未更新" 的防线**)

原注释:「是否还有第三处未捕,**层1 无机械判据**」—— 那是当时诚实的不确定标注,
**现在答案已确定**(机械枚举出 7 处清单)。不更新它就从"诚实的不确定"**变质成"已知而未更新"**。

**更新后的表述纪律(第 11 次就在这里等着,已守)**:
- ✅ 只写:"经**机械枚举** `json.loads`/`json.dumps` 消费未受信 LLM JSON 的调用点
  (命令+输出见修正 11①),**当前清单 7 处已全部捕获 `RecursionError`**"。
- ❌ **不得**写 "`/api/parse` / 全仓对 RecursionError 已全覆盖"。
- **层1 仍无机械判据**("哪些算未受信 LLM JSON"是语义判断;predicate 是启发式代理)
  → **残余风险照旧标注**。

#### ⑤ Task 4 两条 e2e(implementer 自己重跑,非采信预期)

**A `test_e2e_offline_deterministic_byte_equivalence`** —— 红线 §6.4:OFFLINE 同请求三跑
**字节等价**、`llm_used_for_prediction` **恒 False**、`mode=='offline'`。**全部复现通过**。
定性限定:是"**同版本多跑一致**",**非跨版本不变**。
**本条不需要可区分锚点**(照修正 10③ 自问):它走 OFFLINE、不涉 LLM 分支,不存在"没跑就
退化成同形"的塌缩 —— "跑"即确定性 runtime,无退化路径。

**B `test_e2e_provenance_contract_no_invented_gene_reaches_frontend`** —— LLM 返
`[None,"AHR"]`(自然错误)→ `/api/parse` → **200**,前端收到 `['AHR']`,`'NONE'` **不在其中**。

**🔴 B 的静默空壳排查(照修正 10③ 判据,实测坐实控制器的预警)**:
自问"期望结果和'它根本没跑'的退化结果,能区分吗?" → **实测:不能** ——
`_deterministic_parse("human AHR 敲低")` 正则抓出的 targets **恰好也是 `['AHR']`**(亲跑打印),
故无 key 退化时 status 仍 200、targets 仍 `['AHR']`、`'NONE'` 仍不在其中 →
**三条断言全为真而 LLM 分支一次没走**。

**修法 + 三段式证据(比修正 10② 更完整)**:
1. 加 `setenv` stub key(自足)+ **两重锚点**:`llm_metadata.response_hash`(无 key 时
   `llm_metadata == {}`)与 `llm_used is True`,**置于三条同形断言之前**。
2. **变异 a**(抽掉 stub key、**留**锚点)→ **FAILED**(`LLM 分支未被走过(llm_metadata={})`)。
3. **变异 b**(抽掉 stub key **且**抽掉锚点)→ **PASSED(静默绿!)** ←
   **这一步才真正证明"锚点是唯一在挡的东西"**,而非"stub key 恰好在"。恢复后复绿。

#### ⑥ 本轮红线核对

Task 1 白名单 / Task 2 边界 try(`:75`)/ Task 3 的 7 处元素级白名单 / `:206` **均未动**
(`:205` 只改**注释文本**,`except` 元组逐字未变)。核心内核(`core/message.py`/`bus.py`/
`agent.py`)+ 根 `tests/` + `agents/reliability.py`/`critic.py` **零触碰**。

### 修正 12(opus final review —— **第六次复发活在 HEAD 上** + "根治"作废 + 判据 A 补两条适用条件)

#### ① 🔴 `praxis_vc_web/app.py:66` —— 第五次复发的失效模式**原封不动活着**(已修)

`rvq:223` 的 `"candidate_request": v["normalized"] or {**cand, ...}` 在 `schema_valid=False`
时返回**未归一、未白名单化的原始 LLM dict**;消费者 `app.py:66` 直接
`",".join(cand.get("perturbation_targets", []))`。

**implementer 在 HEAD 上独立复现(未采信转述)**:

| LLM 返回 | 实测结果 | 危害 |
|---|---|---|
| `"AHR"`(**C3 认定的"自然错误"**) | join → `'A,H,R'` → 回填 `['A','H','R']` → 用户确认 → **`validate_candidate` 返 schema_valid=True、targets=`['A','H','R']`** | **第五次复发,原封不动;内核真按假基因 A/H/R 跑** |
| `{"g":"AHR"}`(targets **本身**是 dict) | `','.join({'g':'AHR'})` → `'g'` | **发明** —— 溯源契约得名的那类危害 |
| `[{"g":"AHR"}]` / `[1,2]` | `TypeError: sequence item 0: expected str instance, dict found` | Streamlit 异常页 |

**这是 C4 的失职(opus 原话,implementer 认同)**:`rvq:57-59` 与测试边界 try 那条 docstring
**明确点名分析了 `app.py`**,甚至白纸黑字写出"schema_valid=False 时是未经归一的原始 LLM JSON",
然后**只问了"key 是不是 str"**就下结论"**结论不变**"。**值从没被问过。**
与 **C2 漏 `MLBackedPredictor`**、**C3 漏 `cross_module_reasoner`** 是**同一形状**:
**消费点只枚举了一半,结论却按已结案陈述。**

**可达性(照纪律限定)**:`praxis-vc web` 是 pyproject 挂着的入口(`cli.py:76-80` →
`streamlit run praxis_vc_web/app.py`);需 llm_assisted + schema_valid=False。**非 C4 引入**
(v0.6 既存)。**不在 .53 部署栈上**(那是 FastAPI+React)。故 **Important 非 Critical**。

**React 侧为何没事 = 纯属走运,不是设计**(implementer 用 node 实跑 `readStr` 复核):
`readStr` 用 `String(v)` 而非 `join` → `"AHR"` → `"AHR"` → split → `['AHR']` **安全**。
**但 React 并非全身而退**:实测 `[{g:'AHR'}]` → `String(v)` → `"[object Object]"` →
`['[object Object]']` —— **仍是发明,只是可见**。→ **记录为残余风险,本轮不修**
(`praxis_vc_react/` 是前端 WIP,红线禁碰)。

#### ② 修法决策:**(a) 消费侧修** —— 但**opus 建议的具体写法有缺陷,已订正为两层**

**🔴 opus 建议的 (a)「`app.py:66` 加 `isinstance(t, str)` 过滤」修不好主危害**(implementer 实跑):
```python
[t for t in "AHR" if isinstance(t, str)] == ['A','H','R']   # ← 字符拆照样发生
```
**拆出来的字符本身就是 str** → **元素级 isinstance 对字符拆毫无防护**。这正是本文件 docstring
与**修正 9③ 判据②**早已记录的事实(字符拆只能由**容器级** `isinstance(value, list)` 挡)。
→ 必须**两层**:容器级挡字符拆 + 元素级挡 dict/None/int。

**为什么选 (a) 不选 (b)(产出侧白名单化)** —— implementer 的理由:
1. **(b) 摧毁 False 分支的设计目的**:该分支存在就是为了把 LLM 原样返回的东西给用户看、让用户
   补充/修正(spec §2.4)。白名单化后 `"AHR"` → `[]`,用户**反而丢失**"LLM 其实答了 AHR"这一
   信息,只能重打 —— **信息丢失,UX 更差**。
2. **(b) 只治一个字段,却给人"根治"的错觉**:False 分支返的 `{**cand, ...}` 里
   `species`/`cell_type`/`perturbation_type` **全是原始值**。要真"产出侧根治"就得把整个 dict
   白名单化 = 让 False 分支等同 True 分支 → **等于删掉该设计**,远超末轮范围。
3. **末轮改契约无复审预算**,风险不对称。
4. **(a) 的"只修一个消费者"缺点是真实的** → 用**共享守卫 + 契约测试**补(见 ③),
   拿到 (b) 的主要收益(可复用、不各自重写)而不改契约。

#### ③ 实现:**共享**消费侧守卫 `coerce_str_list`(而非 app.py 内联)

新增 `rvq::coerce_str_list(value) -> list[str]`(**纯增函数,不动 Task 1/2/3 与 7 处回填**),
`app.py` 导入使用(`app.py` 本就 import 自 rvq,无新依赖方向)。
**为什么做成共享函数**:直接回应 (a) 的缺点 —— **未来第三个消费者复用它,而不是各自重写**
(C3 教训 #2「同型缺口未回填」的预防)。

**测试(真实覆盖,非"抄一份表达式来测"的假覆盖)**:
- `test_coerce_str_list_two_layer_guard`(7 参数化):5 类畸形 → `[]`、部分畸形保留合法、
  合法零回归。
- `test_coerce_str_list_kills_char_split_that_element_guard_alone_cannot`:**直接钉死"为什么
  必须两层"**,防未来有人"简化"成单层。
- `test_parse_query_false_branch_returns_raw_uncoerced_contract`:**契约测试** ——
  钉住"False 分支返原始未归一 dict"是**设计而非疏漏**,并写明**守卫责任在消费侧**;
  带**可区分锚点**(`response_hash`,照修正 10③)防静默空壳。
- **变异证伪**:把 `coerce_str_list` 退化成**单层元素级**(即 opus 建议的写法)→ **5 条红**
  (含字符拆那条)→ 恢复 → 9 条复绿。**证明测试抓得住 opus 那版缺陷。**

**诚实边界**:`app.py` 是 Streamlit 顶层脚本(import 即执行 `st.*`)→ **其第 66 行本身未被
直接测试覆盖**。**implementer 有意不写"抄一份 join 表达式"的测试** —— 那正是
**safety_contract 抄 llm_router** 的失效模式(测试绿而真实那行腐烂)。改为:
**被调用的 `coerce_str_list` 有真实覆盖** + `app.py:66` 注释指向契约测试。
**残余**:若未来有人把 `app.py:66` 改回直接 `join`,测试**抓不到** —— 如实记录。

#### ④ 🔴 第 11 次过度声称:**"根治"**,就住在 commit 标题里

- `a8c7f97`:「…+ **根治第五次复发**」 · `388a261`:「…+ **根治发明假基因名**」

**未限定作用域的全称词**,从未收窄到 `validate_candidate`,被 ① 的复现**直接证伪**。
**最讽刺(opus 原话)**:`7301b37` 正文写着"**表述纪律(第 11 次已守)**" ——
**纪律施加于 docstring 和 spec,却从没回头扫自己的 commit 标题。第 11 次就住在那儿。**
commit 已提交、不 amend → **在此作废该措辞**:
> **"根治" 加入已作废措辞黑名单。** 正确写法:"修复 `validate_candidate` 这一处的字符拆",
> **不得**写"根治第五次复发"(论域=全仓消费未受信 LLM 值的代码点,**无机械枚举**)。

#### ⑤ 判据 A 补两条适用条件(opus 要求;**A 本来就能抓到 ④,只是从没被施于自己的散文**)

原判据 A(修正 9③):全称成立 ⟺ ①论域全覆盖 ∧ ②每个分支的行为各自满足该性质。
**补**:
1. **① 要求论域可机械枚举**;论域是**语义判断**(层1)时 ① **永远无法兑现** → 全称就不能提。
   *施于"发明假基因名已根治":论域 = 全仓消费未受信 LLM 值的代码点 → 无机械枚举 → ① 不成立
   → 全称不可声称。* **A 与层1 自洽且有效。**
2. **A 必须施于 prose**(**commit 标题** / 台账 / paper / 报告),**不止代码分支** ——
   本单元漏的就是这一步。

#### ⑥ 🔴 "层1 无机械判据"**是否变成免罪符 —— 是,已经开始了**(opus 最重的一句)

它被写了 4+ 次,但在本单元里它被用来**关闭**一个分析(`app.py` 的 key),而不是**打开**一个。
Task 3 质量审那句"**标注风险 ≠ 枚举风险**"又应验了一次:风险标注了,而标注里**唯一点名的
那个消费者从没被逐字段枚举**。

**立规矩(写进 §10,收官文档须照此执行)**:
> **prose 里一旦点名某消费者,就必须对它做「字段 × 行」的枚举,不能只问"key 是不是 str"。**

**本轮已照此执行**(implementer 实跑 `grep -nE 'cand\.get\(|cand\[|p\["|p\.get\('
praxis_vc_web/app.py`),app.py 从 cand 读的**全部 4 个字段 × 行**及逐一裁定:

| 字段 × 行 | 消费方式 | 裁定(**带证据**) |
|---|---|---|
| `perturbation_targets` `:64-66` | `",".join(...)` —— **迭代** | 🔴 **高危**:字符拆(静默)/ 发明 / TypeError → **已修** |
| `species` `:61` | `st.text_input(label, value)` | 低:Streamlit 源码实证 `value = str(value) if value is not None else None` → dict 渲染成**可见垃圾**、非静默、非崩溃 → 用户能看见并改 |
| `cell_type` `:62` | 同上(`or ""`) | 同上 |
| `perturbation_type` `:63` | 同上 | 同上 |
| (`assumptions` `:70` 来自 `p` 非 `cand`) | `"; ".join(...)` | 安全:**Task 3 已在 `parse_query` 侧白名单化为 `list[str]`** |

→ **只有 `join` 那处需修**(其余经 `str()` cast,危害形状不同)—— 这是**枚举后的裁定**,
不是"只看了一眼"。

#### ⑦ Minor 处理

1. **修正 3 引用路径笔误**:`brains/virtualcell/human/model_applicability.yaml:13` →
   应为 **`praxis_virtualcell/brains/virtualcell/human/model_applicability.yaml:13`**
   (行号与内容都对,纯前缀)。**照 §10 append-only 惯例在此订正,不回改修正 3 原文。**
2. **敌对环境数字 238 vs 239 —— 双方都对,是口径差**(implementer 复跑核对):
   **phase10 单跑 = 238**(opus 口径);**phase10 + 泄漏探针 = 239**(implementer 口径,
   探针是 scratchpad 里的外部文件,+1)。**非错误,但报数须显式标口径**。
   本轮新增测试后:**247**(不带探针)/ **248**(带探针)。

### 修正 13(末件 —— **破例新增 §0 摘要区块** + 重钉基线锚定方式)

#### ① 破例决策(控制器拍板;implementer 提议并采纳其两点改进)

**破了什么**:此前的铁约束是"**§1–§9 逐字节不动**",且用**行数口径**基线
(`sed -n '1,316p' | shasum = e858d81d328e`)守护。本次**新增 §0**,位置在
**前言块之后、§1 之前** → §1–§9 **文字逐字节未动**,但**行号后移** → 旧行数口径基线失效。

**为什么值得破**:§10 已 ~750 行 / 13 条 append-only,且**作废链 7+ 条**
("绝不"/"硬编码"/"可达"/"自产 normalized 拷贝"/"三种判据合计覆盖四类"/"一条断言覆盖四类"/
9⑥/"根治")→ **paper 作者引到已作废句的概率接近 1**。
**§0 是纯新增区块、不改任何历史文字 → 审计价值几乎不损**;两害相权,后者风险远大于前者代价。

**implementer 的两点改进(控制器照单全收)**:
1. **§0 置于文首而非塞进 §8** —— §8 在中间,**读者是从头读的**,放文首才拦得住"读到 §4.2
   就以为那是结论";且 §8 自身**已被 §10 修正过**,塞进去会产生新的自指混乱。
2. **黑名单必须带「正确写法」列** —— 否则作者知道不能写"根治",但会**换个同义全称词**,
   而那正是本单元 12 次复发的**同一形状**。

#### ② 新基线锚定方式(**换成内容区间,不再用行数**)

**问题**:行数口径 `sed -n '1,N p'` **对任何前置插入都会失效** —— 本次 §0 就把它打破了;
以后若再加 §-1 / 扉页 / 目录,还会再失效一次。

**新锚(portable,BSD/GNU 通用)** —— 锚"**§1 起、§10 前止**"这个**内容区间**:
```bash
F=docs/superpowers/specs/2026-07-15-phase10c4-untrusted-json-whitelist-design.md
awk '/^## 10\. 执行期修正/{exit} /^## 1\. 目标与背景$/{f=1} f' "$F" | shasum | cut -c1-12
# → e7fa122290f4   ← §1–§9 的新基线
```
**该锚对"在 §1 之前插入任意区块"免疫**(§0 / 未来的目录页都不影响它),
**只对 §1–§9 本身的文字改动敏感** —— 正是我们要守的那个不变量。

#### ③ 新旧基线的对应关系(**可复核,非口说**)

在 **commit `e02677e`(§0 插入前的最后一个 commit)** 上,**新旧两锚同时成立**:

| 锚 | 口径 | 在 `e02677e` 上的值 | §0 插入后 |
|---|---|---|---|
| **旧** | `sed -n '1,316p'`(行数) | **`e858d81d328e`** | **按设计失效**(实测变为 `57d6be3d5fe3` —— §0 挤占行号) |
| **新** | `awk` §1→§10 前(内容区间) | **`e7fa122290f4`** | **`e7fa122290f4` 不变** ✅ |

→ `e02677e` 即**新旧口径的对应锚点**:任何人可 checkout 该 commit 同时复算两值,
从而把 `e858d81d328e` 时代的审计链**接续**到 `e7fa122290f4` 时代。
**旧基线 `e858d81d328e` 自本修正起作废**(仅作历史对应用),**以后一律用 `e7fa122290f4`**。

#### ④ §0 的内容边界(防止 §0 自己变成下一个被过读的对象)

- §0 **明标"本节是摘要、非原始记录"**,并写明:§1–§9 是**已被证伪多处**的原始设计、
  §10 是 **append-only 审计轨迹(逐条读会读到已作废措辞)**、**冲突时以 §0 为准**。
- §0 **不引入任何新主张** —— 每条都是 §10 已确立事实的**转述 + 指路**,
  且**每条带最硬的那个证据**(端到端 HTTP 码 / 变异红数 / 实测值)。
- §0 含:0.1 定位 · 0.2 当前真相(带证据)· **0.3 可直接引用的表述** ·
  **0.4 ❌ 不得声称清单** · **0.5 已作废措辞黑名单(带「正确写法」列)** ·
  **0.6 判据 A/B + 适用条件** · **0.7 残余风险** · **0.8 新规矩**。
- **§0 不是 append-only** —— 它是"当前状态"面,**后续发现应直接改写 §0**
  (审计轨迹由 §10 承担)。这是 §0 与 §10 的**分工**,不得混淆。

#### ⑤ 本轮红线核对

**未动任何实现代码**(本轮只改 spec)。§1–§9 **逐字节未动**(新锚 `e7fa122290f4` 前后一致)。
§10 **纯 append**。前端 WIP 未碰。
