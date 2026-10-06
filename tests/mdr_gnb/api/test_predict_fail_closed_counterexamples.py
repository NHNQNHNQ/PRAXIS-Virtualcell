"""T5 production HTTP counterexamples: fail closed with auditable reasons.

These are deliberately API-level assertions.  They make sure that a route-level
coverage gap and a runtime input-sufficiency failure remain distinguishable in
the user-facing report *and* in the replayable trace.
"""
from __future__ import annotations

import pytest


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


FAKE_DRUG = {
    "species": "escherichia_coli",
    "drug_panel": [
        {"drug": "totally_fake_drug_zzz", "drug_class": "carbapenem"}
    ],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}
ENTEROBACTER_MEROPENEM = {
    "species": "enterobacter_cloacae",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"blaKPC-2": True},
}
EMPTY_PROFILE = {
    "species": "escherichia_coli",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {},
}
UNRELATED_PROFILE = {
    "species": "escherichia_coli",
    "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenem"}],
    "requested_outputs": ["SIR"],
    "amr_profile": {"irrelevant_gene_xyz": True},
}


def _predict_and_trace(client, raw: dict) -> tuple[dict, list[dict]]:
    response = client.post("/predict", json=raw)
    assert response.status_code == 200
    body = response.json()
    trace_response = client.get(f"/trace/{body['task_id']}")
    assert trace_response.status_code == 200
    return body, trace_response.json()["trace"]


def _assert_no_prediction(body: dict) -> None:
    report = body["report"]
    assert report["abstained"] is True
    assert report["sir"] is None
    assert report["sir_prob"] is None
    assert report["output_kind"] is None
    assert body["prediction_available"] is False


@pytest.mark.parametrize(
    ("raw", "supported_species"),
    [
        (FAKE_DRUG, True),
        (ENTEROBACTER_MEROPENEM, False),
    ],
    ids=["fake-drug", "enterobacter-without-ready-model"],
)
def test_http_no_ready_capability_is_an_auditable_hard_abstain(
    client, raw, supported_species
):
    """Route-level absence must not become a silent negative SIR prediction."""
    body, trace = _predict_and_trace(client, raw)

    _assert_no_prediction(body)
    assert body["supported_species"] is supported_species
    assert {"no_ready_capability", "sir_model_not_declared"} <= set(
        body["report"]["abstain_reasons"]
    )

    route = next(event for event in trace if event["message_type"] == "route_decided")
    assert route["payload"]["disposition"] == "abstain"
    assert route["payload"]["reason"] == "no_ready_capability"
    assert "sir_model_not_declared" in route["payload"]["unready_reason_codes"]


@pytest.mark.parametrize(
    "raw", [EMPTY_PROFILE, UNRELATED_PROFILE], ids=["empty", "unrelated"]
)
def test_http_unrecognized_amr_profile_is_runtime_hard_abstain_with_reason(client, raw):
    """A routeable model still must refuse insufficient or unrelated AMR input."""
    body, trace = _predict_and_trace(client, raw)

    _assert_no_prediction(body)
    assert body["supported_species"] is True
    assert "amr_profile_no_recognized_features" in body["report"]["abstain_reasons"]

    route = next(event for event in trace if event["message_type"] == "route_decided")
    assert route["payload"]["disposition"] == "accept"
    assert route["payload"]["reason"] == "specialized_model_available"

    result = next(event for event in trace if event["message_type"] == "predictor_result")
    assert result["payload"]["status"] == "failed"
    assert result["payload"]["reason_code"] == "amr_profile_no_recognized_features"


@pytest.mark.parametrize("raw", [FAKE_DRUG, EMPTY_PROFILE], ids=["fake-drug", "empty-profile"])
def test_http_counterexample_is_deterministic(client, raw):
    """Fail-closed output and replay trace retain content-addressed determinism."""
    first, first_trace = _predict_and_trace(client, raw)
    second, second_trace = _predict_and_trace(client, raw)

    assert second == first
    assert second_trace == first_trace
