"""An executable MDR request must bind exactly one non-empty drug."""
from __future__ import annotations

from importlib import import_module
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.schemas import PredictRequest
from praxis_virtualcell.mdr_gnb.cli import main


# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts

workflow = import_module("praxis_virtualcell.mdr_gnb.workflows.run_mdr_query")


@pytest.mark.parametrize(
    "drug_panel",
    [
        [],
        [
            {"drug": "meropenem", "drug_class": "carbapenem"},
            {"drug": "ceftriaxone", "drug_class": "cephalosporin"},
        ],
    ],
    ids=["zero", "multiple"],
)
def test_api_schema_rejects_non_single_drug_panels(drug_panel):
    with pytest.raises(ValidationError, match="exactly_one_drug_required"):
        PredictRequest(species="escherichia_coli", drug_panel=drug_panel)


def test_api_schema_rejects_empty_drug_name():
    with pytest.raises(ValidationError, match="drug_required"):
        PredictRequest(
            species="escherichia_coli",
            drug_panel=[{"drug": "   ", "drug_class": "carbapenem"}],
        )


@pytest.mark.parametrize("drug_panel", [[], [{"drug": "a"}, {"drug": "b"}]])
def test_core_rejects_non_single_drug_before_registry_construction(monkeypatch, drug_panel):
    def unexpected_registry_build(*_args, **_kwargs):
        raise AssertionError("registry construction must not run for invalid drug input")

    monkeypatch.setattr(workflow, "build_default_registry", unexpected_registry_build)
    with pytest.raises(ValueError, match="exactly_one_drug_required"):
        workflow.run_mdr_query(
            {"species": "escherichia_coli", "drug_panel": drug_panel},
            seed_task_id="invalid-drug-panel",
        )


def test_service_preflight_coordinates_reject_non_single_drug_panel():
    with pytest.raises(ValueError, match="exactly_one_drug_required"):
        service._runtime_request_coordinates(
            {"species": "escherichia_coli", "drug_panel": []}
        )


@pytest.mark.parametrize(
    "drug_panel",
    [[], [{"drug": "meropenem"}, {"drug": "ceftriaxone"}]],
    ids=["zero", "multiple"],
)
def test_http_rejects_non_single_drug_panel_before_execution(drug_panel):
    response = TestClient(create_app()).post(
        "/predict",
        json={"species": "escherichia_coli", "drug_panel": drug_panel},
    )

    assert response.status_code == 422
    assert "exactly_one_drug_required" in response.text


def test_cli_rejects_non_single_drug_panel_before_execution(tmp_path, capsys):
    request_path = tmp_path / "invalid-drug-panel.json"
    request_path.write_text(
        json.dumps({"species": "escherichia_coli", "drug_panel": []}),
        encoding="utf-8",
    )

    assert main(["run", "--request", str(request_path)]) == 2
    assert "exactly_one_drug_required" in capsys.readouterr().err
