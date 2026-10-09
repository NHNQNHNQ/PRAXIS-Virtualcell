"""GEARS ModelWrapper using its native API, with lazy torch/GEARS imports and fail-closed checkpoint loading. The
donor adapter interface is different and is not reused. Historical native pearson_de=0.8392 uses absolute
expression and a different split, so it is not comparable to donor per-cell delta-Pearson.
"""

from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GearsWrapper(ModelWrapper):
    name = "GearsWrapper"

    def __init__(self, ckpt_stem: str | None = None) -> None:

        self._ckpt_stem = ckpt_stem

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["perturbation_response"],
            "perturbation": ["gene", "gene_combination"],
        }

    def declare_provenance(self) -> dict:
        return {
            "model": "gears",
            "type": "public_model",
            "training_data": "norman_2019 (Perturb-seq, K562)",
            "architecture": "GEARS GNN (hidden=64), 5 epoch",
            "metrics": {
                "pearson": 0.9834,
                "pearson_de": 0.8392,
                "mse": 0.0068,
                "comparable_delta_pearson": None,
                "metric_note": "GEARS native pearson on absolute expression; NOT donor delta_pearson",
            },
            "not_comparable_to_donor_base": True,
            "no_fixed_seed_note": "GEARS retrain noise 0.8392->0.8461",
            "remote_env": {
                "host": "operator-configured",
                "conda_env": "virtualcell (torch 2.6+cu124)",
                "donor_src": "PRAXIS_DONOR_SOURCE_ROOT",
            },
            "distributable": False,
            "status_note": "external capability verified; comparable delta-Pearson evaluation remains pending",
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:

        return {"available": False, "reason": "model_reports_no_calibrated_uncertainty", "method": "point_estimate"}

    _GEARS_DATA_NAME = "norman_donor2"

    def run_prediction(self, model_input: dict) -> dict:
        """Lazy-load torch/GEARS, reconstruct PertData, load the checkpoint, and call native predict. Missing
        dependencies/assets raise and become failed through inherited handling. Return absolute expression
        marked gears_native/not_comparable_to_donor_base, never label it donor delta.
        """
        import os

        import pandas as _pd
        import torch

        _pd.Series.nonzero = lambda self: self.to_numpy().nonzero()
        from gears import GEARS, PertData

        if not self._ckpt_stem:
            raise RuntimeError("gears checkpoint is undeclared (registry assets require manual fetch); fail-closed")

        targets = list(model_input.get("targets") or [])
        if not targets:
            raise ValueError("gears run_prediction requires model_input['targets'] (perturbation genes); fail-closed")

        data_root = os.environ.get("GEARS_DATA_ROOT", "").strip()
        if not data_root:
            raise RuntimeError("Set GEARS_DATA_ROOT to the external GEARS data directory; fail-closed")
        data_name = os.environ.get("GEARS_DATA_NAME", self._GEARS_DATA_NAME)
        pert_data = PertData(data_root)
        pert_data.load(data_path=os.path.join(data_root, data_name))
        pert_data.prepare_split(split="simulation", seed=1)
        pert_data.get_dataloader(batch_size=32, test_batch_size=64)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        g = GEARS(pert_data, device=device)
        g.load_pretrained(self._ckpt_stem)

        for gene in targets:
            if gene not in g.pert_list:
                raise ValueError(
                    f"{gene} is absent from GEARS.pert_list (vocabulary size 9853); fail-closed "
                    "(use a real Norman perturbation gene in the vocabulary)"
                )

        res = g.predict([targets])
        cond_key = "_".join(targets)
        expr = res[cond_key]

        return {
            "prediction": {
                "expression": expr,
                "n_genes": int(len(expr)),
                "condition": cond_key,
                "value_type": "gears_native_absolute_expression",
                "not_comparable_to_donor_base": True,
            },
            "uncertainty": self.estimate_uncertainty(model_input, None),
        }

    def run_delta(self, model_input: dict) -> dict:
        """Return GEARS-internal delta as mean perturbed expression minus mean control expression. Mark it
        noncomparable to donor outputs; never place absolute expression in a delta field. Missing
        dependencies/checkpoints raise fail-closed.
        """
        import os

        import pandas as _pd
        import torch

        _pd.Series.nonzero = lambda self: self.to_numpy().nonzero()
        from gears import GEARS, PertData

        if not self._ckpt_stem:
            raise RuntimeError("gears checkpoint is undeclared; fail-closed")
        targets = list(model_input.get("targets") or [])
        if not targets:
            raise ValueError("gears run_delta requires model_input['targets']; fail-closed")

        data_root = os.environ.get("GEARS_DATA_ROOT", "").strip()
        if not data_root:
            raise RuntimeError("Set GEARS_DATA_ROOT to the external GEARS data directory; fail-closed")
        data_name = os.environ.get("GEARS_DATA_NAME", self._GEARS_DATA_NAME)
        pert_data = PertData(data_root)
        pert_data.load(data_path=os.path.join(data_root, data_name))
        pert_data.prepare_split(split="simulation", seed=1)
        pert_data.get_dataloader(batch_size=32, test_batch_size=64)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        g = GEARS(pert_data, device=device)
        g.load_pretrained(self._ckpt_stem)

        for gene in targets:
            if gene not in g.pert_list:
                raise ValueError(f"{gene} is absent from GEARS.pert_list; fail-closed")

        import numpy as _np

        perturbed = g.predict([targets])["_".join(targets)]

        ctrl_adata = pert_data.adata[pert_data.adata.obs["condition"] == "ctrl"]
        control = _np.asarray(ctrl_adata.X.mean(axis=0)).ravel()
        delta = _np.asarray(perturbed).ravel() - control

        return {
            "prediction": {
                "delta": [round(float(x), 4) for x in delta],
                "n_genes": int(len(delta)),
                "condition": "_".join(targets),
                "value_type": "gears_internal_delta",
                "not_comparable_to_donor_base": True,
                "non_deterministic": True,
            },
            "uncertainty": self.estimate_uncertainty(model_input, None),
        }
