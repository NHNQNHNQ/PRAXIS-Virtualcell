"""Reference repair hints are scoped to exact observed values and source identity."""
from __future__ import annotations

from copy import deepcopy

import pytest

from praxis_virtualcell.llm_prediction.evidence import matching_value_pointers, validate_evidence
from praxis_virtualcell.llm_prediction.schemas import Assessment, EvidenceReference


def reference(**changes):
    fields = {"tool_call_id": "overview-1", "pointer": "/input_role", "source_id": "profile:one", "value": "baseline"}
    fields.update(changes)
    return EvidenceReference(**fields)


def calls():
    return {
        "overview-1": {"tool_call_id": "overview-1", "ok": True, "name": "overview", "data": {
            "source_id": "profile:one", "provenance": {"input_role": "baseline"},
            "other": {"source_id": "profile:other", "input_role": "baseline"},
        }},
        "overview-2": {"tool_call_id": "overview-2", "ok": True, "name": "overview", "data": {
            "source_id": "profile:one", "different_call": "only-in-other-call",
        }},
    }


def test_nested_provenance_has_exact_same_source_leaf_hint():
    ref = reference()
    assert matching_value_pointers(ref, calls()) == ["/provenance/input_role"]
    assert ref.pointer == "/input_role"  # No automatic correction.


@pytest.mark.parametrize("changes", [
    {"value": "invented"}, {"source_id": "invented"}, {"tool_call_id": "missing"},
    {"value": "only-in-other-call"},
])
def test_fabrication_or_other_calls_provide_no_hints(changes):
    assert matching_value_pointers(reference(**changes), calls()) == []


def test_failed_call_provides_no_hints():
    observed = calls()
    observed["overview-1"]["ok"] = False
    assert matching_value_pointers(reference(), observed) == []


def test_hints_use_json_pointer_escaping_and_are_capped_at_five():
    observed = calls()
    observed["overview-1"]["data"] = {"source_id": "profile:one", "a~/b": "baseline",
                                       "repeated": ["baseline"] * 20}
    assert matching_value_pointers(reference(), observed) == [
        "/a~0~1b", "/repeated/0", "/repeated/1", "/repeated/2", "/repeated/3",
    ]


def test_boolean_is_not_a_numeric_match_and_container_values_are_not_leaves():
    observed = calls()
    observed["overview-1"]["data"] = {"source_id": "profile:one", "value": True, "nested": {"number": 1}}
    assert matching_value_pointers(reference(value=1), observed) == ["/nested/number"]
    assert matching_value_pointers(reference(value={"number": 1}), observed) == []


def test_reference_diagnostic_preserves_offending_reference_and_original_rejection():
    ref = reference().model_dump()
    draft = {"activity": "uncertain", "mic_estimate": {"value": None, "reason": "unknown"},
             "supporting_evidence": [{"claim": "baseline metadata", "observations": [{
                 "gene_id": None, "field": "input_role", "value": "baseline", "evidence_ref": ref,
             }]}], "rationale_summary": "unknown"}
    model = Assessment.model_validate(draft)
    before = deepcopy(model.model_dump())
    diagnostics = []
    issues = validate_evidence(model, list(calls().values()), diagnostics=diagnostics)
    assert "unresolved_evidence_pointer" in issues
    for error in diagnostics:
        if error["code"] in {"invalid_observation_reference", "unresolved_evidence_pointer"}:
            assert error["offending_reference"] == ref
            assert error["matching_value_pointers"] == ["/provenance/input_role"]
    assert model.model_dump() == before
