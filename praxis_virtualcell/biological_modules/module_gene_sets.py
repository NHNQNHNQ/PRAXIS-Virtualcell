"""Load curated M1/M5/M8 gene sets for deterministic advisory matching. Lazy cached symbols activate
rule_based/evidence_limited module entries for relevant gene perturbations. Membership supports qualitative
advice, never a numerical delta.
"""
from __future__ import annotations

import json
from functools import cache
from importlib.resources import files

from praxis_virtualcell.biological_modules import modules as M

_DATA_DIR = files("praxis_virtualcell").joinpath("data", "module_gene_sets")


_MODULE_FILES: dict[str, str] = {
    "membrane_system": "membrane_system.json",
    "biosynthetic_network": "biosynthetic_network.json",
    "degradation_machinery": "degradation_machinery.json",
}


GENE_SET_MODULES = frozenset(_MODULE_FILES)


@cache
def gene_set_of(module_id: str) -> frozenset[str]:
    """Return uppercase module gene symbols from lazy cached JSON; non-gene-set modules return an empty set."""
    fname = _MODULE_FILES.get(module_id)
    if fname is None:
        return frozenset()
    doc = json.loads((_DATA_DIR / fname).read_text(encoding="utf-8"))
    return frozenset(str(g).strip().upper() for g in doc.get("gene_set", []))


def modules_hit_by(targets: list[str]) -> list[str]:
    """Return unique M1/M5/M8 matches in MODULE_ORDER using exact uppercase identifiers, avoiding substring matches
    such as IFNB2/IL-6.
    """
    norm = {str(t).strip().upper() for t in (targets or []) if str(t).strip()}
    hits = [mid for mid in _MODULE_FILES if norm & gene_set_of(mid)]
    return sorted(hits, key=M.MODULE_ORDER.index)
