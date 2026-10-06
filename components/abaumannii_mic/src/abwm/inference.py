"""Offline structure-only MIC inference using the preserved direct checkpoints."""
from pathlib import Path
import hashlib
import numpy as np
import torch

from .data import fingerprint
from .models import DirectMICBaseline, validate_mic_inputs


class Predictor:
    def __init__(self, model_root, seed=42, scheme="compound", device="cpu"):
        if scheme not in {"compound", "scaffold", "study", "isolate"}:
            raise ValueError("Unknown frozen MIC split scheme")
        self.seed = seed
        self.scheme = scheme
        self.device = torch.device(device)
        self.path = Path(model_root) / f"direct_mic_{scheme}_seed{seed}.pt"
        self.checkpoint = torch.load(self.path, map_location=self.device, weights_only=True)
        ck = self.checkpoint
        if not ck.get("trained") or ck.get("stage") != "direct_mic":
            raise ValueError("A trained direct MIC checkpoint is required")
        if ck.get("world_model") is not False:
            raise ValueError("Cell-state checkpoints are unsupported")
        if ck.get("seed") != seed or ck.get("scheme") != scheme:
            raise ValueError("Checkpoint seed or split scheme does not match its filename")
        self.model = DirectMICBaseline(ck["config"]["model"]["hidden_dim"]).to(self.device)
        self.model.load_state_dict(ck["model_state"])
        self.model.eval()

    @torch.inference_mode()
    def predict(self, payload):
        validate_mic_inputs(payload)
        if payload.get("task", "mic") != "mic" or payload.get("model", "direct") != "direct":
            raise ValueError("Only task=mic, model=direct is available")
        if set(payload) - {"task", "model", "smiles"}:
            raise ValueError("Structure-only MIC does not accept strain, state, or target inputs")
        fp = torch.as_tensor(fingerprint(payload["smiles"])[None, :], device=self.device)
        mu, sigma = self.model(fp)
        a, s = float(mu[0]), float(sigma[0])
        if not np.isfinite([a, s]).all() or abs(a) + 1.644854 * s > 1000:
            raise ValueError("Input outside finite predictive range")
        return dict(
            status="predicted", model="direct_baseline", unit="ug/mL",
            log2_mean=a, log2_sigma=s, median=float(2 ** a),
            interval90=[float(2 ** (a - 1.644854 * s)), float(2 ** (a + 1.644854 * s))],
            state_origin=None,
            uncertainty="learned Gaussian predictive spread; not externally calibrated confidence",
            target_readout=dict(status="untrained", scores=None),
            species="Acinetobacter baumannii", strain_specific=False,
            scope="Structure-to-MIC model; no killing-rate or protein-target prediction",
            checkpoint=dict(filename=self.path.name, seed=self.seed, scheme=self.scheme,
                            sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                            trained_components=self.checkpoint.get("components_trained")),
        )
