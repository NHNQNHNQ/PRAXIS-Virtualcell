"""Tests for negative cases."""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import SchemaError, normalize_request
from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate

_NEG_DIR = Path(__file__).parent / "negative_cases"


def _load_cases():
    cases = []
    for f in sorted(_NEG_DIR.glob("*.yaml")):
        if f.name.startswith("._"):
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load_cases()


def test_negative_case_count():
    assert len(_CASES) >= 12, f"Too few negative cases ({len(_CASES)}); check the fixture glob"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_negative(case):
    layer, inp, exp = case["layer"], case["input"], case["expect"]
    if layer == "normalize":
        with pytest.raises(SchemaError):
            normalize_request(inp)
    elif layer == "validate":
        v = validate_candidate(inp)
        assert v["schema_valid"] is False, f"{case['case_id']}: expected schema_valid=False"
        if "error_contains" in exp:
            assert any(exp["error_contains"] in e for e in v["errors"]), \
                f"{case['case_id']}: errors {v['errors']} does not contain {exp['error_contains']}"
        if "missing_contains" in exp:
            assert exp["missing_contains"] in v["missing_fields"], \
                f"{case['case_id']}: missing {v['missing_fields']} does not contain {exp['missing_contains']}"
    elif layer == "route":
        dec = route(normalize_request(inp))
        assert dec.disposition == exp["disposition"], \
            f"{case['case_id']}: disposition {dec.disposition} != {exp['disposition']}"
    else:
        pytest.fail(f"{case['case_id']}: Unknown layer={layer}")


def test_negative_never_silently_accepts():
    """Verify negative never silently accepts."""
    offenders = []
    for c in _CASES:
        layer, inp = c["layer"], c["input"]
        if layer == "normalize":
            try:
                normalize_request(inp)
                offenders.append(f"{c['case_id']}(normalize did not reject)")
            except SchemaError:
                pass
        elif layer == "validate":
            if validate_candidate(inp)["schema_valid"] is not False:
                offenders.append(f"{c['case_id']}(validate unexpectedly accepted)")
        elif layer == "route":
            if route(normalize_request(inp)).disposition == "accept":
                offenders.append(f"{c['case_id']}(route unexpectedly accepted)")
    assert offenders == [], f"Silent acceptance violations: {offenders}"
