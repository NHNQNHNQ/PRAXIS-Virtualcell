"""report 级 provenance 完整性契约(Gate B)。防御性类不变量:现状字段恒由代码构造,
罕触发;作 fail-closed 断言防未来重构漏挂。非'多模块结果比对',非高频缺失检测。

契约仅聚焦 provenance/审计完整性相关键(models_used/models_rejected/reliability/provenance
及 provenance 子键 n_messages/rules_referenced/models_used),非全 report 字段——
abstain/prediction/request_id 等由 ReportAgent 及其它 gate 逻辑保证,不在本契约范围。"""
from __future__ import annotations

_TOP_REQUIRED = ("models_used", "models_rejected", "reliability", "provenance")
_PROV_REQUIRED = ("n_messages", "rules_referenced", "models_used")


def check_report_provenance(report: dict) -> list[str]:
    """返回缺失/非法的必需键清单(空=完整)。顶层键须存在;provenance 须为 dict 且含子键。
    report 本身非 dict(重构漏挂/异常路径)→ fail-closed 返回全部顶层必需键(对齐 Gate A)。"""
    if not isinstance(report, dict):
        return list(_TOP_REQUIRED)
    missing = [k for k in _TOP_REQUIRED if k not in report]
    prov = report.get("provenance")
    if not isinstance(prov, dict):
        if "provenance" not in missing:
            missing.append("provenance")
        return missing
    missing.extend(f"provenance.{k}" for k in _PROV_REQUIRED if k not in prov)
    return missing
