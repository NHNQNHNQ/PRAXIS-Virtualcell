"""Verify an installed full release wheel from outside the source checkout."""

from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import httpx


async def _verify_api() -> dict[str, object]:
    from praxis_vc_api.main import _REACT_DIST, app

    assert _REACT_DIST is not None
    assert _REACT_DIST.name == "static"
    assert _REACT_DIST.parent.name == "praxis_vc_api"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://release.test") as client:
        health = await client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["product_version"] == version("praxis-virtualcell")

        root = await client.get("/")
        assert root.status_code == 200
        match = re.search(r'(?:src|href)="([^"]+assets/[^"]+)"', root.text)
        assert match, root.text
        asset = await client.get(match.group(1))
        assert asset.status_code == 200 and asset.content

        jobs_root = Path(os.environ["PRAXIS_VC_RUNS"])
        assert not jobs_root.exists()
        direct_v2 = await client.post(
            "/api/jobs",
            json={
                "request": {
                    "schema_version": "vc.request.v2",
                    "request_id": "release-direct-v2-unconfigured",
                    "species": {
                        "schema_version": "vc.species-ref.v1",
                        "taxonomy_id": "NCBITaxon:999999999",
                        "scientific_name": "test-only organism",
                        "common_name": None,
                    },
                    "cell_context": {
                        "schema_version": "vc.cell-context.v1",
                        "cell_type_name": None,
                        "cell_type_id": None,
                        "tissue_name": None,
                        "tissue_id": None,
                        "attributes": {},
                    },
                    "input_modality": {
                        "schema_version": "vc.modality.v1",
                        "name": "test_input",
                        "ontology_id": None,
                        "unit": "dimensionless",
                        "feature_namespace": "TestFeature",
                    },
                    "output_modality": {
                        "schema_version": "vc.modality.v1",
                        "name": "test_output",
                        "ontology_id": None,
                        "unit": "dimensionless",
                        "feature_namespace": "TestFeature",
                    },
                    "perturbation": {
                        "schema_version": "vc.perturbation.v1",
                        "kind": "gene",
                        "targets": ["TEST:1"],
                        "dose_value": None,
                        "dose_unit": None,
                        "timepoint": None,
                    },
                    "task": {
                        "schema_version": "vc.task.v1",
                        "task_type": "test_scalar_task",
                        "requested_outputs": ["test_output"],
                    },
                    "baseline_context": None,
                    "metadata": {},
                    "constraints": {},
                },
                "mode": "offline",
                "enable_llm_report": False,
                "pack_id": "test-only-pack",
                "pack_version": "0.0.0",
                "submission_contract": "vc.direct-v2-execution.v1",
            },
        )
        assert direct_v2.status_code == 503, direct_v2.text
        assert direct_v2.json() == {"detail": "direct_v2_factory_unconfigured"}
        assert not jobs_root.exists()

        job = await client.post(
            "/api/jobs",
            json={
                "request": {
                    "species": "human",
                    "perturbation_type": "gene",
                    "perturbation_targets": ["AHR"],
                    "input_modality": "scRNA",
                    "output_modality": "delta_expression",
                    "task_type": "predict_delta_expression",
                },
                "mode": "offline",
            },
        )
        assert job.status_code == 200, job.text
        return {
            "health": health.status_code,
            "asset": match.group(1),
            "direct_v2_unconfigured": direct_v2.status_code,
            "job_id": job.json()["job_id"],
        }


def main() -> None:
    product_version = version("praxis-virtualcell")
    assert files("praxis_vc_web").joinpath("app.py").is_file()
    assert not files("praxis_virtualcell").joinpath("tests").is_dir()
    registrations = files("praxis_virtualcell.model_zoo").joinpath("registrations")
    assert registrations.joinpath("golden_additive_source_card.yaml").is_file()
    assert registrations.joinpath("golden_additive_research_release.json").is_file()
    request = files("praxis_virtualcell").joinpath("examples", "norman_mock_request.json")

    from praxis_virtualcell.cli import main as cli_main

    with tempfile.TemporaryDirectory(prefix="praxis-release-") as tmp:
        output = Path(tmp) / "run"
        os.environ["PRAXIS_VC_RUNS"] = str(Path(tmp) / "jobs")
        assert cli_main(["run", "--request", str(request), "--mode", "offline", "--out", str(output)]) == 0
        for name in ("report.md", "report.json", "trace.json", "provenance.json"):
            assert (output / name).is_file(), name
        result = asyncio.run(_verify_api())

    print(json.dumps({"version": product_version, **result}, sort_keys=True))


if __name__ == "__main__":
    main()
