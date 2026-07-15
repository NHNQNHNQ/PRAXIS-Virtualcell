"""P10.C3 LLM 全入口守卫 + narrative 一致性 + 抗注入边界 测试。
narrative gate:确定性窄门(数值出处 + abstain 语义)→ 违规 fail-closed 丢弃 narrative,
绝不碰 abstain/prediction/reliability(LLM 外层问题不得反向改写确定性裁决)。"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.governance.narrative_consistency import check_narrative
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_ACCEPT = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def test_baseline_offline_has_no_narrative_and_no_c3_gate():
    """接线前提坐实:OFFLINE 无 LLMReport → 无 narrative → C3 gate 不进(字节等价保留);
    且无 C3 gate provenance 键。接线后本断言仍须成立(gate 不误伤 offline 主链)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert "narrative" not in sr                 # run_query 的 structured_report 已剔 narrative
    assert "narrative_consistency_gate" not in sr["provenance"]


def test_narrative_numeric_must_come_from_report():
    """判据1(仅 abstain 场景生效):narrative 浮点必须在 report 数值集合有舍入匹配(2 位)。"""
    rep = {"abstain": True, "prediction": {"delta": [0.42, -0.28]}}
    assert check_narrative(rep, "证据不足,系统弃权;若强行给出 delta 为 0.42 与 -0.28。") == []
    v = check_narrative(rep, "证据不足,系统弃权;但 delta 为 9.99。")            # 编造
    assert any("9.99" in x for x in v) and any("numeric_not_in_report" in x for x in v)


def test_narrative_numeric_rounding_tolerance():
    """report 0.4237 与 narrative 0.42 舍入(2 位)匹配 → 不误伤。"""
    rep = {"abstain": True, "prediction": {"delta": [0.4237]}}
    assert check_narrative(rep, "证据不足弃权;delta 约 0.42。") == []


def test_narrative_integers_not_checked_no_false_positive():
    """判据1 只提取浮点:中文里的合法整数(3 个模型)不误伤。"""
    rep = {"abstain": True, "prediction": {"delta": [0.42]}}
    assert check_narrative(rep, "共 3 个模型参与,2 个被拒;证据不足弃权,delta 为 0.42。") == []


def test_narrative_omits_abstain_flagged():
    """判据2:abstain=True 但 narrative 无弃权语义 → 违规。"""
    rep = {"abstain": True, "prediction": None}
    assert "narrative_omits_abstain" in check_narrative(rep, "模型给出了明确结论。")


def test_narrative_with_abstain_word_passes():
    rep = {"abstain": True, "prediction": None}
    assert check_narrative(rep, "证据不足,系统弃权,未给出预测。") == []


def test_narrative_bool_not_treated_as_number_and_edge_inputs():
    """bool 不当数值收;空/非法输入 → 不误伤返回 []。"""
    rep = {"abstain": True, "prediction": None}
    assert check_narrative(rep, "") == []                    # 空 narrative 不校验
    assert check_narrative(rep, "   ") == []
    assert check_narrative("not_a_dict", "x") == []          # 非 dict report
    assert check_narrative(rep, None) == []                  # 非 str narrative
    # bool 不产数值出处:report 里只有 abstain=True 这个 bool,narrative 写 1.0 应判违规
    assert any("1.0" in x for x in check_narrative({"abstain": True}, "值为 1.0,系统弃权。"))


def test_narrative_version_and_percent_not_flagged():
    """C1:版本号 v1.2 / 百分比 12.5% 与预测值格式相同 → 正则须排除,不产幽灵违规。"""
    rep = {"abstain": True, "prediction": None}
    assert check_narrative(rep, "模型 v1.2 未能给出预测,系统弃权。") == []
    assert check_narrative(rep, "置信度 12.5% 不足,弃权。") == []


def test_narrative_range_hyphen_not_parsed_as_negative():
    """C2:区间 "0.28-0.42" 的连字符不得被 `-?` 吞成负号(旧实现产幽灵 -0.42 违规)。"""
    rep = {"abstain": True, "model_disagreement": {"low": 0.28, "high": 0.42}}
    v = check_narrative(rep, "分歧区间 0.28-0.42,证据不足弃权。")
    assert not any("-0.42" in x for x in v)                  # 无幽灵负数违规
    assert v == []                                           # 0.28/0.42 均有出处


def test_narrative_int_float_equivalence():
    """I1:report 里的 int 1 与 narrative 的 1.0 须等价(_collect_numbers 收 int)。"""
    rep = {"abstain": True, "prediction": None, "n": 1}
    assert check_narrative(rep, "值 1.0,证据不足弃权。") == []


def test_narrative_non_abstain_not_checked_at_all():
    """收窄边界(用户 2026-07-15 拍板):非 abstain 场景完全不校验数值——
    即使编造 8.88 也不报(自由文本无法可靠区分预测值与版本号/章节号 → 诚实放弃覆盖)。"""
    assert check_narrative({"abstain": False, "prediction": {"delta": [0.42]}},
                           "模型 v9.99 预测 delta 为 8.88。") == []
