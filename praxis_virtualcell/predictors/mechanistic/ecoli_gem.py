"""W2.1(v0.4):E. coli KO growth case —— 复用通用 GemModel(见 gem_model.py)。

用 cobrapy **自带** e_coli_core(textbook)GEM,无需联网、无外部数据。机制模型(FBA),
route_table → gem_fba,证明 PRAXIS 能接入非 NN 的机制型预测处理"虚拟细菌细胞"任务。
"""
from __future__ import annotations

import os

from praxis_virtualcell.predictors.mechanistic.gem_model import (  # noqa: F401 (re-export)
    GemModel,
    KOResult,
    run_growth_case,
)

_ECOLI_BOUNDARY = ("FBA growth 是约束型可行性/最优通量的相对量(steady-state 假设),**非**绝对生长"
                   "速率;in-silico essentiality,需湿实验证实;e_coli_core 是核心代谢子集,非全基因组模型。")


def _bundled_textbook_path() -> str:
    import cobra
    return os.path.join(os.path.dirname(cobra.__file__), "data", "textbook.xml.gz")


class EcoliGEM(GemModel):
    """E. coli core GEM(cobrapy textbook,自带),默认无参加载。"""

    def __init__(self, sbml_path: str | None = None) -> None:
        super().__init__(sbml_path or _bundled_textbook_path())


def run_ecoli_growth_case(raw_req: dict, gem: EcoliGEM | None = None):
    """E. coli KO growth case → 7 部分 CaseReport(真实数值)。返回 (CaseReport, RouteDecision)。"""
    gem = gem or EcoliGEM()
    return run_growth_case(raw_req, gem, tool="cobrapy e_coli_core (textbook)",
                           model_label="e_coli_core (textbook)", boundary=_ECOLI_BOUNDARY,
                           default_case_id="C4_ecoli_ko_growth")
