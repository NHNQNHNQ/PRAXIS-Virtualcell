"""W2(v0.4):通用基因组尺度代谢模型(GEM/FBA)基座 —— 供 E. coli / yeast 复用。

物种无关的机制模型逻辑:载入 SBML → WT growth(biomass FBA)→ 大小写不敏感单基因 KO →
7 部分 CaseReport(真实数值 + 治理:基因不在 GEM → abstain/caution 不虚构)。

注:用 `with model:` 上下文手动 knock_out(单进程),避 cobra single_gene_deletion 多进程在
macOS 上 spawn 卡死。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KOResult:
    gene: str
    in_model: bool
    growth: float | None
    ratio: float | None
    essential: bool | None


class GemModel:
    """通用 GEM:任意 SBML 路径 → WT + 单基因 KO growth。"""

    def __init__(self, sbml_path: str) -> None:
        from cobra.io import read_sbml_model
        self.model = read_sbml_model(str(sbml_path))
        self.wt_growth = float(self.model.slim_optimize())

    def _resolve(self, gid: str) -> str | None:
        """大小写不敏感解析(E. coli b-number 小写、酵母系统名大写,schema 归一大写 → 需兼容)。"""
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
        with self.model:
            self.model.genes.get_by_id(resolved).knock_out()
            g = float(self.model.slim_optimize())
        g = max(g, 0.0)
        ratio = (g / self.wt_growth) if self.wt_growth else 0.0
        return KOResult(resolved, in_model=True, growth=g, ratio=ratio, essential=g < eps)

    def knockout_many(self, gene_ids) -> list[KOResult]:
        return [self.knockout(g) for g in gene_ids]


def run_growth_case(raw_req: dict, gem: GemModel, *, tool: str, model_label: str,
                    boundary: str, default_case_id: str):
    """通用 KO growth case:route → GEM 真跑 → 7 部分 CaseReport。返回 (CaseReport, RouteDecision)。

    治理:全部 target 不在 GEM → abstain(不虚构);部分不在 → caution(降级);全在 → accept。
    """
    from praxis_virtualcell.agents.species_schema import normalize_request
    from praxis_virtualcell.agents.route_table import route
    from praxis_virtualcell.agents.case_report import CaseReport

    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":                # 路由铁律:微生物 growth 必走机制模型
        raise ValueError(f"growth case 期望 gem_fba,route 给了 {dec.engine}")

    kos = gem.knockout_many(norm["perturbation_targets"])
    in_model = [k for k in kos if k.in_model]
    missing = [k.gene for k in kos if not k.in_model]

    if not in_model:
        disposition, flags = "abstain", ["all_targets_not_in_gem"]
    elif missing:
        disposition, flags = "caution", [f"targets_not_in_gem:{missing}"]
    else:
        disposition, flags = "accept", []

    report = CaseReport(
        case_id=raw_req.get("case_id", default_case_id),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"], "perturbation_object": norm["perturbation_object"],
            "normalized_targets": norm["perturbation_targets"], "target_output": norm["target_output"],
            "medium": norm.get("medium"),
        },
        models_tools_selected={"engine": dec.engine, "tool": tool,
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
        reliability_decision={"disposition": disposition, "caution_flags": flags, "data_gated": False},
        provenance_boundary={
            "tool": "cobrapy", "model": model_label, "objective": "biomass FBA",
            "rules_hit": [dec.reason], "boundary": boundary,
        },
    )
    return report, dec
