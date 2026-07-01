"""W2.1(v0.4):E. coli 基因组尺度代谢模型(GEM)接入 —— WT/KO growth + essentiality。

用 cobrapy **自带** e_coli_core(textbook)模型,无需联网、无外部数据。这是**机制模型**(FBA),
与神经网络 predictor 走完全不同的引擎(route_table → gem_fba),证明 PRAXIS 能接入非 NN 的机制型
预测,处理"虚拟细菌细胞"任务。

治理点:查询基因**不在 GEM 中**时,系统 downgrade/abstain(不虚构生长),而非硬出预测。

注:cobra 的 single_gene_deletion 默认多进程在 macOS 上会卡;这里用 `with model:` 上下文手动
knock_out(单进程,快),避免多进程 spawn 问题。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _bundled_textbook_path() -> str:
    import cobra
    return os.path.join(os.path.dirname(cobra.__file__), "data", "textbook.xml.gz")


@dataclass
class KOResult:
    gene: str
    in_model: bool
    growth: float | None       # KO 后 growth(不在模型 → None)
    ratio: float | None        # growth / WT
    essential: bool | None     # growth ≈ 0


class EcoliGEM:
    """E. coli core GEM(cobrapy textbook),提供 WT + 单基因 KO growth。"""

    def __init__(self, sbml_path: str | None = None) -> None:
        from cobra.io import read_sbml_model
        self.model = read_sbml_model(sbml_path or _bundled_textbook_path())
        self.wt_growth = float(self.model.slim_optimize())

    def _resolve(self, gid: str) -> str | None:
        """大小写不敏感解析基因 id(E. coli b-number 小写,schema 归一大写 → 需兼容)。"""
        gid = str(gid).strip()
        for cand in (gid, gid.lower(), gid.upper()):
            if self.model.genes.has_id(cand):
                return cand
        return None

    def knockout(self, gene_id: str, eps: float = 1e-6) -> KOResult:
        resolved = self._resolve(gene_id)
        if resolved is None:
            return KOResult(str(gene_id).strip(), in_model=False,
                            growth=None, ratio=None, essential=None)
        gid = resolved                          # 用模型内真实 id(如 b0720)
        with self.model:                       # 上下文:退出即恢复,单进程无 spawn
            self.model.genes.get_by_id(gid).knock_out()
            g = float(self.model.slim_optimize())
        g = max(g, 0.0)                         # FBA 可能返回 -0.0/微小负值,截到 0
        ratio = (g / self.wt_growth) if self.wt_growth else 0.0
        return KOResult(gid, in_model=True, growth=g, ratio=ratio, essential=g < eps)

    def knockout_many(self, gene_ids) -> list[KOResult]:
        return [self.knockout(g) for g in gene_ids]


def run_ecoli_growth_case(raw_req: dict, gem: "EcoliGEM | None" = None):
    """完整 E. coli KO growth case:route → GEM 真跑 → 7 部分 CaseReport(真实数值)。

    治理:全部 target 不在 GEM → abstain(不虚构);部分不在 → caution(降级)。
    """
    from praxis_virtualcell.agents.species_schema import normalize_request
    from praxis_virtualcell.agents.route_table import route
    from praxis_virtualcell.agents.case_report import CaseReport

    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":                # 路由铁律:细菌 growth 必走 GEM
        raise ValueError(f"E. coli growth case 期望 gem_fba,route 给了 {dec.engine}")

    gem = gem or EcoliGEM()
    kos = gem.knockout_many(norm["perturbation_targets"])
    in_model = [k for k in kos if k.in_model]
    missing = [k.gene for k in kos if not k.in_model]

    # reliability:据"是否在模型内 + 是否有 essential"给 disposition
    if not in_model:
        disposition, flags = "abstain", ["all_targets_not_in_gem"]
    elif missing:
        disposition, flags = "caution", [f"targets_not_in_gem:{missing}"]
    else:
        disposition, flags = "accept", []

    return CaseReport(
        case_id=raw_req.get("case_id", "C4_ecoli_ko_growth"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"], "perturbation_object": norm["perturbation_object"],
            "normalized_targets": norm["perturbation_targets"], "target_output": norm["target_output"],
            "medium": norm.get("medium"),
        },
        models_tools_selected={"engine": dec.engine, "tool": "cobrapy e_coli_core (textbook)",
                               "method": "FBA (constraint-based)", "reason": dec.reason},
        raw_output={
            "wt_growth": round(gem.wt_growth, 5),
            "knockouts": [{"gene": k.gene, "in_model": k.in_model,
                           "growth": None if k.growth is None else round(k.growth, 5),
                           "ratio": None if k.ratio is None else round(k.ratio, 4),
                           "essential": k.essential} for k in kos],
        },
        baseline_comparison={
            "baseline": "WT (no knockout) growth", "wt_growth": round(gem.wt_growth, 5),
            "essential_count": sum(1 for k in in_model if k.essential),
            "n_in_model": len(in_model), "n_missing": len(missing),
        },
        reliability_decision={"disposition": disposition, "caution_flags": flags,
                              "data_gated": False},
        provenance_boundary={
            "tool": "cobrapy", "model": "e_coli_core (textbook)", "objective": "biomass FBA",
            "rules_hit": [dec.reason],
            "boundary": ("FBA growth 是约束型可行性/最优通量的相对量(steady-state 假设),"
                         "**非**绝对生长速率;in-silico essentiality,需湿实验证实;"
                         "e_coli_core 是核心代谢子集,非全基因组模型。"),
        },
    ), dec
