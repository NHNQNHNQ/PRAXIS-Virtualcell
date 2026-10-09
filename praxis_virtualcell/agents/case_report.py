"""Seven-part case reports, validation, and routing-prototype construction. Missing or empty sections raise
CaseReportError. Routing cases derive actual normalization and routing evidence; numerical model execution is
separate and pending/data-gated boundaries remain explicit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from praxis_virtualcell.agents.route_table import RouteDecision, route
from praxis_virtualcell.agents.species_schema import normalize_request

_REQUIRED = ("structured_input", "object_normalization", "models_tools_selected",
             "raw_output", "baseline_comparison", "reliability_decision", "provenance_boundary")


class CaseReportError(ValueError):
    """A case report is missing one of its 7 required sections or has an empty section."""


@dataclass
class CaseReport:
    case_id: str
    structured_input: dict = field(default_factory=dict)
    object_normalization: dict = field(default_factory=dict)
    models_tools_selected: dict = field(default_factory=dict)
    raw_output: dict = field(default_factory=dict)
    baseline_comparison: dict = field(default_factory=dict)
    reliability_decision: dict = field(default_factory=dict)
    provenance_boundary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def validate_case_report(report) -> None:
    """Require all 7 case-report sections to be nonempty; otherwise raise CaseReportError."""
    d = report.to_dict() if isinstance(report, CaseReport) else dict(report)
    for k in _REQUIRED:
        if not d.get(k):
            raise CaseReportError(f"case report missing or empty field: {k}")


def _boundary(dec: RouteDecision) -> str:
    """Describe the evidence boundary implied by the routing decision."""
    if dec.engine == "gem_fba" and not dec.data_gated:
        return ("routing verified: routed to mechanistic gem_fba; numerical growth/flux prediction is pending "
                "(requires GEM execution); this case verifies routing and reports no numerical growth estimate.")
    if dec.data_gated:
        return (
            'data-gated: downstream data/model assets are unavailable; routing evidence alone '
            'supports no performance claim.'
        )
    if dec.caution_flags:
        return (
            'cross-species transfer requires caution (for example, ortholog mapping); interpret '
            'predictions conservatively, without assuming native performance in the source '
            'species.'
        )
    if dec.disposition == "abstain":
        return "abstain: no applicable engine; the system abstains and produces no prediction."
    return "native human routing; numerical accuracy is defined by the core benchmark (Table A)."


def routing_case(case_id: str, raw_req: dict) -> CaseReport:
    """Build a routing-prototype case with 7 populated sections from the original request."""
    norm = normalize_request(raw_req)
    dec = route(norm)
    return CaseReport(
        case_id=case_id,
        structured_input=dict(raw_req),
        object_normalization={
            "species": norm["species"],
            "perturbation_object": norm["perturbation_object"],
            "normalized_targets": norm["perturbation_targets"],
            "target_output": norm["target_output"],
        },
        models_tools_selected={"engine": dec.engine, "reason": dec.reason},
        raw_output={"route_decision": dec.to_dict()},
        baseline_comparison={
            "ungoverned": (
                'Calling a mammalian predictor without applicability checks can force predictions for '
                'unsupported species.'
            ),
            "governed": f"engine={dec.engine} · disposition={dec.disposition} · reason={dec.reason}",
        },
        reliability_decision={
            "disposition": dec.disposition,
            "caution_flags": list(dec.caution_flags),
            "data_gated": dec.data_gated,
        },
        provenance_boundary={"rules_hit": [dec.reason], "boundary": _boundary(dec)},
    )
