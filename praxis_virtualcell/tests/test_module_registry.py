"""Tests for module registry."""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry


@pytest.fixture(scope="module")
def reg():
    return ModuleRegistry()


def test_matrix_is_four_by_eight(reg):
    mat = reg.matrix()
    assert set(mat.keys()) == {"human", "mouse", "yeast", "bacteria"}
    for species, row in mat.items():
        assert set(row.keys()) == set(M.MODULE_ORDER), f"{species} row does not contain eight modules"


def test_support_query_returns_level_and_reason(reg):
    rec = reg.support("yeast", "cytoplasmic_metabolism")
    assert rec["support"] == "strong"
    rec2 = reg.support("yeast", "genetic_hub")
    assert rec2["support"] == "weak"
    assert rec2["reason"]


def test_verdict_mapping(reg):

    assert reg.default_verdict("yeast", "cytoplasmic_metabolism") == "accept"
    assert reg.default_verdict("yeast", "genetic_hub") == "caution"


def test_unknown_species_or_module_is_unsupported(reg):
    assert reg.support("martian", "genetic_hub")["support"] == "unsupported"
    assert reg.default_verdict("martian", "genetic_hub") == "reject"
    with pytest.raises(KeyError):
        reg.support("human", "no_such_module")


def test_biological_mismatch_lookup(reg):

    assert reg.biological_mismatch("bacteria", "bacteria_autophagy") == "caution"
    assert reg.biological_mismatch("yeast", "tissue_spatial_niche") == "reject"
    assert reg.biological_mismatch("human", "anything_normal") is None


def test_display_name_honors_bacteria_alias(reg):
    assert reg.display_name("bacteria", "mitochondrial_energy_metabolism") \
        == "Energy metabolism / redox module"
