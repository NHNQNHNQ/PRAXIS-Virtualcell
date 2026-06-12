"""复用 donor SubAgent/Coordinator 构建 praxis 侧 Coordinator(sys.path 注入,不重写 MoE/Ensembler)。

ADR-W4b-4:prototype-first,Coordinator 路由/ensembler 直接复用 donor。仅远端 virtualcell 环境。
"""
from __future__ import annotations

import sys
from pathlib import Path

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


def build_coordinator(ckpt_dir: str, predictor_names: list[str], *, bench_id: str = "norman_2019"):
    """对每个 predictor_name 经 donor_bridge 加载 ckpt → 包 donor SubAgent → 组 donor Coordinator。"""
    from agents.subagent import SubAgent, SubAgentSpec
    from coordinator.coordinator import Coordinator

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

    subs = []
    for pn in predictor_names:
        model, _ = build_predictor_from_ckpt(str(Path(ckpt_dir) / pn))
        spec = SubAgentSpec(name=f"{pn}-{bench_id}", bench_id=bench_id, predictor_name=pn)
        subs.append(SubAgent(spec=spec, predictor=model))
    return Coordinator(subs, default_bench_id=bench_id)
