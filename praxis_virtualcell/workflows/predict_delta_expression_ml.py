"""Communicative workflow using MLBackedPredictorAgent with real donor linear/latent/gnn models in existing Mock*
registry slots. Reuse the brain/ensemble/reliability/critic/provenance/report stack; requires remote torch and
donor dependencies.
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
    from praxis_virtualcell.predictors.ml.checkpoint_identity import (
        ML_SLOT_CHECKPOINTS,
        checkpoint_model_version,
    )
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    cfg = config or RuntimeConfig()
    rt = AgentRuntime(cfg, bus=MessageBus(), clock=Clock(), idgen=IdGen())
    ds = norman_ds if norman_ds is not None else load_norman(split="test", max_perts=2, max_cells=2)


    for name, (pn, expected_class) in ML_SLOT_CHECKPOINTS.items():
        checkpoint_stem = os.path.join(ckpt_dir, pn)
        model_version = checkpoint_model_version(
            checkpoint_stem, expected_class=expected_class
        )
        model, _ = build_predictor_from_ckpt(checkpoint_stem)
        rt.register_agent(make_ml_agent(model, norman_ds=ds, name=name,
                                        model_version=model_version))

    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), EnsembleCoordinatorAgent(), ReliabilityAgent(mode=cfg.reliability_mode),
              CriticAgent(), ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    return rt


def run_request_ml(request_dict: dict, ckpt_dir: str, **kw) -> dict:
    from praxis_virtualcell.core.request import VirtualCellRequest

    rt = build_runtime_ml(ckpt_dir, **kw)
    return rt.run_workflow(VirtualCellRequest.from_dict(request_dict))
