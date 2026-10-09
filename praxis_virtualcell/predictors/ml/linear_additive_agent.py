"""Wrap donor LinearAdditivePredictor for tensor prediction. Build donor Context/Perturbation from control and
pert_emb, call donor.predict, and return mean. Retained for prediction equivalence and EvalAgent reuse; requires
donor dependencies.
"""
from __future__ import annotations

import os
import sys

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

import torch  # noqa: E402


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
        """Return the underlying donor predictor for EvalAgent evaluation."""
        return self.model
