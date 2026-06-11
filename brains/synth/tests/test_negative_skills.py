"""Counter-examples for skills — verify each skill correctly REJECTS bad inputs.

Every priority + phase-2 skill should detect specific anti-patterns and emit
passed_qc=False with explanatory notes (not silently produce garbage).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


# ---------- fba_simulate ----------

def test_fba_rejects_unknown_model_path():
    from fba_simulate_skill import run_fba
    r = run_fba(model_path="this_model_does_not_exist", multi_objective=True)
    assert not r["passed_qc"]
    assert "error" in r


def test_fba_rejects_unknown_backend():
    from fba_simulate_skill import run_fba
    r = run_fba(model_path="iML1515", multi_objective=True, backend="bogus_backend")
    assert not r["passed_qc"]


# ---------- golden_gate_assembly ----------

def test_golden_gate_rejects_palindromic_overhangs():
    """Rule 03 enforcement: palindromic overhangs (TGCA, GATC, CATG) self-anneal → FAIL."""
    from golden_gate_skill import run_golden_gate
    parts = json.loads((FIXTURES / "bad_5fragment-palindrome.json").read_text())
    r = run_golden_gate(parts, enzyme="BsaI")
    assert not r["passed_qc"]
    issues = r["overhang_validation"]["issues"]
    assert any("palindromic" in i.lower() for i in issues), issues


def test_golden_gate_rejects_internal_bsai_site():
    """Rule 04 enforcement: cassette with internal BsaI site → FAIL."""
    from golden_gate_skill import run_golden_gate
    parts = json.loads((FIXTURES / "bad_5fragment-internal-bsai.json").read_text())
    r = run_golden_gate(parts, enzyme="BsaI")
    assert not r["passed_qc"]
    assert r["internal_sites_count"] > 0


def test_golden_gate_rejects_unknown_enzyme():
    from golden_gate_skill import run_golden_gate
    parts = json.loads((FIXTURES / "5-fragment-test.json").read_text())
    r = run_golden_gate(parts, enzyme="ImaginaryEnzyme")
    assert not r["passed_qc"]


def test_golden_gate_rejects_empty_parts():
    from golden_gate_skill import run_golden_gate
    r = run_golden_gate([], enzyme="BsaI")
    assert not r["passed_qc"]


# ---------- codon_optimize ----------

def test_codon_optimize_rejects_no_input():
    """Both protein_seq and dna_native missing → must FAIL with full provenance."""
    from codon_optimize_skill import run_codon_optimize
    r = run_codon_optimize(host="ecoli")
    assert not r["passed_qc"]
    prov = r["tool_provenance"]
    assert all(k in prov for k in ("simulated", "partial", "full"))


# ---------- circuit_simulate ----------

def test_circuit_rejects_bistable_topology_without_sweep():
    """Rule 06 enforcement: bistable / toggle without parametric sweep → REJECT."""
    from circuit_simulate_skill import run
    r = run(topology="toggle", do_parametric_sweep=False)
    assert not r["passed_qc"]
    assert "rule 06" in r["error"].lower()


# ---------- biosensor_design ----------

def test_biosensor_rejects_undersized_panel():
    """Rule 10 enforcement: panel < 5 compounds → REJECT."""
    from biosensor_design_skill import run
    r = run(analyte="arabinose", custom_panel=["glucose"], n_cross_reactants_required=5)
    assert not r["passed_qc"]
    assert "rule 10" in r["error"].lower()


def test_biosensor_rejects_missing_analyte():
    from biosensor_design_skill import run
    r = run(analyte=None)
    assert not r["passed_qc"]


# ---------- cellfree_design ----------

def test_cellfree_rejects_glycosylated_target():
    """Bacterial cell-free has no glycosylation → glycosylated targets REJECTED."""
    from cellfree_design_skill import run
    r = run(target_protein="antibody_Fc", system="TX-TL", has_glycosylation=True)
    assert not r["passed_qc"]
    assert "REJECT_for_glycosylation" in r["flags"]


def test_cellfree_rejects_unknown_system():
    from cellfree_design_skill import run
    r = run(target_protein="GFP", system="MagicCellFree")
    assert not r["passed_qc"]


# ---------- bgc_mining ----------

def test_bgc_mining_rejects_no_cross_mibig():
    """Rule 09 enforcement: cross_mibig=False → REJECT (mandatory cross-check)."""
    from bgc_mining_skill import run
    r = run(fasta_path=str(FIXTURES / "streptomyces_pks_nrps.fasta"), cross_mibig=False)
    assert not r["passed_qc"]
    assert "rule 09" in r["error"].lower()


def test_bgc_mining_rejects_no_input():
    from bgc_mining_skill import run
    r = run(cross_mibig=True)  # no sequence/fasta_path
    assert not r["passed_qc"]


# ---------- skill_executor ----------

def test_skill_executor_handles_unknown_skill_id():
    from agents.skill_executor import run_skill
    r = run_skill("totally_made_up_skill", {})
    assert not r["passed_qc"]
    assert "not registered" in r["error"]
    prov = r["tool_provenance"]
    assert prov["simulated"] is True


def test_skill_executor_handles_bad_args():
    """Pass an arg the skill function doesn't accept → graceful failure."""
    from agents.skill_executor import run_skill
    r = run_skill("fba_simulate", {"this_kwarg_does_not_exist": True})
    assert not r["passed_qc"]
    assert "argument error" in r["error"]


# ---------- kegg-fetcher / ncbi-taxon-fetcher (positive smoke + cache-only neg) ----------

def test_kegg_fetcher_resolves_known_compound_from_cache():
    """'lycopene' is already cached as data/kegg/lycopene.json from prior demo runs."""
    from agents.skill_executor import run_skill
    r = run_skill("kegg_fetcher", {"query": "lycopene", "cache_only": True})
    assert r["passed_qc"], r
    assert r["kegg_id"]  # populated


def test_kegg_fetcher_returns_error_on_cache_miss_when_cache_only():
    from agents.skill_executor import run_skill
    r = run_skill("kegg_fetcher",
                  {"query": "this_compound_is_not_cached_xyz_123", "cache_only": True})
    assert not r["passed_qc"]


def test_ncbi_taxon_fetcher_resolves_known_organism_from_cache():
    """E. coli should be cached from prior demo runs."""
    from agents.skill_executor import run_skill
    r = run_skill("ncbi_taxon_fetcher", {"query": "E. coli", "cache_only": True})
    assert r["passed_qc"], r
    assert r["taxon_id"] == "562"
