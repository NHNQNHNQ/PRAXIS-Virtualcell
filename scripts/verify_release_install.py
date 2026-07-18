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
        return {"health": health.status_code, "asset": match.group(1), "job_id": job.json()["job_id"]}


def main() -> None:
    product_version = version("praxis-virtualcell")
    assert files("praxis_vc_web").joinpath("app.py").is_file()
    assert not files("praxis_virtualcell").joinpath("tests").is_dir()
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
