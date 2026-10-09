"""Declarative routing and applicability rules for normalized requests. donor_predictor covers mammalian scRNA
deltas; gem_fba covers bacterial/yeast growth and flux; embedding covers drug/ligand signatures; reject denotes
no applicable engine. Dispositions are accept/caution/downgrade/abstain. Mammalian predictors must not answer
microbial growth requests, and unsupported microbial expression/state requests abstain. Routing declares
capability, not numerical performance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

ENGINES = ("donor_predictor", "gem_fba", "embedding", "state_scoring", "pathway_scoring",
           "communication", "spatial_niche", "reject")

_MAMMAL = {"human", "mouse"}
_MICROBE = {"bacteria", "yeast"}
_GENE_LIKE = {"gene", "gene_combination"}
_METABOLIC = {"growth", "flux"}


@dataclass
class RouteDecision:
    engine: str
    disposition: str                       # accept / caution / downgrade / abstain
    reason: str
    caution_flags: list[str] = field(default_factory=list)
    data_gated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def route(req: dict) -> RouteDecision:
    """Map a normalized request to a declarative routing decision without executing a model."""
    sp = req["species"]
    obj = req["perturbation_object"]
    out = req["target_output"]


    if out in _METABOLIC:
        if sp in _MICROBE and (obj in _GENE_LIKE or obj in ("medium", "drug")):

            return RouteDecision("gem_fba", "accept",
                                 reason=f"{sp}_metabolic_gem_fba")
        if sp in _MAMMAL and out == "flux":

            return RouteDecision("pathway_scoring", "caution",
                                 reason="mammalian_metabolic_pathway_scoring")
        if sp in _MAMMAL:

            return RouteDecision("gem_fba", "downgrade",
                                 reason="mammalian_growth_model_not_wired",
                                 data_gated=True)

        return RouteDecision("reject", "abstain",
                             reason="no_metabolic_engine_for_request")


    if out == "state":
        if sp == "human":
            if obj == "medium":

                return RouteDecision("spatial_niche", "accept", reason="human_spatial_niche_state")
            return RouteDecision("state_scoring", "accept", reason="human_cell_state_scoring")
        if sp == "mouse":
            return RouteDecision("state_scoring", "caution",
                                 reason="mouse_cell_state_scoring_ortholog",
                                 caution_flags=["ortholog_required"])
        return RouteDecision("reject", "abstain", reason="no_state_engine_for_species")


    if out == "communication":
        if sp == "human":
            return RouteDecision("communication", "accept",
                                 reason="human_ligand_receptor_coexpression")
        return RouteDecision("reject", "abstain", reason="no_communication_engine_for_species")


    if obj == "drug":
        return RouteDecision("embedding", "caution",
                             reason="drug_signature_db_wired", data_gated=False)

    if obj == "ligand":
        return RouteDecision("embedding", "downgrade",
                             reason="ligand_signature_model_data_gated", data_gated=True)


    if obj in _GENE_LIKE and out == "expression":
        if sp == "human":
            return RouteDecision("donor_predictor", "accept",
                                 reason="human_native_scrna_predictor")
        if sp == "mouse":

            return RouteDecision("donor_predictor", "caution",
                                 reason="human_predictor_transfer_to_mouse_requires_ortholog",
                                 caution_flags=["ortholog_required"])
        if sp in _MICROBE:

            return RouteDecision("reject", "abstain",
                                 reason="mammalian_scrna_predictor_not_applicable")

    return RouteDecision("reject", "abstain", reason="no_applicable_engine")
