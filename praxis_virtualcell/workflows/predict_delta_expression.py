"""组装 offline runtime + 跑一个 request。"""
from __future__ import annotations

from praxis_virtualcell.agents.critic import CriticAgent
from praxis_virtualcell.agents.ensemble import EnsembleCoordinatorAgent
from praxis_virtualcell.agents.input_interpreter import InputInterpreterAgent
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.object_normalizer import BioObjectNormalizerAgent
from praxis_virtualcell.agents.provenance_agent import ProvenanceAgent
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.agents.report import ReportAgent
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.predictors.mock_cpa import MockCPAAgent
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent
from praxis_virtualcell.predictors.mock_linear import MockLinearAgent


def build_runtime(config: RuntimeConfig | None = None) -> AgentRuntime:
    cfg = config or RuntimeConfig()
    rt = AgentRuntime(cfg, bus=MessageBus(), clock=Clock(), idgen=IdGen())
    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), MockLinearAgent(), MockCPAAgent(), MockGEARSAgent(),
              EnsembleCoordinatorAgent(), ReliabilityAgent(), CriticAgent(),
              ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    rt.run_workflow_from_dict = lambda d: rt.run_workflow(VirtualCellRequest.from_dict(d))  # type: ignore[attr-defined]
    return rt


def run_request(request_dict: dict) -> dict:
    rt = build_runtime()
    return rt.run_workflow(VirtualCellRequest.from_dict(request_dict))
