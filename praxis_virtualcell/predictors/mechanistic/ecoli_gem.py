"""E. coli knockout-growth case using reusable GemModel and bundled cobra e_coli_core textbook assets. The
mechanistic FBA path requires no network or external dataset.
"""
from __future__ import annotations

import os

from praxis_virtualcell.predictors.mechanistic.gem_model import (  # noqa: F401 (re-export)
    GemModel,
    KOResult,
    run_growth_case,
)

_ECOLI_BOUNDARY = (
    'FBA growth is a relative constrained feasibility/optimal flux measure under steady '
    'state, not an absolute growth rate. In-silico essentiality requires experimental '
    'confirmation; e_coli_core is a core metabolic subset, not a genome-scale model.'
)


def _bundled_textbook_path() -> str:
    import cobra
    return os.path.join(os.path.dirname(cobra.__file__), "data", "textbook.xml.gz")


class EcoliGEM(GemModel):
    """Bundled cobra textbook E. coli core GEM with default parameterless loading."""

    def __init__(self, sbml_path: str | None = None) -> None:
        super().__init__(sbml_path or _bundled_textbook_path())


def run_ecoli_growth_case(raw_req: dict, gem: EcoliGEM | None = None):
    """Run E. coli knockout FBA and return a 7-part CaseReport plus RouteDecision."""
    gem = gem or EcoliGEM()
    return run_growth_case(raw_req, gem, tool="cobrapy e_coli_core (textbook)",
                           model_label="e_coli_core (textbook)", boundary=_ECOLI_BOUNDARY,
                           default_case_id="C4_ecoli_ko_growth")
