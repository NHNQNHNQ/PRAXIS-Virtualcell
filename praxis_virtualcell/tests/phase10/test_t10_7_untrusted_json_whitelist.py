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
| 崩溃(`o in ALLOWED_OUTPUTS`) | **值白名单**(机制不同) | ✅ 本单元新增 | targets 路径不崩,详见下文 |
| 字符拆(`"AHR"`→`['A','H','R']`) | **C3 既有容器级守卫** | ❌ 非本单元贡献 | 同变异仍绿,详见下文 |

- 崩溃补充:targets 路径**根本不会崩**(`str()`/`isinstance()` 对 JSON 可产生的
  全部元素类型均不抛)。
- 字符拆补充:同变异 → **仍绿**(C3 守卫先返 `[]` → fail-closed);反向变异
  (只删 C3 容器守卫、留元素级)→ 字符拆**红** → 证实元素级
  `isinstance(t,str)` 对字符拆毫无防护(拆出的字符本身就是 str)。

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
  oracle 没改 → **本文件多条红**,证明 `_norm` 是独立 oracle),**挡不住协同修改**。
  (§10 修正 10④:此处原亦写"红 6 条" —— **同一陈旧计数的第 2 处**,review 只点了 `_norm`
  那处,本轮一并扫;两处均改为不钉死数字。)
  **paper 若写"溯源契约保证 target 可溯源",读者会过读成"保证归一化无损" → 必须一并披露。**
- 本文件**不覆盖"哪些函数消费未受信 LLM JSON"**(层1 无机械判据:`.complete(` 恰漏
  `safety_contract.py`、`json.loads` 混进 20+ 读本地数据集的无关文件)——属残余风险,
  **不得声称"全覆盖"**。
