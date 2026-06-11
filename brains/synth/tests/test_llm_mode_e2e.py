"""End-to-end LLM-mode tests — the brain MUST actually use case-grounded synthesis,
real tool numbers, and pass all 4 reviewer gates for each canonical demo.

These tests are the contract for "true case-based learning":
  - scoping/design synthesis is read from agents.llm_synthesis (case-grounded)
  - execution numbers come from real tool invocations (cobra, dnachisel, scipy)
  - reviewer gates pass for all 4 stages
  - report.references DOIs all come from retrieved_evidence
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents import llm_synthesis
from agents.orchestrator import run_pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


def _verify_all_gates_pass(history: dict, label: str) -> None:
    for stage in ("scoping_review", "design_review", "execution_review", "report_review"):
        verdict = history.get(stage)
        assert verdict is not None, f"{label}: missing {stage}"
        assert verdict["passed"], (
            f"{label}: {stage} blocked with: {verdict.get('required_repairs')}"
        )


def _verify_synthesis_came_from_llm(history: dict) -> None:
    assert "llm_synthesis" in history["scoping_plan"].get("_synthesis_source", "")
    assert "llm_synthesis" in history["design_plan"].get("_synthesis_source", "")


def _verify_dois_from_retrieved_evidence(history: dict) -> None:
    cited = {ref["doi"] for ref in history["report"].get("references", []) if ref.get("doi")}
    cases = history["scoping_plan"].get("retrieved_evidence", {}).get("cases", [])
    # Read DOIs from case files since stub_reporting reads them at runtime
    known = set()
    for c in cases:
        case_path = PROJECT_ROOT / "memory" / "cases" / f"{c['case_id']}.md"
        if case_path.exists():
            for line in case_path.read_text().splitlines():
                if line.startswith("key_paper_doi:"):
                    known.add(line.split(":", 1)[1].strip())
                    break
    invented = cited - known - {None, ""}
    assert not invented, f"references invented DOIs not in retrieved cases: {invented}"


def _verify_real_numbers_from_tools(history: dict) -> None:
    """Every step that claims full=true must have come from an actual tool call
    (the result dict contains the structured tool output)."""
    for step in history["execution_results"].get("steps", []):
        prov = step.get("tool_provenance", {})
        if prov.get("full"):
            res = step.get("result") or {}
            # Real tool runs produce real result dicts (not just a string error)
            assert isinstance(res, dict), step
            assert not res.get("error"), step
            assert "version" in prov, step
            assert "wallclock_seconds" in prov, step


# ---------- Lycopene demo ----------

def test_lycopene_llm_mode_full_pipeline():
    task = json.loads((FIXTURES / "example_lycopene.json").read_text())
    history = run_pipeline(task, mode="llm")

    _verify_all_gates_pass(history, "lycopene")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)

    # Specific contract: lycopene synthesis names CrtE/CrtB/CrtI explicitly
    design_text = json.dumps(history["design_plan"])
    assert "CrtE" in design_text
    assert "CrtB" in design_text
    assert "CrtI" in design_text
    # Pipeline ordering: codon_optimize MUST be earlier than fba_simulate (rule 02)
    pipeline = history["design_plan"]["computational_pipeline"]
    skills = [s["skill"] for s in pipeline]
    assert skills.index("codon_optimize") < skills.index("fba_simulate")

    # Headline number must be from a real tool — either fba_simulate growth_rate
    # (intermediate step) or optknock_strain top_product_flux (final step). With
    # latest-wins headline pluck the optknock step takes precedence.
    h = history["report"]["summary"]["headline_metric"]
    assert h["name"] in ("growth_rate", "top_product_flux"), h
    # Verify the iML1515 baseline growth was computed in some step
    fba_step = next(
        s for s in history["execution_results"]["steps"] if s["skill"] == "fba_simulate"
    )
    assert 0.85 <= fba_step["result"]["growth_rate"] <= 0.90

    # Rules invoked must be the ones from llm_synthesis
    rules = history["report"]["interpretation"]["rules_invoked"]
    assert "01-fba-multiobjective" in rules
    assert "02-codon-optimize-mandatory" in rules


# ---------- Lysine demo ----------

def test_lysine_llm_mode_full_pipeline():
    task = json.loads((FIXTURES / "example_lysine.json").read_text())
    history = run_pipeline(task, mode="llm")

    _verify_all_gates_pass(history, "lysine")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)

    # Lysine demo cites the OptKnock case directly
    cases = [c["case_id"] for c in history["scoping_plan"]["retrieved_evidence"]["cases"]]
    assert "synth-009-strain-engineering-ko" in cases

    # OptKnock step must have audit_essential=True (rule 08 enforcement)
    pipeline = history["design_plan"]["computational_pipeline"]
    optknock = next(s for s in pipeline if s["skill"] == "optknock_strain")
    assert optknock["args"]["audit_essential"] is True

    # Real OptKnock result has top_3_ko_sets with no ribosomal hits
    optknock_step = next(
        s for s in history["execution_results"]["steps"]
        if s["skill"] == "optknock_strain"
    )
    top3 = optknock_step["result"]["top_3_ko_sets"]
    assert top3, "OptKnock returned no KO sets"
    for ko_set in top3:
        assert not ko_set["ribosomal_hit"]


# ---------- Toggle switch demo ----------

def test_toggle_llm_mode_full_pipeline():
    task = json.loads((FIXTURES / "example_toggle.json").read_text())
    history = run_pipeline(task, mode="llm")

    _verify_all_gates_pass(history, "toggle")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)

    # Direct case match: synth-005
    cases = [c["case_id"] for c in history["scoping_plan"]["retrieved_evidence"]["cases"]]
    assert "synth-005-toggle-switch-circuit" in cases

    # circuit_simulate ran the 4-D parametric sweep (rule 06)
    circuit_step = next(
        s for s in history["execution_results"]["steps"]
        if s["skill"] == "circuit_simulate"
    )
    assert circuit_step["passed_qc"]
    assert circuit_step["result"]["bistable_region_present"] is True
    sweep = circuit_step["result"].get("parametric_sweep")
    assert sweep is not None and sweep["sweep_dims"] == 4

    # Recommended readout = flow_cytometry (rule 07)
    assert circuit_step["result"]["recommended_readout"] == "flow_cytometry"


# ---------- Sanity: list_supported_demos ----------

def test_llm_synthesis_supports_nine_demos():
    """All 9 synth_task types have a canonical LLM-mode demo."""
    demos = llm_synthesis.list_supported_demos()
    expected = {
        "demo-lycopene-ecoli-fermenter",      # pathway_design
        "demo-lysine-cglutamicum-industrial", # strain_engineering
        "demo-toggle-switch-ecoli",           # circuit
        "demo-iml1515-fba-aerobic",           # fba
        "demo-moclo-5fragment-assembly",      # plasmid_assembly
        "demo-il2-codon-opt-yeast",           # codon_opt
        "demo-txtl-gfp-prototyping",          # cell_free
        "demo-arabinose-biosensor",           # biosensor
        "demo-streptomyces-bgc-mining",       # bgc_mining
    }
    assert expected.issubset(set(demos)), f"missing: {expected - set(demos)}"


# ---------- 6 single-skill demos (fba/moclo/codonopt/cellfree/biosensor/bgc) ----------

def test_fba_demo_e2e():
    task = json.loads((FIXTURES / "example_fba.json").read_text())
    history = run_pipeline(task, mode="llm")
    _verify_all_gates_pass(history, "fba")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)
    h = history["report"]["summary"]["headline_metric"]
    assert h["name"] == "growth_rate"
    assert 0.85 <= h["value"] <= 0.90


def test_moclo_demo_e2e():
    task = json.loads((FIXTURES / "example_moclo.json").read_text())
    history = run_pipeline(task, mode="llm")
    _verify_all_gates_pass(history, "moclo")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)
    skills = [s["skill"] for s in history["design_plan"]["computational_pipeline"]]
    assert skills.index("dna_constraint_solve") < skills.index("golden_gate_assembly")
    exps = history["design_plan"]["validation_plan"]["experiments"]
    assert any(e.get("colony_pick_n", 0) >= 3 and e.get("colony_pcr") and e.get("full_plasmid_seq") for e in exps)


def test_codon_opt_demo_e2e():
    task = json.loads((FIXTURES / "example_codonopt.json").read_text())
    history = run_pipeline(task, mode="llm")
    _verify_all_gates_pass(history, "codonopt")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)
    co_step = next(s for s in history["execution_results"]["steps"] if s["skill"] == "codon_optimize")
    res = co_step["result"]
    assert res["cai_delta"] is not None and res["cai_delta"] > 0
    assert res["protein_identical"]
    assert all(v == 0 for v in res["restriction_sites"].values())


def test_cellfree_demo_e2e():
    task = json.loads((FIXTURES / "example_cellfree.json").read_text())
    history = run_pipeline(task, mode="llm")
    _verify_all_gates_pass(history, "cellfree")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)
    skills = [s["skill"] for s in history["design_plan"]["computational_pipeline"]]
    assert skills.index("codon_optimize") < skills.index("cellfree_design")
    cf_step = next(s for s in history["execution_results"]["steps"] if s["skill"] == "cellfree_design")
    assert cf_step["result"]["system_chosen"] == "TX-TL"
    assert 8 <= cf_step["result"]["recipe"]["Mg_mM"] <= 15


def test_biosensor_demo_e2e():
    task = json.loads((FIXTURES / "example_biosensor.json").read_text())
    history = run_pipeline(task, mode="llm")
    _verify_all_gates_pass(history, "biosensor")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)
    bs_step = next(s for s in history["execution_results"]["steps"] if s["skill"] == "biosensor_design")
    res = bs_step["result"]
    assert res["cross_reactant_panel"]["n_compounds"] >= 5
    assert res["dynamic_range_fold"] >= 5
    assert res["recommended_readout"] == "flow_cytometry"


def test_bgc_demo_e2e():
    task = json.loads((FIXTURES / "example_bgc.json").read_text())
    history = run_pipeline(task, mode="llm")
    _verify_all_gates_pass(history, "bgc")
    _verify_synthesis_came_from_llm(history)
    _verify_dois_from_retrieved_evidence(history)
    _verify_real_numbers_from_tools(history)
    bg_step = next(s for s in history["execution_results"]["steps"] if s["skill"] == "bgc_mining")
    res = bg_step["result"]
    for c in res.get("candidate_clusters", []):
        assert "mibig_match_pct" in c
        assert "novelty_band" in c


# ---------- Stub fallback for non-canonical task ----------

def test_llm_mode_falls_back_to_stub_for_unknown_task():
    """When task_id has no embedded synthesis, --mode llm gracefully falls back to stub.
    The pipeline still runs end-to-end; the synthesis_source label distinguishes them."""
    task = {
        "task_id": "non-canonical-fba-test",
        "problem": {"synth_task": "fba", "host_organism": "E. coli K-12 MG1655", "constraints": []},
    }
    history = run_pipeline(task, mode="llm")
    assert history["scoping_plan"]["_synthesis_source"].startswith("stub")
    # Reviewer still gates everything
    _verify_all_gates_pass(history, "fallback")
