"""Remote perturbation-level risk-coverage evaluation using donor aux_bases and tau_disagreement. Historical CPA
plus 4 auxiliary bases: coverage 1.00/0.96/0.88/0.82/0.74 gives delta-Pearson
0.6716/0.6830/0.7071/0.7320/0.7536, gains +0.011/+0.036/+0.060/+0.082 against fixed full coverage. GPU threshold
effects cause approximately ±0.01 run variation; these are not exact per-run guarantees.
"""
from __future__ import annotations

import os
import sys

_DONOR = os.environ.get("PRAXIS_DONOR_SOURCE_ROOT", "").strip()
if not _DONOR:
    raise RuntimeError("Set PRAXIS_DONOR_SOURCE_ROOT to the external donor source checkout")
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

CKPT_DIR = os.environ.get("PRAXIS_DONOR_CHECKPOINT_ROOT", "").strip()
PRIMARY = "cpa_style"
AUX = ["decoder_only", "gnn_pert", "linear_additive", "latent_additive"]
TAUS = (1.0, 0.5, 0.4, 0.3, 0.25, 0.2)


def risk_coverage(*, ckpt_dir: str | None = None, primary: str = PRIMARY,
                  aux: list[str] | None = None, taus=TAUS, test_seed: int = 1) -> dict:
    ckpt_dir = ckpt_dir or CKPT_DIR
    if not ckpt_dir:
        raise RuntimeError("Set PRAXIS_DONOR_CHECKPOINT_ROOT or pass ckpt_dir explicitly")
    import torch
    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    aux = list(aux if aux is not None else AUX)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    def _p(name):

        return build_predictor_from_ckpt(f"{ckpt_dir}/{name}")[0].to(dev)

    prim = _p(primary)
    auxs = [_p(n) for n in aux]
    ds = load_norman(split="test", seed=test_seed)
    ea = EvalAgent(batch_size=64, device=dev)

    rows = []
    ref = None
    for tau in taus:
        rep = ea.evaluate(prim, ds, aux_bases=auxs, tau_disagreement=tau,
                          abstain_granularity="pert_level")
        ar = rep.abstain_rate or 0.0
        keep = rep.delta_pearson_non_abstain
        if ref is None:
            ref = keep
        rows.append({"tau": tau, "abstain_rate": ar, "coverage": 1.0 - ar,
                     "dp_keep": keep,
                     "gain_vs_full": (keep - ref) if (keep is not None and ref is not None) else None})
    return {"reference_full_coverage": ref, "rows": rows}


def main() -> None:
    r = risk_coverage()
    print(f"REF_FULL_COVERAGE_DP = {r['reference_full_coverage']}")
    for x in r["rows"]:
        print(f"RC tau={x['tau']} coverage={x['coverage']:.4f} "
              f"dp_keep={x['dp_keep']} gain={x['gain_vs_full']}")


if __name__ == "__main__":
    main()
