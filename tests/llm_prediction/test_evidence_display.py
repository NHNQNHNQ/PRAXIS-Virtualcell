"""Prose display rounding must not loosen the machine evidence contract."""
from __future__ import annotations

from copy import deepcopy

import pytest

from praxis_virtualcell.llm_prediction.evidence import validate_evidence
from praxis_virtualcell.llm_prediction.schemas import Assessment


def measured_assessment(actual, displayed):
    gene_id = "ABUW_0009"
    source_id = f"omics:AB5075-AZI000:gene:{gene_id}"
    reference = {"tool_call_id": "genes-1", "pointer": "/genes/0/expression_value",
                 "source_id": source_id, "value": actual}
    draft = {"activity": "uncertain", "mic_estimate": {"value": None, "reason": "unknown"},
             "supporting_evidence": [{"claim": f"{gene_id} 表达值 {displayed}",
                 "observations": [{"gene_id": gene_id, "field": "expression_value", "value": actual,
                                   "evidence_ref": deepcopy(reference)}],
                 "evidence_refs": [deepcopy(reference)]}], "rationale_summary": "unknown"}
    calls = [{"tool_call_id": "genes-1", "name": "query_genes", "ok": True,
              "data": {"genes": [{"gene_id": gene_id, "source_id": source_id,
                                   "expression_value": actual}]}}]
    return draft, calls


@pytest.mark.parametrize("actual,displayed", [
    (9.521245002746582, "9.52"),
    (9.533349990844727, "9.53"),
    (4.208322525024414, "4.21"),
    (9.521245002746582, "9.521"),
    (9.521245002746582, "9.5212"),
    (9.521245002746582, "9.52e0"),
    (9.525, "9.53"),
    (-1.235, "-1.24"),
    (9.0, "9"),
])
def test_correct_display_rounding_preserves_exact_structured_observation(actual, displayed):
    draft, calls = measured_assessment(actual, displayed)
    assessment = Assessment.model_validate(draft)
    before = assessment.model_dump()
    assert validate_evidence(assessment, calls) == []
    assert assessment.model_dump() == before


@pytest.mark.parametrize("displayed", ["9.54", "9.53", "9.520", "9.5213", "9", "10",
                                      "9.5212450027465821"])
def test_wrong_decimal_or_inexact_integer_is_rejected(displayed):
    draft, calls = measured_assessment(9.521245002746582, displayed)
    assert "expression_quantity_in_text_not_observed" in validate_evidence(Assessment.model_validate(draft), calls)


@pytest.mark.parametrize("change,issue", [
    ("reference_value", "quoted_value_does_not_match_tool"),
    ("observation_value", "observation_value_does_not_match_tool"),
    ("source", "source_id_does_not_match_tool"),
    ("pointer", "unresolved_evidence_pointer"),
])
def test_rounded_prose_does_not_admit_fabricated_machine_evidence(change, issue):
    draft, calls = measured_assessment(9.521245002746582, "9.52")
    item = draft["supporting_evidence"][0]
    if change == "reference_value":
        item["evidence_refs"][0]["value"] = 9.52
    elif change == "observation_value":
        item["observations"][0]["value"] = 9.52
    elif change == "source":
        item["evidence_refs"][0]["source_id"] = "omics:invented"
    elif change == "pointer":
        item["evidence_refs"][0]["pointer"] = "/genes/999/expression_value"
    issues = validate_evidence(Assessment.model_validate(draft), calls)
    assert issue in issues
    assert "expression_quantity_in_text_not_observed" not in issues


def test_empty_structured_observations_still_fail_despite_valid_references():
    draft, calls = measured_assessment(9.521245002746582, "9.52")
    draft["supporting_evidence"][0]["observations"] = []
    assert validate_evidence(Assessment.model_validate(draft), calls) == [
        "evidence_claim_requires_structured_observations"]
