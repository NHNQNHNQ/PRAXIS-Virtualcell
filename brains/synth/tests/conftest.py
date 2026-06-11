"""Pytest configuration: ensure project root and skill modules are importable."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Skill modules live in dirs with hyphens — register them under underscore aliases.
import importlib.util


def _load_skill(name_with_hyphen: str, alias: str):
    path = PROJECT_ROOT / "skills" / "workflows" / name_with_hyphen / "run.py"
    spec = importlib.util.spec_from_file_location(alias, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules[alias] = mod
    return mod


# Pre-load skill modules under stable names
_load_skill("fba-simulate", "fba_simulate_skill")
_load_skill("golden-gate-assembly", "golden_gate_skill")
_load_skill("codon-optimize", "codon_optimize_skill")
_load_skill("heterologous-pathway-design", "pathway_design_skill")
_load_skill("optknock-strain", "optknock_skill")
_load_skill("circuit-simulate", "circuit_simulate_skill")
_load_skill("dna-constraint-solve", "dna_constraint_solve_skill")
_load_skill("cellfree-design", "cellfree_design_skill")
_load_skill("biosensor-design", "biosensor_design_skill")
_load_skill("bgc-mining", "bgc_mining_skill")
