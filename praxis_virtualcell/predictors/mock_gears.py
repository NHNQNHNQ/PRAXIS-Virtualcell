"""graph generalization mock:gene 不在 vocabulary → rejected,不硬预测。"""
from __future__ import annotations

from praxis_virtualcell.predictors.base import PredictorAgent


class MockGEARSAgent(PredictorAgent):
    name = "MockGEARS"

    def assess_applicability(self, request: dict, brain_context: dict):
        score, reject = super().assess_applicability(request, brain_context)
        if reject is not None:
            return score, reject
        vocab = set((brain_context.get("object_vocabulary") or {}).get("genes", []))
        rules = (brain_context.get("model_applicability") or {}).get(self.name, {})
        if "gene_not_in_graph_vocabulary" in rules.get("reject_if", []):
            missing = [g for g in request.get("perturbation_targets", []) if g not in vocab]
            if missing:
                return 0.0, f"gene_not_in_graph_vocabulary:{missing}"
        return score, None

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.4 for _ in model_input["targets"]] or [0.4]},
                "uncertainty": {"sigma": 0.25}}
