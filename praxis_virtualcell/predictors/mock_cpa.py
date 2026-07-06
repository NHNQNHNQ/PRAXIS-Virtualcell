"""perturbation-conditioned mock:applicable 即 success。"""
from __future__ import annotations

from praxis_virtualcell.predictors.base import PredictorAgent


class MockCPAAgent(PredictorAgent):
    name = "MockCPA"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.5 for _ in model_input["targets"]] or [0.5]},
                "uncertainty": {"sigma": 0.2},
                "evidence": ["mock"], "provenance": {"mock": True}}  # 自声明 mock,非真跑数值
