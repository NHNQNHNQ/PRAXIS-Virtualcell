"""Cell-type domain gate using the same declaring/unsupported logic as reliability without coupling its decision
path. Trigger only when all used predictors that declare supported_cell_types are out of domain.
Already-abstained reports are unchanged; the gate adds public abstention after reliability downgrade while
retaining numerical reliability.
"""
from __future__ import annotations


def check_cell_type_domain(request: dict, brain_context: dict, models_used: list,
                           *, reliability_abstained: bool = False) -> list[str]:
    """Return used predictors whose declared cell-type domain excludes the request, only when all declaring
    predictors are outside it. Return an empty list for prior abstention, absent cell type/models/declarations,
    or any supported declaration.
    """
    if reliability_abstained:
        return []
    req_ct = request.get("cell_type")
    if not req_ct or not models_used:
        return []
    appmap = brain_context.get("model_applicability") or {}
    declaring = [n for n in models_used
                 if appmap.get(n, {}).get("supported_cell_types") is not None]
    unsupported = [n for n in declaring if req_ct not in appmap[n]["supported_cell_types"]]
    if declaring and len(unsupported) == len(declaring):
        return unsupported
    return []
