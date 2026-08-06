"""组装 offline runtime + 跑一个 request。"""
from __future__ import annotations

from praxis_virtualcell.active_learning.active_learning_agent import ActiveLearningAgent
from praxis_virtualcell.agents.critic import CriticAgent
from praxis_virtualcell.agents.ensemble import EnsembleCoordinatorAgent
from praxis_virtualcell.agents.evidence_level_agent import EvidenceLevelAgent
from praxis_virtualcell.agents.input_interpreter import InputInterpreterAgent
from praxis_virtualcell.agents.model_applicability import LegacyModelApplicabilityAdapter
from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.object_normalizer import BioObjectNormalizerAgent
from praxis_virtualcell.agents.provenance_agent import ProvenanceAgent
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.agents.report import ReportAgent
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, Mode, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.adapter_sdk import AdapterRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import EnvironmentSnapshot
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.predictors.case_runner_agent import CaseRunnerPredictorAgent
from praxis_virtualcell.predictors.mock_cpa import MockCPAAgent
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent
from praxis_virtualcell.predictors.mock_linear import MockLinearAgent


def build_runtime(
    config: RuntimeConfig | None = None,
    *,
    model_registry: ModelZooRegistry | None = None,
    model_cache: ModelCache | None = None,
    pack_registry: PackRegistry | None = None,
    environment: EnvironmentSnapshot | None = None,
    adapter_registry: AdapterRegistry | None = None,
) -> AgentRuntime:
    cfg = config or RuntimeConfig()
    rt = AgentRuntime(cfg, bus=MessageBus(), clock=Clock(), idgen=IdGen())
    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              LegacyModelApplicabilityAdapter(),
              ModelBrokerAgent(
                  registry=model_registry,
                  cache=model_cache,
                  pack_registry=pack_registry,
                  environment=environment,
                  adapter_registry=adapter_registry,
              ),
              MockLinearAgent(), MockCPAAgent(), MockGEARSAgent(),
              CaseRunnerPredictorAgent(),
              EnsembleCoordinatorAgent(adapter_registry=adapter_registry),
              ReliabilityAgent(mode=cfg.reliability_mode), CriticAgent(),
              ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    # Phase 4:module-aware 路由两节点(OFFLINE 也注册 → 产确定性 module_plan,零 LLM)
    for a in (SpeciesContextAgent(), ModuleRouterAgent()):
        rt.register_agent(a)
    # Phase 5:证据等级 + 主动学习两节点(OFFLINE 也注册 → 确定性 advisory 产物挂 provenance,零 LLM)
    for a in (EvidenceLevelAgent(), ActiveLearningAgent()):
        rt.register_agent(a)
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(cfg)
    # Phase 4:仅 orchestrated 模式 + client enabled 才注册 LLM 编排节点(planner + reasoner)
    if client.enabled and cfg.mode in (Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT):
        from praxis_virtualcell.llm_orchestration.cross_module_reasoner import LLMCrossModuleReasoner
        from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner
        rt.register_agent(LLMModulePlanner(client))
        rt.register_agent(LLMCrossModuleReasoner(client))
    if client.enabled:
        from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
        from praxis_virtualcell.agents_llm.llm_input_interpreter import LLMInputInterpreterAgent
        from praxis_virtualcell.agents_llm.llm_report import LLMReportAgent
        from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
        for a in (LLMInputInterpreterAgent(client), LLMRouterAgent(client),
                  LLMCriticAgent(client), LLMReportAgent(client)):
            rt.register_agent(a)
    rt.run_workflow_from_dict = lambda d: rt.run_workflow(VirtualCellRequest.from_dict(d))  # type: ignore[attr-defined]
    return rt


def run_request(request_dict: dict) -> dict:
    rt = build_runtime()
    return rt.run_workflow(VirtualCellRequest.from_dict(request_dict))
