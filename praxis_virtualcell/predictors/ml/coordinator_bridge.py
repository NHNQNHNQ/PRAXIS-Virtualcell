"""复用 donor SubAgent/Coordinator 构建 praxis 侧 Coordinator(sys.path 注入,不重写 MoE/Ensembler)。

ADR-W4b-4:prototype-first,Coordinator 路由/ensembler 直接复用 donor。仅远端 virtualcell 环境。
"""
from __future__ import annotations

import sys
from pathlib import Path

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def build_coordinator(ckpt_dir: str, predictor_names: list[str], *, bench_id: str = "norman_2019",
                      perturbation_kinds: frozenset[str] = frozenset({"gene_ko", "gene_combo"}),
                      device: str = "cpu"):
    """加载 predictor_names 的 ckpt → 装进一个 bench Subagent(内部多 predictor)→ 组 donor Coordinator。

    注(donor 真实 API):一个 `Subagent` 持有该 bench 的**多个** Predictor(内部 ensemble);
    `Coordinator` 持有 Subagent 列表。`SubagentSpec(id, perturbation_kinds, bench_id)`。
    Coordinator 非 nn.Module → 不被 EvalAgent.to(device) 递归,故须显式把 predictors 移到 device。
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
