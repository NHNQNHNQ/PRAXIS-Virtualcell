"""Load a donor linear checkpoint and evaluate Norman test delta-Pearson against its S0 anchor. Remote torch/donor
execution only. The deterministic linear_additive checkpoint and identical sampling reproduce S0=0.6638587; test
settings are max_cells_per_pert=200, rng_seed=seed+1=1, and loader-default esm2 features.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

import torch  # noqa: E402


def main(ckpt_stem: str) -> None:
    cfg = json.loads(Path(ckpt_stem + ".json").read_text(encoding="utf-8"))
    from bench.vcbench.loader import load_vcbench_split
    from coordinator.eval_agent import EvalAgent
    from predictors.linear_additive import LinearAdditivePredictor

    model = LinearAdditivePredictor(**cfg["kwargs"])

    bundle = torch.load(ckpt_stem + ".pt", map_location="cpu", weights_only=False)
    state = bundle["state_dict"] if isinstance(bundle, dict) and "state_dict" in bundle else bundle
    model.load_state_dict(state)
    model.eval()


    ds = load_vcbench_split("norman_2019", "test", max_cells_per_pert=200, rng_seed=1)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rep = EvalAgent(batch_size=64, device=dev).evaluate(model, ds)
    print("S0_recorded =", cfg["meta"].get("delta_pearson"))
    print("S_eval delta_pearson =", rep.metrics.delta_pearson)
    print("cosine =", rep.metrics.cosine, "n =", rep.n_samples)


if __name__ == "__main__":
    main(sys.argv[1])
