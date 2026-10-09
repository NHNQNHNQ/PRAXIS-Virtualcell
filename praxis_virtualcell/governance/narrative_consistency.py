"""narrative 忠实性窄门校验(P10.C3 gate)。确定性纯函数,零 LLM。

**适用范围(用户 2026-07-15 拍板收窄)**:两判据**仅在 report["abstain"] is True 时生效**——
abstain 是 roadmap§128"把 hypothesis 写成 conclusion"的最危险场景(系统弃权却给结论/数值)。
- 判据1(数值出处):abstain 时 narrative 里的浮点必须在 report 数值集合有舍入匹配(2 位)。
- 判据2(abstain 语义):abstain 时 narrative 必须含弃权语义词(宽白名单)。

**limitation(诚实披露,勿当完整忠实性验证)**:
1. **非 abstain 场景完全不校验**:自由文本无法确定性区分"预测数值"与版本号/章节号/日期
   (实测 v1.2、"1.1 节"、2026.07 与预测值格式相同);宁可放弃覆盖也不误伤丢弃真实 narrative。
2. **abstain 场景仍有残余误伤**:正则已排除 v1.2/百分比/区间连字符,但"1.1 节"这类章节号
   与预测值格式相同仍会被判违规(abstain narrative 较短,残余风险可接受)。
3. **判据1 只验数值"存在于 report",不验数值与叙述语境的对应关系**(扁平数值集合,
   report 字段越多偶然碰撞越可能);整数编造检不出(只提取浮点)。
4. **判据2 是"存在即通过"的字面检测,非语义判断,漏判面实际较宽**:"无法/不足"等高频
   中文 hedge 词会让掩盖性 narrative 通过(如"模型无法排除该结论,因此给出以下明确预测")。
   宽白名单是故意取舍——宁可漏判也不误伤(误伤=丢弃真实 narrative)。
5. 语义级"hypothesis 写成 conclusion"无法确定性检测。
gate 违规只丢 narrative,**绝不碰 abstain/prediction/reliability 裁决字段**。
"""
from __future__ import annotations

import re

# (?<![vV]) 排版本号 v1.2;(?!%) 排百分比 12.5%;(?<![\d.]) 让 "0.28-0.42" 的连字符不被当负号
# (引擎从 0.42 起匹配,抓正的 0.42 而非幽灵 -0.42),而 "delta 为 -0.28"(负号前是空格)仍能抓负数。
_FLOAT_RE = re.compile(r"(?<![vV])(?<![\d.])-?\d+\.\d+(?!%)")
_ABSTAIN_WORDS = ("弃权", "abstain", "无法", "不足", "未能", "不予", "拒绝", "保留判断", "不给出")
_ROUND = 2


def _collect_numbers(obj, out: set) -> None:
    """递归收集 report 里所有数值(int/float,统一 round(float(x), _ROUND))。
    bool 是 int 子类须**显式排除**(abstain=True 不该产生 1.0 出处);
    narrative 键跳过(不拿被校验文本当出处)。
    注:假设调用方已把 numpy 标量转原生 float(同 governance/provenance_hash.py 约定)。"""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(round(float(obj), _ROUND))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k == "narrative":
                continue
            _collect_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_numbers(v, out)


def check_narrative(report, narrative) -> list[str]:
    """返回违规串清单(空=通过)。非 dict report / 非 str / 空白 narrative → []（不误伤）。
    **两判据均仅在 report["abstain"] is True 时生效**(见模块 docstring 的范围与 limitation)。"""
    if not isinstance(report, dict) or not isinstance(narrative, str) or not narrative.strip():
        return []
    if report.get("abstain") is not True:
        return []                     # 收窄:非 abstain 场景不校验(自由文本数值提取不可靠)
    violations: list[str] = []
    report_numbers: set = set()
    _collect_numbers(report, report_numbers)
    for m in _FLOAT_RE.findall(narrative):
        if round(float(m), _ROUND) not in report_numbers:
            violations.append(f"narrative_numeric_not_in_report:{m}")
    low = narrative.lower()
    if not any(w.lower() in low for w in _ABSTAIN_WORDS):
        violations.append("narrative_omits_abstain")
    return sorted(set(violations))
