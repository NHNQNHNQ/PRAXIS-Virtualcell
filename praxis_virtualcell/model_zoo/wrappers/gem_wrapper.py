"""Wrap actual GemModel FBA with the ModelWrapper contract. Default uses bundled e_coli_core textbook assets.
Missing cobra/SBML raises; absent genes produce in_model=False without fabricated growth. Uncertainty is labeled
deterministic FBA.
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GemWrapper(ModelWrapper):
    name = "GemWrapper"

    def __init__(self, sbml_path: str | None = None) -> None:

        from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM
        from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel

        self._gem = GemModel(sbml_path) if sbml_path else EcoliGEM()

    def declare_scope(self) -> dict:
        return {
            "species": ["bacteria", "yeast"],
            "module": "cytoplasmic_metabolism",
            "task": ["growth"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        """Run cobra knockout FBA and return WT growth, knockout results, and uncertainty. Absent genes yield
        in_model=False/growth=None.
        """
        targets = model_input.get("targets", [])
        kos = self._gem.knockout_many(targets)
        return {
            "prediction": {
                "wt_growth": round(self._gem.wt_growth, 5),
                "knockouts": [
                    {"gene": k.gene, "in_model": k.in_model,
                     "growth": None if k.growth is None else round(k.growth, 5),
                     "ratio": None if k.ratio is None else round(k.ratio, 4),
                     "essential": k.essential}
                    for k in kos
                ],
            },

            "uncertainty": {"method": "deterministic_fba"},
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        """Declare available deterministic_fba metadata rather than probabilistic uncertainty."""
        return {"available": True, "method": "deterministic_fba",
                "note": "constraint-based FBA is deterministic; essentiality needs wet-lab confirmation"}
