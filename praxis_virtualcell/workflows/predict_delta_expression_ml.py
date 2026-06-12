"""M2:真 ML predictor 版 runtime —— `MLBackedPredictorAgent` 替代 mock,端到端 communicative workflow。

借用 Mock* 的 name 槽位(`ModelApplicability._CANDIDATES` + brain `model_applicability` 已含这些 name),
predictor 实现换成真 donor 模型(linear/latent/gnn);其余 agent(brain/ensemble/reliability/critic/provenance/report)
复用 Week 2 骨架。仅远端 virtualcell 环境(import torch + donor)。
"""
from __future__ import annotations

import os


def build_runtime_ml(ckpt_dir: str, *, config=None, norman_ds=None):
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
    from praxis_virtualcell.core.runtime import AgentRuntime
    from praxis_virtualcell.predictors.ml.agent_adapter import make_ml_agent
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    cfg = config or RuntimeConfig()
    rt = AgentRuntime(cfg, bus=MessageBus(), clock=Clock(), idgen=IdGen())
    ds = norman_ds if norman_ds is not None else load_norman(split="test", max_perts=2, max_cells=2)

    # 真 model 借用 Mock* name 槽位:ModelApplicability._CANDIDATES + brain 规则已含,路由不变,实现换真。
    slots = {"MockLinear": "linear_additive", "MockCPA": "latent_additive", "MockGEARS": "gnn_pert"}
    for name, pn in slots.items():
        model, _ = build_predictor_from_ckpt(os.path.join(ckpt_dir, pn))
        rt.register_agent(make_ml_agent(model, norman_ds=ds, name=name))

    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), EnsembleCoordinatorAgent(), ReliabilityAgent(),
              CriticAgent(), ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    return rt


def run_request_ml(request_dict: dict, ckpt_dir: str, **kw) -> dict:
    from praxis_virtualcell.core.request import VirtualCellRequest

    rt = build_runtime_ml(ckpt_dir, **kw)
    return rt.run_workflow(VirtualCellRequest.from_dict(request_dict))