"""
import json

import pytest

from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC

# ⚠️ 类名订正:该 agent 类实际名 LLMCrossModuleReasoner(非 CrossModuleReasonerAgent ——
# 原 task prompt 此处的类名是错的,已用 grep + Read 实测核对,见 llm_orchestration/cross_module_reasoner.py)。
from praxis_virtualcell.llm_orchestration.cross_module_reasoner import LLMCrossModuleReasoner
from praxis_virtualcell.workflows.run_virtualcell_query import (
    ALLOWED_OUTPUTS,
    coerce_str_list,
    parse_query,
    run_query,
    validate_candidate,
)

_BASE = {"species": "human", "perturbation_type": "gene",
         "task_type": "predict_delta_expression"}


def _norm(s: str) -> str:
    """声明的归一化(与 validate_candidate 的 strip + gene/ligand 大写一致)。

    **scope 限制(诚实标注)**:硬编码 `.strip().upper()` 只对应实现的
    `gene`/`gene_combination`/`ligand` 分支;本文件全部用例均为 `perturbation_type: "gene"`,
    **`drug` 分支(归一为小写)本文件未覆盖**。
    非同义反复(审查者实测证伪该风险):把实现的 `.upper()` 变异成 `.lower()`(oracle `_norm`
    不动)→ **本文件多条红**(§10 修正 10④:原写"红 6 条"是**陈旧计数** —— Task 3 新增用例后
    实测为 **8 条**;此处**有意不钉死数字**,以免每次加用例都变成新的陈旧计数)
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
    `/api/parse`、Streamlit 确认页与 `/api/jobs` 都会调用它;`/api/jobs` 还把它作为
    runner/save 前最终复验。函数本身因此生产可达,不能再写“非生产可达”。

    本条的**具体混合 key 形状**仍须单独定性:标准 HTTP JSON object key 恒为 string,
    但脚本/notebook/直接 Python 调用可以构造混合类型 key,使
    `json.dumps(d, sort_keys=True)` 抛 TypeError。测试证明边界对此 fail-closed 且非空壳;
    它不证明该具体形状能穿过 HTTP JSON parser。
    """
    v = validate_candidate({1: "a", "species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "candidate_malformed" in v["errors"]


def test_boundary_try_deep_nested_dict_returns_invalid_not_raises():
    """**RecursionError 缺口**(代码质量审逐类枚举 `json.dumps` 可抛异常时发现,已补):
    深嵌套非循环 dict → `json.dumps(sort_keys=True)` 抛 RecursionError,而它是
    **RuntimeError 子类**(`RecursionError.__mro__` 实测不含 TypeError/AttributeError/
    ValueError)→ 原三元组**捕不到、原样穿透**边界 try。

    可达性(照本单元纪律限定作用域):**直接调用可达**(本测试即是)。LLM parse 路径受
    `max_tokens` 默认值限制,而 `/api/jobs` 已把 validator 接到生产入口;超深 HTTP body
    是否能穿过上游 JSON parser 到达本层未在此证明,故两者均不得外推成笼统的可达/不可达。

    **余量随嵌套形状变化(§10 修正 9⑤),"15x" 只是最好情况**:dict 形状每层 6 字符
    (`{"n":` + `}`)→ 1024 token(粗估 ~3.5 char/token ≈ 3584 字符)约 597 层,对
    ~10000 层阈值余量 **~15x**;但 **list 形状每层仅 2 字符**(`[`+`]`)→ 约 1792 层 →
    余量降到 **~5x**,再叠 BPE 对重复括号的打包,余量继续被吃。且 `{"x": [[[…]]]}`
    这种深 list 嵌在 dict 值里**确实能走到** `json.dumps`。这些余量只解释 LLM 默认输出,
    **不是 `/api/jobs` ingress 的结构保证**,也不是一个稳定常数。

    **20000 层是"远高于阈值"的余量取值,不是阈值本身**:实测本机(CPython 3.13/macOS)
    8000 层**不抛**、10000 层抛 —— 且 3.13 按 **C 栈指针**判定而非 `recursionlimit` 计数
    (故 `sys.getrecursionlimit()==1000` 却需约万层),**阈值随栈大小/版本浮动、非稳定常数**
    → 测试取远超阈值的层数,不钉死具体数字。
    """
    d = cur = {}
    for _ in range(20000):
        cur["n"] = {}
        cur = cur["n"]
    v = validate_candidate({**_BASE, "perturbation_targets": ["AHR"], "deep": d})
    assert v["schema_valid"] is False
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


# ---------------------------------------------------------------------------
# 姊妹 7 处同型缺口:`list(x) if isinstance(x, list) else []` —— 容器守了、元素没守。
# ⚠️ 清单来自**实跑** predicate(7 处),非 spec §2.6 手工挑的 6 处(那条是不实表述)。
# 第 1 处(parse_query 的 assumptions)是**第二个活的生产 500**;其余 6 处只进 provenance。
# ---------------------------------------------------------------------------

_GARBAGE = ["ok_flag", {"evil": 1}, ["nested"], None, 42]      # 1 合法 str + 4 类畸形元素


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
    LLMCrossModuleReasoner(_StubClient(content)).handle(
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


def test_sibling1_parse_query_assumptions_drops_non_str_elements(monkeypatch):
    """**第二个活的生产 500**(端到端实测坐实,非构造):parse_query 里**独立的**
    `list(raw_assumptions)` 元素级无守卫 → 返回 → ParseOut.assumptions: list[str] →
    pydantic 对 dict/list/None/int 四种元素**全抛 ValidationError** → HTTP 500。

    LLM 把 assumption 写成对象是**自然错误**。仅 llm_assisted 可达(OFFLINE 的
    _deterministic_parse 恒产 ["deterministic keyword parse"])。
    ⚠️ 与 Task 1 修的那处**不是同一处** —— Task 1 改的是 validate_candidate 内部的
    assumptions,parse_query 这处独立且不受其保护;包着它的 try 也捕不到
    (list() 不抛,ValidationError 在 return 之后)。
    """
    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "task_type": "predict_delta_expression",
        "assumptions": ["单基因敲低", {"note": "LLM 返了个对象"}, ["nested"], None, 42],
    })))
    out = parse_query("human AHR 敲低", config=RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True))
    assert out["assumptions"] == ["单基因敲低"]          # 畸形元素丢弃、合法保留
    assert all(isinstance(a, str) for a in out["assumptions"])


def test_sibling1_parse_query_assumptions_e2e_api_not_500(monkeypatch):
    """同上,但走**真实生产链路** /api/parse(FastAPI TestClient)—— 修复前 HTTP 500。

    ⚠️ 防泄漏:`runtime_service.config_for()` 内部对 llm_assisted 分支直接
    `os.environ["PRAXIS_VIRTUALCELL_MODE"] = "llm_assisted"`(不经 monkeypatch),
    该进程级副作用会**跨测试残留**、污染同一 pytest session 后面依赖
    RuntimeConfig.from_env() 默认 offline 的用例(phase10/ 在 tests/ 目录序里排在
    test_*.py 前面)。

    **必须用 setenv 而非 delenv(§10 修正 9①,读 pytest 源码 + 实验双证)**:
    `delenv(raising=False)` → `delitem`,`if name not in dic: pass` —— **key 不存在时是
    纯 no-op、不登记 undo 记录**,只有 key 已存在才登记。本仓 `.env` 有
    `PRAXIS_VIRTUALCELL_MODE=offline` 且 conftest 收集期 `load_env()` 用 `setdefault`
    预置了它 → delenv 恰好命中"已存在"分支 → **本地能复原纯属环境侥幸,非 delenv 的保证**;
    实测把 cwd 换到无 `.env` 处(load_env 用相对路径,找不到即 no-op)→ **真泄漏
    `'llm_assisted'`**。`setenv` → `setitem` **无条件**登记 `dic.get(name, notset)`,
    key 之前存不存在都能精确复原。

    **DEEPSEEK_API_KEY 同理须显式置**:`config_for()` 走 `from_env()`,而
    `llm_enabled = (mode in LLM_MODES and bool(key))` —— **无 key 则 llm_enabled=False**
    → 根本不进 LLM 分支、回落 `_deterministic_parse` → assumptions 恒
    `["deterministic keyword parse"]`。显式 setenv 一个 stub key 让本条对环境**自足**
    (stub client 已接管 make_llm_client,不发网络请求)。

    ⚠️ **归属订正(§10 修正 10①)**:修正 9⑥ 原在此处写"**本条**在无 `.env` 的 CI 里
    不是'红',而是静默地不再测它声称要测的 bug" —— **这句是错的,且与它自己下一句
    '实测:修前红'自相矛盾**。**本条是吵闹会红的**:第二条断言
    `assert r.json()["assumptions"] == ["单基因敲低"]` 必然拦下退化值
    `["deterministic keyword parse"]` → 红(敌对环境抽掉 stub key 行实测 **FAILED**)。
    **真正静默的是 `test_parse_query_deep_nested_json_loads_recursionerror_not_500`**
    (修正 9 自己新造的那条,期望结果与退化结果同形 → 实测 **PASSED 静默空过**),
    已在该条补 `llm_metadata.response_hash` 可区分锚点。**"静默"归错对象 = 本单元第 10 次
    过度声称**(形状讽刺:修正 9⑥ 末尾那句正确的教训,恰好精准描述了它自己没发现的那条)。
    """
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")   # setitem 无条件登记 undo
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    from fastapi.testclient import TestClient

    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "task_type": "predict_delta_expression",
        "assumptions": ["单基因敲低", {"note": "LLM 返了个对象"}],
    })))
    from praxis_vc_api.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/parse", json={"text": "human AHR 敲低", "mode": "llm_assisted"})
    assert r.status_code == 200, f"修复前是 500,现应 200;实际 {r.status_code}"
    assert r.json()["assumptions"] == ["单基因敲低"]


def test_parse_query_deep_nested_json_loads_recursionerror_not_500(monkeypatch):
    """**第 3 个潜在 500**(§10 修正 9②):`:184` 的 `cand = json.loads(content)` 与
    Task 2 修前的边界 try 是**同一形状的缺口** —— 它所在的
    `except (json.JSONDecodeError, TypeError, AttributeError)` 同样**不含 RecursionError**
    (RecursionError 是 **RuntimeError 子类**,实测 `__mro__` 不含这三者)→ 深嵌套 JSON →
    **UNCAUGHT RecursionError** → /api/parse 500,且 Task 2 在 validate_candidate 的边界 try
    **根本轮不到执行**(json.loads 程序顺序在先)。

    实测阈值(本机 CPython 3.13/macOS,二分):`json.loads` 约 **9999 层**(list 形状)
    vs `json.dumps` 约万层 —— 且 **loads 在先** → 深到能让 dumps 崩的输入基本都先崩在 loads。
    与 Task 2 同,阈值随栈大小/版本浮动、非稳定常数,故取远超阈值的 20000 层。

    **可达性(照本单元纪律限定作用域)**:与 Task 2 同 —— 因 `llm_client.py` 的
    `max_tokens: int = 1024` 是**函数默认参数**(可被调用点覆盖,**非硬编码、非结构不变量**)
    而当前生产不可达;本条是**直接可达**的防御(stub client 绕过 max_tokens)。

    **修后不得声称"/api/parse 对 RecursionError 无条件安全"** —— 只能说
    **`json.loads`(:184)与 `validate_candidate` 边界(:75)两处已捕 RecursionError**;
    是否还有第三处未捕,**层1 无机械判据**(本单元反复吃到的教训)。

    ⚠️ **本条曾是"环境依赖的静默空壳"(§10 修正 10 —— 本单元第 10 次,且形状极讽刺:
    修正 9⑥ 把"静默"归给了另一条**吵闹会红**的测试,而真正静默的正是本条,是修正 9 自己
    新造的)**:本条的期望结果 = `200 / fallback_used=True / assumptions=deterministic`,
    **与"根本没跑 LLM 分支"的退化结果完全同形** —— 无 `DEEPSEEK_API_KEY` 时
    `llm_enabled=False` → 压根不进 LLM 分支、`json.loads` 一次都没执行,**三条断言照样全
    True → 静默绿**。此前只靠下面那行 stub key 撑着,**谁将来删掉它,本条就永远静默绿**。

    **可区分锚点(结构性修法,不再依赖"那行还在")**:`llm_metadata.response_hash` ——
    实测**有 key**:`{'provider':'deepseek', …, 'response_hash':'31851d9adc33c985', …}`;
    **无 key**:`llm_metadata == {}`。该断言**只有真走过 LLM 分支才可能成立** →
    本条结构上不可能再静默空过。变异证伪:抽掉 stub key 行 → 加锚点前**绿**、加锚点后**红**。

    **判据(§10 修正 10,比"测试在本机绿 ≠ 测试在测它声称测的东西"更可操作)**:
    > **问"这条测试的期望结果,和'它根本没跑'的退化结果,能区分吗?"**
    > 不能区分 → 它就是环境依赖的静默空壳,必须补一个**只有真跑过才成立**的锚点。
    """
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    from fastapi.testclient import TestClient

    deep = "[" * 20000 + "]" * 20000          # json.loads 必抛 RecursionError(远超阈值)
    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(deep))
    from praxis_vc_api.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/parse", json={"text": "human AHR 敲低", "mode": "llm_assisted"})
    assert r.status_code == 200, f"补 RecursionError 前是 500;实际 {r.status_code}"
    d = r.json()
    # **可区分锚点必须在最前**(§10 修正 10):下面三条与"没跑"的退化结果同形、无区分力,
    # 本条断言只有**真走过 LLM 分支**(json.loads 真被执行、response_hash 真被算出)才成立。
    # 无 key 退化时 llm_metadata == {} → 本条红。
    assert d["llm_metadata"].get("response_hash"), (
        f"LLM 分支未被走过(llm_metadata={d['llm_metadata']})—— 本条退化成静默空壳,"
        "json.loads 根本没执行,后面三条断言对'没跑'恒真")
    # fail-closed 落回 _deterministic_parse(与 JSONDecodeError 路径同语义)
    assert d["fallback_used"] is True
    assert d["assumptions"] == ["deterministic keyword parse"]


def test_sibling_critic_notes_flags_drop_non_str_elements():
    """llm_critic.py notes/flags —— 元素级畸形不得原样进 provenance。"""
    out = _critic_notes(json.dumps({"notes": _GARBAGE, "flags": _GARBAGE}))
    assert out["notes"] == ["ok_flag"]
    assert out["flags"] == ["ok_flag"]


def test_sibling_xmod_notes_flags_drop_non_str_elements():
    """cross_module_reasoner.py notes/flags —— 同型(经 core/runtime.py::_dispatch_collect 同步调用)。"""
    out = _xmod_notes(json.dumps({"notes": _GARBAGE, "flags": _GARBAGE}))
    assert out["notes"] == ["ok_flag"]
    assert out["flags"] == ["ok_flag"]


def test_sibling_router_risk_flags_drop_non_str_elements():
    """llm_router.py risk_flags —— 元素级。
    ⚠️ recommended/excluded_agents **不在本 task 范围**:它们已是**值白名单**
    (`if a in candidates`,candidates 是 **list** → `in` 用 `==` 不需 hash),天然安全。"""
    sug = _route_suggestion(json.dumps({"recommended_agents": ["MockPredictor"],
                                        "excluded_agents": [], "reasoning_summary": "x",
                                        "risk_flags": _GARBAGE}))
    assert sug["risk_flags"] == ["ok_flag"]
    assert sug["recommended_agents"] == ["MockPredictor"]      # 值白名单零回归


def test_sibling_safety_contract_risk_flags_drop_non_str_elements():
    """safety_contract.py risk_flags —— 实测修复前 [{'evil':1},['nested'],None] 原样透传。"""
    out = SC.sanitize_llm_plan(
        json.dumps({"selected_modules": ["gene_hub"], "risk_flags": _GARBAGE}),
        ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["ok_flag"]
    assert out["selected_modules"] == ["gene_hub"]             # 零回归


def test_arch_invariant_router_value_whitelist_natively_safe():
    """**架构不变量的文档化**(非回归测试,修复前后都应绿):值白名单对元素级畸形
    **天然安全** —— candidates 是 list → `in` 用 `==` 不需 hash → 畸形元素恒不匹配被丢。
    这是本单元"跟随既有正确先例"的证据之一。"""
    sug = _route_suggestion(json.dumps({"recommended_agents": [["nested"], {"d": 1}, None],
                                        "excluded_agents": [], "reasoning_summary": "",
                                        "risk_flags": []}))
    assert sug["recommended_agents"] == []


def test_arch_invariant_sanitize_llm_plan_fail_closed_on_element_malformed():
    """**架构不变量的文档化**(修复前后都应绿):整段 try 对元素级畸形 fail-closed 保 primary
    —— 且**作者从未枚举过该畸形**(注释只写"非可迭代标量(如 123)")→ except 不需要
    知道畸形长什么样。这是本单元"白名单/fail-closed > 枚举畸形类型"论点的证据。"""
    out = SC.sanitize_llm_plan(json.dumps({"selected_modules": [["gene_hub"]]}),
                               ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["llm_parse_failed"]
    assert out["selected_modules"] == ["gene_hub"]


# ---------------------------------------------------------------------------
# 末轮:RecursionError 同型缺口回填(§10 修正 11)
# 清单来自**实跑**机械枚举(命令与输出见 §10 修正 11),**非手工挑** ——
# 历史执行时:json.loads 消费 LLM 响应 6 处 + validator json.dumps 1 处 = **原 7 处**;
# 当时已修 2 处并回填其余 5 处。2026-07-18 新增 response-safe json.dumps 后,
# 原 LLM JSON 口径登记 8 处;显式 structured user JSON 的 json.loads 独立再 +1。
# ⚠️ 表述纪律:8/8+1 都只是当前 predicate 命中清单;
# **不得**说"/api/parse 或全仓对 RecursionError 已全覆盖" —— **层1(哪些算"未受信 LLM
# JSON")是语义判断、无机械判据**,残余风险照旧。
# ---------------------------------------------------------------------------

_DEEP_JSON = "[" * 20000 + "]" * 20000      # json.loads 必抛 RecursionError(实测阈值约 9999)


def test_backfill_critic_deep_nested_recursionerror_fail_closed():
    """llm_critic.py:43 —— 回填 RecursionError。修复前:RecursionError 穿透 handle()
    → 经 core/runtime.py:44 的 `agent.handle(...)`(**该处无 try/except**,已核实)
    → CLI 直接崩 traceback(`cli.py` 全文无 try/except,grep 零输出实证)/
    `/api/jobs` 降级 400(端点有 except Exception)。"""
    out = _critic_notes(_DEEP_JSON)
    assert out["flags"] == ["llm_parse_failed"]        # fail-closed,与 JSONDecodeError 同语义
    assert out["notes"] == []


def test_backfill_xmod_deep_nested_recursionerror_fail_closed():
    """cross_module_reasoner.py:48 —— 同型回填(经 runtime 同步 _dispatch_collect 调用)。"""
    out = _xmod_notes(_DEEP_JSON)
    assert out["flags"] == ["llm_parse_failed"]
    assert out["notes"] == []


def test_backfill_router_deep_nested_recursionerror_fail_closed():
    """llm_router.py:52 —— 同型回填。"""
    sug = _route_suggestion(_DEEP_JSON)
    assert sug["risk_flags"] == ["llm_parse_failed"]
    assert sug["recommended_agents"] == []             # fail-closed 不放行任何 agent


def test_backfill_safety_contract_deep_nested_recursionerror_fail_closed():
    """safety_contract.py:64 —— 同型回填(纯函数,经 module_planner:50 传入 LLM 响应)。
    fail-closed 语义:保 primary 不丢主模块。"""
    out = SC.sanitize_llm_plan(_DEEP_JSON, ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["llm_parse_failed"]
    assert out["selected_modules"] == ["gene_hub"]     # primary 保底


def test_backfill_input_interpreter_deep_nested_recursionerror_fail_closed():
    """llm_input_interpreter.py:53 —— 五元组(含 InputValidationError/KeyError)仍缺
    RecursionError,同型回填。

    **可达性最弱(照本单元纪律限定作用域,且订正一处措辞)**:该 agent **确实被注册进生产
    runtime**(`workflows/predict_delta_expression.py:55`)、**也确实由生产代码
    `core/runtime.py:269` 派发** —— 故**不是"未接入的死码"**;准确说法是:
    **通往它的唯一方法 `runtime.run_workflow_from_text` 当前无任何生产调用点**
    (实跑 grep:仅 `test_llm_e2e_demo.py` 与 `test_t10_6_llm_guard.py` 调用,
    无 API route、无 CLI 子命令)→ **当前无生产入口可达**,可达性最弱。
    """
    from praxis_virtualcell.agents_llm.llm_input_interpreter import LLMInputInterpreterAgent
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMInputInterpreterAgent(_StubClient(_DEEP_JSON)).handle(
        AgentMessage("m1", "client", "LLMInputInterpreter", "parse_text", {"text": "x"}, "t1"), bus)
    m = bus.latest("llm_input_failed")
    assert m is not None, "RecursionError 未被捕获 → 未走 fail 分支"
    assert "llm_parse_invalid" in m.payload["reason"]


# ---------------------------------------------------------------------------
# Task 4 收尾:把两条已实证的性质固化成 e2e 测试(§10 修正 11)
# ---------------------------------------------------------------------------


def test_e2e_offline_deterministic_byte_equivalence():
    """**红线 §6.4**:OFFLINE 同请求多跑**字节等价**(注意:是"同版本多跑一致",
    **非跨版本不变** —— 不得过读成后者)。

    与本单元的关系:白名单对 `_deterministic_parse` 产物(恒 `list[str]`)**恒等**
    → 本单元三处收紧 + 5 处 RecursionError 回填对 OFFLINE 路径**零行为漂移**。
    本条为**防回归**,非修 bug。

    ⚠️ 本条**不需要**可区分锚点:它走 OFFLINE、根本不涉 LLM 分支,
    `llm_used_for_prediction` 恒 False 是被断言的**目标性质本身**,不存在"没跑就退化"的
    同形塌缩(判据见 §10 修正 10③:问"期望结果与'没跑'的退化结果能区分吗"——
    本条的"跑"就是确定性 runtime,无退化路径)。
    """
    req = {"request_id": "c4-det", "species": "human", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"], "input_modality": "scRNA",
           "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    cfg = RuntimeConfig(mode=Mode.OFFLINE)
    outs = [json.dumps(run_query(dict(req), config=cfg)["structured_report"],
                       sort_keys=True, default=str) for _ in range(3)]
    assert len(set(outs)) == 1, "OFFLINE 同请求三跑不字节等价 → 红线 §6.4 破"
    out = run_query(dict(req), config=cfg)
    assert out["llm_used_for_prediction"] is False      # 恒 False:LLM 不碰预测
    assert out["mode"] == "offline"


def test_e2e_provenance_contract_no_invented_gene_reaches_frontend(monkeypatch):
    """**溯源契约的端到端形态**:LLM 返 `[None, "AHR"]`(**自然错误**,非对抗构造)→
    经 `/api/parse` → 前端**不得**收到发明出来的 `'NONE'`。

    修复前的真实危害:`candidate_request.perturbation_targets = ['NONE', 'AHR']` 且
    `schema_valid=True` → 用户在页面 2 确认后,**内核真按假基因名 NONE 跑**。

    ⚠️ **本条曾会是静默空壳,已排查并加锚点**(照 §10 修正 10③ 的判据自问:
    "期望结果和'它根本没跑'的退化结果,能区分吗?")—— **实测:不能** ——
    `_deterministic_parse("human AHR 敲低")` 正则抓出的 targets **恰好也是 `['AHR']`**
    (亲跑实证),故无 key 退化时:status 仍 200、targets 仍 `['AHR']`、`'NONE'` 仍不在其中
    → **三条断言全为真而 LLM 分支一次没走**。
    → 故必须(a)`setenv` stub key 让本条自足、(b)加**只有真走过 LLM 分支才成立**的锚点
    `llm_metadata.response_hash`(无 key 时 `llm_metadata == {}`)。
    """
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")   # setitem 无条件登记 undo
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    from fastapi.testclient import TestClient

    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene",
        "perturbation_targets": [None, "AHR"],          # LLM 把缺失值写成 null:自然错误
        "task_type": "predict_delta_expression",
    })))
    from praxis_vc_api.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/parse", json={"text": "human AHR 敲低", "mode": "llm_assisted"})
    assert r.status_code == 200, f"实际 {r.status_code}"
    d = r.json()
    # **可区分锚点必须在最前**:无 key 退化时 llm_metadata=={} → 红。
    assert d["llm_metadata"].get("response_hash"), (
        f"LLM 分支未被走过(llm_metadata={d['llm_metadata']})—— 本条退化成静默空壳:"
        "_deterministic_parse 恰好也产 ['AHR'],下面三条断言对'没跑'恒真")
    assert d["llm_used"] is True                        # 第二重锚点:确证走的是 LLM 分支
    targets = d["candidate_request"]["perturbation_targets"]
    assert targets == ["AHR"], f"发明/丢失 target:{targets}"
    assert "NONE" not in targets, "发明了输入里不存在的假基因名 NONE → 溯源契约破"


# ---------------------------------------------------------------------------
# §10 修正 12:第六次复发 —— `praxis_vc_web/app.py:66` 消费 parse_query 的
# validator-invalid 且无 normalized 时的 raw-like candidate(**未做语义归一/值白名单**)字符拆。
#
# ⚠️ **本单元的失职**:rvq:57-59 与本文件边界 try 那条 docstring **明确点名分析了 app.py**,
# 甚至白纸黑字写出“该 validator-invalid 分支保留 raw-like LLM 候选”,然后**只问了"key 是不是
# str"**就下结论"结论不变" —— **值从没被问过**。与 C2 漏 MLBackedPredictor、C3 漏
# cross_module_reasoner 是**同一形状**:消费点只枚举了一半,结论却按已结案陈述。
# → 规矩(§10 修正 12):**prose 里一旦点名某消费者,就必须对它做「字段 × 行」的枚举**。
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected,desc", [
    ("AHR",            [],       "C3 认定的『自然错误』:LLM 单基因返标量 → 修前 'A,H,R' → ['A','H','R']"),
    ({"g": "AHR"},     [],       "targets 本身是 dict → join 迭代 **key** → 'g' → 发明"),
    ([{"g": "AHR"}],   [],       "list 含 dict → join 抛 TypeError → Streamlit 异常页"),
    ([1, 2],           [],       "list 含 int → join 抛 TypeError"),
    (None,             [],       "None"),
    (["AHR", None, 7], ["AHR"],  "部分畸形:保留合法、丢弃畸形(与 llm_router 先例同语义)"),
    (["AHR", "TP53"],  ["AHR", "TP53"], "合法输入零回归"),
])
def test_coerce_str_list_two_layer_guard(raw, expected, desc):
    """`coerce_str_list` = **消费侧共享守卫**(两层:容器级 + 元素级)。

    **两层缺一不可(实测,亦是 opus 建议修法里的缺陷)**:
    - 只加**元素级** `isinstance(t, str)` → `[t for t in "AHR" if isinstance(t,str)]`
      == `['A','H','R']` → **字符拆照样发生**(拆出的字符本身就是 str)。
    - 字符拆只能由**容器级** `isinstance(value, list)` 挡(C3 既有手法)。
    """
    assert coerce_str_list(raw) == expected, desc


def test_coerce_str_list_kills_char_split_that_element_guard_alone_cannot():
    """**钉死"为什么必须两层"**(防未来有人"简化"成单层元素级过滤)。
    本条直接对比两种写法在 `"AHR"` 上的行为差异 —— 单层元素级过滤会退化成字符拆。"""
    naive_element_only = [t for t in "AHR" if isinstance(t, str)]
    assert naive_element_only == ["A", "H", "R"]          # 单层:字符拆(反面教材)
    assert coerce_str_list("AHR") == []                   # 两层:fail-closed
    assert ",".join(coerce_str_list("AHR")) == ""         # app.py:66 的 join 不再拆


def test_parse_query_false_branch_returns_raw_uncoerced_contract(monkeypatch):
    """**契约测试(设计,非疏漏)**:本例让 validator 无 normalized,故 `parse_query` 的
    `candidate_request` 是 response-safe、但**未做语义归一/值白名单**的 raw-like LLM 候选。
    `schema_valid=False` 本身不是分支判据:structured error 可令最终 False 仍携带 normalized。

    **存在理由**:让用户在 UI 上看到"LLM 到底答了什么"并补充/修正(spec §2.4)——
    若在产出侧白名单化,`"AHR"` 会变成 `[]`,用户**反而丢失**"LLM 其实答了 AHR"这一信息。

    **→ 因此守卫的责任在消费侧**:任何消费这种 raw-like 产物的代码(当前:`praxis_vc_web/app.py`;
    未来的第三个消费者同理)**必须自己调 `coerce_str_list`**,不得直接 `join`/迭代。
    本条即为那份契约的**可执行文档** —— 未来读者由此知道这是**设计**而非疏漏。
    """
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene",
        "perturbation_targets": "AHR",              # 自然错误 → 触发 schema_valid=False
        "task_type": "predict_delta_expression",
    })))
    out = parse_query("human AHR 敲低",
                      config=RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True))
    # 可区分锚点(§10 修正 10③):证明真走过 LLM 分支,而非无 key 静默退化
    assert out["llm_metadata"].get("response_hash"), "LLM 分支未被走过 → 本条退化成静默空壳"
    assert out["schema_valid"] is False
    # **契约本体**:本例的 validator-invalid 分支保留 LLM 标量,未做值白名单(这是设计)
    assert out["candidate_request"]["perturbation_targets"] == "AHR"
    # **消费侧守卫是唯一防线**:直接 join 会字符拆,调 coerce_str_list 才安全
    assert ",".join(coerce_str_list(out["candidate_request"]["perturbation_targets"])) == ""
