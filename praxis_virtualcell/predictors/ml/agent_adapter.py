"""Wrap real donor models as communicative PredictorAgents with retrieval, applicability, input adaptation, and
prediction. Convert targets to esm2 perturbation embeddings plus Norman controls, then call donor model.predict.
Requires the remote torch/donor environment.
"""  # noqa: E501
from __future__ import annotations

import os
import sys

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if _DONOR and _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

from praxis_virtualcell.predictors.base import PredictorAgent  # noqa: E402


class MLBackedPredictorAgent(PredictorAgent):
    """Predictor agent backed by a real ML model rather than a mock implementation."""

    model_version = "donor_ml"



    def __init__(self, donor_model, *, control, pert_table, pert_dim, name=None,
                 model_version: str | None = None):
        self.model = donor_model.eval()
        self.name = name or f"ML{type(donor_model).__name__}"
        if model_version is not None and (
            not isinstance(model_version, str) or not model_version.strip()
        ):
            raise ValueError("model_version must be a non-empty string when provided")
        self.model_version = (
            model_version if model_version is not None
            else f"donor_ml:{type(donor_model).__name__}"
        )
        self._control = control
        self._pert_table = pert_table
        self._pert_dim = pert_dim

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        """Adapt request.perturbation_targets to esm2 pert_emb and reuse the Norman control baseline."""
        if not _DONOR:
            raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
        from bench.vcbench.loader import _pert_emb_for

        targets = list(request.get("perturbation_targets", []))
        pname = "+".join(targets) if targets else "control"
        pert_emb = _pert_emb_for(pname, self._pert_table, self._pert_dim)
        return {"control": self._control, "pert_emb": pert_emb, "targets": tuple(targets)}

    def run_prediction(self, model_input: dict) -> dict:
        from praxis_virtualcell.predictors.ml.ml_predictor_agent import MLPredictorAgent

        targets = model_input["targets"]
        kind = "gene_combo" if len(targets) > 1 else "gene_ko"
        mean = MLPredictorAgent(self.model).predict_tensor(
            model_input["control"], model_input["pert_emb"], kind=kind, targets=targets)

        delta = (mean.squeeze(0) - model_input["control"]).detach().cpu().tolist()
        return {"prediction": {"delta": delta, "n_genes": len(delta)},
                "uncertainty": {"std": float(mean.std())}}


def make_ml_agent(donor_model, *, norman_ds=None, name=None,
                  model_version: str | None = None) -> MLBackedPredictorAgent:
    """Initialize control baseline and perturbation table from Norman data for workflows/tests."""
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    ds = norman_ds if norman_ds is not None else load_norman(split="test", max_perts=2, max_cells=2)
    return MLBackedPredictorAgent(donor_model, control=ds[0].control, pert_table=ds.pert_table,
                                  pert_dim=ds.pert_dim, name=name, model_version=model_version)
