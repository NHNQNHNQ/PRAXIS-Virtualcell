"""Sanity tests for the 5 Phase-2 skills."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


# ---------- circuit_simulate ----------

def test_toggle_bistable_with_hill_2_is_bistable():
    """Sanity: Gardner toggle (n=2) shows bistable region; rule 06 + 07 invoked; flow_cytometry recommended."""
    from circuit_simulate_skill import run

    r = run(topology="toggle", params={"alpha": 10.0, "n": 2.0, "K": 1.0}, do_parametric_sweep=True)
    assert r["passed_qc"], r
    assert r["bistable_region_present"] is True
    assert r["parameter_robustness_score"] > 0
    assert r["recommended_readout"] == "flow_cytometry"
    assert "06-bistable-parametric-sim" in r["rules_invoked"]
    assert "07-flow-cytometry-bimodal" in r["rules_invoked"]


def test_toggle_no_sweep_is_rejected():
    """Rule 06: bistable topology without parametric sweep is rejected."""
    from circuit_simulate_skill import run

    r = run(topology="toggle", do_parametric_sweep=False)
    assert not r["passed_qc"]
    assert "rule 06" in r["error"].lower()


# ---------- dna_constraint_solve ----------

def test_dna_constraint_solve_gfp_passes():
    """Sanity: GFP DNA + constraints → output passes BsaI/BsmBI/NotI/GC."""
    from dna_constraint_solve_skill import run

    r = run(fasta_path=str(FIXTURES / "gfp_native.fasta"))
    assert r["passed_qc"], r["after"]
    assert all(v == 0 for v in r["after"]["site_counts"].values())
    assert 0.40 <= r["after"]["gc"] <= 0.55
    assert "04-restriction-site-destroy" in r["rules_invoked"]


# ---------- cellfree_design ----------

def test_cellfree_txtl_default():
    """Sanity: TX-TL GFP default recipe → predicted yield > 0; rule 02 invoked."""
    from cellfree_design_skill import run

    r = run(target_protein="GFP", system="TX-TL")
    assert r["passed_qc"], r
    assert r["system_chosen"] == "TX-TL"
    assert r["predicted_yield_mg_per_mL"] > 0
    assert "02-codon-optimize-mandatory" in r["rules_invoked"]
    assert r["recommended_codon_optimize"] is True


def test_cellfree_glycosylation_rejected():
    """Glycosylated target should be rejected (no glycosylation in cell-free E.coli)."""
    from cellfree_design_skill import run

    r = run(target_protein="antibody_Fc", system="TX-TL", has_glycosylation=True)
    assert not r["passed_qc"]
    assert "REJECT_for_glycosylation" in r["flags"]


# ---------- biosensor_design ----------

def test_biosensor_arabinose_default_panel():
    """Sanity: arabinose AraC-pBAD → 5 cross-reactants, dynamic range ≥ 5x, flow cytometry."""
    from biosensor_design_skill import run

    r = run(analyte="arabinose")
    assert r["passed_qc"], r
    assert r["cross_reactant_panel"]["n_compounds"] >= 5
    assert r["dynamic_range_fold"] >= 5
    assert r["specificity_ratio"] >= 5
    assert r["recommended_readout"] == "flow_cytometry"
    assert "10-biosensor-specificity-panel" in r["rules_invoked"]


def test_biosensor_small_panel_rejected():
    """Rule 10: panel < n_required is rejected."""
    from biosensor_design_skill import run

    r = run(analyte="arabinose", custom_panel=["glucose", "galactose"], n_cross_reactants_required=5)
    assert not r["passed_qc"]
    assert "rule 10" in r["error"].lower()


# ---------- bgc_mining ----------

def test_bgc_mining_streptomyces_with_mibig_cross():
    """Sanity: streptomyces fixture → ≥1 cluster found, every cluster has mibig_match_pct.

    We pass require_consensus=False because antiSMASH/DeepBGC binaries are not
    in this CI environment — the heuristic fallback runs alone. In production,
    this flag stays default-True so any single-backend run is flagged.
    """
    from bgc_mining_skill import run

    r = run(fasta_path=str(FIXTURES / "streptomyces_pks_nrps.fasta"), require_consensus=False)
    assert r["passed_qc"], r
    assert r["n_clusters_found"] >= 1
    for cluster in r["candidate_clusters"]:
        assert "mibig_match_pct" in cluster
        assert "novelty_band" in cluster
    assert "09-antismash-mibig-cross" in r["rules_invoked"]


def test_bgc_mining_rejects_no_mibig():
    """Rule 09: cross_mibig=False rejected."""
    from bgc_mining_skill import run

    r = run(fasta_path=str(FIXTURES / "streptomyces_pks_nrps.fasta"), cross_mibig=False)
    assert not r["passed_qc"]
    assert "rule 09" in r["error"].lower()
