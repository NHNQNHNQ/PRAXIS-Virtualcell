"""P10.C4 未受信 LLM JSON 白名单化 + 溯源契约 测试。

本文件的判据是**输出侧**的 —— 不枚举输入侧畸形类型。理由:输入侧枚举是无底递归
(入口→字段→畸形类型→后果类型),C3 Task 7 照"双层机械枚举"教训做了
11 字段 × 6 畸形 = 66 组合,仍漏了层3(6 种畸形全是容器级、无一元素级)与层4
(判据只有"崩溃/字符拆"、没有"零发明")。溯源契约只问"输出有没有凭空多出东西",
故一条断言同时覆盖字符拆/发明/嵌套/崩溃四类后果。

诚实边界(收官文档/paper 引用须照此表述):
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
    """声明的归一化(与 validate_candidate 的 strip + gene/ligand 大写一致)。"""
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
