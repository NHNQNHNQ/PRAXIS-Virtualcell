"""P10.B M2:GEARS 真实预测 → offline 主链 CaseReport adapter(.53 gated)。

复用 GearsWrapper.run_delta(GEARS-内部 delta=扰动−对照),产 7 部分 CaseReport。诚实:
delta 明标 gears_internal / not_comparable_to_donor_base / non_deterministic,不冒充 donor delta;
基因不在 GEARS vocab / 缺 torch → fail-closed(GearsWrapper 抛 → 此处不吞,由既有 handle 归 failed)。
真跑是 .53 的事(Mac 无 torch → GearsWrapper.run_delta 即抛)。
"""
from __future__ import annotations

import os

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.core.exceptions import UnsupportedEngine


def run_gears_case(raw_req: dict):
    """human gene→expression GEARS case → (CaseReport, RouteDecision)。GEARS-内部 delta,非 donor 可比。"""
    from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

    norm = normalize_request(raw_req)
    dec = route(norm)
    targets = norm["perturbation_targets"]

    # runner 自兜底 human 约束(不只依赖 dispatch),防 mouse Ahr→AHR 命中 human vocab 张冠李戴
    if norm["species"] != "human":
        raise UnsupportedEngine(
            f"run_gears_case 仅 human(GEARS norman human vocab);got species={norm['species']};fail-closed")

    wrapper = GearsWrapper(ckpt_stem=os.environ.get("GEARS_CKPT"))
    out = wrapper.run_delta({"targets": targets})       # 缺 torch/ckpt/vocab → 抛(fail-closed)
    pred = out["prediction"]

    report = CaseReport(
        case_id=raw_req.get("case_id", "M2_gears_delta"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"], "perturbation_object": norm["perturbation_object"],
            "normalized_targets": targets, "target_output": norm["target_output"],
        },
        models_tools_selected={"engine": dec.engine, "model": "gears",
                               "method": "GEARS GNN (norman_2019)", "reason": dec.reason},
        raw_output={
            "gears_delta": pred["delta"],
            "targets": targets,
            "condition": pred["condition"],
            "value_type": pred["value_type"],
            "not_comparable_to_donor_base": pred["not_comparable_to_donor_base"],
            "non_deterministic": pred["non_deterministic"],
        },
        baseline_comparison={
            "baseline": "GEARS ctrl condition (mean-over-cells)",
            "value_type": "gears_internal_delta",
            "not_comparable_to_donor_base": True,
        },
        reliability_decision={"disposition": "accept", "caution_flags": ["gears_internal_delta",
                              "not_comparable_to_donor_base", "non_deterministic"], "data_gated": False},
        provenance_boundary={
            "model": "gears", "type": "public_model", "training_data": "norman_2019 (Perturb-seq, K562)",
            "no_fixed_seed": True, "non_deterministic": True,
            "rules_hit": [dec.reason],
            "boundary": ("GEARS 真实预测(.53);delta=扰动−对照 GEARS-内部,非 donor 可比(指标/split 不同,"
                         "不同表对比);GEARS 无固定 seed,数值非确定性。"),
        },
    )
    return report, dec
