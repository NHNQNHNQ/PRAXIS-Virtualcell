"""Pure data shared by the offline G3 gate and the production mechanism sidecar.

The production activity path only needs anchor membership to preserve the
conservative ``not_evaluated`` claim boundary.  It must not import the offline
G3 runner, whose separate workflow constructs a cell-state model and executes
falsifiability checks.
"""
from __future__ import annotations

# Anchor combination -> interventions relevant to that species × drug mechanism.
# Keep this source independent of ``predictors.mechanistic`` so production G3 status
# cannot import any on-demand experimental mechanism helper.
G3_ANCHORS: dict[str, dict[str, object]] = {
    "escherichia_coli__ceftriaxone": {
        "species": "escherichia_coli",
        "drug": "ceftriaxone",
        "interventions": ["ampC_derepression", "gyrA_qrdr_mutation"],
    },
    "klebsiella_pneumoniae__meropenem": {
        "species": "klebsiella_pneumoniae",
        "drug": "meropenem",
        "interventions": ["ompK36_knockout", "carbapenemase_acquisition"],
    },
}
