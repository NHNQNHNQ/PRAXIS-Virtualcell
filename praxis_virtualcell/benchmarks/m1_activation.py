"""Exercise disagreement and abstention through real remote donor predictor messages. Three bases produce
2000-dimensional deltas; disagreement_threshold=0.5 triggers abstention/downgrade. Historical 60-perturbation
run: disagreement 0.23–0.504, mean 0.359; 1 exceeded 0.5, with reliability_counts high=59/low=1. Record reports
in EvalLedger.
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


def _pert_set(ds):
    from bench.vcbench.loader import collate_perturbation
    from torch.utils.data import DataLoader

    s = set()
    for b in DataLoader(ds, batch_size=256, collate_fn=collate_perturbation):
        s.update(b["perturbation"])
    return s


def run_activation_demo(*, ckpt_dir: str | None = None, n: int = 60, ledger_path: str | None = None):
    ckpt_dir = ckpt_dir or CKPT_DIR
    if not ckpt_dir:
        raise RuntimeError("Set PRAXIS_DONOR_CHECKPOINT_ROOT or pass ckpt_dir explicitly")
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
