"""T4 trace contract for catalog-backed MDR predictors."""
from __future__ import annotations

from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


def test_catalog_predictor_trace_binds_contract_and_io_hashes():
    """Trace the verified model unit and hashed I/O without exposing raw features."""
    out = run_mdr_query(
        {
            "species": "escherichia_coli",
            "drug_panel": [
                {"drug": "meropenem", "drug_class": "carbapenems"}
            ],
            "requested_outputs": ["SIR"],
            "amr_profile": {"blaKPC-2": True},
        },
        seed_task_id="predictor-trace-contract",
    )
    by_type = {message.message_type: message for message in out["trace"]}
    route = by_type["route_decided"]
    contract = by_type["predictor_contract_checked"]
    result = by_type["predictor_result"]

    assert contract.parent_message_id == route.message_id
    assert result.parent_message_id == contract.message_id
    assert contract.payload["contract_status"] == "catalog_verified"
    assert contract.payload["spec"] == "genotype_to_sir"
    assert contract.payload["catalog"] == result.payload["catalog"]
    assert contract.payload["catalog"] == {
        "model_id": "sir/escherichia_coli/meropenem",
        "catalog_digest": out["report"]["provenance"]["capability"]["catalog_digest"],
        "artifact_path": (
            "data/mdr_gnb/models/escherichia_coli/"
            "genotype_to_sir__meropenem.joblib"
        ),
        "artifact_sha256": contract.payload["catalog"]["artifact_sha256"],
        "declared": True,
        "ready": True,
        "validated": False,
        "validation_status": "limited",
        "reason_code": "ready",
    }
    assert len(contract.payload["catalog"]["artifact_sha256"]) == 64
    assert len(contract.payload["predictor_input_sha256"]) == 64
    assert result.payload["predictor_input_sha256"] == contract.payload[
        "predictor_input_sha256"
    ]
    assert len(result.payload["predictor_result_sha256"]) == 64
    assert "amr_profile" not in contract.payload
    assert "prediction" not in result.payload
