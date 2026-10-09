"""Tests for module rules."""
from praxis_virtualcell.agents.module_rules import (
    mismatch_query_for,
    pick_primary,
    pick_secondary,
)
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.biological_modules import modules as M


def _req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["AHR"]}
    base.update(kw)
    return normalize_request(base)


def test_gene_expression_primary_is_genetic_hub():
    assert pick_primary(_req()) == "genetic_hub"


def test_growth_primary_is_cytoplasmic_metabolism():
    r = _req(species="bacteria", target_output="growth", perturbation_targets=["b0720"])
    assert pick_primary(r) == "cytoplasmic_metabolism"


def test_drug_expression_primary_is_stress_processor():
    r = _req(perturbation_object="drug", target_output="expression",
             perturbation_targets=["vorinostat"])
    assert pick_primary(r) == "stress_processor"


def test_state_primary_is_stress_processor():
    r = _req(target_output="state", perturbation_targets=["SNAI1"])
    assert pick_primary(r) == "stress_processor"


def test_niche_state_primary_is_cytoskeletal_framework():
    r = _req(perturbation_object="medium", target_output="state",
             perturbation_targets=[], medium="niche")
    assert pick_primary(r) == "cytoskeletal_framework"


def test_all_primaries_are_legal_modules():
    for r in (_req(), _req(target_output="growth", species="bacteria",
                           perturbation_targets=["b0720"])):
        assert pick_primary(r) in M.MODULE_ORDER


def test_mammalian_growth_has_m3_secondary():
    r = _req(species="human", target_output="growth", perturbation_targets=["MYC"])
    sec = pick_secondary(r, "cytoplasmic_metabolism")
    assert "mitochondrial_energy_metabolism" in sec


def test_secondary_excludes_primary():
    r = _req(species="human", target_output="growth", perturbation_targets=["MYC"])
    sec = pick_secondary(r, "cytoplasmic_metabolism")
    assert "cytoplasmic_metabolism" not in sec


def test_mismatch_query_bacteria_degradation_autophagy():
    r = _req(species="bacteria", perturbation_object="gene",
             target_output="growth", perturbation_targets=["lon"])

    assert mismatch_query_for(r, "degradation_machinery") == "bacteria_autophagy"


def test_mismatch_query_none_when_no_mismatch():
    assert mismatch_query_for(_req(), "genetic_hub") is None
