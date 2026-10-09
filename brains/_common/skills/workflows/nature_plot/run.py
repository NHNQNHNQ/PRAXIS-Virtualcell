#!/usr/bin/env python3

import json
from pathlib import Path
import sys

ARCHETYPE = "omics_scrna"
BRAIN = "_common"
SKILL = "nature_plot"


def simulate(payload):

    import copy
    import random

    random.seed(int(payload.get("seed", 42)) if isinstance(payload, dict) else 42)
    out = copy.deepcopy(
        {
            "skill_id": "nature_plot",
            "matrix_path": "",
            "n_cells_post_qc": 0,
            "cluster_sizes": {},
            "marker_genes_per_cluster": {},
            "umap_png": "",
            "diagnostics": {"brain": "_common", "archetype": "omics_scrna"},
        }
    )
    if isinstance(out, dict):
        out.setdefault("diagnostics", {})
        if isinstance(out["diagnostics"], dict):
            out["diagnostics"].update(
                {
                    "simulated": True,
                    "archetype": ARCHETYPE,
                    "brain": BRAIN,
                    "skill": SKILL,
                }
            )
        if "skill_id" in out and not out["skill_id"]:
            out["skill_id"] = SKILL
    return out


def real(payload):

    try:
        from brains._common.lib.run_tool import run_tool
    except ImportError:
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
        from _common.lib.run_tool import run_tool  # noqa: F401

    r = run_tool(["python3", "-c", "print('skill-real-placeholder')"], timeout=30)
    diagnostics = {
        "brain": BRAIN,
        "skill": SKILL,
        "archetype": ARCHETYPE,
        "todo": "replace echo with real CLI; see SKILL.md SOP",
        "subprocess": {"cmd": r.get("cmd"), "wall_sec": r.get("wall_sec"), "rc": r.get("returncode")},
    }
    if r.get("dry"):
        diagnostics["dry"] = True
    if not r["ok"]:
        return {"ok": False, "error": r.get("error", "subprocess failed"), "diagnostics": diagnostics}
    return {"ok": True, "skill_id": SKILL, "result": "placeholder; replace with real parse", "diagnostics": diagnostics}


def main():

    payload = {}
    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                payload = {}
        except json.JSONDecodeError:
            payload = {}
    if not payload:
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("--simulate", action="store_true", default=True)
        ap.add_argument("--seed", type=int, default=42)
        args, _ = ap.parse_known_args()
        payload = {"simulate": args.simulate, "seed": args.seed}

    simulate_mode = bool(payload.get("simulate", True))
    try:
        out = simulate(payload) if simulate_mode else real(payload)
    except Exception as e:
        out = {"ok": False, "error": f"run.py error: {e!r}"}

    if isinstance(out, dict):
        out.setdefault("diagnostics", {})
        if isinstance(out["diagnostics"], dict):
            out["diagnostics"].update({"archetype": ARCHETYPE, "brain": BRAIN, "skill": SKILL})
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
