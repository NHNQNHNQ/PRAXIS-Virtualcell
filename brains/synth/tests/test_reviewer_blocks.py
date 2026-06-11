"""Reviewer-block tests — verify the deterministic Reviewer rejects bad plans
that violate the 11 case-distilled rules. PROMPT-PRAXIS-Synth.md §完成标准 #4
requires the Reviewer to block at least one 'essential gene OptKnock' plan.
"""

from __future__ import annotations

import json
import re

import pytest

from agents import reviewer

# A minimally schema-valid scoping_plan we can reuse as `prior` for design tests
GOOD_SCOPING = {
    "task_id": "reviewer-block-test",
    "problem": {
        "synth_task": "strain_engineering",
        "host_organism": "E. coli",
        "scale": "industrial",
        "constraints": ["industrial fermenter"],
    },
    "candidate_strategies": [
        {"name": "OptKnock", "rationale": "case-009-derived",
         "evidence_case_ids": ["synth-009-strain-engineering-ko"]},
    ],
    "retrieved_evidence": {
        "cases": [{"case_id": "synth-009-strain-engineering-ko", "similarity": 0.5,
                   "pool": "same_task_same_host", "doi": "10.1002/bit.10803"}],
        "rules": [{"rule_id": "08-optknock-essential-audit"}],
    },
    "confidence": "high",
}


def _good_design():
    return {
        "task_id": "reviewer-block-test",
        "selected_strategy": {"name": "OptKnock baseline", "rationale": "..."},
        "design_library": [{
            "design_id": "D1",
            "kind": "KO_set",
            "spec": {"target": "lysine"},
            "rationale": "OptKnock-derived",
            "evidence_case_ids": ["synth-009-strain-engineering-ko"],
            "evidence_rule_ids": ["08-optknock-essential-audit", "01-fba-multiobjective"],
        }],
        "excluded_designs": [{
            "kind": "essential_gene_KO",
            "item": "rps* / rpl* essential genes",
            "reason": "rule 08 — essential KOs lethal",
            "rule_id": "08-optknock-essential-audit",
        }],
        "computational_pipeline": [{
            "step": 1, "skill": "optknock_strain",
            "args": {"audit_essential": True, "target_reaction": "EX_lys__L_e", "n_seeds": 5},
            "multi_objective": True,
            "rationale": "Rule 08 + Rule 01",
        }],
        "validation_plan": {"experiments": [{"assay": "HPLC", "expected_metric": "g/L lysine"}]},
        "confidence": "high",
    }


def test_design_passes_when_compliant():
    """Sanity: a fully-compliant design plan passes."""
    verdict = reviewer.review("design", _good_design(), prior={"scoping_plan": GOOD_SCOPING})
    assert verdict["passed"], verdict["required_repairs"]


def test_design_blocked_when_optknock_missing_audit_essential():
    """PROMPT 完成标准 #4 — bad OptKnock plan (no essential audit) MUST be blocked."""
    bad = _good_design()
    bad["computational_pipeline"][0]["args"].pop("audit_essential")
    verdict = reviewer.review("design", bad, prior={"scoping_plan": GOOD_SCOPING})
    assert not verdict["passed"]
    assert any("rule 08" in r for r in verdict["required_repairs"]), verdict


def test_design_blocked_when_excluded_designs_empty():
    """Empty excluded_designs[] is rejected (PRAXIS principle 7)."""
    bad = _good_design()
    bad["excluded_designs"] = []
    verdict = reviewer.review("design", bad, prior={"scoping_plan": GOOD_SCOPING})
    assert not verdict["passed"]
    assert any("excluded_designs" in r for r in verdict["required_repairs"])


def test_design_blocked_when_fba_single_objective():
    """Rule 01 — single-objective FBA blocked."""
    bad = _good_design()
    bad["computational_pipeline"].append({
        "step": 2, "skill": "fba_simulate", "args": {}, "multi_objective": False,
        "rationale": "should be rejected",
    })
    verdict = reviewer.review("design", bad, prior={"scoping_plan": GOOD_SCOPING})
    assert not verdict["passed"]
    assert any("rule 01" in r for r in verdict["required_repairs"])


def test_design_blocked_when_codon_optimize_after_fba():
    """Rule 02 — codon_optimize must precede fba_simulate when heterologous."""
    pathway_scoping = {**GOOD_SCOPING}
    pathway_scoping["problem"] = {**GOOD_SCOPING["problem"], "synth_task": "pathway_design"}
    bad = _good_design()
    bad["computational_pipeline"] = [
        {"step": 1, "skill": "fba_simulate", "args": {}, "multi_objective": True, "rationale": ""},
        {"step": 2, "skill": "codon_optimize", "args": {"forbidden_sites": {"BsaI": "GGTCTC"}}, "rationale": ""},
    ]
    verdict = reviewer.review("design", bad, prior={"scoping_plan": pathway_scoping})
    assert not verdict["passed"]
    assert any("rule 02" in r for r in verdict["required_repairs"])


