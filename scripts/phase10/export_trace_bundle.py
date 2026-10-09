"""Phase 10 trace/provenance audit bundle 导出 —— 对 T10.3 的 16 case 请求集调 run_query。

权威请求集 = test_t10_3_end_to_end_cases 的 16 case（此处内嵌同一份,保持与 D-A 一致）。
导出每请求的 trace[](8 字段/条)+ provenance(rules_referenced/models_used/n_messages/per_call_hashes)
+ reliability_decision + 关键 structured_report 字段,落 PHASE10_TRACE_AUDIT.md。OFFLINE 确定性。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"
_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_BASE = {"input_modality": "scRNA", "task_type": "predict_delta_expression"}


def _req(name, species, ptype, targets, out="delta_expression"):
    return (name, {**_BASE, "species": species, "perturbation_type": ptype,
                   "perturbation_targets": targets, "output_modality": out})


# 与 test_t10_3_end_to_end_cases 的 16 core case 一致(S2b 远端变体不含,延后)
_CASES = [
    _req("S1_M1_membrane_FASN", "human", "gene", ["FASN"]),
    _req("S2_M2_genetic_AHR", "human", "gene", ["AHR"]),
    _req("S3_M3_mito_MYC_growth", "human", "gene", ["MYC"], "growth"),
    _req("S4_M4_cobra_b0720_b1136", "bacteria", "gene", ["b0720", "b1136"], "growth"),
    _req("S5_M5_biosynth_RPL5", "human", "gene", ["RPL5"]),
    _req("S6_M6_niche_state", "human", "medium", ["stromal_niche"], "state"),
    _req("S7_M7_state_IFNB1", "human", "ligand", ["IFNB1"], "state"),
    _req("S8_M8_degrad_UBB", "bacteria", "gene", ["UBB"], "growth"),
    _req("X1_M4M3_flux_IFNB1", "human", "ligand", ["IFNB1"], "flux"),
    _req("X2_M4M3_growth_MYC_KRAS", "human", "gene_combination", ["MYC", "KRAS"], "growth"),
    _req("X3_quad_SLC2A1_RPL5_PSMB5", "human", "gene", ["SLC2A1", "RPL5", "PSMB5"]),
    _req("X4_M4M8_bact_UBB", "bacteria", "gene", ["UBB"], "growth"),
    _req("X5_negtransfer_b0720_expr", "bacteria", "gene", ["b0720"]),
    _req("X6_C1gate_MYC_growth", "human", "gene", ["MYC"], "growth"),
    _req("X7_mouse_GATA1", "mouse", "gene", ["GATA1"]),
    _req("X8_diverge_SNAI1_state", "human", "gene", ["SNAI1"], "state"),
]


def _bundle_one(name: str, req: dict) -> dict:
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    prov = out["provenance"]
    return {
        "case": name,
        "request": req,
        "abstain": sr.get("abstain"),
        "models_used": sr.get("models_used"),
        "models_rejected": sr.get("models_rejected"),
        "prediction": sr.get("prediction"),
        "module_plan": prov.get("module_plan"),
        "provenance_keys": sorted(prov.keys()),
        "per_call_hashes": prov.get("per_call_hashes"),
        "rules_referenced": prov.get("rules_referenced"),
        "n_messages": prov.get("n_messages"),
        "reliability_decision": out.get("reliability_decision"),
        "trace_len": len(out.get("trace", [])),
        "llm_used_for_prediction": out.get("llm_used_for_prediction"),
    }


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    bundles = [_bundle_one(n, r) for n, r in _CASES]
    (_OUT / "trace_bundle.json").write_text(
        json.dumps(bundles, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    n_total = len(bundles)
    n_false = sum(b["llm_used_for_prediction"] is False for b in bundles)
    md = ["# PHASE 10 TRACE/PROVENANCE AUDIT BUNDLE", "",
          "> 对 T10.3 16 case 请求集调 `run_query`(OFFLINE 确定性)导出。原始 JSON 见 `trace_bundle.json`。",
          f"> `llm_used_for_prediction`:{n_false}/{n_total} case 均为 False(OFFLINE 恒 False,无 LLM 参与预测)。", "",
          "| case | abstain | models_used | prediction | module_plan.primary | trace_len |",
          "|---|---|---|---|---|---|"]
    for b in bundles:
        mp = b["module_plan"]
        prim = mp.get("primary") if mp else "None(unroutable)"
        md.append(f"| {b['case']} | {b['abstain']} | {b['models_used']} | {b['prediction']} | {prim} | {b['trace_len']} |")
    (_OUT / "PHASE10_TRACE_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[export_trace_bundle] wrote {_OUT / 'PHASE10_TRACE_AUDIT.md'} + trace_bundle.json ({len(bundles)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
