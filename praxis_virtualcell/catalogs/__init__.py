"""只读 cell/model 预设 catalog(展示层)。非权威词汇/治理——权威仍在
species_schema/run_virtualcell_query 白名单 + model_applicability/reliability。"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.workflows.run_virtualcell_query import SUPPORTED_SPECIES

_CATALOG = Path(__file__).parent / "cell_catalog.yaml"


def load_cell_presets() -> list[dict]:
    """读 cell_catalog.yaml 的 presets。校验 species ∈ SUPPORTED_SPECIES(防与单一真相源漂移)。"""
    doc = yaml.safe_load(_CATALOG.read_text(encoding="utf-8")) or {}
    presets = doc.get("presets", [])
    bad = [p["id"] for p in presets if p.get("species") not in SUPPORTED_SPECIES]
    if bad:
        raise ValueError(f"cell_catalog 预设 species 越白名单:{bad}")
    return presets
