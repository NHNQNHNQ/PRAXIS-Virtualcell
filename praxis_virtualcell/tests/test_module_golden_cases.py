"""Tests for module golden cases."""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_DIR = Path(__file__).parent / "module_golden_cases"


def _load():
    cases = []
    for f in sorted(_DIR.glob("*.yaml")):
        if f.name.startswith("._"):
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load()


def _plan_for(request):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]}, timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


def test_case_count():
    assert len(_CASES) >= 60, f"Too few module golden cases ({len(_CASES)}); at least 60 are required"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_module_plan_matches(case):
    p = _plan_for(case["input"])
    exp = case["expect"]
    assert p["primary"] == exp["primary"], \
        f"{case['case_id']}: primary {p['primary']} != {exp['primary']}"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == exp["engine"], \
        f"{case['case_id']}: engine {prim['engine']} != {exp['engine']}"
    assert p["overall_verdict"] == exp["overall_verdict"], \
        f"{case['case_id']}: overall {p['overall_verdict']} != {exp['overall_verdict']}"
    if "primary_verdict" in exp:
        assert prim["verdict"] == exp["primary_verdict"], \
            f"{case['case_id']}: primary_verdict {prim['verdict']} != {exp['primary_verdict']}"


def test_no_unsafe_accept():
    """Verify no unsafe accept."""
    unsafe = [c["case_id"] for c in _CASES
              if c["expect"]["overall_verdict"] != "accept"
              and _plan_for(c["input"])["overall_verdict"] == "accept"]
    assert unsafe == [], f"module unsafe accept: {unsafe}"
