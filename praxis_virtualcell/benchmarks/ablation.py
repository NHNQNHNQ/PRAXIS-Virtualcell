"""Week 7 GPT §9:最小可发表 ablation —— A(ML-only Coordinator) ↔ D(Full PRAXIS) 两极。

对抗验证(week7-ablation-design verdict, consistent=false)判定:4 档中 B 纯纸面、C≈D(同 agent 栈),
实为 2.5 档;§9.2 性能不损害是集合恒等同义反复 + predictor 集合错配;abstain_gain 数值违反 manifest 制度。
故采纳 verdict 的最小可发表方案:A↔D 两极 × 4 个 Mac 确定性可靠性/系统指标(已实跑验证, offline 全复现)。

诚实边界(见 finding_w7):
- 系统/可靠性维度 Mac offline 真测;性能维度只论证"communicative 包装对 predictor 前向零代价"(Week4b 等价
  性 atol 1e-6), 不声称 D 系统跑出更高 Pearson(communicative 层不参与张量计算)。
- A 用 Mac stub(无 bus/brain/species 检查)忠实模拟"无这些组件"——它确实没有, 非假装没有。
- B(brain-guided 无 bus)/C(communicative 无 reliability/critic)未实现, 留 backlog(verdict 指出 B 纸面、C≈D)。
- abstain_gain 数值(需 held-out OOD-pert split)未做:无 data/manifests 声明前不可发表(CLAUDE.md 不变量3)。
core/ 不改, 无 torch, Mac 可 import/run。
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
_OOD_TAGS = {"bacteria_ood", "martian_ood", "empty_ood"}        # 应被 abstain
_XSPECIES_OOD = {"bacteria_ood", "martian_ood"}                 # 不该用 mammalian predictor(wrong-model-use)


def run_group_A(request: dict) -> dict:
    """A. ML-only Coordinator(Mac stub):无 bus/brain/communication/provenance。
    直接调 3 mock predictor run_prediction + 手动平均;无 species/vocab 检查 → 对 OOD 一律硬预测。"""
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
    """D. Full PRAXIS-VirtualCell:build_runtime 全 agent, 经 message bus, 有 brain/ensemble/
    reliability/abstain/critic/provenance/report。"""
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
        # OOD 请求被正确拒/弃答的比例(§9.3)
        "OOD_rejection_rate": sum(1 for r in ood if res[r["request_id"]]["abstain"]
                                  or not res[r["request_id"]]["models_used"]) / len(ood),
        # 跨物种 OOD 请求误用 mammalian predictor 的比例(越低越好)
        "wrong_model_use_rate": sum(1 for r in xspecies if res[r["request_id"]]["models_used"]) / len(xspecies),
        # provenance schema 字段齐全度(present-as-key 口径, 非内容非空)
        "provenance_completeness": round(sum(_prov(res[r["request_id"]]) for r in requests) / len(requests), 3),
        # OOD 请求应弃答且弃答
        "abstain_correctness": sum(1 for r in ood if res[r["request_id"]]["abstain"]) / len(ood),
        # trace stage 齐全度
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
    lines += ["", "性能维度: communicative 包装对 predictor 前向零代价(Week4b 等价性 atol 1e-6),",
              "Full 不损害性能(不参与张量计算, Pearson 由共享 predictor 经 EvalAgent 给出)。",
              "B/C 档 + abstain_gain 数值 + 远端性能锚定见 finding_w7(诚实 backlog)。"]
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    r = run_ablation()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print("\n" + to_markdown(r))
