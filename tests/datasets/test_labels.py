"""Experimental endpoints remain separate from inference and predicted values."""
from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from praxis_virtualcell.datasets.labels import EndpointLabel, ExperimentRecord


def payload():
    return {
        "record_id": "activity:1",
        "molecule": {"source_molecule_id": "CHEMBL1", "canonical_smiles": "CCO", "identity_key": "example"},
        "organism": {"species": "Acinetobacter baumannii", "strain": "AB5075", "isolate_id": None,
                     "identity_evidence": "structured_assay_strain"},
        "conditions": {"medium": None, "exposure_hours": 16.0},
        "endpoint": {"kind": "MIC", "relation": ">", "unit": "ug/mL", "value": 64.0,
                     "raw": {"value": "64", "unit": "ug/mL", "relation": ">"},
                     "conversion": "identity mass unit"},
        "source": {"source_id": "chembl:activity:1", "origin": "experimental_database",
                   "reported_as_measured": True, "measured_qualifier": "Reported experimental MIC.",
                   "native_locator": {"file": "source.csv", "csv_line": 2}},
        "pairing": {"status": "same_strain_reference", "profile_ids": ["AB5075-AZI000"]},
        "admission": {"label_eligible": True, "paired_omics_eligible": False,
                      "reasons": ["No condition-matched omics evidence."]},
    }


@pytest.mark.parametrize("relation,censor,lower,upper,closed", [
    ("=", "exact", 64.0, 64.0, (True, True)),
    ("<", "left", None, 64.0, (True, False)),
    ("<=", "left", None, 64.0, (True, True)),
    (">", "right", 64.0, None, (False, True)),
    (">=", "right", 64.0, None, (True, True)),
])
def test_relation_keeps_censor_bounds_without_midpoint(relation, censor, lower, upper, closed):
    value = payload()["endpoint"]
    value["relation"] = relation
    endpoint = EndpointLabel.model_validate(value)
    assert endpoint.censoring == censor
    assert (endpoint.lower, endpoint.upper) == (lower, upper)
    assert (endpoint.lower_closed, endpoint.upper_closed) == closed


def test_interval_has_no_exact_value_and_keeps_closure():
    value = payload()["endpoint"]
    value.update(relation="interval", value=None, lower=4.0, upper=16.0, lower_closed=False, upper_closed=True)
    endpoint = EndpointLabel.model_validate(value)
    assert endpoint.censoring == "interval"
    assert endpoint.value is None
    assert not endpoint.lower_closed


@pytest.mark.parametrize("change", [
    {"value": True}, {"value": "64"}, {"value": float("nan")}, {"value": 0.0},
    {"value": -1.0}, {"lower": 8.0}, {"relation": "~"},
    {"relation": "interval", "value": None, "lower": 16.0, "upper": 4.0},
    {"relation": "interval", "value": 4.0, "lower": 4.0, "upper": 16.0},
])
def test_invalid_numeric_or_relational_endpoints_are_rejected(change):
    value = payload()["endpoint"]
    value.update(change)
    with pytest.raises(ValidationError):
        EndpointLabel.model_validate(value)


@pytest.mark.parametrize("kind", ["MIC", "growth_inhibition", "target_binding", "MBC", "timekill"])
def test_endpoints_are_explicit_and_cannot_be_conflated(kind):
    value = payload()["endpoint"]
    value["kind"] = kind
    assert EndpointLabel.model_validate(value).kind == kind
    value["kind"] = "killing_inferred_from_MIC"
    with pytest.raises(ValidationError):
        EndpointLabel.model_validate(value)


def test_analysis_whitelist_excludes_labels_descriptions_and_unpaired_reference():
    value = payload()
    value["source"]["measured_qualifier"] = "MIC >64 ug/mL; y_pred=8; source drug response."
    value["conditions"]["provenance"] = {"medium": "Description also reports MIC=64."}
    record = ExperimentRecord.model_validate(value)
    inputs = record.analysis_input()
    assert inputs["candidate"] == {"smiles": "CCO"}
    assert set(inputs) == {"candidate", "organism", "conditions", "omics_profile_ids"}
    assert inputs["omics_profile_ids"] == []
    text = json.dumps(inputs)
    for forbidden in ("MIC", "endpoint", "y_pred", "64", "qualifier", "admission", "source"):
        assert forbidden not in text


@pytest.mark.parametrize("origin", ["model_prediction", "synthetic", "unverified"])
def test_model_predictions_or_synthetic_values_never_admit_as_experiments(origin):
    value = payload()
    value["source"]["origin"] = origin
    with pytest.raises(ValidationError):
        ExperimentRecord.model_validate(value)


def test_unmeasured_or_untraceable_sources_do_not_admit():
    for change in ({"reported_as_measured": False}, {"native_locator": {}}, {"reported_as_measured": "True"}):
        value = payload()
        value["source"].update(change)
        with pytest.raises(ValidationError):
            ExperimentRecord.model_validate(value)


def test_pairing_requires_explicit_isolate_and_condition_sources():
    value = payload()
    value["admission"]["paired_omics_eligible"] = True
    with pytest.raises(ValidationError):
        ExperimentRecord.model_validate(value)
    value["pairing"].update(status="matched_isolate_and_condition", isolate_evidence_source_ids=["identity:1"],
                            condition_evidence_source_ids=["condition:1"])
    record = ExperimentRecord.model_validate(value)
    assert record.analysis_input()["omics_profile_ids"] == ["AB5075-AZI000"]
    original = deepcopy(value)
    value["organism"]["identity_evidence"] = "unresolved"
    with pytest.raises(ValidationError):
        ExperimentRecord.model_validate(value)
    value = original
    value["admission"]["label_eligible"] = False
    with pytest.raises(ValidationError):
        ExperimentRecord.model_validate(value)


def test_unrequested_legacy_prediction_fields_fail_contract_validation():
    value = payload()
    value["y_pred"] = 8.0
    with pytest.raises(ValidationError):
        ExperimentRecord.model_validate(value)
