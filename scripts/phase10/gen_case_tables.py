from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"


def main() -> int:
    bundles = json.loads((_OUT / "trace_bundle.json").read_text(encoding="utf-8"))

    cases_md = [
        "# Offline end-to-end case matrix",
        "",
        "> Eight single-module and eight cross-module requests executed by run_query; records are in trace_bundle.json.",
        "> Assertions are in praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py.",
        "> M1, M5, and M8 provide advisory routing entries rather than numerical predictions; M6 has a pipeline limitation.",
        "> X8 exposes routing/engine divergence; the X6 C1 gate is inactive for this input. Real GEARS requires an explicitly configured backend.",
        "",
        "| case | type | abstain | prediction | primary | secondary |",
        "|---|---|---|---|---|---|",
    ]
    for b in bundles:
        mp = b["module_plan"] or {}
        typ = "single-module" if b["case"].startswith("S") else "cross-module"
        cases_md.append(
            f"| {b['case']} | {typ} | {b['abstain']} | {b['prediction']} | "
            f"{mp.get('primary', 'None')} | {mp.get('secondary', [])} |"
        )
    (_OUT / "PHASE10_CASES.md").write_text("\n".join(cases_md) + "\n", encoding="utf-8")

    neg = [b for b in bundles if b["abstain"] is True]
    fail_md = [
        "# Negative cases and abstention",
        "",
        f"> Among the 16 end-to-end cases, {len(neg)} abstain; see trace_bundle.json.",
        "> Additional negative fixtures cover schema, routing, provenance, and injection behavior.",
        "> See phase10 tests T10.4, T10.5, T10.6, and test_negative_cases.py.",
        "",
        "| case | inferred abstention reason | models_rejected | module_plan |",
        "|---|---|---|---|",
    ]
    for b in neg:
        mp = b["module_plan"]
        mps = "None(unroutable)" if mp is None else f"{mp.get('primary')} overall={mp.get('overall_verdict')}"
        fail_md.append(f"| {b['case']} | prediction None | {b['models_rejected']} | {mps} |")
    (_OUT / "PHASE10_FAILURES.md").write_text("\n".join(fail_md) + "\n", encoding="utf-8")
    print(f"[gen_case_tables] wrote PHASE10_CASES.md ({len(bundles)}) + PHASE10_FAILURES.md ({len(neg)} abstain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
