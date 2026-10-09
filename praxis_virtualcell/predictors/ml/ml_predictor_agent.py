"""通用 ML predictor-agent 包装(rich↔torch 适配)。

`predict_tensor`:给 control + pert_emb,经 donor Context/Perturbation 调 `donor.predict`,返回 mean。
对所有 donor base predictor(linear/latent/cpa/gnn/decoder/pretrained_backbone)接口相同。
(Week 4a 的 LinearAdditivePredictorAgent 是其前身,保留以兼容旧测试。)仅远端 virtualcell 环境。
"""
from __future__ import annotations

import sys

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


class MLPredictorAgent:
    def __init__(self, donor_model) -> None:
        self.model = donor_model.eval()
        self.name = f"ML{type(donor_model).__name__}"

    def predict_tensor(self, control: torch.Tensor, pert_emb: torch.Tensor, *,
                       kind: str = "gene_ko", targets: tuple = ()) -> torch.Tensor:
        from predictors.base import Context, Perturbation

        ctx = Context(control=control)
        pert = Perturbation(kind=kind, targets=targets, meta={"pert_emb": pert_emb})
        return self.model.predict(ctx, pert).mean

    def as_donor_predictor(self):
        """返回底层 donor Predictor,供 EvalAgent.evaluate / Coordinator 复用。"""
        return self.model
