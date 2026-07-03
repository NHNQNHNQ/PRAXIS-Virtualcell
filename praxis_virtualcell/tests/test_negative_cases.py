"""Negative / fuzz:固化 3 层拒绝路径,守 KPI「无静默 accept」。数据在 negative_cases/*.yaml。
铁律:只读断言现有拒绝行为;若某路径实际不拒绝=真实 gap,停下报告不改测试迁就。"""
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
    assert len(_CASES) >= 12, f"negative 用例过少({len(_CASES)}),疑 glob 落空"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_negative(case):
    layer, inp, exp = case["layer"], case["input"], case["expect"]
    if layer == "normalize":
        with pytest.raises(SchemaError):
            normalize_request(inp)
    elif layer == "validate":
        v = validate_candidate(inp)
        assert v["schema_valid"] is False, f"{case['case_id']}: 应 schema_valid=False"
        if "error_contains" in exp:
            assert any(exp["error_contains"] in e for e in v["errors"]), \
                f"{case['case_id']}: errors {v['errors']} 未含 {exp['error_contains']}"
        if "missing_contains" in exp:
            assert exp["missing_contains"] in v["missing_fields"], \
                f"{case['case_id']}: missing {v['missing_fields']} 未含 {exp['missing_contains']}"
    elif layer == "route":
        dec = route(normalize_request(inp))
        assert dec.disposition == exp["disposition"], \
            f"{case['case_id']}: disposition {dec.disposition} != {exp['disposition']}"
    else:
        pytest.fail(f"{case['case_id']}: 未知 layer={layer}")
