"""Generic tensor adapter for donor linear/latent/cpa/gnn/decoder/pretrained_backbone models. Build
Context/Perturbation, invoke predict, and return mean. Preserve the earlier linear adapter for compatibility;
requires donor dependencies.
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
        """Return the underlying donor predictor for EvalAgent or Coordinator reuse."""
        return self.model
