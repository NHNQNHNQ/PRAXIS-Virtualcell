"""Tests for module support data."""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.biological_modules import modules as M

_ROOT = Path(__file__).resolve().parents[1] / "brains" / "virtualcell"
_SPECIES = ["human", "mouse", "yeast", "bacteria"]
_LEVELS = {"strong", "medium", "weak", "unsupported"}


def _load(species):
    return yaml.safe_load((_ROOT / species / "module_support.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("species", _SPECIES)
def test_file_exists_and_species_matches(species):
    doc = _load(species)
    assert doc["species"] == species


@pytest.mark.parametrize("species", _SPECIES)
def test_all_eight_modules_present(species):
    doc = _load(species)
    assert set(doc["modules"].keys()) == set(M.MODULE_ORDER), \
        f"{species} module_support has missing or extra modules"


@pytest.mark.parametrize("species", _SPECIES)
def test_support_levels_legal_and_reasoned(species):
    doc = _load(species)
    for mid, rec in doc["modules"].items():
        assert rec["support"] in _LEVELS, f"{species}/{mid} Invalid support:  {rec['support']}"
        if rec["support"] in {"weak", "unsupported"}:
            assert rec.get("reason"), f"{species}/{mid} Weak or unsupported modules must declare a reason"


def test_bacteria_declares_autophagy_mismatch():

    doc = _load("bacteria")
    mismatches = {m["query"] for m in doc.get("biological_mismatch", [])}
    assert "bacteria_autophagy" in mismatches


def test_yeast_declares_tissue_niche_mismatch():

    doc = _load("yeast")
    mismatches = {m["query"] for m in doc.get("biological_mismatch", [])}
    assert "tissue_spatial_niche" in mismatches
