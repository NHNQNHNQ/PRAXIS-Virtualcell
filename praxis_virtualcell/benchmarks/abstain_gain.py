"""S4(W8):abstain_gain / risk-coverage —— disagreement-based abstention 的治理价值定量证据。

PRAXIS 在「人类、词表内、未见扰动」上**真实成立**的 abstain 机制 = ensemble 跨 base disagreement
(物种 / 词表拒绝在此不触发)。复用 donor EvalAgent 内置 aux_bases + tau_disagreement(pert_level):
弃权高分歧扰动 → 保留集 ΔPearson 单调上升。仅远端 virtualcell env 跑。

split 与数据指纹见 data/manifests/norman_2019.yaml。实测(cpa primary + 4 base aux, donor norman test):
    coverage 1.00 → dp 0.6716(满覆盖参考)
    coverage 0.96 → 0.6830 (+0.011)
    coverage 0.88 → 0.7071 (+0.036)
    coverage 0.82 → 0.7320 (+0.060)
    coverage 0.74 → 0.7536 (+0.082)
诚实:阈值附近 GPU 浮点非确定性 → abstain_rate/gain 有 ~±0.01 run 间抖动;gain 以**固定满覆盖参考**计,
不报单点精确值;趋势(单调正向)稳健。

用法:conda activate virtualcell; python -m praxis_virtualcell.benchmarks.abstain_gain
"""
from __future__ import annotations

import sys

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

CKPT_DIR = _DONOR + "/runs/full_bench_20260521_060815/checkpoints/norman_2019"
PRIMARY = "cpa_style"
AUX = ["decoder_only", "gnn_pert", "linear_additive", "latent_additive"]
TAUS = (1.0, 0.5, 0.4, 0.3, 0.25, 0.2)


def risk_coverage(*, ckpt_dir: str = CKPT_DIR, primary: str = PRIMARY,
                  aux: list[str] | None = None, taus=TAUS, test_seed: int = 1) -> dict:
    import torch

    from coordinator.eval_agent import EvalAgent

    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    aux = list(aux if aux is not None else AUX)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    def _p(name):
        # aux_bases / primary 须显式 .to(device)(donor predictor 非自动递归搬 device)
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
            ref = keep  # taus[0] 最大 → 满覆盖参考
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
