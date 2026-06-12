"""baseline / sanity:总 success,返回常数 delta。"""
from __future__ import annotations

from praxis_virtualcell.predictors.base import PredictorAgent


class MockLinearAgent(PredictorAgent):
    name = "MockLinear"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.0 for _ in model_input["targets"]] or [0.0]},
                "uncertainty": {"sigma": 0.1}}
