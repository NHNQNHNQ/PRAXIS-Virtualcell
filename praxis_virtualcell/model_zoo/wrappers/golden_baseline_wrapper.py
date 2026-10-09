"""Capability-bound wrapper for the three frozen Golden Norman baselines."""

from __future__ import annotations

from pathlib import Path

from praxis_virtualcell.benchmarks.golden_norman import predict_from_artifact
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GoldenBaselineWrapper(ModelWrapper):
    """Load only broker-verified local artifacts and return ordered deltas."""

    name = "golden_norman_baseline"

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        metadata = self.capability_assets.get("baseline.json")
        if metadata is None:
            raise ValueError("broker did not provide baseline.json")
        result = predict_from_artifact(Path(metadata).parent, model_input["targets"])
        return {
            "prediction": {
                "delta": result["delta"].tolist(),
                "baseline": result["baseline"],
                "feature_ids_sha256": result["feature_ids_sha256"],
                "n_features": result["n_features"],
                "value_type": result["value_type"],
                "unseen_train_targets": result["unseen_train_targets"],
            },
            "uncertainty": {
                "method": "point_estimate",
                "available": False,
                "sigma": None,
                "reason": "simple baseline has no calibrated predictive uncertainty",
            },
            "evidence": ["golden_norman_hash_locked_baseline"],
            "provenance": {
                "model_version": self.model_version,
                "scientifically_validated": False,
            },
        }
