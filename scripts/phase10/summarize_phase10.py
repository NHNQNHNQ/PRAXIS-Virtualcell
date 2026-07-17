"""Phase 10 SUMMARY 生成 —— 实跑 junitxml 取数 + MODULE_ORDER,禁誊抄台账。

数据源:reports/phase10/junit-*.xml(Task 5 产)+ biological_modules/modules.py::MODULE_ORDER。
**口径纪律**:所有测试数须来自实跑 junitxml,显式标口径(not-llm 稳定基线 vs 裸口径);
禁止从 UPGRADE-PROGRESS 誊抄(858 是误记孤例)。
**诚实纪律(spec §8)**:8 模块状态须带 advisory(M1/M5/M8)/remote(M2)/limitation(M6/emt/fate)
限定词,不得写"8/8 真实模型"。
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from praxis_virtualcell.biological_modules.modules import MODULE_ORDER

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"

# 8 模块真实覆盖状态(源:UPGRADE-PROGRESS 定论 + spec §2.2 实测,非誊抄数字,是能力定性)
_MODULE_STATUS = {
    "membrane_system": "rule-based advisory(B4;基因集 OOV→请求 abstain,断 module_plan advisory entry)",
    "genetic_hub": "引擎级:mock donor(本地)/ 真实 GEARS(仅 .53,gears_available 门控)",
    "mitochondrial_energy_metabolism": "引擎级 gem_fba/pathway_scoring;**从不 primary**,只作 growth/flux secondary",
    "cytoplasmic_metabolism": "引擎级真实 cobra FBA(gem_fba)+ pathway_scoring",
    "biosynthetic_network": "rule-based advisory(B4)",
    "cytoskeletal_framework": "诚实 limitation:spatial_niche 管线不可达(引擎级另有真值)",
    "stress_processor": "引擎级真实 state_scoring(IFN-β)/ embedding(drug),窄门",
    "degradation_machinery": "rule-based advisory(B4)+ 物种 mismatch 治理",
}


def _parse_junit(path: Path) -> dict:
    if not path.exists():
        return {"tests": "N/A", "failures": "N/A", "skipped": "N/A", "errors": "N/A"}
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return {k: suite.get(k, "0") for k in ("tests", "failures", "skipped", "errors")}


def _summary_md() -> str:
    not_llm = _parse_junit(_OUT / "junit-not-llm.xml")
    full = _parse_junit(_OUT / "junit-full.xml")
    lines = [
        "# PHASE 10 SUMMARY",
        "",
        "> 本文件由 `scripts/phase10/summarize_phase10.py` 实跑 junitxml 生成,**禁誊抄台账数字**。",
        "> **完整能力边界、门槛对账、收窄项以 spec §0/§2.3/§8 为准**——本文件只做实测计数汇总。",
        "",
        "## 1. 测试计数(实跑 junitxml,显式标口径)",
        "",
        "| 口径 | tests | failures | errors | skipped | 说明 |",
        "|---|---|---|---|---|---|",
        f"| `-m \"not llm\"` 稳定基线(**完成门槛权威口径**) | {not_llm['tests']} | {not_llm['failures']} | {not_llm['errors']} | {not_llm['skipped']} | 9 条 llm deselect |",
        f"| 裸口径(含 9 条 `@pytest.mark.llm` 真实网络) | {full['tests']} | {full['failures']} | {full['errors']} | {full['skipped']} | 网络挂时 llm FAIL 不 skip→看退出码给假红 |",
        "",
        "> **口径为 `praxis_virtualcell` 包**(`pytest praxis_virtualcell/tests`,不含整仓根 `tests/`;",
        "> 整仓根 `tests/` 是 praxis2 子项目,有既有测试隔离性 failed,不属本单元口径,故不并入)。",
        "> 表中 `tests` 为 junit 总数(含 skipped),故 **passed = tests − skipped − failures − errors**(本口径 failures=errors=0,故等于 tests − skipped)。",
        "",
        "## 2. 8 模块覆盖状态(诚实限定,**非 8/8 真实模型**)",
        "",
        "| 模块 | 覆盖状态 |",
        "|---|---|",
    ]
    for mid in MODULE_ORDER:
        code = mid if isinstance(mid, str) else mid.get("code", str(mid))
        lines.append(f"| `{code}` | {_MODULE_STATUS.get(code, '(未定义)')} |")
    lines += [
        "",
        "> **真实引擎级覆盖仅 4 族**:M2(.53)/M3/M4/M7。M1/M5/M8=rule-based advisory;",
        "> M6/emt/fate/spatial/communication=诚实 limitation。这不是 SOTA 预测模型,是**代码治理操作层**。",
        "",
        "## 3. 门槛对账 + 失败与修复叙事",
        "",
        "> **门槛 13 指标对账 + C1-C4 失败→修复叙事以 spec §2.3 + UPGRADE-PROGRESS 事件日志为准**",
        "> (含 C4 的 11 次过度声称、2 个新挖 500)。收窄项(conflict detection / LLM unsupported claim=0)",
        "> **绝不打绿**——见 spec §8。",
        "",
        "## 4. UI e2e / 16-case 明细",
        "",
        "> UI 段依赖 D-B(前端 playwright,延后);16-case 明细见 `PHASE10_TRACE_AUDIT.md` 与",
        "> `test_t10_3_end_to_end_cases.py`。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "PHASE10_SUMMARY.md").write_text(_summary_md(), encoding="utf-8")
    print(f"[summarize] wrote {_OUT / 'PHASE10_SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
