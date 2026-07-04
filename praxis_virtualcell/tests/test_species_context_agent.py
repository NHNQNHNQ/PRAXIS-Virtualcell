"""Phase 3:SpeciesContextAgent(插点 A)—— 进 bus,读 module_support.yaml 判物种每模块可用度。
铁律:未声明的模块 → unsupported/reject(不静默 accept);bacteria M3 显示名映射 energy/redox。"""
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _ask(species):
    return AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context",
        payload={"request": {"species": species, "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]}},
        timestamp="t1")


def _run(species):
    bus = MessageBus()
    SpeciesContextAgent().handle(_ask(species), bus)
    return bus.latest("species_context_ready").payload


def test_emits_ready_with_all_eight_modules():
    p = _run("human")
    assert p["species"] == "human"
    assert set(p["module_support"]) == set(M.MODULE_ORDER)   # 8 模块全覆盖


def test_human_genetic_hub_is_strong_accept():
    p = _run("human")
    gh = p["module_support"]["genetic_hub"]
    assert gh["support"] == "strong"
    assert gh["verdict"] == "accept"


def test_bacteria_m3_display_name_maps_to_energy_redox():
    """铁律(决策 E):bacteria 不叫线粒体,M3 显示 Energy/redox。"""
    p = _run("bacteria")
    m3 = p["module_support"]["mitochondrial_energy_metabolism"]
    assert "redox" in m3["display_name"].lower() or "energy" in m3["display_name"].lower()


def test_bacteria_genetic_hub_is_weak_caution():
    p = _run("bacteria")
    gh = p["module_support"]["genetic_hub"]
    assert gh["support"] == "weak"
    assert gh["verdict"] == "caution"       # weak → caution(不 accept)


def test_bus_message_structure():
    bus = MessageBus()
    SpeciesContextAgent().handle(_ask("yeast"), bus)
    res = bus.latest("species_context_ready")
    assert res.sender == "SpeciesContextAgent"
    assert res.message_type == "species_context_ready"
    assert set(res.payload) >= {"species", "module_support", "mismatch_queries"}


def test_mismatch_queries_surfaced_for_bacteria():
    """bacteria module_support 声明的 biological_mismatch(自噬/线粒体)要被暴露供 router 用。"""
    p = _run("bacteria")
    mq = p["mismatch_queries"]
    assert "bacteria_autophagy" in mq
    assert mq["bacteria_autophagy"] == "caution"
