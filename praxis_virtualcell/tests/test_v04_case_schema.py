"""Tests for v04 case schema."""
import pytest

from praxis_virtualcell.agents.case_report import (
    CaseReport,
    CaseReportError,
    routing_case,
    validate_case_report,
)

_FULL = dict(
    case_id="X", structured_input={"a": 1}, object_normalization={"b": 1},
    models_tools_selected={"c": 1}, raw_output={"d": 1}, baseline_comparison={"e": 1},
    reliability_decision={"f": 1}, provenance_boundary={"g": 1},
)


def test_validator_accepts_full_report():
    validate_case_report(CaseReport(**_FULL))


@pytest.mark.parametrize("missing", [
    "structured_input", "object_normalization", "models_tools_selected",
    "raw_output", "baseline_comparison", "reliability_decision", "provenance_boundary",
])
def test_validator_rejects_missing_or_empty(missing):
    bad = dict(_FULL)
    bad[missing] = {}
    with pytest.raises(CaseReportError):
        validate_case_report(CaseReport(**bad))


def test_validator_accepts_dict_form():
    validate_case_report(dict(_FULL, case_id="Y"))




def test_case_C3_mouse_ortholog_routing():
    c = routing_case("C3_mouse_ortholog", {
        "species": "mouse", "cell_type": "fibroblast", "perturbation_object": "gene",
        "perturbation_targets": ["Trp53"], "target_output": "expression"})
    validate_case_report(c)
    d = c.to_dict()
    assert d["models_tools_selected"]["engine"] == "donor_predictor"
    assert d["reliability_decision"]["disposition"] in ("caution", "downgrade")
    assert any("ortholog" in x for x in d["reliability_decision"]["caution_flags"])


def test_case_C4_ecoli_ko_routes_gem():
    c = routing_case("C4_ecoli_ko_growth", {
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "gene",
        "perturbation_targets": ["b0720"], "target_output": "growth"})
    validate_case_report(c)
    d = c.to_dict()
    assert d["models_tools_selected"]["engine"] == "gem_fba"

    assert "pending" in str(d["provenance_boundary"]).lower() or \
           "gem" in str(d["provenance_boundary"]).lower()


def test_case_C5_yeast_deletion_routes_gem():
    c = routing_case("C5_yeast_deletion_growth", {
        "species": "yeast", "cell_type": "S. cerevisiae", "perturbation_object": "gene",
        "perturbation_targets": ["YAL001C"], "target_output": "growth"})
    validate_case_report(c)
    assert c.to_dict()["models_tools_selected"]["engine"] == "gem_fba"
