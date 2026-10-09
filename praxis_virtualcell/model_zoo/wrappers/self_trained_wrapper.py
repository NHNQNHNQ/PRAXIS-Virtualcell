"""Wrap a trained model with the same fail-closed retrieval contract. The initial example is the
perturbation-agnostic Norman mean baseline, using lazy donor mean-baseline helpers. Historical per-cell
delta-Pearson=0.4615, cosine=0.9850, n=18874 under the donor split; trained bases were 0.6183–0.6716. Real
execution requires donor dependencies and persisted mean_delta.
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class SelfTrainedWrapper(ModelWrapper):
    name = "SelfTrainedWrapper"

    def __init__(self, spec_name: str | None = None, ckpt_stem: str | None = None) -> None:

        self._spec_name = spec_name or "norman_mean_baseline"
        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene", "gene_combination"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "norman_mean_baseline",
            "type": "self_trained",
            "training_data": "donor norman_2019 (Perturb-seq K562); mean_delta over non-control cells",
            "architecture": "mean-perturbation naive baseline (perturbation-agnostic: control + mean_delta)",
            "metrics": {

                "delta_pearson": 0.4615,
                "cosine": 0.9850,
                "n": 18874,
                "n_train": 25463,
                "metric_note": "per-cell delta_pearson on donor norman test split (train seed 0/test seed 1)",
            },

            "is_naive_lower_bound_baseline": True,
            "baseline_note": "perturbation-agnostic; cannot capture pert-specific effects — "
                             "intentional same-protocol lower bound (>=3 baseline invariant)",
            "remote_env": {
                "host": "operator-configured",
                "conda_env": "virtualcell (torch 2.6+cu124)",
                "data": "GEARS_DATA_ROOT/norman_donor/perturb_processed.h5ad",
                "donor_src": "PRAXIS_DONOR_SOURCE_ROOT",
                "training_script": "praxis_virtualcell.benchmarks.mean_baseline",
            },
            "distributable": False,
            "status_note": "external capability verified (mean_baseline scored 0.4615); checkpoint fetch remains gated",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:

        return {"available": False, "reason": "mean_baseline_is_point_estimate",
                "method": "point_estimate"}

    def run_prediction(self, model_input: dict) -> dict:
        """Rebuild the persisted mean predictor and predict control+mean_delta. Missing torch or
        undeclared/untrained checkpoints raise and become failed; no synthetic delta fallback is returned.
        """
        if not self._ckpt_stem:
            raise RuntimeError(

                    'self_trained checkpoint is undeclared (mean_delta is untrained or unsaved; registry '
                    'assets require manual fetch); fail-closed: never silently return a fabricated delta'
                )

        import torch

        from praxis_virtualcell.benchmarks.mean_baseline import _build_mean_predictor


        mean_delta = torch.load(self._ckpt_stem, weights_only=False)
        if hasattr(mean_delta, "mean_delta"):
            mean_delta = mean_delta["mean_delta"] if isinstance(mean_delta, dict) else mean_delta.mean_delta
        predictor = _build_mean_predictor(mean_delta)



        from predictors.base import Context, Perturbation

        targets = list(model_input.get("targets") or [])
        if not targets:
            raise ValueError("self_trained run_prediction requires model_input['targets']; fail-closed")
        ctx = model_input.get("_context")
        if ctx is None:
            raise RuntimeError("missing control context (requires the donor Norman control tensor); fail-closed; "
                               "real inference requires explicit control injection")
        pert = Perturbation(kind="gene_ko", targets=tuple(targets))
        out = predictor.predict(Context(control=ctx), pert)


        delta = (out.mean - ctx).squeeze(0)
        return {
            "prediction": {
                "delta": delta.tolist(),
                "n_genes": int(delta.numel()),
                "value_type": "mean_baseline_delta",
                "is_naive_lower_bound_baseline": True,
            },
            "uncertainty": self.estimate_uncertainty(model_input, None),
        }
