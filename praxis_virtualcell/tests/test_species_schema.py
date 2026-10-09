"""Tests for species schema."""
import pytest

from praxis_virtualcell.agents.species_schema import (
    PERTURBATION_OBJECTS,
    SPECIES,
    TARGET_OUTPUTS,
    SchemaError,
    normalize_request,
)


def test_vocab_covers_v04_scope():
    assert {"human", "mouse", "yeast", "bacteria"} <= SPECIES
    assert {"gene", "gene_combination", "drug", "medium", "ligand"} <= PERTURBATION_OBJECTS
    assert {"expression", "growth", "flux", "state", "communication"} <= TARGET_OUTPUTS


def test_human_gene_normalized():
    r = normalize_request({
        "species": "Human", "cell_type": "K562",
        "perturbation_object": "gene", "perturbation_targets": [" ahr "],
        "target_output": "expression",
    })
    assert r["species"] == "human"
    assert r["perturbation_object"] == "gene"
    assert r["perturbation_targets"] == ["AHR"]           # gene → strip + upper
    assert r["target_output"] == "expression"


def test_mouse_gene_normalized():
    r = normalize_request({
        "species": "mouse", "cell_type": "fibroblast",
        "perturbation_object": "gene", "perturbation_targets": ["Trp53"],
        "target_output": "expression",
    })
    assert r["species"] == "mouse"
    assert r["perturbation_targets"] == ["TRP53"]


def test_ecoli_ko_growth_normalized():

    r = normalize_request({
        "species": "bacteria", "cell_type": "E. coli",
        "perturbation_object": "gene", "perturbation_targets": ["b0720"],
        "target_output": "growth", "medium": "glucose_minimal",
    })
    assert r["species"] == "bacteria"
    assert r["target_output"] == "growth"
    assert r["perturbation_targets"] == ["B0720"]
    assert r["medium"] == "glucose_minimal"


def test_yeast_deletion_growth_normalized():
    r = normalize_request({
        "species": "yeast", "cell_type": "S. cerevisiae",
        "perturbation_object": "gene", "perturbation_targets": ["YAL001C"],
        "target_output": "growth",
    })
    assert r["species"] == "yeast"
    assert r["target_output"] == "growth"


def test_human_drug_normalized():
    r = normalize_request({
        "species": "human", "cell_type": "A549",
        "perturbation_object": "drug", "perturbation_targets": [" Aspirin "],
        "target_output": "expression", "dose": "1uM",
    })
    assert r["perturbation_object"] == "drug"
    assert r["perturbation_targets"] == ["aspirin"]       # drug → strip + lower
    assert r["dose"] == "1uM"


def test_unknown_species_raises():
    with pytest.raises(SchemaError):
        normalize_request({"species": "martian", "perturbation_object": "gene",
                           "perturbation_targets": ["AHR"], "target_output": "expression"})


def test_unknown_perturbation_object_raises():
    with pytest.raises(SchemaError):
        normalize_request({"species": "human", "perturbation_object": "curse",
                           "perturbation_targets": ["AHR"], "target_output": "expression"})


def test_unknown_target_output_raises():
    with pytest.raises(SchemaError):
        normalize_request({"species": "human", "perturbation_object": "gene",
                           "perturbation_targets": ["AHR"], "target_output": "telepathy"})


def test_missing_required_field_raises():
    with pytest.raises(SchemaError):
        normalize_request({"species": "human", "perturbation_object": "gene"})


def test_empty_targets_raises_for_gene():
    with pytest.raises(SchemaError):
        normalize_request({"species": "human", "perturbation_object": "gene",
                           "perturbation_targets": [], "target_output": "expression"})
