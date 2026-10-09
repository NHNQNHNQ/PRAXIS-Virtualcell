"""Deterministic narrative gate applied only when report['abstain'] is True. Narrative floats must match report
numbers rounded to 2 places, and text must include a broad abstention cue. Nonabstaining narratives are
unchecked. Versions, percentages, and range formatting are partly excluded; section labels such as 1.1 can still
collide. Numeric membership does not verify contextual attribution, and integer fabrication is not detected. Cue
presence is lexical rather than semantic and can miss misleading conclusions. Violations discard narrative only,
never prediction/reliability/abstention decisions.
"""

from __future__ import annotations

import re

_FLOAT_RE = re.compile(r"(?<![vV])(?<![\d.])-?\d+\.\d+(?!%)")
_ABSTAIN_WORDS = (
    "abstained",
    "abstain",
    "unable",
    "insufficient",
    "failed",
    "withheld",
    "rejected",
    "judgment reserved",
    "not provided",
)
_ROUND = 2


def _collect_numbers(obj, out: set) -> None:
    """Recursively collect report int/float values rounded with _ROUND, explicitly excluding bool so abstain=True
    does not supply 1.0. Skip narrative to avoid self-attribution. Callers should convert NumPy scalars to
    native floats.
    """
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
    """Return narrative violations only for abstained reports. Nondictionary reports, nonstring/blank narratives,
    and nonabstaining reports return an empty list; the gate retains the documented lexical and numeric
    limitations.
    """
    if not isinstance(report, dict) or not isinstance(narrative, str) or not narrative.strip():
        return []
    if report.get("abstain") is not True:
        return []
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
