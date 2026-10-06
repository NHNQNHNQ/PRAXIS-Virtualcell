"""Regression tests for the bounded MDR mechanism-sidecar import boundary."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# This module exercises the local MDR catalog/artifacts; excluded from the base CI set.
pytestmark = pytest.mark.local_artifacts


REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE = "praxis_virtualcell.mdr_gnb.predictors.mechanistic"
_MODULES = {
    "cell_state": f"{_PACKAGE}.cell_state",
    "gem_fba": f"{_PACKAGE}.gem_fba",
    "mechanism_state_model": f"{_PACKAGE}.mechanism_state_model",
    "intervention": f"{_PACKAGE}.intervention",
    "falsifiability": f"{_PACKAGE}.falsifiability",
    "run_g3_gate": f"{_PACKAGE}.run_g3_gate",
}


def _child_payload(script: str) -> dict[str, object]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    marker = "__MECHANISTIC_IMPORT_BOUNDARY__="
    lines = [
        line.removeprefix(marker)
        for line in result.stdout.splitlines()
        if line.startswith(marker)
    ]
    assert len(lines) == 1, result.stdout
    return json.loads(lines[0])


def test_mechanistic_package_import_has_no_eager_experimental_modules():
    payload = _child_payload(
        f"""
import importlib
import json
import sys

importlib.import_module({_PACKAGE!r})
modules = {json.dumps(_MODULES, sort_keys=True)}
print(
    "__MECHANISTIC_IMPORT_BOUNDARY__="
    + json.dumps({{name: module in sys.modules for name, module in modules.items()}}, sort_keys=True)
)
"""
    )

    assert payload == {name: False for name in _MODULES}


def test_public_mechanistic_exports_remain_compatible_on_demand():
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic import (
        BacterialCellState,
        GemFbaPredictor,
        MechanismStateModel,
        run_ablation,
        run_intervention_consistency,
        simulate_intervention,
    )
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic import gem_fba, run_g3_gate

    assert BacterialCellState.__name__ == "BacterialCellState"
    assert GemFbaPredictor.__name__ == "GemFbaPredictor"
    assert MechanismStateModel.__name__ == "MechanismStateModel"
    assert callable(simulate_intervention)
    assert callable(run_ablation)
    assert callable(run_intervention_consistency)
    assert gem_fba.GemFbaPredictor is GemFbaPredictor
    assert run_g3_gate.__name__.endswith("run_g3_gate")


def test_actual_activity_service_path_loads_only_the_bounded_gem_sidecar():
    """A fresh production-style request must not import unwired VC helpers."""
    payload = _child_payload(
        f"""
import json
import sys
from praxis_virtualcell.mdr_gnb.api import service

result = service.predict({{
    "species": "escherichia_coli",
    "smiles": "COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC",
    "drug_panel": [{{"drug": "trimethoprim", "drug_class": "novel_compound"}}],
    "requested_outputs": ["activity"],
}})
mechanism = result["response"]["report"]["mechanism"]
modules = {json.dumps(_MODULES, sort_keys=True)}
print(
    "__MECHANISTIC_IMPORT_BOUNDARY__="
    + json.dumps({{
        "loaded": {{name: module in sys.modules for name, module in modules.items()}},
        "mechanism_claim": mechanism.get("mechanism_claim"),
        "g3_status": mechanism.get("g3_gate", {{}}).get("status"),
    }}, sort_keys=True)
)
"""
    )

    assert payload["loaded"] == {
        "cell_state": False,
        "gem_fba": True,
        "mechanism_state_model": False,
        "intervention": False,
        "falsifiability": False,
        "run_g3_gate": False,
    }
    assert payload["mechanism_claim"] is None
    assert payload["g3_status"] == "not_evaluated"
