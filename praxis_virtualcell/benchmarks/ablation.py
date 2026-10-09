"""Compare A (ML-only coordinator stub) with D (full communicative runtime) on 4 deterministic reliability/system
metrics. A omits bus/brain/species checks and calls 3 mock predictors; B/C are not implemented.
Predictor-forward equivalence uses atol 1e-6, not a claim of improved Pearson. Numerical abstain_gain requires a
declared held-out OOD split. No torch is required.
"""
from __future__ import annotations

_STAGE_MARKERS = ("brain_retrieved", "applicability_decided", "predictor_result", "ensemble_done",
                  "reliability_decided", "critic_done", "provenance_done", "report_done")
_PROV_REQUIRED = ("rules_referenced", "rules_hit", "models_used", "models_rejected",
                  "models_failed", "critic_violations")


def _req(tag, species, targets, rid):
    return {"_tag": tag, "request_id": rid, "species": species, "perturbation_type": "gene",
            "perturbation_targets": targets, "input_modality": "scRNA",
            "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


SEED_REQUESTS = [
    _req("human_indist", "human", ["AHR"], "s1"),
    _req("bacteria_ood", "bacteria", ["recA"], "s2"),
    _req("martian_ood", "martian", ["AHR"], "s3"),
    _req("unknown_gene", "human", ["ZZZZ9"], "s4"),
    _req("empty_ood", "human", [], "s5"),
    _req("mouse_caution", "mouse", ["TRP53"], "s6"),
]
_OOD_TAGS = {"bacteria_ood", "martian_ood", "empty_ood"}
_XSPECIES_OOD = {"bacteria_ood", "martian_ood"}


def run_group_A(request: dict) -> dict:
    """ML-only coordinator stub: call 3 mock predictors and average manually, without bus, brain, communication, or
    provenance. No species/vocabulary check prevents forced OOD predictions.
    """
    from praxis_virtualcell.predictors.mock_cpa import MockCPAAgent
    from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent
    from praxis_virtualcell.predictors.mock_linear import MockLinearAgent

    mi = {"targets": request.get("perturbation_targets", [])}
    preds = [a.run_prediction(mi)["prediction"]["delta"]
             for a in (MockLinearAgent(), MockCPAAgent(), MockGEARSAgent())]
    n = max((len(p) for p in preds), default=0)
    delta = [sum(p[i] for p in preds) / len(preds) for i in range(n)] if n else []
    return {"abstain": False, "models_used": ["MockLinear", "MockCPA", "MockGEARS"],
            "prediction": {"delta": delta}, "trace": None, "provenance": None}


def run_group_D(request: dict) -> dict:
    """Full build_runtime agent stack with message bus, brain, ensemble, reliability, abstention, critic,
    provenance, and report.
    """
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

    rt = build_runtime()
    report = rt.run_workflow(VirtualCellRequest.from_dict(
        {k: v for k, v in request.items() if not k.startswith("_")}))
    return {"abstain": report["abstain"], "models_used": report["models_used"],
            "prediction": report["prediction"], "report": report, "trace": rt.bus.trace}


def _metrics_for(group_fn, requests) -> dict:
    res = {r["request_id"]: group_fn(r) for r in requests}
    ood = [r for r in requests if r["_tag"] in _OOD_TAGS]
    xspecies = [r for r in requests if r["_tag"] in _XSPECIES_OOD]

    def _prov(out):
        prov = (out.get("report") or {}).get("provenance") if out.get("report") else out.get("provenance")
        return sum(1 for k in _PROV_REQUIRED if k in prov) / len(_PROV_REQUIRED) if prov else 0.0

    def _trace(out):
        tr = out.get("trace")
        if not tr:
            return 0.0
        present = {m.message_type for m in tr}
        return sum(1 for s in _STAGE_MARKERS if s in present) / len(_STAGE_MARKERS)

    return {

        "OOD_rejection_rate": sum(1 for r in ood if res[r["request_id"]]["abstain"]
                                  or not res[r["request_id"]]["models_used"]) / len(ood),

        "wrong_model_use_rate": sum(1 for r in xspecies if res[r["request_id"]]["models_used"]) / len(xspecies),

        "provenance_completeness": round(sum(_prov(res[r["request_id"]]) for r in requests) / len(requests), 3),

        "abstain_correctness": sum(1 for r in ood if res[r["request_id"]]["abstain"]) / len(ood),

        "trace_completeness": round(sum(_trace(res[r["request_id"]]) for r in requests) / len(requests), 3),
    }


def run_ablation(requests=None) -> dict:
    reqs = requests or SEED_REQUESTS
    return {"A_ML_only": _metrics_for(run_group_A, reqs), "D_Full": _metrics_for(run_group_D, reqs)}


def to_markdown(result: dict) -> str:
    cols = ["OOD_rejection_rate", "wrong_model_use_rate", "provenance_completeness",
            "abstain_correctness", "trace_completeness"]
    lines = ["# Week 7 Ablation (A: ML-only Coordinator ↔ D: Full PRAXIS) — Mac offline, deterministic",
             "", "| arm | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for arm, label in [("A_ML_only", "A ML-only"), ("D_Full", "D Full")]:
        lines.append(f"| {label} | " + " | ".join(str(result[arm][c]) for c in cols) + " |")
    lines += ["", (
        'Performance scope: the communicative wrapper adds no predictor-forward computation '
        '(Week4b equivalence atol 1e-6); '
    ),
              (
                  'Full preserves predictor performance (it performs no tensor computation; the shared '
                  'predictor supplies Pearson through EvalAgent). '
              ),
              "B/C groups, numerical abstain_gain, and remote performance anchors remain documented in finding_w7."]
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    r = run_ablation()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print("\n" + to_markdown(r))
