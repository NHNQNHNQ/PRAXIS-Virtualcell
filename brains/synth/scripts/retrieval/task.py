"""synth_task channel + (task, host) pool routing.

The synth_task channel is exact-tag matching against the canonical 9-enum.
Pool routing replaces EnzymeAgent's CAZy family routing with (task, host) tuples:

    same_task_same_host  (5 picks)
    same_task            (2 picks)
    same_host            (1 pick)
    cross                (1 pick, only in `full` mode)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal


CANONICAL_TASK_MAP = {
    "flux_balance_analysis": "fba",
    "fba": "fba",
    "heterologous_pathway_design": "pathway_design",
    "pathway_design": "pathway_design",
    "plasmid_construction": "plasmid_assembly",
    "plasmid_assembly": "plasmid_assembly",
    "codon_optimization": "codon_opt",
    "codon_opt": "codon_opt",
    "dna_constraint_optimization": "codon_opt",
    "genetic_circuit_design": "circuit",
    "circuit": "circuit",
    "cell_free_protein_synthesis_design": "cell_free",
    "cell_free": "cell_free",
    "biosensor_circuit_design": "biosensor",
    "biosensor": "biosensor",
    "strain_engineering_for_production": "strain_engineering",
    "strain_engineering": "strain_engineering",
    "biosynthetic_gene_cluster_mining": "bgc_mining",
    "bgc_mining": "bgc_mining",
}

PoolLabel = Literal["same_task_same_host", "same_task", "same_host", "cross"]


def canonicalize(task: str) -> str:
    return CANONICAL_TASK_MAP.get((task or "").strip(), (task or "").strip())


def pool_label(qtask: str, qhost: str, ctask: str, chost: str) -> PoolLabel:
    """Decide which pool a candidate case belongs to relative to the query."""
    qt, ct = canonicalize(qtask), canonicalize(ctask)
    qh, ch = (qhost or "").lower(), (chost or "").lower()

    # Loose host equality: exact OR genus prefix shared (e.g. "E. coli" ~ "E. coli K-12 MG1655")
    same_host = bool(qh) and bool(ch) and (qh == ch or qh.split()[0] == ch.split()[0])

    if qt and ct and qt == ct and same_host:
        return "same_task_same_host"
    if qt and ct and qt == ct:
        return "same_task"
    if same_host:
        return "same_host"
    return "cross"


def rank_by_task(query_task: str, cases: list[dict]) -> list[str]:
    """Return case_ids ordered by how well their task matches `query_task`.
    Identical canonical task first; everything else after (stable order)."""
    qt = canonicalize(query_task)
    ranked = []
    rest = []
    for c in cases:
        ct = canonicalize(c.get("task") or c.get("synth_task", ""))
        if qt and ct == qt:
            ranked.append(c["case_id"])
        else:
            rest.append(c["case_id"])
    return ranked + rest
