"""Read-only display catalogs for cell/model presets. Schema allowlists, applicability, and reliability retain
vocabulary and governance authority.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES

_CATALOG = Path(__file__).parent / "cell_catalog.yaml"


def load_cell_presets() -> list[dict]:
    """Load cell presets and check species against SUPPORTED_SPECIES and modules against MODULE_ORDER."""
    from praxis_virtualcell.biological_modules.modules import MODULE_ORDER
    doc = yaml.safe_load(_CATALOG.read_text(encoding="utf-8")) or {}
    presets = doc.get("presets", [])
    bad = [p["id"] for p in presets if p.get("species") not in SUPPORTED_SPECIES]
    if bad:
        raise ValueError(f"cell_catalog preset species outside allowlist:{bad}")
    bad_mod = [(p["id"], m) for p in presets for m in (p.get("modules") or [])
               if m not in MODULE_ORDER]
    if bad_mod:
        raise ValueError(f"cell_catalog preset module outside allowlist:{bad_mod}")
    return presets
