"""P10.C4 未受信 LLM JSON 白名单化 + 溯源契约 测试。

本文件的判据是**输出侧**的 —— 不枚举输入侧畸形类型。理由:输入侧枚举是无底递归
(入口→字段→畸形类型→后果类型),C3 Task 7 照"双层机械枚举"教训做了
11 字段 × 6 畸形 = 66 组合,仍漏了层3(6 种畸形全是容器级、无一元素级)与层4
(判据只有"崩溃/字符拆"、没有"零发明")。溯源契约只问"输出有没有凭空多出东西"。

**覆盖主张(经两轮代码质量审逐类变异实证订正 —— 收官文档/paper 须照此表述)**:

> 本单元三处收紧中,**溯源契约贡献「发明」「嵌套」两类、值白名单贡献「崩溃」一类、
> 类型过滤不对应这四类中任何一类**(独立加固)。第四类「字符拆」由 **C3 既有容器级守卫**
> 覆盖,本单元的溯源契约仅对其提供**回归防护**,非新覆盖。

逐类归属(按贡献直说,**不用"三种判据合计覆盖四类"这种凑数量的表述**):

| 后果 | 谁覆盖的 | 是本单元判据吗 | 变异实证 |
|---|---|---|---|
| 发明(`[None,'AHR']`→`'NONE'`) | **溯源契约** | ✅ 本单元新增 | 删 isinstance 守卫 → 红 |
| 嵌套(`[['AHR']]`→`"['AHR']"`) | **溯源契约** | ✅ 本单元新增 | 删 isinstance 守卫 → 红 |
| 崩溃(`o in ALLOWED_OUTPUTS`) | **值白名单**(机制不同) | ✅ 本单元新增 | targets 路径**根本不会崩**(`str()`/`isinstance()` 对 JSON 可产生的全部元素类型均不抛) |
| 字符拆(`"AHR"`→`['A','H','R']`) | **C3 既有的容器级 `isinstance(targets, list)`** | ❌ **非本单元贡献**,契约仅提供回归防护 | 同变异 → **仍绿**(C3 守卫先返 `[]` → fail-closed);反向变异(只删 C3 容器守卫、留元素级)→ 字符拆**红** → 证实元素级 `isinstance(t,str)` 对字符拆毫无防护(拆出的字符本身就是 str) |

**类型过滤(assumptions)对这四类贡献 0 类**(实测:修复前 `list(x)` 元素**原样透传、不经
`str()`** → 无发明;不字符串化 → 非嵌套;`metadata.assumptions` 无 `in set` 消费点 → 不崩;
容器守卫 C3 已有 → 非字符拆)。它是**正当的纵深加固**(防非 str 元素进 metadata),
**但不属四类中任何一类,不得算进"覆盖四类"的分子**。

**已作废的两处措辞**(勿复活):①"一条断言覆盖四类";②"三种判据合计覆盖四类"——
后者仍是 conflate:表自己的归属列只有 3 行落在本单元三处收紧内,第 4 行(字符拆)
落在三者之外。③"崩溃:契约求值前先抛 TypeError → 红"——只在"任何未捕获异常都会让
任何 pytest 测试红"这个**平凡意义**上成立,**不是 ⊆ 契约本身的性质**。

诚实边界(收官文档/paper 引用须照此表述):
- **溯源契约仅适用 `perturbation_targets`**(有溯源语义的字段);`requested_outputs` 是
  **值白名单**(输出 ⊆ ALLOWED_OUTPUTS,更强)、`assumptions` 是**类型过滤**(元素恒 str)
  —— 三者判据不同,**不得统称"溯源契约"**。
- **⊆ 是单向的(不对称)**:`got ⊆ src` **只禁"多出"(发明)、不禁"少掉"(丢真数据)** ——
  丢掉部分合法元素仍恒 PASS,且 `∅ ⊆ src` 恒真(全丢亦 PASS)。**paper 引用溯源契约时
  须同时说明它是单向的。** "不丢真数据"由另两条从反侧覆盖:
  `test_targets_no_silent_partial_loss`(3+ 合法混畸形,**精确相等**)+
  `test_targets_all_elements_malformed_fails_closed`(全丢 → fail-closed)。
- **静默丢弃无信号(已知残余风险)**:部分元素被丢弃时,调用方/前端**收不到任何信号**
  (与"用户本来就传得少"无法区分)。这是"部分丢弃"设计(跟随 llm_router 先例)的已知代价。
- **契约相对于「声明的归一化」而言,不校验归一化规则本身是否无损(盲区)**:`src` 是**用
  `_norm` 定义的**,所以任何**本身就在损毁数据的归一化**都在盲区 —— 实测:实现改成
  `t.strip().upper()[:3]`、`_norm` 同步改 → `'TP53'`→`'TP5'`(数据已损毁)**照样 PASS**。
  下方 `_norm` docstring 记的 `.upper()`→`.lower()` 变异只证伪了**单侧漂移**(实现改、
  oracle 没改 → 红 6 条,证明 `_norm` 是独立 oracle),**挡不住协同修改**。
  **paper 若写"溯源契约保证 target 可溯源",读者会过读成"保证归一化无损" → 必须一并披露。**
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
    """声明的归一化(与 validate_candidate 的 strip + gene/ligand 大写一致)。

    **scope 限制(诚实标注)**:硬编码 `.strip().upper()` 只对应实现的
    `gene`/`gene_combination`/`ligand` 分支;本文件全部用例均为 `perturbation_type: "gene"`,
    **`drug` 分支(归一为小写)本文件未覆盖**。
    非同义反复(审查者实测证伪该风险):把实现的 `.upper()` 变异成 `.lower()` → 本文件红 6 条
    → `_norm` 是**独立 oracle**,不是跟着实现走的空壳。
    """
    return s.strip().upper()


# 已知畸形全集(勘察实测):含 C3 修过的字符拆与本单元的活 bug。
# 注意:本清单是**证据留档**(证明修复对已知实例有效),**不是判据来源** ——
# 判据是下面的溯源契约(输出侧),不依赖本清单穷尽输入侧畸形。
_TARGETS_CASES = [
    ("C3 字符拆:LLM 单基因返标量(自然错误,非对抗构造)", "AHR"),
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

    **本契约新覆盖的后果 = 发明 + 嵌套两类**(变异实证:删 isinstance 守卫则该两类红):
    - 发明:'NONE' 不溯源自 None → ⊄ {'AHR'} → 红
    - 嵌套:"['AHR']" 不溯源自 ['AHR'](那是 list 不是 str)→ ⊄ ∅ → 红

    **不属本契约贡献**(见文件 docstring 归属表,不得混为一谈):
    - 字符拆("AHR"):由 **C3 既有的容器级 `isinstance(targets, list)`** 挡住(→ `[]` →
      fail-closed,走下面的早退分支)。本契约"会"抓该处未来回归,但本 task 没修它。
    - 崩溃:targets 路径不会崩;真崩溃在 `requested_outputs`,由值白名单那条覆盖。

    **方向性**:本条只禁"多出",不禁"少掉" —— 见 test_targets_no_silent_partial_loss。
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
    """**main 活 bug**:`o in ALLOWED_OUTPUTS`(set)对 unhashable 元素抛 TypeError。
    生产可达:/api/parse → parse_query → validate_candidate,全链无 try/except,
    且 validate_candidate 在 parse_query 的 try 块**外面** → FastAPI 500。

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
    与 C3 对 "AHR" 的既有语义一致(不静默放行污染数据)。"""
    v = validate_candidate({**_BASE, "perturbation_targets": [["AHR"], {"g": "TP53"}, 123]})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "perturbation_targets" in v["missing_fields"]


def test_targets_partial_malformed_keeps_legit_drops_garbage():
    """**"部分丢弃"语义(设计决策)**:保留合法元素、丢弃畸形元素,而非整体 fail。
    ①满足溯源契约(既不发明 'NONE'、也不丢真数据 'AHR');②与 llm_router 的
    `if a in candidates` 语义完全一致(静默丢弃越界元素、不报错)—— 跟随既有先例。"""
    v = validate_candidate({**_BASE, "perturbation_targets": [None, "AHR", ["x"], 7]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR"]
    assert "NONE" not in v["normalized"]["perturbation_targets"]   # 层4:不发明


def test_targets_no_silent_partial_loss():
    """溯源契约的 ⊆ 只禁"多出"、不禁"少掉" —— 本条从另一侧钉住"不丢真数据"。

    背景(代码质量审指出):`got ⊆ src` 对"丢掉部分合法元素"恒 PASS(`∅ ⊆ src` 亦真);
    全套测试(test_run_virtualcell_query / test_negative_cases / test_t10_6_llm_guard /
    本文件)**无一条 3+ 合法混畸形用例** → 未来"丢一个合法 target"的 bug 会穿过整个测试套件。
    本条用**精确相等**(不多不少、保序)补上这一侧。当前实现是 per-element 独立 filter,
    不丢真数据 —— 本条是**防回归**,非修 bug。
    """
    v = validate_candidate({**_BASE, "perturbation_targets":
                            ["AHR", None, "TP53", ["x"], "MYC", {"g": 1}]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR", "TP53", "MYC"]   # 精确相等


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


def test_boundary_try_non_str_key_returns_invalid_not_raises():
    """**边界 try = public API 契约防线**:validate_candidate 是 public 函数,
    `/api/parse` → parse_query 与 `praxis_vc_web/app.py:75` 两条链路均无 try/except
    → 未捕获异常会成为 FastAPI 500。本层 fail-closed:返回 schema_valid=False 而非抛。

    **定性须精确(§10 修正 7)——"可达"分两种,本条测的是后一种**:
    - **当前两个已知消费点的正常路径不可达**:`parse_query` 的 cand 来自 `json.loads`
      (**JSON object key 恒 str**)或 `_deterministic_parse`(固定 str key);`app.py:75`
      的 cand 是 validate_candidate 自产 normalized dict 的拷贝(key 恒 str)。
      → 本层**不是**当前生产 500 的防线(那个由 Task 1 的元素级白名单管)。
    - **直接调用可达**(实测,故非死码):非 JSON 来源的 dict 含混合类型 key →
      `json.dumps(d, sort_keys=True)` 抛 TypeError: '<' not supported between 'str' and 'int'。

    真实价值 = 防脚本 / notebook / 直接调用 / **未来第 3 个调用点**;对标 **C2 Gate B**
    (防御性完整性断言,正常路径不触发、防未来重构漏挂)。**非空壳但非生产可达** ——
    变异实证:except 改 `except ():` → 本条红(C3 T10.6 的"永真空壳"教训)。
    """
    v = validate_candidate({1: "a", "species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "candidate_malformed" in v["errors"]


def test_boundary_try_does_not_swallow_legit_results():
    """**对照组**:边界 try 不得吞掉正常路径(若 try 把一切都变成 invalid,本条会红)。
    这条防的是"为了不崩而把所有东西都 fail-closed"这种过度防御。

    **已知局限(实测,§10 修正 7)**:本条**挡不住"捕获范围过宽"** —— 把 except 变异成
    `except Exception:`(过度捕获)→ 本条与上条**均仍绿**,因为正常路径本来就不抛异常。
    即:当前两条测试能证明"except 真在捕获"(`except ():` → 上条红),
    **不能证明"except 的捕获范围不过宽"**。
    """
    v = validate_candidate({"species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR"]
