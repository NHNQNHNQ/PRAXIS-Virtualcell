"""Adapt real GearsWrapper.run_delta to a 7-part offline case report. Mark delta as
gears_internal/not_comparable_to_donor_base/non_deterministic; missing vocabulary/dependencies raise and become
failed, never fabricated donor-compatible output.
"""

from __future__ import annotations

import os

from praxis_virtualcell.agents.case_report import CaseReport
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.core.exceptions import UnsupportedEngine


def run_gears_case(raw_req: dict):
    """Return a human gene→expression GEARS CaseReport and RouteDecision using GEARS-internal, non-donor-comparable
    deltas.
    """
    from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

    norm = normalize_request(raw_req)
    dec = route(norm)
    targets = norm["perturbation_targets"]

    if norm["species"] != "human":
        raise UnsupportedEngine(
            "run_gears_case supports only human (GEARS Norman human vocabulary); "
            f"got species={norm['species']};fail-closed"
        )

    wrapper = GearsWrapper(ckpt_stem=os.environ.get("GEARS_CKPT"))
    out = wrapper.run_delta({"targets": targets})
    pred = out["prediction"]

    report = CaseReport(
        case_id=raw_req.get("case_id", "M2_gears_delta"),
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "normalized_targets": targets,
            "target_output": norm["target_output"],
        },
        models_tools_selected={
            "engine": dec.engine,
            "model": "gears",
            "method": "GEARS GNN (norman_2019)",
            "reason": dec.reason,
        },
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
        reliability_decision={
            "disposition": "accept",
            "caution_flags": ["gears_internal_delta", "not_comparable_to_donor_base", "non_deterministic"],
            "data_gated": False,
        },
        provenance_boundary={
            "model": "gears",
            "type": "public_model",
            "training_data": "norman_2019 (Perturb-seq, K562)",
            "no_fixed_seed": True,
            "non_deterministic": True,
            "rules_hit": [dec.reason],
            "boundary": (
                "Real GEARS prediction; delta=perturbed−control within GEARS and is not comparable to "
                "donor outputs (different metrics/splits and tables). GEARS has no fixed seed here; "
                "numerical output is nondeterministic."
            ),
        },
    )
    return report, dec
