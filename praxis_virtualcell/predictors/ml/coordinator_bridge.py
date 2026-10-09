"""Build the praxis coordinator by reusing donor SubAgent/Coordinator routing and ensembling, without rewriting the
ML implementation. Requires donor dependencies.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def build_coordinator(ckpt_dir: str, predictor_names: list[str], *, bench_id: str = "norman_2019",
                      perturbation_kinds: frozenset[str] = frozenset({"gene_ko", "gene_combo"}),
                      device: str = "cpu"):
    """Load named checkpoints into one benchmark Subagent containing multiple predictors, then build Coordinator
    from Subagents. SubagentSpec uses id/perturbation_kinds/bench_id. Coordinator is not nn.Module, so move
    predictors to the device explicitly rather than relying on EvalAgent.to recursion.
    """
    from agents.subagent import Subagent, SubagentSpec
    from coordinator.coordinator import Coordinator

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

    predictors = [build_predictor_from_ckpt(str(Path(ckpt_dir) / pn))[0].to(device)
                  for pn in predictor_names]
    spec = SubagentSpec(id=f"subagent@{bench_id}", perturbation_kinds=set(perturbation_kinds),
                        bench_id=bench_id)
    coord = Coordinator([Subagent(spec, predictors)])
    coord.default_bench_id = bench_id
    return coord
