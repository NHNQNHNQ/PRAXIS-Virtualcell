"""Golden case 固化:声明式路由 golden(纯 route() 断言,无重依赖,零 skip)。
KPI:golden pass 100% + unsafe accept=0。数据在 golden_cases/*.yaml。
铁律:只读断言现有 route 行为;route 输出与期望不符=真实 bug,不改 golden 迁就。"""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

_GOLDEN_DIR = Path(__file__).parent / "golden_cases"


def _load_cases():
    cases = []
    for f in sorted(_GOLDEN_DIR.glob("*.yaml")):
        if f.name.startswith("._"):        # 跳过 macOS AppleDouble 元数据(外置盘会生成)
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load_cases()


def test_case_count():
    assert len(_CASES) >= 16, f"golden 用例过少({len(_CASES)}),疑 glob 落空或数据缺失"


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
    """KPI:凡期望非 accept 的 case,实际不得 accept(不许把该弃权/降级硬报为可信)。"""
    unsafe = [c["case_id"] for c in _CASES
              if c["expect"]["disposition"] != "accept"
              and route(normalize_request(c["input"])).disposition == "accept"]
    assert unsafe == [], f"unsafe accept(应非 accept 却 accept):{unsafe}"
