"""把 donor LinearAdditivePredictor 包成 praxis predictor-agent(rich↔torch 适配)。

predict_tensor:给 control + pert_emb,经 donor Context/Perturbation 调 donor.predict,返回 mean。
(bus 级 PredictorAgent 集成在 Coordinator 迁移时接;本期只证预测等价 + 可在 EvalAgent 复用。)
仅远端 virtualcell 环境 import。
"""
from __future__ import annotations

import sys

import torch

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)


class LinearAdditivePredictorAgent:
    name = "MLLinearAdditive"

    def __init__(self, donor_model) -> None:
        self.model = donor_model.eval()

    def predict_tensor(self, control: torch.Tensor, pert_emb: torch.Tensor, *,
                       kind: str = "gene_ko", targets: tuple = ()) -> torch.Tensor:
        from predictors.base import Context, Perturbation

        ctx = Context(control=control)
        pert = Perturbation(kind=kind, targets=targets, meta={"pert_emb": pert_emb})
        return self.model.predict(ctx, pert).mean

    def as_donor_predictor(self):
        """返回底层 donor Predictor,供 EvalAgent.evaluate 复用(Task 5)。"""
        return self.model
