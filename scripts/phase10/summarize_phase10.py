from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from praxis_virtualcell.biological_modules.modules import MODULE_ORDER

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"


_MODULE_STATUS = {
    "membrane_system": "Rule-based advisory; out-of-vocabulary genes request abstention",
    "genetic_hub": "Local mock donor or explicitly configured GEARS backend",
    "mitochondrial_energy_metabolism": "GEM FBA/pathway scoring as a growth or flux secondary module",
    "cytoplasmic_metabolism": "Cobra FBA and pathway scoring",
    "biosynthetic_network": "Rule-based advisory",
    "cytoskeletal_framework": "Spatial niche pipeline limitation",
    "stress_processor": "Restricted IFN-beta state scoring or drug embedding",
    "degradation_machinery": "Rule-based advisory and species mismatch checks",
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
        "# Offline evaluation summary",
        "",
        "> Generated from JUnit records. These counts do not establish model performance.",
        "",
        "| Suite | tests | failures | errors | skipped |",
        "|---|---|---|---|---|",
        f"| not llm | {not_llm['tests']} | {not_llm['failures']} | {not_llm['errors']} | {not_llm['skipped']} |",
        f"| all marked suites | {full['tests']} | {full['failures']} | {full['errors']} | {full['skipped']} |",
        "",
        "Counts cover praxis_virtualcell/tests. Passed = tests - skipped - failures - errors.",
        "",
        "## Module limits",
        "",
        "| Module | Evaluation scope |",
        "|---|---|",
    ]
    for mid in MODULE_ORDER:
        code = mid if isinstance(mid, str) else mid.get("code", str(mid))
        lines.append(f"| `{code}` | {_MODULE_STATUS.get(code, 'Undefined')} |")
    lines.extend(
        [
            "",
            "Advisory routing entries are not numerical predictors. Real GEARS requires configured artifacts.",
            "See PHASE10_TRACE_AUDIT.md and the phase10 tests for case-level evidence and limitations.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "PHASE10_SUMMARY.md").write_text(_summary_md(), encoding="utf-8")
    print(f"[summarize] wrote {_OUT / 'PHASE10_SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
