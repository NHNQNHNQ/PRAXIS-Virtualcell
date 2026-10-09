"""scGPT wrapper reusing donor checkpoint construction and MLPredictorAgent with lazy dependency loading. Frozen
backbone 53.8M and head 2.47M had predictor equivalence atol 1e-6. Historical checkpoint size was about 196MB;
donor Norman evaluation reported delta-Pearson 0.4407, cosine 0.9808, n=7290. These fixed-protocol anchors are
not a general accuracy claim.
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class ScgptWrapper(ModelWrapper):
    name = "ScgptWrapper"

    def __init__(self, ckpt_stem: str | None = None) -> None:

        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "scgpt",
            "type": "public_model",
            "training_data": "donor norman_2019 (frozen scGPT encoder + light head)",
            "architecture": "frozen scGPT backbone 53.8M + head 2.47M (train_loss 0.045->0.044 saturated)",
            "metrics": {

                "delta_pearson": 0.4407,
                "cosine": 0.9808,
                "n": 7290,
                "metric_note": "per-cell delta_pearson on donor norman test split (comparable to base)",
            },
            "not_comparable_to_donor_base": False,
            "frozen_backbone_underperforms": True,
            "underperform_reason": "frozen foundation encoder + light head saturates on norman; "
                                   "SOTA needs fine-tune (unfreeze 53.8M + flash_attn) — backlog",
            "remote_env": {
                "host": "operator-configured",
                "conda_env": "vc-scgpt (torch 2.3+cu121)",
                "donor_src": "PRAXIS_DONOR_SOURCE_ROOT",
                "ckpt": "SCGPT_CHECKPOINT_ROOT/pretrained_backbone.{pt,json}",
            },
            "distributable": False,
            "status_note": (
                'integration pipeline historically verified in its external environment; frozen '
                'baseline retains its low score'
            ),
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        return {"available": False, "reason": "model_reports_no_calibrated_uncertainty",
                "method": "point_estimate"}

    def run_prediction(self, model_input: dict) -> dict:
        """Lazy-load donor_bridge, rebuild scGPT and its head from checkpoint, and execute MLPredictorAgent.
        Missing torch/checkpoint raises and becomes failed, never a fabricated delta.
        """
        if not self._ckpt_stem:
            raise RuntimeError("scgpt checkpoint is undeclared (registry assets require manual fetch); fail-closed")

        from praxis_virtualcell.predictors.ml.agent_adapter import make_ml_agent
        from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt

        model, _cfg = build_predictor_from_ckpt(self._ckpt_stem)


        agent = make_ml_agent(model, name="scgpt")
        targets = list(model_input.get("targets", []))

        mi = agent.prepare_input({"perturbation_targets": targets}, {})

        return agent.run_prediction(mi)
