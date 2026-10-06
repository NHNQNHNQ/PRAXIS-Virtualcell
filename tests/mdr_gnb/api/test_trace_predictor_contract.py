"""HTTP replay exposes the catalog-backed predictor trace contract."""
from __future__ import annotations

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def test_http_trace_preserves_predictor_contract_and_hashed_io(client):
    task_id = client.post(
        "/predict",
        json={
            "species": "escherichia_coli",
            "drug_panel": [
                {"drug": "meropenem", "drug_class": "carbapenems"}
            ],
            "requested_outputs": ["SIR"],
            "amr_profile": {"blaKPC-2": True},
        },
    ).json()["task_id"]

    events = {
        event["message_type"]: event for event in client.get(f"/trace/{task_id}").json()["trace"]
    }
    contract = events["predictor_contract_checked"]
    result = events["predictor_result"]

    assert result["parent_message_id"] == contract["message_id"]
    assert contract["payload"]["contract_status"] == "catalog_verified"
    assert contract["payload"]["catalog"]["ready"] is True
    assert contract["payload"]["catalog"]["validated"] is False
    assert result["payload"]["predictor_input_sha256"] == contract["payload"][
        "predictor_input_sha256"
    ]
    assert len(result["payload"]["predictor_result_sha256"]) == 64