def test_design_blocked_when_p450_missing_cpr():
    """Rule 11 — P450 in design_library must have CPR partner."""
    pathway_scoping = {**GOOD_SCOPING}
    pathway_scoping["problem"] = {**GOOD_SCOPING["problem"], "synth_task": "pathway_design"}
    bad = _good_design()
    bad["design_library"] = [{
        "design_id": "D1_artemisinin",
        "kind": "pathway_enzyme_set",
        "spec": {"enzyme": "CYP71AV1 (P450)", "ec": "1.14.13.x"},
        "rationale": "test",
    }]
    bad["computational_pipeline"] = [
        {"step": 1, "skill": "codon_optimize", "args": {"forbidden_sites": {"BsaI": "GGTCTC"}}, "rationale": ""},
        {"step": 2, "skill": "fba_simulate", "args": {}, "multi_objective": True, "rationale": ""},
    ]
    verdict = reviewer.review("design", bad, prior={"scoping_plan": pathway_scoping})
    assert not verdict["passed"]
    assert any("rule 11" in r.lower() for r in verdict["required_repairs"])


def test_execution_blocked_when_passed_qc_false_without_notes():
    """passed_qc=false MUST have explanatory notes (so the report agent can interpret).

    NB: full=true + passed_qc=false is now allowed — that legitimately means a
    validation skill ran fully and detected a design problem (e.g., overhang
    collision or restriction site present). What we still reject is
    passed_qc=false with no notes — that's an unaccounted failure.
    """
    bad_exec = {
        "task_id": "test",
        "steps": [{
            "step": 1, "skill": "fba_simulate", "args": {},
            "result": {"growth_rate": 0.0},
            "passed_qc": False,
            "tool_provenance": {"simulated": False, "partial": False, "full": True},
            "notes": "",  # <-- empty notes is the violation
        }],
        "summary": {"all_steps_passed": False, "any_simulated": False,
                    "headline_metric": {"name": "growth_rate", "value": 0.0, "unit": "1/h"}},
    }
    verdict = reviewer.review("execution", bad_exec)
    assert not verdict["passed"]
    assert any("notes" in r.lower() for r in verdict["required_repairs"])


def test_execution_passes_when_validation_skill_legitimately_rejects_design():
    """Validation skills (golden_gate, dna_constraint_solve) can run with full=true
    AND emit passed_qc=false WHEN there is a concrete reason (notes explain).
    This is the correct outcome for 'tool ran fine, design has a flaw'."""
    legit_exec = {
        "task_id": "test",
        "steps": [{
            "step": 1, "skill": "golden_gate_assembly", "args": {"enzyme": "BsaI"},
            "result": {
                "overhang_validation": {"passed": True},
                "internal_sites_count": 0,
            },
            "passed_qc": True,
            "tool_provenance": {"simulated": False, "partial": False, "full": True},
            "notes": "",
        }],
        "summary": {"all_steps_passed": True, "any_simulated": False,
                    "headline_metric": {"name": "n_internal_sites", "value": 0, "unit": "count"}},
    }
    verdict = reviewer.review("execution", legit_exec)
    assert verdict["passed"], verdict["required_repairs"]


def test_reporting_blocked_when_reproduce_sh_missing():
    """'不允许的捷径' #9 — missing reproduce.sh shell_script."""
    bad_report = {
        "task_id": "test",
        "summary": {"title": "test", "headline_metric": {"name": "x", "value": 1, "unit": ""}},
        "interpretation": {"why_succeeded": [], "why_failed": ["No failures recorded"], "literature_alignment": []},
        "reproducibility": {"shell_script": "", "tool_versions": {}},
        "references": [],
        "confidence": "low",
    }
    verdict = reviewer.review("reporting", bad_report, prior={})
    assert not verdict["passed"]
    assert any("shell_script" in r for r in verdict["required_repairs"])


def test_reporting_blocked_when_doi_invented():
    """References must come from retrieved_evidence — invented DOI is rejected."""
    bad_report = {
        "task_id": "test",
        "summary": {"title": "test", "headline_metric": {"name": "x", "value": 1, "unit": ""}},
        "interpretation": {"why_succeeded": [], "why_failed": ["No failures recorded"], "literature_alignment": []},
        "reproducibility": {"shell_script": "#!/bin/bash\necho hi", "tool_versions": {}},
        "references": [{"doi": "10.1234/fake.invented.2099", "citation": "Invented citation"}],
        "confidence": "medium",
    }
    prior = {"scoping_plan": {"retrieved_evidence": {"cases": [{"case_id": "x", "doi": "10.1038/nature12051"}]}}}
    verdict = reviewer.review("reporting", bad_report, prior=prior)
    assert not verdict["passed"]
    assert any("not in retrieved_evidence" in r for r in verdict["required_repairs"])
