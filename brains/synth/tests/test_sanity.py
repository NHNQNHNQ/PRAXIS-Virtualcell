"""Sanity tests — 4 reference numerical checks from PROMPT-PRAXIS-Synth.md §Phase 7.

Each test is deterministic enough to assert numeric ranges. Failures surface
either real regressions or anti-shortcut violations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


def test_iml1515_fba_aerobic_glucose():
    """sanity 1 — iML1515 baseline growth ∈ [0.85, 0.90]; multi-objective default; MEMOTE passes."""
    from fba_simulate_skill import run_fba

    r = run_fba(model_path="iML1515", multi_objective=True)
    assert r["passed_qc"], r
    assert 0.85 <= r["growth_rate"] <= 0.90, f"growth_rate={r['growth_rate']!r}"
    assert r["memote_passed"], r["memote_issues"]
    assert r["multi_objective"] is True
    assert r["tool_provenance"]["full"] is True


def test_fba_rejects_single_objective_without_override():
    """Rule-01 enforcement: single-objective mode is rejected unless explicit override."""
    from fba_simulate_skill import run_fba

    r = run_fba(model_path="iML1515", multi_objective=False)
    assert not r["passed_qc"]
    assert "rule 01" in r["error"].lower()


def test_golden_gate_5frag_unique_overhangs():
    """sanity 2 — 5-fragment fixture: unique non-palindromic overhangs, 0 internal sites."""
    from golden_gate_skill import run_golden_gate

    parts = json.loads((FIXTURES / "5-fragment-test.json").read_text())
    r = run_golden_gate(parts, enzyme="BsaI")
    assert r["passed_qc"], r
    junctions = [p["overhang_3"] for p in r["plan"]["parts"]]
    assert len(set(junctions)) == len(junctions), "junctions must be unique"
    assert r["internal_sites_count"] == 0
    assert r["overhang_validation"]["passed"] is True
    assert r["plan"]["ligation_chain_ok"] is True


def test_gfp_codon_optimize_cai_rises():
    """sanity 3 — GFP rare-codon-loaded → ΔCAI ≥ 0.3, protein identical, 0 forbidden sites, GC ∈ [0.35, 0.55]."""
    from codon_optimize_skill import run_codon_optimize

    fasta_text = (FIXTURES / "gfp_native.fasta").read_text()
    dna = "".join(line.strip() for line in fasta_text.splitlines() if not line.startswith(">"))

    r = run_codon_optimize(dna_native=dna, host="ecoli")
    assert r["passed_qc"], r["issues"]
    assert r["cai_delta"] is not None and r["cai_delta"] >= 0.3, f"cai_delta={r['cai_delta']!r}"
    assert r["protein_identical"]
    for site, count in r["restriction_sites"].items():
        assert count == 0, f"forbidden site {site} count={count}"
    assert 0.35 <= r["gc_after"] <= 0.55, f"gc_after={r['gc_after']!r}"


@pytest.mark.slow
def test_optknock_lysine_no_ribosomal():
    """sanity 4 — OptKnock(iML1515, lysine) top-3 contains no ribosomal genes; essential audit applied."""
    from optknock_skill import run_optknock

    r = run_optknock(
        model_path="iML1515",
        target_reaction="EX_lys__L_e",
        max_ko=2,
        n_candidates_per_seed=8,
        n_seeds=2,
        audit_essential=True,
    )
    assert r["passed_qc"], r["audit_violations"]
    assert r["n_essential_audited"] > 50, "essential audit removed too few"
    assert len(r["top_3_ko_sets"]) > 0
    pattern = re.compile(r"^(rps|rpl|rpm|infA|infB|infC|tufA|tufB)", re.IGNORECASE)
    for ko_set in r["top_3_ko_sets"]:
        assert not ko_set["ribosomal_hit"], ko_set
        for g in ko_set["genes"]:
            assert g not in r["essential_genes_audited_out"], f"essential {g} slipped through"


def test_heterologous_pathway_recommends_codon_opt():
    """Rule-02 + rule-11 enforcement: artemisinic acid → pipeline starts with codon_optimize, P450 needs CPR."""
    from pathway_design_skill import design_pathway

    r = design_pathway("artemisinic_acid", host="Saccharomyces cerevisiae", require_kegg_validation=False)
    assert r["passed_qc"], r["warnings"]
    assert r["needs_codon_opt"] is True
    assert r["partner_check"]["P450_present"] is True
    assert r["partner_check"]["CPR_required"] is True
    pipeline_steps = [s["step"] for s in r["recommended_pipeline"]]
    assert pipeline_steps[0] == "codon_optimize", pipeline_steps
    # codon_optimize must come BEFORE fba_simulate
    assert pipeline_steps.index("codon_optimize") < pipeline_steps.index("fba_simulate")
