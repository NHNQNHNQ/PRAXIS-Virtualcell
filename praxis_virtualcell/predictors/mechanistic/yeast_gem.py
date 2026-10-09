"""S. cerevisiae knockout-growth case using BiGG iMM904 at data/gems/iMM904.xml.gz. Reuse the E. coli
FBA/knockout/report pipeline, changing only SBML and annotations.
"""
from __future__ import annotations

from pathlib import Path

from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel, run_growth_case

_DEFAULT_YEAST_SBML = Path(__file__).resolve().parents[3] / "data" / "gems" / "iMM904.xml.gz"

_YEAST_BOUNDARY = (
    'FBA growth is a relative constrained feasibility/optimal flux measure under steady '
    'state, not an absolute growth rate. In-silico essentiality depends on the medium and '
    'objective and requires experimental confirmation; iMM904 is an S. cerevisiae '
    'genome-scale reconstruction with limited coverage (~905 genes).'
)


class YeastGEM(GemModel):
    """S. cerevisiae iMM904 GEM; default sbml_path is data/gems/iMM904.xml.gz."""

    def __init__(self, sbml_path: str | None = None) -> None:
        super().__init__(str(sbml_path or _DEFAULT_YEAST_SBML))


def run_yeast_growth_case(raw_req: dict, gem: YeastGEM | None = None, sbml_path: str | None = None):
    """Run yeast knockout FBA and return a 7-part report plus RouteDecision."""
    gem = gem or YeastGEM(sbml_path)
    return run_growth_case(raw_req, gem, tool="cobrapy iMM904",
                           model_label="iMM904 (S. cerevisiae)", boundary=_YEAST_BOUNDARY,
                           default_case_id="C5_yeast_deletion_growth")
