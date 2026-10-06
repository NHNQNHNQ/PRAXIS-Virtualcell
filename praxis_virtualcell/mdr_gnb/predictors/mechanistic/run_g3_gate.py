"""Gate G3 入口:对锚点组合跑机理三支柱并落报告。

消融所需的 with/without 下游 VME 由真实消融实验(env/g3_ablation.py)产出的
`data/mdr_gnb/reports/gates/ablation_inputs.json` 提供;若该 json 存在则读真值,
否则用占位统计并在报告注明"待接真实消融"——保证脚本可跑、可证伪逻辑可验,
同时不伪装成真实性能。
"""
from __future__ import annotations

import json
from pathlib import Path

from praxis_virtualcell.mdr_gnb.g3_anchors import G3_ANCHORS

from .cell_state import BacterialCellState
from .falsifiability import (
    correlate_mechanism_supervision,
    run_ablation,
    run_intervention_consistency,
)
from .report import build_mechanistic_report, mechanism_gate_decision

# Backwards-compatible public name for offline callers.  The pure root-level
# data module keeps production membership checks independent from this runner.
ANCHORS = G3_ANCHORS

# 真实消融评估产物(存在则读真值)
_ABLATION_JSON = Path("data/mdr_gnb/reports/gates/ablation_inputs.json")


def _load_ablation_inputs(key: str) -> tuple[dict, dict]:
    if _ABLATION_JSON.exists():
        data = json.loads(_ABLATION_JSON.read_text(encoding="utf-8"))
        if key in data:
            e = data[key]
            return e["with_mechanism"], e["without_mechanism"]
    # 占位(报告会注明来源为占位):结构合法,便于验证可证伪逻辑
    return (
        {"vme": 0.06, "major_error": 0.08, "n_strains": 0, "source": "placeholder"},
        {"vme": 0.14, "major_error": 0.10, "n_strains": 0, "source": "placeholder"},
    )


def run_g3_gate(out_dir: str | Path = "data/mdr_gnb/reports/mechanistic") -> dict:
    out: dict[str, dict] = {}
    for key, cfg in ANCHORS.items():
        with_m, without_m = _load_ablation_inputs(key)
        abl = run_ablation(with_m, without_m)
        base = BacterialCellState(species=cfg["species"])
        cons = run_intervention_consistency(base, cfg["interventions"])
        sup = correlate_mechanism_supervision(
            predicted={"beta_lactamase_activity": [], "efflux_activity": []},
            measured={},  # 独立功能数据未接入 -> unverified(诚实)
        )
        report_path = build_mechanistic_report(
            species=cfg["species"],
            drug=cfg["drug"],
            ablation=abl,
            consistency=cons,
            supervision=sup,
            out_dir=out_dir,
        )
        out[key] = {
            "report_path": report_path,
            "decision": mechanism_gate_decision(abl, cons),
            "consistency": cons,
            "ablation_source": with_m.get("source", "real"),
        }
    return out


if __name__ == "__main__":  # 手动跑 gate
    res = run_g3_gate()
    for k, v in res.items():
        print(k, "->", v["decision"]["allow_mechanism_explanation"], v["report_path"])
