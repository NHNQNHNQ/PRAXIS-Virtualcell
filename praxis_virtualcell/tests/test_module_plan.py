"""Phase 3:ModulePlan 数据结构 —— module-aware 路由产物 + Phase 4 输入契约。
测:白名单校验、verdict 保守合成、overall_verdict 取最保守、to_dict 序列化、mismatch 降级。"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.module_plan import (
    ModulePlan,
    ModulePlanEntry,
    synthesize_verdict,
)


def _entry(**over):
    base = dict(
        module="genetic_hub", display_name="Genetic Hub", role="primary",
        engine="donor_predictor", route_disposition="accept",
        species_support="strong", species_verdict="accept",
        caution_flags=[], data_gated=False, pillars=["dynamic_states"],
        available_models=["donor_predictor"], reason="human_native_scrna_predictor",
        mismatch=None,
    )
    base.update(over)
    return ModulePlanEntry(**base)


def test_synthesize_verdict_takes_more_conservative():
    # accept + caution → caution;caption + downgrade → downgrade;任意 + reject → reject
    assert synthesize_verdict("accept", "caution", None) == "caution"
    assert synthesize_verdict("caution", "downgrade", None) == "downgrade"
    assert synthesize_verdict("accept", "accept", None) == "accept"
    assert synthesize_verdict("accept", "accept", "reject") == "reject"     # mismatch 降级
    assert synthesize_verdict("caution", "accept", "caution") == "caution"


def test_entry_verdict_synthesized_on_init():
    e = _entry(route_disposition="caution", species_verdict="accept")
    assert e.verdict == "caution"          # 取更保守


def test_entry_rejects_illegal_module():
    with pytest.raises(ValueError):
        _entry(module="not_a_module")


def test_entry_rejects_illegal_engine():
    with pytest.raises(ValueError):
        _entry(engine="not_an_engine")


def test_plan_overall_verdict_is_most_conservative():
    prim = _entry(module="genetic_hub", role="primary", verdict=None,
                  route_disposition="accept", species_verdict="accept")
    sec = _entry(module="stress_processor", display_name="Stress Processor", role="secondary",
                 engine="state_scoring", route_disposition="downgrade",
                 species_support="medium", species_verdict="accept",
                 pillars=["dynamic_states"], available_models=["state_scoring"],
                 reason="x")
    plan = ModulePlan(species="human", request={"species": "human"},
                      primary="genetic_hub", secondary=["stress_processor"],
                      entries=[prim, sec], notes=[])
    assert plan.overall_verdict == "downgrade"     # 最保守


def test_plan_to_dict_roundtrip_keys():
    plan = ModulePlan(species="human", request={"species": "human"},
                      primary="genetic_hub", secondary=[], entries=[_entry()], notes=[])
    d = plan.to_dict()
    assert d["primary"] == "genetic_hub"
    assert d["overall_verdict"] in ("accept", "caution", "downgrade", "abstain", "reject")
    assert d["entries"][0]["module"] == "genetic_hub"
    assert set(d["entries"][0]) >= {
        "module", "role", "engine", "route_disposition", "species_verdict",
        "verdict", "caution_flags", "pillars", "reason", "mismatch"}


def test_primary_must_be_in_entries():
    with pytest.raises(ValueError):
        ModulePlan(species="human", request={}, primary="membrane_system",
                   secondary=[], entries=[_entry(module="genetic_hub")], notes=[])
