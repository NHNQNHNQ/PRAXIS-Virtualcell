"""Tests for golden cases."""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

_GOLDEN_DIR = Path(__file__).parent / "golden_cases"


def _load_cases():
    cases = []
    for f in sorted(_GOLDEN_DIR.glob("*.yaml")):
        if f.name.startswith("._"):
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load_cases()


def test_case_count():
    assert len(_CASES) >= 16, f"Too few golden cases ({len(_CASES)}); check the fixture glob and data"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_route_matches(case):
    dec = route(normalize_request(case["input"]))
    exp = case["expect"]
    assert dec.engine == exp["engine"], f"{case['case_id']}: engine {dec.engine} != {exp['engine']}"
    assert dec.disposition == exp["disposition"], \
        f"{case['case_id']}: disposition {dec.disposition} != {exp['disposition']}"
    if "caution_flags" in exp:
        assert set(dec.caution_flags) == set(exp["caution_flags"]), \
            f"{case['case_id']}: caution_flags {dec.caution_flags} != {exp['caution_flags']}"
    if "data_gated" in exp:
        assert dec.data_gated == exp["data_gated"], \
            f"{case['case_id']}: data_gated {dec.data_gated} != {exp['data_gated']}"


def test_no_unsafe_accept():
    """Verify no unsafe accept."""
    unsafe = [c["case_id"] for c in _CASES
              if c["expect"]["disposition"] != "accept"
              and route(normalize_request(c["input"])).disposition == "accept"]
    assert unsafe == [], f"Unsafe accept (accepted despite an expected rejection):{unsafe}"


_WF_CASES = [c for c in _CASES if c.get("workflow") == "offline"]


def test_has_workflow_offline_case():
    assert len(_WF_CASES) >= 1, "At least one offline workflow case must cover the offline reporting pipeline"


@pytest.mark.parametrize("case", _WF_CASES, ids=[c["case_id"] for c in _WF_CASES] or ["_none"])
def test_workflow_offline_report(case):
    """Verify workflow offline report."""
    from praxis_virtualcell.core.config import Mode, RuntimeConfig
    from praxis_virtualcell.io.report_markdown import render_report_md
    from praxis_virtualcell.workflows.run_virtualcell_query import run_query
    cfg = RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)
    out = run_query(case["request"], config=cfg)
    assert out["structured_report"].get("provenance"), "Provenance must not be empty"
    assert isinstance(out["structured_report"].get("abstain"), bool)
    job = {"report": out["structured_report"], "request": case["request"],
           "provenance": out["provenance"], "mode": out["mode"]}
    md = render_report_md(job)
    for sec in ("## 1. Question", "## 5. Governance Verdict", "## 9. Reproducibility"):
        assert sec in md, f"report.md is missing a section: {sec}"
