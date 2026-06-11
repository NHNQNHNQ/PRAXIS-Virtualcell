"""4-stage orchestrator with Reviewer gate (PRAXIS-Synth).

Stages: scoping → design → execution → reporting
Gate: deterministic rule-based Reviewer (agents.reviewer.review)
Repair: max 2 loops per stage; on persistent failure, output is frozen with `_warning`.

Two operating modes:
  --mode stub  (default)    Tools-only: composes plans deterministically from retrieval
                            + rule library. No LLM call. Good for demos and CI.
  --mode llm                Calls Anthropic API for each stage. Requires ANTHROPIC_API_KEY.

The stub mode is exposed primarily for end-to-end smoke tests + the
PROMPT-PRAXIS-Synth.md §完成标准 demo (lycopene → pathway design).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.retrieval import retrieve  # noqa: E402
from agents import reviewer as reviewer_mod  # noqa: E402
from agents.skill_executor import run_skill, list_skills  # noqa: E402
from agents import llm_synthesis  # noqa: E402
from agents import llm_api  # noqa: E402

CASES_DIR = PROJECT_ROOT / "memory" / "cases"
RULES_DIR = PROJECT_ROOT / "memory" / "rules"
RUNS_DIR = PROJECT_ROOT / "runs"

P450_RE = re.compile(r"(p450|cyp\d|EC\s*1\.14)", re.IGNORECASE)


# ---------- helpers ----------

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _read_doi_from_case(case_id: str) -> str | None:
    p = CASES_DIR / f"{case_id}.md"
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
        m = re.search(r"key_paper_doi:\s*(.+)", text)
        if m:
            return m.group(1).strip().strip('"').strip()
    except Exception:
        pass
    return None


def _slim_rules_for(synth_task: str, retrieved_rules: list[dict]) -> list[dict]:
    """Trim retrieved rules to those applicable to this synth_task."""
    out = []
    for r in retrieved_rules:
        applies = (r.get("applies_to") or {}).get("synth_tasks") or []
        if "ALL" in applies or "all" in applies or synth_task in applies:
            out.append(r)
        elif r.get("rule_type") == "cold_start_defaults":
            out.append(r)
    return out


# ---------- stub stage implementations ----------

def stub_scoping(task_input: dict) -> dict:
    """Compose a scoping plan from retrieval + rules — no LLM."""
    problem = task_input["problem"]
    synth_task = problem["synth_task"]
    retrieval = retrieve(
        {
            "synth_task": synth_task,
            "host_organism": problem.get("host_organism"),
            "target_compound": (
                problem.get("target_compound", {}).get("name")
                if isinstance(problem.get("target_compound"), dict)
                else problem.get("target_compound")
            ),
            "pathway_class": problem.get("pathway_class"),
            "assembly_strategy": problem.get("assembly_strategy"),
            "scale": problem.get("scale"),
        },
        stage="scoping",
        top_k=5,
    )

    cases = retrieval.get("cases", []) or []
    rules = _slim_rules_for(synth_task, retrieval.get("rules", []) or [])

    # Build candidate strategies
    candidates = []
    if synth_task == "pathway_design":
        candidates = [
            {
                "name": "RetroPath2.0-derived enzyme set",
                "rationale": "Multi-tool consensus required for pathway_design (synthesis §VII multi-method).",
                "method": "retropath2",
                "evidence_case_ids": [c["case_id"] for c in cases[:1]] or [],
                "evidence_rule_ids": [r["rule_id"] for r in rules if "task-overview-pathway_design" in r.get("rule_id", "")],
            },
            {
                "name": "KEGG graph traversal + Cameo pathway prediction",
                "rationale": "Provides orthogonal route hypotheses; KEGG-validated intermediates.",
                "method": "kegg+cameo",
                "evidence_case_ids": [c["case_id"] for c in cases[:1]] or [],
                "evidence_rule_ids": [r["rule_id"] for r in rules if r["rule_id"] == "02-codon-optimize-mandatory"],
            },
            {
                "name": "OptKnock-augmented strain design (when host = production strain)",
                "rationale": "Couples pathway with strain engineering for industrial scale.",
                "method": "optknock+pathway",
                "evidence_case_ids": [c["case_id"] for c in cases if c.get("synth_task") in ("strain_engineering", "fba")][:1] or [c["case_id"] for c in cases[:1]] or [],
                "evidence_rule_ids": [r["rule_id"] for r in rules if r["rule_id"] in ("01-fba-multiobjective", "08-optknock-essential-audit")],
            },
        ]
    elif synth_task == "bgc_mining":
        candidates = [
            {"name": "antiSMASH 7 rule-based prediction", "rationale": "Standard tool; high recall.", "method": "antismash",
             "evidence_case_ids": [c["case_id"] for c in cases[:1]] or [], "evidence_rule_ids": ["09-antismash-mibig-cross"]},
            {"name": "DeepBGC ML prediction", "rationale": "Catches BGCs that antiSMASH rules miss.", "method": "deepbgc",
             "evidence_case_ids": [c["case_id"] for c in cases[:1]] or [], "evidence_rule_ids": ["09-antismash-mibig-cross"]},
            {"name": "BiG-SCAPE clustering + MIBiG cross-check", "rationale": "Group homologous BGCs and assess novelty.", "method": "bigscape",
             "evidence_case_ids": [c["case_id"] for c in cases[:1]] or [], "evidence_rule_ids": ["09-antismash-mibig-cross"]},
        ]
    else:
        # Single-strategy default for the other 7 synth_task types
        first_case = cases[0]["case_id"] if cases else None
        candidates = [{
            "name": f"{synth_task}-default",
            "rationale": f"Standard pipeline derived from retrieved case + applicable rules.",
            "method": synth_task,
            "evidence_case_ids": [first_case] if first_case else [],
            "evidence_rule_ids": [r["rule_id"] for r in rules[:2]],
        }]

    # Confidence
    if retrieval.get("retrieval_mode") == "cold_start":
        confidence = "cold_start"
    elif len(cases) >= 2 and any(c["pool"] == "same_task_same_host" for c in cases):
        confidence = "high"
    elif cases:
        confidence = "medium"
    else:
        confidence = "low"

    plan = {
        "task_id": task_input.get("task_id"),
        "problem": problem,
        "literature_summary": [
            {"doi": _read_doi_from_case(c["case_id"]) or "",
             "key_finding": f"From {c['case_id']}: pool={c['pool']}, similarity={c.get('similarity', 0)}",
             "relevance": "high" if c["pool"] == "same_task_same_host" else "medium"}
            for c in cases[:3]
        ],
        "retrieved_evidence": {
            "cases": [{"case_id": c["case_id"], "similarity": c.get("similarity", 0.0), "pool": c["pool"],
                       "key_takeaway": f"{c.get('synth_task')} on {c.get('host_organism', '?')}",
                       "doi": c.get("doi")} for c in cases],
            "rules": [{"rule_id": r["rule_id"], "applicability_note": f"score={r.get('score', 'fallback')}"}
                      for r in rules],
        },
        "candidate_strategies": candidates,
        "confidence": confidence,
        "open_questions": ["Confirm host strain (K-12 vs BL21 vs industrial)"] if confidence == "cold_start" else [],
    }
    return plan


def stub_design(scoping_plan: dict) -> dict:
    """Compose a design plan that satisfies all 11 rules deterministically."""
    problem = scoping_plan["problem"]
    synth_task = problem["synth_task"]
    selected = scoping_plan["candidate_strategies"][0]

    design_library: list[dict] = []
    excluded: list[dict] = []
    pipeline: list[dict] = []
    experiments: list[dict] = []

    # Compose by synth_task
    if synth_task == "pathway_design":
        target = problem.get("target_compound", {})
        target_name = target.get("name") if isinstance(target, dict) else str(target)
        design_library.append({
            "design_id": "D1_pathway_enzymes",
            "kind": "pathway_enzyme_set",
            "spec": {
                "target_compound": target_name,
                "host": problem.get("host_organism"),
                "heterologous": True,
                "native_source": "Artemisia annua / Pantoea ananatis (per case-002/synth-010)",
                "p450": True if "artemisin" in str(target_name).lower() else False,
                "cpr_partner": "yeast NADPH-CPR (case-002)" if "artemisin" in str(target_name).lower() else None,
            },
            "rationale": "Heterologous pathway; ★rule 02 codon_optimize required; ★rule 11 P450+CPR pairing",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:2]],
            "evidence_rule_ids": ["02-codon-optimize-mandatory", "11-p450-cpr-partner"],
        })
        excluded.extend([
            {"kind": "essential_gene_KO", "item": "rps* / rpl* / infA / tufA",
             "reason": "iML1515 essential by Keio data; rule 08", "rule_id": "08-optknock-essential-audit"},
            {"kind": "internal_restriction_site", "item": "BsaI / BsmBI / SapI in cassette",
             "reason": "Type-IIs cleaves internally → assembly failure (rule 04)",
             "rule_id": "04-restriction-site-destroy"},
        ])
        pipeline = [
            {"step": 1, "skill": "heterologous_pathway_design",
             "args": {"target_compound": str(target_name), "host": problem.get("host_organism", "E. coli")},
             "rationale": "Resolve enzyme set + KEGG validation"},
            {"step": 2, "skill": "codon_optimize",
             "args": {"protein_seq": "MKKL...placeholder", "host": "ecoli",
                      "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC", "SapI": "GCTCTTC"}},
             "rationale": "Rule 02: heterologous → codon opt mandatory"},
            {"step": 3, "skill": "golden_gate_assembly",
             "args": {"enzyme": "BsaI", "parts": []},
             "rationale": "Modular plasmid assembly (rule 04 prerequisite met by step 2 forbidden_sites)"},
            {"step": 4, "skill": "fba_simulate",
             "args": {"model_path": "iML1515", "secondary_objective": None},
             "multi_objective": True,
             "rationale": "Rule 01: multi-objective Pareto growth + product"},
            {"step": 5, "skill": "optknock_strain",
             "args": {"model_path": "iML1515", "target_reaction": "EX_lyc_e",
                      "audit_essential": True, "n_seeds": 5, "max_ko": 3},
             "multi_objective": True,
             "rationale": "Rule 08: essential audit must run before KO search"},
        ]
        experiments = [
            {"assay": "HPLC titer", "expected_metric": "mg/L", "n_replicates": 3,
             "colony_pick_n": 3, "colony_pcr": True, "full_plasmid_seq": True},
        ]
    elif synth_task == "fba":
        design_library.append({
            "design_id": "D1_fba_baseline",
            "kind": "strain_modification",
            "spec": {"model": "iML1515", "medium": "M9+glucose aerobic"},
            "rationale": "Baseline FBA + Pareto",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["01-fba-multiobjective"],
        })
        excluded.append({"kind": "essential_gene_KO", "item": "all Keio-essential genes",
                         "reason": "rule 08", "rule_id": "08-optknock-essential-audit"})
        pipeline = [
            {"step": 1, "skill": "fba_simulate",
             "args": {"model_path": "iML1515"}, "multi_objective": True,
             "rationale": "Rule 01: multi-objective"},
        ]
        experiments = [{"assay": "biomass yield", "expected_metric": "g/g_glucose", "n_replicates": 3}]
    elif synth_task == "plasmid_assembly":
        design_library.append({
            "design_id": "D1_moclo_plasmid",
            "kind": "plasmid_construct",
            "spec": {"strategy": "Golden Gate / MoClo", "n_fragments": 5},
            "rationale": "Standard MoClo level-1 assembly",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["03-golden-gate-overhang-collision", "04-restriction-site-destroy", "05-multi-colony-pick"],
        })
        excluded.append({"kind": "palindromic_overhang", "item": "TGCA / GATC / etc.",
                         "reason": "rule 03 — palindromes self-anneal", "rule_id": "03-golden-gate-overhang-collision"})
        pipeline = [
            {"step": 1, "skill": "codon_optimize",
             "args": {"protein_seq": "M...", "host": "ecoli",
                      "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC"}},
             "rationale": "Rule 04 prerequisite for golden_gate"},
            {"step": 2, "skill": "golden_gate_assembly",
             "args": {"enzyme": "BsaI", "parts": []},
             "rationale": "MoClo level-1 assembly"},
        ]
        experiments = [
            {"assay": "colony PCR", "expected_metric": "n correct/n picked", "colony_pick_n": 3,
             "colony_pcr": True, "full_plasmid_seq": True},
        ]
    elif synth_task == "strain_engineering":
        design_library.append({
            "design_id": "D1_ko_set",
            "kind": "KO_set",
            "spec": {"target": problem.get("target_compound"), "host": problem.get("host_organism"),
                     "max_ko": 3},
            "rationale": "OptKnock-derived KO recommendations with essential-gene audit",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["08-optknock-essential-audit", "01-fba-multiobjective"],
        })
        excluded.append({"kind": "essential_gene_KO", "item": "all genes flagged by single_gene_deletion",
                         "reason": "rule 08", "rule_id": "08-optknock-essential-audit"})
        pipeline = [
            {"step": 1, "skill": "optknock_strain",
             "args": {"model_path": "iML1515", "target_reaction": "EX_lys__L_e",
                      "audit_essential": True, "n_seeds": 2, "max_ko": 2,
                      "n_candidates_per_seed": 8},
             "multi_objective": True,
             "rationale": "Rule 08 audit + rule 01 multi-objective"},
        ]
        experiments = [{"assay": "HPLC titer (lysine)", "expected_metric": "g/L", "n_replicates": 3}]
    elif synth_task == "circuit":
        design_library.append({
            "design_id": "D1_toggle",
            "kind": "circuit_topology",
            "spec": {"type": "bistable toggle", "host": "E. coli"},
            "rationale": "Bistable toggle with parametric sweep",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["06-bistable-parametric-sim", "07-flow-cytometry-bimodal"],
        })
        excluded.append({"kind": "single_param_design", "item": "fixed alpha/beta/n",
                         "reason": "rule 06 — bistability is parametric-region-bounded",
                         "rule_id": "06-bistable-parametric-sim"})
        pipeline = [{"step": 1, "skill": "circuit_simulate",
                     "args": {"topology": "toggle", "param_sweep_dims": 4},
                     "rationale": "Rule 06 parametric sweep"}]
        experiments = [{"assay": "fluorescence bimodal", "expected_metric": "% bistable cells",
                        "n_replicates": 3, "flow_cytometry": True}]
    elif synth_task == "biosensor":
        design_library.append({
            "design_id": "D1_sensor",
            "kind": "sensor_topology",
            "spec": {"type": "TF-promoter", "analyte": problem.get("target_analyte")},
            "rationale": "Inducible TF-promoter sensor",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["10-biosensor-specificity-panel", "07-flow-cytometry-bimodal"],
        })
        excluded.append({"kind": "single-target-test", "item": "no off-targets",
                         "reason": "rule 10", "rule_id": "10-biosensor-specificity-panel"})
        pipeline = [{"step": 1, "skill": "biosensor_design",
                     "args": {"analyte": problem.get("target_analyte")},
                     "rationale": "Rule 10 cross-reactant panel"}]
        experiments = [{
            "assay": "dose-response", "expected_metric": "fold-change", "n_replicates": 3,
            "flow_cytometry": True,
            "cross_reactant_panel": {"n_compounds": 5, "list": ["glucose", "galactose", "xylose", "lyxose", "fructose"]},
        }]
    elif synth_task == "bgc_mining":
        design_library.append({
            "design_id": "D1_bgc_consensus",
            "kind": "BGC_candidate",
            "spec": {"genome": problem.get("target_data") or "Streptomyces sp.", "tools": ["antiSMASH", "DeepBGC"]},
            "rationale": "Multi-tool consensus + MIBiG cross-check",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["09-antismash-mibig-cross"],
        })
        excluded.append({"kind": "single-tool-prediction", "item": "antiSMASH-only",
                         "reason": "rule 09 multi-method consensus", "rule_id": "09-antismash-mibig-cross"})
        # Use the bundled streptomyces fixture for stub-mode demos
        fixture = str(PROJECT_ROOT / "tests" / "fixtures" / "streptomyces_pks_nrps.fasta")
        pipeline = [{"step": 1, "skill": "bgc_mining",
                     "args": {"fasta_path": fixture, "cross_mibig": True, "require_consensus": False},
                     "rationale": "Rule 09: cross-MIBiG (consensus relaxed in stub mode when antiSMASH binary absent)"}]
        experiments = [{"assay": "untargeted MS", "expected_metric": "novel mass features", "n_replicates": 3}]
    elif synth_task == "codon_opt":
        design_library.append({
            "design_id": "D1_codon",
            "kind": "sequence_optimized",
            "spec": {"protein": problem.get("target_protein") or problem.get("input_protein"),
                     "host": problem.get("host_organism") or problem.get("target_host")},
            "rationale": "DNAchisel multi-constraint solve",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["02-codon-optimize-mandatory", "04-restriction-site-destroy"],
        })
        excluded.append({"kind": "rare_codon_overuse", "item": "CAI > 0.95",
                         "reason": "rule 02 boundary — over-opt breaks folding",
                         "rule_id": "02-codon-optimize-mandatory"})
        pipeline = [{"step": 1, "skill": "codon_optimize",
                     "args": {"host": problem.get("target_host", "ecoli"),
                              "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC", "SapI": "GCTCTTC"}},
                     "rationale": "Rule 02"}]
        experiments = [{"assay": "expression yield", "expected_metric": "mg/L", "n_replicates": 3}]
    elif synth_task == "cell_free":
        design_library.append({
            "design_id": "D1_cellfree",
            "kind": "fermentation_recipe",
            "spec": {"system": "TX-TL", "Mg_mM": 12, "K_glu_mM": 150},
            "rationale": "Standard TX-TL protein synthesis recipe",
            "evidence_case_ids": [c["case_id"] for c in scoping_plan["retrieved_evidence"]["cases"][:1]],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
        })
        excluded.append({"kind": "PTM_target", "item": "glycosylated antibody Fc",
                         "reason": "TX-TL E. coli extract lacks glycosylation",
                         "rule_id": "02-codon-optimize-mandatory"})
        pipeline = [
            {"step": 1, "skill": "codon_optimize",
             "args": {"host": "ecoli", "forbidden_sites": {"BsaI": "GGTCTC"}},
             "rationale": "Rule 02"},
            {"step": 2, "skill": "cellfree_design",
             "args": {"system": "TX-TL"},
             "rationale": "TX-TL recipe"},
        ]
        experiments = [{"assay": "protein yield", "expected_metric": "mg/mL", "n_replicates": 3}]

    return {
        "task_id": scoping_plan["task_id"],
        "selected_strategy": {"name": selected["name"], "rationale": selected["rationale"]},
        "design_library": design_library,
        "excluded_designs": excluded,
        "computational_pipeline": pipeline,
        "validation_plan": {"experiments": experiments, "readout": "wet-lab"},
        "confidence": scoping_plan.get("confidence", "medium"),
    }


def _resolve_relpath_args(args: dict, skill: str) -> dict:
    """Translate the LLM-mode `_relpath` shorthand args into actual skill kwargs.

    The LLM design plan can use abstract names like `dna_native_fasta_relpath` so it
    doesn't have to inline kilobyte sequences; the orchestrator resolves these to
    concrete `dna_native` / `fasta_path` / `parts` arguments at execution time.
    """
    out = dict(args)
    if "dna_native_fasta_relpath" in out:
        rel = out.pop("dna_native_fasta_relpath")
        text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
        out["dna_native"] = "".join(line.strip() for line in text.splitlines() if not line.startswith(">"))
    if "fasta_path_relpath" in out:
        out["fasta_path"] = str(PROJECT_ROOT / out.pop("fasta_path_relpath"))
    if "parts_fixture_relpath" in out:
        out["parts"] = json.loads((PROJECT_ROOT / out.pop("parts_fixture_relpath")).read_text(encoding="utf-8"))
    return out


def stub_execution(design_plan: dict, run_dir: Path | None = None) -> dict:
    """Run each pipeline step via skill_executor and tag provenance."""
    results = []
    any_simulated = False
    all_passed = True
    headline = None

    for step_spec in design_plan.get("computational_pipeline", []):
        skill = step_spec["skill"]
        original_args = step_spec.get("args", {}) or {}
        args = _resolve_relpath_args(original_args, skill)
        step_idx = step_spec.get("step", len(results) + 1)
        notes = ""

        skill_result = run_skill(skill, args)
        # Make sure tool_provenance has all three flags
        prov = skill_result.get("tool_provenance") or {}
        for k in ("simulated", "partial", "full"):
            prov.setdefault(k, False)
        if not any(prov.get(k) for k in ("simulated", "partial", "full")):
            prov["simulated"] = True
        skill_result["tool_provenance"] = prov

        if prov.get("simulated"):
            any_simulated = True
            notes = skill_result.get("error", "tool unavailable; simulated stub")

        passed = bool(skill_result.get("passed_qc", True))
        if not passed:
            all_passed = False
            if not notes:
                notes = skill_result.get("error", "passed_qc=false from skill")

        # Pluck a headline metric. Strategy: the LATEST step in the pipeline that produced
        # a known-shape result wins, because pipelines are ordered and downstream steps
        # are usually the user-facing answer (e.g., for cell_free the codon_optimize CAI
        # is a means; the cellfree_design predicted_yield is the goal).
        candidate_headline = None
        if skill == "fba_simulate" and "growth_rate" in skill_result:
            candidate_headline = {"name": "growth_rate", "value": skill_result["growth_rate"], "unit": "1/h"}
        elif skill == "optknock_strain" and skill_result.get("top_3_ko_sets"):
            top = skill_result["top_3_ko_sets"][0]
            candidate_headline = {"name": "top_product_flux", "value": top.get("product_flux", 0.0),
                                  "unit": "mmol/gDW/h"}
        elif skill == "codon_optimize" and "cai_after" in skill_result:
            candidate_headline = {"name": "CAI", "value": skill_result["cai_after"], "unit": "-"}
        elif skill == "circuit_simulate":
            candidate_headline = {
                "name": "parameter_robustness_score",
                "value": skill_result.get("parameter_robustness_score", 0.0),
                "unit": "fraction_bistable",
            }
        elif skill == "biosensor_design":
            candidate_headline = {
                "name": "dynamic_range_fold",
                "value": skill_result.get("dynamic_range_fold", 0.0),
                "unit": "fold-change",
            }
        elif skill == "cellfree_design":
            candidate_headline = {
                "name": "predicted_yield",
                "value": skill_result.get("predicted_yield_mg_per_mL", 0.0),
                "unit": "mg/mL",
            }
        elif skill == "bgc_mining":
            candidate_headline = {
                "name": "n_clusters_found",
                "value": skill_result.get("n_clusters_found", 0),
                "unit": "count",
            }
        elif skill == "golden_gate_assembly" and "internal_sites_count" in skill_result:
            candidate_headline = {"name": "n_internal_sites", "value": skill_result["internal_sites_count"],
                                  "unit": "count"}
        # Latest-wins: overwrite previous headline if this step produced one.
        if candidate_headline is not None and skill_result.get("passed_qc", True):
            headline = candidate_headline

        results.append({
            "step": step_idx, "skill": skill, "args": args,
            "result": skill_result, "passed_qc": passed,
            "tool_provenance": prov, "notes": notes,
        })

    return {
        "task_id": design_plan["task_id"],
        "steps": results,
        "summary": {
            "all_steps_passed": all_passed,
            "any_simulated": any_simulated,
            "headline_metric": headline or {"name": "n_steps", "value": len(results), "unit": "count"},
        },
        "wetlab_results": [],
        "confidence": design_plan.get("confidence", "medium"),
    }


def stub_reporting(execution_results: dict, prior: dict) -> dict:
    """Compose a final report from execution + prior stages."""
    scoping = prior.get("scoping_plan", {})
    design = prior.get("design_plan", {})

    rules_invoked = sorted({rid for d in design.get("design_library", []) for rid in d.get("evidence_rule_ids", [])} |
                           {ex.get("rule_id") for ex in design.get("excluded_designs", []) if ex.get("rule_id")})
    rules_invoked = [r for r in rules_invoked if r]

    cases_used = scoping.get("retrieved_evidence", {}).get("cases", [])
    references = []
    for c in cases_used[:3]:
        doi = c.get("doi") or _read_doi_from_case(c["case_id"])
        if doi:
            references.append({"doi": doi, "citation": f"Cited via case {c['case_id']}",
                               "case_id": c["case_id"]})

    why_succeeded = []
    why_failed = []
    for s in execution_results.get("steps", []):
        prov = s.get("tool_provenance", {}) or {}
        if s.get("passed_qc"):
            tag = "full" if prov.get("full") else "partial" if prov.get("partial") else "simulated"
            why_succeeded.append(f"step {s['step']} ({s['skill']}) passed with {tag} tool")
        else:
            why_failed.append(f"step {s['step']} ({s['skill']}): {s.get('notes', '?')}")
    if not why_failed:
        why_failed = ["No failures recorded"]
    if not why_succeeded:
        why_succeeded = ["Stub mode: pipeline assembled deterministically from rules"]

    headline = execution_results["summary"]["headline_metric"]

    # Compose reproduce.sh
    pipeline = design.get("computational_pipeline", [])
    reproduce = [
        "#!/usr/bin/env bash",
        "# Auto-generated reproduce.sh for PRAXIS-Synth task",
        f"# task_id: {execution_results.get('task_id', '<unknown>')}",
        "set -euo pipefail",
        "cd \"$(dirname \"$0\")/../..\"",
        "pip install -e .",
        "python scripts/distill/qa.py --all --strict",
    ]
    for s in pipeline:
        args_repr = json.dumps(s.get("args", {}), ensure_ascii=False)
        reproduce.append(
            f"python -c \"from agents.skill_executor import run_skill; "
            f"import json; print(json.dumps(run_skill('{s['skill']}', {args_repr}), indent=2))\""
        )
    shell_script = "\n".join(reproduce) + "\n"

    interpretation = {
        "why_succeeded": why_succeeded or ["Stub mode: pipeline assembled deterministically from rules"],
        "why_failed": why_failed,
        "literature_alignment": [
            f"Aligned with case {c['case_id']} (pool={c.get('pool')}, similarity={c.get('similarity', 0):.4f})"
            for c in cases_used[:2]
        ],
        "rules_invoked": rules_invoked,
    }

    title = f"PRAXIS-Synth report: {scoping.get('problem', {}).get('synth_task', '?')} on {scoping.get('problem', {}).get('host_organism', '?')}"
    if isinstance(scoping.get("problem", {}).get("target_compound"), dict):
        target = scoping["problem"]["target_compound"].get("name")
        title += f" → {target}"

    return {
        "task_id": execution_results.get("task_id"),
        "summary": {
            "title": title,
            "headline_metric": headline,
            "tldr": f"{len(cases_used)} cases retrieved, {len(rules_invoked)} rules invoked, {len(execution_results.get('steps', []))} pipeline steps executed.",
        },
        "interpretation": interpretation,
        "reproducibility": {
            "shell_script": shell_script,
            "tool_versions": {"python": "3.13", "praxis-synth": "0.1.0"},
            "seed": 42,
        },
        "references": references,
        "case_writeback_proposal": {
            "should_write": False,
            "case_id_suggestion": "",
            "rationale": "Stub run; no new wet-lab data to commit",
        },
        "confidence": execution_results.get("confidence", "medium"),
    }


# ---------- pipeline driver ----------

def _load_validated_envelopes(run_dir: Path) -> list[dict]:
    """Load all envelopes that the watcher has moved to wetlab_data/_validated/."""
    validated_dir = run_dir / "wetlab_data" / "_validated"
    if not validated_dir.exists():
        return []
    out = []
    for p in sorted(validated_dir.glob("*.json")):
        if p.name.startswith("."):
            continue
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def _merge_envelopes_into_execution(execution_results: dict, envelopes: list[dict]) -> dict:
    """Append validated envelope payloads into execution_results.wetlab_results."""
    if not envelopes:
        return execution_results
    out = dict(execution_results)
    wl = list(out.get("wetlab_results") or [])
    for env in envelopes:
        wl.append({
            "envelope_id": env.get("experiment_id"),
            "envelope_kind": env.get("envelope_kind"),
            "source_agent": env.get("source_agent", "direct"),
            "experiment_type": env.get("experiment_type"),
            "samples": env.get("samples", []),
            "payload_summary": _summarize_envelope_payload(env),
            "qc_passed": (env.get("qc") or {}).get("passed", True),
            "operator": env.get("operator"),
            "timestamp_utc": env.get("timestamp_utc"),
        })
    out["wetlab_results"] = wl
    out["summary"] = dict(out.get("summary") or {})
    out["summary"]["n_wetlab_envelopes_merged"] = len(wl)
    out["summary"]["all_steps_passed"] = bool(
        out.get("summary", {}).get("all_steps_passed") and all(w["qc_passed"] for w in wl)
    )
    return out


def _summarize_envelope_payload(envelope: dict) -> dict:
    """Compact, schema-friendly summary of payload for storage in execution_results."""
    payload = envelope.get("payload") or {}
    et = envelope.get("experiment_type", "")
    summary = {"experiment_type": et}
    if et == "compound_target":
        c = payload.get("compound") or {}
        summary["compound"] = c.get("name")
        summary["target_titer_mg_L"] = payload.get("target_titer_mg_L")
        summary["preferred_host"] = payload.get("preferred_host")
    elif et == "ko_handoff":
        summary["ko_genes"] = payload.get("ko_genes")
        summary["host"] = payload.get("host")
        summary["n_sgRNAs"] = len(payload.get("sgRNAs", []))
    elif et == "enzyme_handoff":
        summary["uniprot"] = payload.get("uniprot")
        summary["organism"] = payload.get("organism")
    elif et == "wetlab_titer":
        summary["compound"] = payload.get("compound")
        summary["mean_titer"] = payload.get("mean_g_per_L")
        summary["n_replicates"] = len(payload.get("values_g_per_L", []))
    elif et == "wetlab_flow_cytometry":
        summary["instrument"] = payload.get("instrument")
        summary["n_samples"] = len(payload.get("results_per_sample", []))
        summary["bimodal_confirmed"] = all(
            s.get("bimodal", False) for s in payload.get("results_per_sample", [])
        )
    elif et == "wetlab_colony_pcr":
        summary["n_picked"] = payload.get("n_picked")
        summary["n_correct"] = payload.get("n_correct")
    elif et == "wetlab_full_plasmid_seq":
        summary["coverage_x"] = payload.get("coverage_x")
        summary["identity_pct"] = payload.get("identity_pct")
    elif et == "strain_simulation_request":
        summary["protein"] = (payload.get("protein") or {}).get("name")
        summary["request_kind"] = payload.get("request_kind")
        summary["n_questions"] = len(payload.get("questions_for_md", []))
    return summary


def run_pipeline(task_input: dict, mode: str = "stub", max_repairs: int = 2,
                 skip_reviewer: bool = False, run_dir: Path | None = None,
                 resume_from: str | None = None) -> dict:
    """Run all 4 stages with the Reviewer gate after each.

    Mode semantics:
      - mode='stub'    Tools-only: deterministic plans from retrieval + rule library.
      - mode='llm'     If task_id has an embedded synthesis in agents.llm_synthesis,
                       use that for scoping + design + report interpretation; falls
                       back to stub for stages without an embedded synthesis.
                       Execution always runs real skills (the numbers in the report
                       come from genuine tool invocations, never the LLM).

    Resume semantics:
      - resume_from='reporting'  Load existing intermediates/{scoping_plan,design_plan,
                                  execution_results}.json (if `run_dir` provided), merge
                                  any wetlab_data/_validated/*.json envelopes into
                                  execution_results.wetlab_results, then re-run only
                                  the Reporting stage. Used after the LIMS watcher has
                                  picked up a wetlab envelope drop.
    """
    if mode not in ("stub", "llm"):
        raise ValueError(f"unknown mode {mode!r}; use 'stub' or 'llm'")
    if resume_from is not None and resume_from != "reporting":
        raise ValueError(f"resume_from must be 'reporting' or None; got {resume_from!r}")

    history = {}
    task_id = task_input.get("task_id", "")
    use_llm = mode == "llm"

    # Resume from reporting: load earlier stages from disk + merge wetlab envelopes
    if resume_from == "reporting" and run_dir:
        intermediates = run_dir / "intermediates"
        for stage_key in ("scoping_plan", "design_plan", "execution_results"):
            f = intermediates / f"{stage_key}.json"
            if not f.exists():
                raise FileNotFoundError(
                    f"resume_from='reporting' requires {f} to exist (run the full pipeline first)"
                )
            history[stage_key] = json.loads(f.read_text(encoding="utf-8"))
        # Merge validated envelopes
        envelopes = _load_validated_envelopes(run_dir)
        history["execution_results"] = _merge_envelopes_into_execution(
            history["execution_results"], envelopes
        )
        history["envelopes_merged"] = [e.get("experiment_id") for e in envelopes]
        # Skip ahead to step 4
        report = stub_reporting(history["execution_results"], prior=history)
        if use_llm and llm_synthesis.has_llm_output(task_id, "report_interpretation"):
            llm_interp = llm_synthesis.get_llm_output(task_id, "report_interpretation")
            report["interpretation"] = llm_interp
            report["_synthesis_source"] = "llm_synthesis (interpretation) + wetlab_envelopes"
        # Reflect envelopes in literature_alignment so the report shows them
        if envelopes:
            literature = (report.get("interpretation") or {}).get("literature_alignment") or []
            for env in envelopes:
                literature.append(
                    f"Wetlab/cross-agent envelope merged: {env.get('experiment_type')} "
                    f"from {env.get('source_agent', 'direct')} "
                    f"(envelope_id={env.get('experiment_id')})"
                )
            if "interpretation" in report:
                report["interpretation"]["literature_alignment"] = literature
        history["report"] = report
        report_verdict = {"passed": True, "skipped": True}
        if not skip_reviewer:
            report_verdict = reviewer_mod.review("reporting", report, prior=history)
            if not report_verdict["passed"]:
                report["_review_warnings"] = report_verdict["required_repairs"]
        history["report_review"] = report_verdict
        return history

    # 1) Scoping — 3-tier fallback: embedded synthesis → API → stub
    scoping_plan = None
    if use_llm and llm_synthesis.has_llm_output(task_id, "scoping"):
        scoping_plan = llm_synthesis.get_llm_output(task_id, "scoping")
        scoping_plan["_synthesis_source"] = "llm_synthesis (case-grounded, embedded)"
    elif use_llm and llm_api.is_api_available():
        problem = task_input.get("problem", {}) or {}
        target_compound = problem.get("target_compound")
        if isinstance(target_compound, dict):
            target_compound = target_compound.get("name")
        bundle = retrieve(
            {
                "synth_task": problem.get("synth_task"),
                "host_organism": problem.get("host_organism"),
                "target_compound": target_compound,
                "pathway_class": problem.get("pathway_class"),
                "assembly_strategy": problem.get("assembly_strategy"),
                "scale": problem.get("scale"),
            },
            stage="scoping", top_k=5,
        )
        api_out = llm_api.synthesize("scoping", task_input, bundle)
        if api_out is not None:
            scoping_plan = api_out
            scoping_plan["_synthesis_source"] = "llm_api (Anthropic API)"
    if scoping_plan is None:
        scoping_plan = stub_scoping(task_input)
        scoping_plan["_synthesis_source"] = "stub (deterministic from retrieval + rules)"
    history["scoping_plan"] = scoping_plan
    scoping_verdict = {"passed": True, "skipped": True}
    if not skip_reviewer:
        scoping_verdict = reviewer_mod.review("scoping", scoping_plan)
        if not scoping_verdict["passed"]:
            scoping_plan["_review_warnings"] = scoping_verdict["required_repairs"]
    history["scoping_review"] = scoping_verdict

    # 2) Design — 3-tier fallback
    design_plan = None
    if use_llm and llm_synthesis.has_llm_output(task_id, "design"):
        design_plan = llm_synthesis.get_llm_output(task_id, "design")
        design_plan["_synthesis_source"] = "llm_synthesis (case-grounded, embedded)"
    elif use_llm and llm_api.is_api_available():
        problem = task_input.get("problem", {}) or {}
        bundle = retrieve(
            {
                "synth_task": problem.get("synth_task"),
                "host_organism": problem.get("host_organism"),
                "method_choice": (scoping_plan.get("candidate_strategies") or [{}])[0].get("method"),
            },
            stage="design", top_k=5,
        )
        api_out = llm_api.synthesize("design", task_input, bundle, prior_history=history)
        if api_out is not None:
            design_plan = api_out
            design_plan["_synthesis_source"] = "llm_api (Anthropic API)"
    if design_plan is None:
        design_plan = stub_design(scoping_plan)
        design_plan["_synthesis_source"] = "stub"
    history["design_plan"] = design_plan
    design_verdict = {"passed": True, "skipped": True}
    if not skip_reviewer:
        for round_n in range(max_repairs + 1):
            design_verdict = reviewer_mod.review("design", design_plan, prior=history)
            if design_verdict["passed"]:
                break
            if round_n == max_repairs:
                design_plan["_review_warnings"] = design_verdict["required_repairs"]
                break
            for r in design_verdict["required_repairs"]:
                _stub_design_repair(design_plan, r, history)
    history["design_plan"] = design_plan
    history["design_review"] = design_verdict

    # 3) Execution — always real skills (rule: numbers come from tools, not LLM)
    execution_results = stub_execution(design_plan, run_dir=run_dir)
    history["execution_results"] = execution_results
    exec_verdict = {"passed": True, "skipped": True}
    if not skip_reviewer:
        exec_verdict = reviewer_mod.review("execution", execution_results, prior=history)
        if not exec_verdict["passed"]:
            execution_results["_review_warnings"] = exec_verdict["required_repairs"]
    history["execution_review"] = exec_verdict

    # 4) Reporting — combines real execution numbers with LLM interpretation (3-tier)
    report = stub_reporting(execution_results, prior=history)
    if use_llm and llm_synthesis.has_llm_output(task_id, "report_interpretation"):
        llm_interp = llm_synthesis.get_llm_output(task_id, "report_interpretation")
        report["interpretation"] = llm_interp
        report["_synthesis_source"] = "llm_synthesis (interpretation) + real_tools (numbers)"
    elif use_llm and llm_api.is_api_available():
        api_out = llm_api.synthesize("report_interpretation", task_input,
                                      retrieval_bundle={}, prior_history=history)
        if api_out is not None:
            report["interpretation"] = api_out
            report["_synthesis_source"] = "llm_api (interpretation) + real_tools (numbers)"
    history["report"] = report
    report_verdict = {"passed": True, "skipped": True}
    if not skip_reviewer:
        report_verdict = reviewer_mod.review("reporting", report, prior=history)
        if not report_verdict["passed"]:
            report["_review_warnings"] = report_verdict["required_repairs"]
    history["report_review"] = report_verdict

    return history


def _stub_design_repair(design_plan: dict, hint: str, prior: dict) -> None:
    """Best-effort stub repair logic: add a missing field based on the reviewer hint."""
    if "rule 02" in hint and "codon_optimize must precede" in hint:
        # move codon_optimize earlier — simple: re-sort pipeline so codon_optimize comes first
        pipe = design_plan.get("computational_pipeline", [])
        pipe.sort(key=lambda s: 0 if s.get("skill") == "codon_optimize" else 1)
        for i, s in enumerate(pipe):
            s["step"] = i + 1
        design_plan["computational_pipeline"] = pipe
    elif "rule 01" in hint:
        for s in design_plan.get("computational_pipeline", []):
            if s.get("skill") in ("fba_simulate", "optknock_strain"):
                s["multi_objective"] = True
    elif "rule 08" in hint:
        for s in design_plan.get("computational_pipeline", []):
            if s.get("skill") == "optknock_strain":
                s.setdefault("args", {})["audit_essential"] = True
    elif "excluded_designs" in hint:
        if not design_plan.get("excluded_designs"):
            design_plan["excluded_designs"] = [{
                "kind": "default", "item": "see _default_bootstrap rule",
                "reason": "auto-repair bootstrap", "rule_id": "_default_bootstrap",
            }]
    elif "rule 11" in hint:
        # Add CPR partner annotation
        for d in design_plan.get("design_library", []):
            spec = d.get("spec", {})
            if "p450" in str(spec).lower() or "P450" in str(spec):
                spec["cpr_partner"] = "yeast NADPH-CPR (auto-repair)"
                d["spec"] = spec


def main() -> int:
    ap = argparse.ArgumentParser(description="PRAXIS-Synth orchestrator")
    ap.add_argument("--task-file", type=Path, required=True)
    ap.add_argument("--mode", choices=["stub", "llm"], default="stub")
    ap.add_argument("--skip-reviewer", action="store_true")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--max-repairs", type=int, default=2)
    ap.add_argument("--resume-from", choices=["reporting"], default=None,
                    help="Resume from a stage; only 'reporting' supported. Reloads "
                         "intermediates/* and merges wetlab_data/_validated/*.json into "
                         "execution.wetlab_results before re-running Reporting only.")
    args = ap.parse_args()

    task = json.loads(args.task_file.read_text(encoding="utf-8"))
    run_dir = args.out_dir or (RUNS_DIR / task.get("task_id", "untitled"))
    run_dir.mkdir(parents=True, exist_ok=True)
    intermediates = run_dir / "intermediates"
    intermediates.mkdir(exist_ok=True)
    outputs = run_dir / "outputs"
    outputs.mkdir(exist_ok=True)

    history = run_pipeline(task, mode=args.mode, max_repairs=args.max_repairs,
                           skip_reviewer=args.skip_reviewer, run_dir=run_dir,
                           resume_from=args.resume_from)

    for stage_key, stage_out in history.items():
        target = intermediates / f"{stage_key}.json"
        target.write_text(json.dumps(stage_out, ensure_ascii=False, indent=2), encoding="utf-8")
    (outputs / "report.json").write_text(json.dumps(history.get("report", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {run_dir}/ — outputs/report.json + intermediates/{{scoping_plan,design_plan,execution_results,report}}.json")

    # Print top-line summary
    report = history.get("report", {})
    headline = (report.get("summary") or {}).get("headline_metric") or {}
    print(f"\n=== Report summary ===")
    print(f"  task_id: {report.get('task_id')}")
    print(f"  title: {(report.get('summary') or {}).get('title', '?')}")
    print(f"  headline: {headline.get('name')} = {headline.get('value')} {headline.get('unit', '')}")
    print(f"  rules_invoked: {(report.get('interpretation') or {}).get('rules_invoked', [])}")
    for stage in ("scoping", "design", "execution", "report"):
        rev = history.get(f"{stage}_review")
        if rev:
            mark = "OK" if rev.get("passed") else "ISSUES"
            n = len(rev.get("required_repairs", []))
            print(f"  {stage} review: {mark}{f' ({n} issue(s))' if n else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
