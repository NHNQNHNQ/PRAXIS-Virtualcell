"""skill_executor — invoke registered skills by id with logged provenance.

Skill registry pulls from skills/workflows/<skill-id>/run.py and exposes one
entry function (e.g., run_fba, run_golden_gate, ...). The executor adds a
common wrapper that tags simulate fallbacks when the underlying tool is missing.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills" / "workflows"


SKILL_ENTRYPOINTS: dict[str, tuple[str, str]] = {
    # skill_id (snake_case) -> (folder_name_with_hyphens, function_name)
    "fba_simulate":                  ("fba-simulate", "run_fba"),
    "golden_gate_assembly":          ("golden-gate-assembly", "run_golden_gate"),
    "codon_optimize":                ("codon-optimize", "run_codon_optimize"),
    "heterologous_pathway_design":   ("heterologous-pathway-design", "design_pathway"),
    "optknock_strain":               ("optknock-strain", "run_optknock"),
    "environment_setup":             ("environment-setup", "run"),
    "kegg_fetcher":                  ("kegg-fetcher", "run"),
    "ncbi_taxon_fetcher":            ("ncbi-taxon-fetcher", "run"),
    # phase-2 skeletons (registered for orchestrator visibility; impl deferred)
    "circuit_simulate":              ("circuit-simulate", "run"),
    "dna_constraint_solve":          ("dna-constraint-solve", "run"),
    "cellfree_design":               ("cellfree-design", "run"),
    "biosensor_design":              ("biosensor-design", "run"),
    "bgc_mining":                    ("bgc-mining", "run"),
}


_loaded: dict[str, Callable] = {}


def _load_entrypoint(skill_id: str) -> Callable | None:
    if skill_id in _loaded:
        return _loaded[skill_id]
    if skill_id not in SKILL_ENTRYPOINTS:
        return None
    folder, fn_name = SKILL_ENTRYPOINTS[skill_id]
    path = SKILLS_DIR / folder / "run.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"_skill_{skill_id}", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    fn = getattr(mod, fn_name, None)
    if fn:
        _loaded[skill_id] = fn
    return fn


def list_skills() -> list[dict]:
    """Return [{id, available, entrypoint, description}]."""
    out = []
    for sid, (folder, fn) in SKILL_ENTRYPOINTS.items():
        path = SKILLS_DIR / folder / "run.py"
        out.append({
            "id": sid,
            "folder": folder,
            "entrypoint": fn,
            "available": path.exists(),
            "loaded": sid in _loaded,
        })
    return out


def run_skill(skill_id: str, args: dict | None = None) -> dict:
    """Invoke a skill by id; return its result dict (or a stub on failure)."""
    args = args or {}
    fn = _load_entrypoint(skill_id)
    t0 = time.time()
    if fn is None:
        return {
            "skill_id": skill_id,
            "passed_qc": False,
            "error": f"skill {skill_id!r} not registered or run.py missing",
            "tool_provenance": {
                "simulated": True, "partial": False, "full": False,
                "version": {"python": platform.python_version()},
                "wallclock_seconds": round(time.time() - t0, 3),
            },
        }
    try:
        result = fn(**args)
        if isinstance(result, dict):
            result.setdefault("skill_id", skill_id)
            return result
        return {"skill_id": skill_id, "passed_qc": True, "result": result,
                "tool_provenance": {"simulated": False, "partial": False, "full": True}}
    except TypeError as e:
        return {
            "skill_id": skill_id, "passed_qc": False,
            "error": f"argument error: {e}",
            "tool_provenance": {"simulated": True, "partial": False, "full": False,
                                "wallclock_seconds": round(time.time() - t0, 3)},
        }
    except Exception as e:
        return {
            "skill_id": skill_id, "passed_qc": False,
            "error": f"runtime error: {e}",
            "traceback": traceback.format_exc(),
            "tool_provenance": {"simulated": True, "partial": False, "full": False,
                                "wallclock_seconds": round(time.time() - t0, 3)},
        }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True)
    ap.add_argument("--args-json", default="{}")
    a = ap.parse_args()
    print(json.dumps(run_skill(a.skill, json.loads(a.args_json)), indent=2))
