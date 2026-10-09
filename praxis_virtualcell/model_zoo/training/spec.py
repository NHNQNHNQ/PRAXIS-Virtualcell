"""Declarative self-training contract: training_data/split/baseline/metrics/provenance, training_script, and
remote_env. Required text fields are nonempty strings; metrics has a complete dictionary structure and can
retain null planned values. Derive the 5-key training card for registry validation; no LLM is used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_TEXT_FIELDS = ("training_data", "split", "baseline", "provenance")


@dataclass
class SelfTrainingSpec:
    name: str
    training_data: str
    split: str
    baseline: str
    metrics: dict
    provenance: str
    training_script: str
    remote_env: dict = field(default_factory=dict)

    def __post_init__(self) -> None:

        for f in ("name",) + _TEXT_FIELDS + ("training_script",):
            v = getattr(self, f)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"SelfTrainingSpec field {f} must be a nonempty str (received {v!r});fail-closed")

        if not isinstance(self.metrics, dict) or not self.metrics:
            raise ValueError(
                f"SelfTrainingSpec.metrics must be a nonempty dict (received {self.metrics!r});fail-closed"
            )
        if not isinstance(self.remote_env, dict):
            raise ValueError(f"SelfTrainingSpec.remote_env must be a dict (received {self.remote_env!r})")

    def to_training_card(self) -> dict:
        """Return the registry's 5-key training card matching required_card."""
        return {
            "training_data": self.training_data,
            "split": self.split,
            "baseline": self.baseline,
            "metrics": self.metrics,
            "provenance": self.provenance,
        }
