"""species agent:brain 五键 schema、缺 brain 降级、经 bus retrieve-before-predict。"""
from pathlib import Path

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen
from praxis_virtualcell.core.message import AgentMessage
import praxis_virtualcell.mdr_gnb.agents as species_agents
from praxis_virtualcell.mdr_gnb.agents.brain_loader import load_species_brain
from praxis_virtualcell.mdr_gnb.agents.escherichia_coli.agent import EColiAgent

_BRAIN_ROOT = Path(species_agents.__file__).resolve().parent


def test_brain_schema_five_keys():
    brain = load_species_brain(_BRAIN_ROOT / "escherichia_coli" / "brain")
    for key in ("rules", "resistance_mechanisms", "negative_cases",
                "assay_boundaries", "species_specific_breakpoints"):
        assert key in brain, f"缺 brain 键:{key}"
    assert brain["species_specific_breakpoints"]  # 至少一个折点


def test_missing_brain_dir_degrades_not_crash():
    brain = load_species_brain(Path("/nonexistent/brain"))
    assert brain["rules"] == [] and brain["species_specific_breakpoints"] == {}


def test_species_agent_retrieves_before_emitting():
    bus = MessageBus()
    clock, idg = Clock(), IdGen()
    agent = EColiAgent(brain_root=_BRAIN_ROOT, clock=clock, idgen=idg)
    task = AgentMessage(idg.next(), "Coordinator", "EColiAgent", "mdr_task",
                        {"request": {"species": "escherichia_coli",
                                     "amr_profile": {"blaCTX-M-15": True},
                                     "drug": "ceftriaxone"}},
                        clock.now())
    agent.handle(task, bus)
    types = [m.message_type for m in bus.trace]
    assert "brain_retrieved" in types
    out = bus.latest("brain_retrieved")
    assert out.payload["brain_context"]["species"] == "escherichia_coli"
    assert out.payload["brain_context"]["rules_referenced"]  # provenance 非空
