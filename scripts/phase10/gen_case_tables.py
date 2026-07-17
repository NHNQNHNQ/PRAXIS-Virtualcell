"""③16-case 表 + ④负例 abstain 表 —— 从 trace_bundle.json 派生(实测数据,非手写)。"""
from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"


def main() -> int:
    bundles = json.loads((_OUT / "trace_bundle.json").read_text(encoding="utf-8"))
    # ③ 16-case 表
    cases_md = ["# PHASE 10 — T10.3 端到端 16 CASE 表", "",
                "> 8 单模块(S)+ 8 跨模块(X),`run_query` 驱动,数据源 trace_bundle.json(实测)。",
                "> 断言明细见 `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`。",
                "> **诚实**:M1/M5/M8 是 advisory(断 module_plan entry 非预测);M6 管线 limitation;",
                "> X8 路由声明与引擎背离;X6 C1 gate NO-OP(自然输入不触发)。S2b 真实 GEARS 需 .53(延后)。", "",
                "| case | 类型 | abstain | prediction | primary | secondary |", "|---|---|---|---|---|---|"]
    for b in bundles:
        mp = b["module_plan"] or {}
        typ = "单模块" if b["case"].startswith("S") else "跨模块"
        cases_md.append(f"| {b['case']} | {typ} | {b['abstain']} | {b['prediction']} | "
                        f"{mp.get('primary','None')} | {mp.get('secondary',[])} |")
    (_OUT / "PHASE10_CASES.md").write_text("\n".join(cases_md) + "\n", encoding="utf-8")
    # ④ 负例与 abstain 表(从 bundle 抽 abstain==True 的)
    neg = [b for b in bundles if b["abstain"] is True]
    fail_md = ["# PHASE 10 — 负例与 ABSTAIN 表", "",
               f"> T10.3 16 case 中 {len(neg)} 个诚实 abstain(数据源 trace_bundle.json)。",
               "> 补充负例 corpus(schema/route/provenance gate/注入)见 tests/negative_cases、",
               "> test_t10_4/5/6、test_negative_cases.py —— 见 spec §2.5 数据源清单。", "",
               "| case | abstain_reason(推断) | models_rejected | module_plan |", "|---|---|---|---|"]
    for b in neg:
        mp = b["module_plan"]
        mps = "None(unroutable)" if mp is None else f"{mp.get('primary')} overall={mp.get('overall_verdict')}"
        fail_md.append(f"| {b['case']} | prediction None | {b['models_rejected']} | {mps} |")
    (_OUT / "PHASE10_FAILURES.md").write_text("\n".join(fail_md) + "\n", encoding="utf-8")
    print(f"[gen_case_tables] wrote PHASE10_CASES.md ({len(bundles)}) + PHASE10_FAILURES.md ({len(neg)} abstain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
