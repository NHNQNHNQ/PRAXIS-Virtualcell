"""W2.2(v0.4):Yeast(S. cerevisiae)KO growth case —— 复用通用 GemModel。

用 iMM904(BiGG,S. cerevisiae 基因组尺度模型;`data/gems/iMM904.xml.gz`)。与 E. coli case
共用同一 FBA/KO/case 管线(gem_model.run_growth_case),仅换 SBML 与标注 → 证明框架对不同物种
机制模型可扩展(代表物种桥梁:真核微生物)。
"""
from __future__ import annotations

from pathlib import Path

from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel, run_growth_case

# repo_root/data/gems/iMM904.xml.gz(parents[3] = repo 根)
_DEFAULT_YEAST_SBML = Path(__file__).resolve().parents[3] / "data" / "gems" / "iMM904.xml.gz"

_YEAST_BOUNDARY = ("FBA growth 是约束型可行性/最优通量的相对量(steady-state 假设),**非**绝对生长"
                   "速率;in-silico essentiality 随培养基/目标函数变,需湿实验证实;iMM904 是 S. cerevisiae "
                   "基因组尺度重建,基因覆盖有限(~905 genes)。")


class YeastGEM(GemModel):
    """S. cerevisiae GEM(iMM904)。sbml_path 缺省用 data/gems/iMM904.xml.gz。"""

    def __init__(self, sbml_path: str | None = None) -> None:
        super().__init__(str(sbml_path or _DEFAULT_YEAST_SBML))


def run_yeast_growth_case(raw_req: dict, gem: YeastGEM | None = None, sbml_path: str | None = None):
    """Yeast KO growth case → 7 部分 CaseReport(真实数值)。返回 (CaseReport, RouteDecision)。"""
    gem = gem or YeastGEM(sbml_path)
    return run_growth_case(raw_req, gem, tool="cobrapy iMM904",
                           model_label="iMM904 (S. cerevisiae)", boundary=_YEAST_BOUNDARY,
                           default_case_id="C5_yeast_deletion_growth")
