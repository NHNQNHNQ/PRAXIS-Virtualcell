"""W1.3(v0.4):case report 7 部分结构 + validator + routing-prototype 构造器。

7 部分是每个 v0.4 case 的质量铁律,缺任一 → CaseReportError(把"必须真实分析"变成可执行门)。
routing_case 从原始请求构建 routing-prototype case:此类 case 的分析输出 = 治理路由行为本身,
7 部分由 species_schema 归一 + route_table 路由**真实**填充(非 mock)。需要真跑工具的数值预测
(GEM 生长、药物 signature)由后续步骤扩展,boundary 里诚实标注 pending / data-gated。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from praxis_virtualcell.agents.route_table import RouteDecision, route
from praxis_virtualcell.agents.species_schema import normalize_request

_REQUIRED = ("structured_input", "object_normalization", "models_tools_selected",
             "raw_output", "baseline_comparison", "reliability_decision", "provenance_boundary")


class CaseReportError(ValueError):
    """case report 缺/空 7 部分中的任一。"""


@dataclass
class CaseReport:
    case_id: str
    structured_input: dict = field(default_factory=dict)
    object_normalization: dict = field(default_factory=dict)
    models_tools_selected: dict = field(default_factory=dict)
    raw_output: dict = field(default_factory=dict)
    baseline_comparison: dict = field(default_factory=dict)
    reliability_decision: dict = field(default_factory=dict)
    provenance_boundary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def validate_case_report(report) -> None:
    """7 部分齐全且非空,否则抛 CaseReportError。"""
    d = report.to_dict() if isinstance(report, CaseReport) else dict(report)
    for k in _REQUIRED:
        if not d.get(k):                       # None / "" / {} / [] 均视为缺
            raise CaseReportError(f"case report 缺/空字段: {k}")


def _boundary(dec: RouteDecision) -> str:
    """据路由决策生成诚实的边界声明(不过度解释)。"""
    if dec.engine == "gem_fba" and not dec.data_gated:
        return ("routing verified: 路由到机制模型 gem_fba;生长/flux 数值预测 pending"
                "(由 W2 GEM 真跑补充),本 case 仅验证路由正确,不声称生长数值。")
    if dec.data_gated:
        return "data-gated: 下游数据/模型未就位,当前仅路由级证据,不可作性能结论。"
    if dec.caution_flags:
        return ("cross-species 迁移带 caution(如 ortholog),预测需降级解读,"
                "不可当母种原生精度。")
    if dec.disposition == "abstain":
        return "abstain:无适用引擎,系统正确弃权(治理有效),不产出预测。"
    return "human 原生路由;数值精度以 core benchmark(表 A)为准。"


def routing_case(case_id: str, raw_req: dict) -> CaseReport:
    """从原始请求构建 routing-prototype case(7 部分真实填充)。"""
    norm = normalize_request(raw_req)
    dec = route(norm)
    return CaseReport(
        case_id=case_id,
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "normalized_targets": norm["perturbation_targets"],
            "target_output": norm["target_output"],
        },
        models_tools_selected={"engine": dec.engine, "reason": dec.reason},
        raw_output={"route_decision": dec.to_dict()},
        baseline_comparison={
            "ungoverned": "直接调用哺乳类 predictor 且无适用性检查(可能对不适用物种硬出预测)",
            "governed": f"engine={dec.engine} · disposition={dec.disposition} · reason={dec.reason}",
        },
        reliability_decision={
            "disposition": dec.disposition,
            "caution_flags": list(dec.caution_flags),
            "data_gated": dec.data_gated,
        },
        provenance_boundary={"rules_hit": [dec.reason], "boundary": _boundary(dec)},
    )
