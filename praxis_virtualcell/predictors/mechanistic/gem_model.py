"""Species-independent GEM/FBA engine: load SBML, solve WT biomass growth, resolve single-gene knockouts
case-insensitively, and form a 7-part governed report. Absent genes abstain/caution without fabricated growth.
Use single-process model contexts to avoid macOS multiprocessing spawn stalls.
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
    """Generic SBML model for WT and single-gene knockout growth."""

    def __init__(self, sbml_path: str) -> None:
        from cobra.io import read_sbml_model
        self.model = read_sbml_model(str(sbml_path))
        self.wt_growth = float(self.model.slim_optimize())

    def _resolve(self, gid: str) -> str | None:
        """Resolve IDs case-insensitively to reconcile lowercase E. coli b-numbers, uppercase yeast names, and
        schema normalization.
        """
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
    """Route and execute knockout FBA, returning a 7-part report and RouteDecision. All absent targets abstain,
    some absent targets caution, and complete coverage accepts.
    """
    from praxis_virtualcell.agents.case_report import CaseReport
    from praxis_virtualcell.agents.route_table import route
    from praxis_virtualcell.agents.species_schema import normalize_request

    norm = normalize_request(raw_req)
    dec = route(norm)
    if dec.engine != "gem_fba":
        raise ValueError(f"growth case expected gem_fba; routing selected {dec.engine}")

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
