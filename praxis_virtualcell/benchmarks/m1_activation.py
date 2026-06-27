"""M1(v0.3):真 predictor 通讯流"通电"证明 —— disagreement / abstain 在真模型上自发激活。

解 v0.2 局限「声明式机制 mock 不激活」:mock e2e 是 1 维 delta + 零向量伪分歧;真 donor predictor
(linear/latent/gnn,run_request_ml 已注册)输出 2000 维真 delta → ensemble disagreement 变真值 →
ReliabilityAgent 越阈值(generic default_abstain_rules disagreement_threshold=0.5)即**自发 abstain/降级**。

跑一批 Norman 真扰动过完整通讯流,逐样本记进 EvalLedger。仅远端 virtualcell env。
实测(60 扰动,cpa 槽位=latent;3 base):disagreement 分布 0.23~0.504(mean 0.359,非伪 0.5),
1 个越 0.5 → 真 abstain(reliability_counts {high:59, low:1})。机制运行时真激活,非纸面、非手搓。

用法:conda activate virtualcell; python -m praxis_virtualcell.benchmarks.m1_activation
"""
from __future__ import annotations

import sys

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

CKPT_DIR = _DONOR + "/runs/full_bench_20260521_060815/checkpoints/norman_2019"


def _pert_set(ds):
    from torch.utils.data import DataLoader

    from bench.vcbench.loader import collate_perturbation

    s = set()
    for b in DataLoader(ds, batch_size=256, collate_fn=collate_perturbation):
        s.update(b["perturbation"])
    return s


def run_activation_demo(*, ckpt_dir: str = CKPT_DIR, n: int = 60, ledger_path: str | None = None):
    from praxis_virtualcell.benchmarks.eval_ledger import EvalLedger
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman
    from praxis_virtualcell.workflows.predict_delta_expression_ml import build_runtime_ml

    train_perts = _pert_set(load_norman(split="train", seed=0, max_cells=2))
    ds = load_norman(split="test", seed=1, max_cells=2)
    test_perts = sorted(_pert_set(ds) - {"control"})
    rt = build_runtime_ml(ckpt_dir, norman_ds=ds)
    led = EvalLedger()
    for i, pname in enumerate(test_perts[:n]):
        targets = pname.split("+")
        req = {"request_id": f"r{i}", "species": "human", "perturbation_type": "gene",
               "perturbation_targets": targets, "input_modality": "scRNA",
               "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
        report = rt.run_workflow(VirtualCellRequest.from_dict(req))
        led.record(report, request=req, seen_in_train=(pname in train_perts))
    if ledger_path:
        led.to_jsonl(ledger_path)
    return led


def main() -> None:
    import json

    led = run_activation_demo(ledger_path="/tmp/m1_ledger.jsonl")
    print("SUMMARY:", json.dumps(led.summary(), ensure_ascii=False))
    scores = sorted(e.disagreement_score for e in led.entries if e.disagreement_score is not None)
    if scores:
        print(f"disagreement min/median/max = {scores[0]:.3f}/{scores[len(scores)//2]:.3f}/{scores[-1]:.3f}")
    print("n_abstain =", sum(1 for e in led.entries if e.abstain),
          " n_triggered =", sum(1 for e in led.entries if e.disagreement_triggered),
          " n_models =", led.entries[0].disagreement_n_models if led.entries else None)


if __name__ == "__main__":
    main()
