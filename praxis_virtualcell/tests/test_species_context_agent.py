"""Tests for species context agent."""
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
    assert set(p["module_support"]) == set(M.MODULE_ORDER)


def test_human_genetic_hub_is_strong_accept():
    p = _run("human")
    gh = p["module_support"]["genetic_hub"]
    assert gh["support"] == "strong"
    assert gh["verdict"] == "accept"


def test_bacteria_m3_display_name_maps_to_energy_redox():
    """Verify bacteria m3 display name maps to energy redox."""
    p = _run("bacteria")
    m3 = p["module_support"]["mitochondrial_energy_metabolism"]
    assert "redox" in m3["display_name"].lower() or "energy" in m3["display_name"].lower()


def test_bacteria_genetic_hub_is_weak_caution():
    p = _run("bacteria")
    gh = p["module_support"]["genetic_hub"]
    assert gh["support"] == "weak"
    assert gh["verdict"] == "caution"


def test_bus_message_structure():
    bus = MessageBus()
    SpeciesContextAgent().handle(_ask("yeast"), bus)
    res = bus.latest("species_context_ready")
    assert res.sender == "SpeciesContextAgent"
    assert res.message_type == "species_context_ready"
    assert set(res.payload) >= {"species", "module_support", "mismatch_queries"}


def test_mismatch_queries_surfaced_for_bacteria():
    """Verify mismatch queries surfaced for bacteria."""
    p = _run("bacteria")
    mq = p["mismatch_queries"]
    assert "bacteria_autophagy" in mq
    assert mq["bacteria_autophagy"] == "caution"
