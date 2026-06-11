"""Retrieval tests — verify 8-channel retrieval surfaces the right cases + rules."""

from __future__ import annotations

import pytest

from agents.retrieval import retrieve


def test_lycopene_query_surfaces_pathway_and_host():
    """Lycopene/E.coli query surfaces synth-002 (same_task pathway) AND a same_host case."""
    r = retrieve({
        "synth_task": "pathway_design",
        "host_organism": "E. coli",
        "target_compound": "lycopene",
        "pathway_class": "terpenoid",
    }, stage="scoping", top_k=5)
    case_ids = [c["case_id"] for c in r["cases"]]
    assert "synth-002-pathway-artemisinin" in case_ids
    pools = {c["case_id"]: c["pool"] for c in r["cases"]}
    # Should have at least one same_host (E. coli) case
    assert any(p in ("same_task_same_host", "same_host") for p in pools.values())


def test_lycopene_query_surfaces_codon_opt_and_p450_rules():
    """Rules: pathway_design + terpenoid query → codon-opt + P450-CPR rules surface."""
    r = retrieve({
        "synth_task": "pathway_design",
        "host_organism": "E. coli",
        "target_compound": "lycopene",
        "pathway_class": "terpenoid",
    }, stage="scoping", top_k=5)
    rule_ids = [rl["rule_id"] for rl in r["rules"]]
    assert "02-codon-optimize-mandatory" in rule_ids
    assert "11-p450-cpr-partner" in rule_ids


def test_strain_engineering_query_surfaces_optknock_audit():
    """Strain-engineering + C. glutamicum + lysine query → rule 08 + rule 01 surface."""
    r = retrieve({
        "synth_task": "strain_engineering",
        "host_organism": "Corynebacterium glutamicum",
        "target_compound": "lysine",
        "scale": "industrial",
    }, stage="design", top_k=5)
    rule_ids = [rl["rule_id"] for rl in r["rules"]]
    assert "08-optknock-essential-audit" in rule_ids
    assert "01-fba-multiobjective" in rule_ids


def test_bgc_mining_surfaces_mibig_rule():
    r = retrieve({"synth_task": "bgc_mining", "host_organism": "Streptomyces"}, stage="scoping", top_k=5)
    rule_ids = [rl["rule_id"] for rl in r["rules"]]
    assert "09-antismash-mibig-cross" in rule_ids


def test_retrieval_mode_at_n10():
    """With n=10 cases, mode should be same_task_only (not full)."""
    r = retrieve({"synth_task": "fba", "host_organism": "E. coli"}, stage="scoping")
    assert r["n_cases_in_library"] == 10
    assert r["retrieval_mode"] == "same_task_only"


def test_freetext_only_query_uses_no_pool_routing():
    r = retrieve({"free_text": "toggle switch bistable"}, stage="scoping", top_k=3)
    assert r["retrieval_mode"] == "no_pool_routing"
    case_ids = [c["case_id"] for c in r["cases"]]
    assert "synth-005-toggle-switch-circuit" in case_ids
