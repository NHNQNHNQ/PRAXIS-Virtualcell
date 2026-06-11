"""Deterministic Reviewer — rule-based enforcement of the 11 case-distilled rules
plus schema validation. The orchestrator runs this gate after each stage; it
returns {passed, required_repairs[], notes}.

This is intentionally LLM-free so reviewer behavior is reproducible and the
hard rules from the synthesis can never be talked-out-of.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

P450_REGEX = re.compile(r"(p450|cyp\d|EC\s*1\.14)", re.IGNORECASE)
RIBOSOMAL_REGEX = re.compile(r"^(rps|rpl|rpm|infA|infB|infC|tufA|tufB)", re.IGNORECASE)


def _validate_schema(stage_output: dict, schema_filename: str) -> list[str]:
    schema = json.loads((SCHEMAS_DIR / schema_filename).read_text())
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"schema: {'.'.join(str(p) for p in e.path) or '<root>'} — {e.message}"
        for e in validator.iter_errors(stage_output)
    ]


# ---------- per-stage reviewers ----------

def review_scoping(plan: dict) -> dict:
    repairs: list[str] = _validate_schema(plan, "scoping_plan.schema.json")

    if "confidence" not in plan:
        repairs.append("missing 'confidence' label (set one of cold_start|low|medium|high|domain_knowledge)")

    cases = plan.get("retrieved_evidence", {}).get("cases", []) or []
    if not cases and plan.get("confidence") != "cold_start":
        repairs.append("retrieved_evidence.cases is empty but confidence != 'cold_start'")

    synth_task = plan.get("problem", {}).get("synth_task", "")
    strategies = plan.get("candidate_strategies", []) or []
    if synth_task in ("pathway_design", "bgc_mining") and len(strategies) < 3:
        repairs.append(
            f"rule: multi-method consensus required for {synth_task!r} — "
            f"candidate_strategies has {len(strategies)}, need ≥3"
        )

    for i, s in enumerate(strategies):
        if not (s.get("evidence_case_ids") or s.get("evidence_rule_ids")):
            repairs.append(f"candidate_strategies[{i}] cites no case_id or rule_id")

    return {"passed": not repairs, "required_repairs": repairs,
            "notes": "scoping reviewed" if not repairs else f"{len(repairs)} issue(s)"}


def review_design(plan: dict, prior: dict | None = None) -> dict:
    repairs: list[str] = _validate_schema(plan, "design_plan.schema.json")

    excluded = plan.get("excluded_designs", []) or []
    if not excluded:
        repairs.append("rule: excluded_designs[] must be non-empty (★)")

    pipeline = plan.get("computational_pipeline", []) or []
    skill_order = [s.get("skill", "") for s in pipeline]

    # Rule 02: codon_optimize before fba_simulate / golden_gate_assembly when heterologous
    has_codon = "codon_optimize" in skill_order
    fba_idx = skill_order.index("fba_simulate") if "fba_simulate" in skill_order else -1
    gg_idx = skill_order.index("golden_gate_assembly") if "golden_gate_assembly" in skill_order else -1
    codon_idx = skill_order.index("codon_optimize") if has_codon else -1

    # Heuristic: scoping might have set host_organism != design_library entries' source
    is_heterologous = False
    if prior and "scoping_plan" in prior:
        synth_task = prior["scoping_plan"].get("problem", {}).get("synth_task", "")
        if synth_task in ("pathway_design", "cell_free"):
            is_heterologous = True
    # Also flag heterologous if any design_library spec mentions a non-host source
    for d in plan.get("design_library", []) or []:
        spec = d.get("spec", {}) or {}
        if "native_source" in spec or "heterologous" in str(spec).lower():
            is_heterologous = True

    if is_heterologous and not has_codon:
        repairs.append("rule 02: heterologous design plan must include a codon_optimize step")
    if has_codon and fba_idx > -1 and codon_idx > fba_idx:
        repairs.append("rule 02: codon_optimize must precede fba_simulate (currently after)")
    if has_codon and gg_idx > -1 and codon_idx > gg_idx:
        repairs.append("rule 02: codon_optimize must precede golden_gate_assembly")

    # Rule 04: golden_gate must be preceded by dna_constraint_solve OR codon_optimize w/ forbidden_sites
    if gg_idx > -1:
        preceded = False
        for prior_step in pipeline[:gg_idx]:
            sk = prior_step.get("skill", "")
            if sk == "dna_constraint_solve":
                preceded = True
                break
            if sk == "codon_optimize":
                forbidden = (prior_step.get("args", {}) or {}).get("forbidden_sites")
                if forbidden:
                    preceded = True
                    break
        if not preceded:
            repairs.append("rule 04: golden_gate_assembly must be preceded by dna_constraint_solve OR codon_optimize with forbidden_sites")

    # Rule 01: every fba_simulate / optknock_strain must have multi_objective: true
    for i, s in enumerate(pipeline):
        sk = s.get("skill", "")
        if sk in ("fba_simulate", "optknock_strain"):
            if not s.get("multi_objective") and not (s.get("args", {}) or {}).get("allow_single_objective"):
                repairs.append(f"rule 01: pipeline[{i}].skill={sk!r} requires multi_objective=true")

    # Rule 08: optknock_strain must have audit_essential: true
    for i, s in enumerate(pipeline):
        if s.get("skill") == "optknock_strain":
            if not (s.get("args", {}) or {}).get("audit_essential", False):
                repairs.append(f"rule 08: pipeline[{i}] (optknock_strain) must have args.audit_essential=true")

    # Rule 11: P450 in design_library → CPR partner check
    has_p450 = False
    for d in plan.get("design_library", []) or []:
        spec_str = json.dumps(d, ensure_ascii=False)
        if P450_REGEX.search(spec_str):
            has_p450 = True
            break
    if has_p450:
        cpr_present = any("cpr" in json.dumps(d, ensure_ascii=False).lower() for d in plan.get("design_library", []) or [])
        if not cpr_present:
            repairs.append("rule 11: P450 detected in design_library; missing CPR partner entry")

    # Validation plan checks
    vp = plan.get("validation_plan", {}) or {}
    experiments = vp.get("experiments", []) or []
    if not experiments:
        repairs.append("validation_plan.experiments must be non-empty")

    # Rule 05: cloning needs ≥3 colony pick + colony PCR + full plasmid seq
    has_cloning = any("plasmid_construct" in (d.get("kind") or "") for d in plan.get("design_library", []) or [])
    if has_cloning:
        meets = any(
            (e.get("colony_pick_n") or 0) >= 3 and e.get("colony_pcr") and e.get("full_plasmid_seq")
            for e in experiments
        )
        if not meets:
            repairs.append("rule 05: plasmid_construct needs colony_pick_n>=3 + colony_pcr + full_plasmid_seq in validation_plan")

    # Rule 07: bistable circuit / digital biosensor needs flow_cytometry
    has_bistable = any(d.get("kind") in ("circuit_topology", "sensor_topology")
                       and ("bistable" in str(d.get("spec", {})).lower() or "digital" in str(d.get("spec", {})).lower())
                       for d in plan.get("design_library", []) or [])
    if has_bistable and not any(e.get("flow_cytometry") for e in experiments):
        repairs.append("rule 07: bistable / digital readout requires flow_cytometry in validation_plan")

    # Rule 10: biosensor needs cross_reactant_panel
    has_biosensor = any(d.get("kind") == "sensor_topology" for d in plan.get("design_library", []) or [])
    if has_biosensor:
        has_panel = any((e.get("cross_reactant_panel") or {}).get("n_compounds", 0) >= 5 for e in experiments)
        if not has_panel:
            repairs.append("rule 10: biosensor design needs cross_reactant_panel.n_compounds>=5")

    return {"passed": not repairs, "required_repairs": repairs,
            "notes": "design reviewed" if not repairs else f"{len(repairs)} issue(s)"}


def review_execution(results: dict, prior: dict | None = None) -> dict:
    repairs: list[str] = _validate_schema(results, "execution_results.schema.json")

    for i, step in enumerate(results.get("steps", []) or []):
        prov = step.get("tool_provenance", {}) or {}
        # Mutual exclusion: only one of simulated|partial|full true
        flags = [bool(prov.get("simulated")), bool(prov.get("partial")), bool(prov.get("full"))]
        if sum(flags) != 1:
            repairs.append(f"step[{i}].tool_provenance: exactly one of simulated|partial|full must be true (got {flags})")

        # passed_qc=false must have notes (concrete reason). Note: a tool can
        # legitimately run with full=true AND emit passed_qc=false — that means
        # "I ran the QC, the design failed". This is not contradictory; we just
        # require explanatory notes so the reporting agent can interpret.
        if not step.get("passed_qc") and not step.get("notes"):
            repairs.append(f"step[{i}] passed_qc=false without notes")

        # Rule 09: antiSMASH / BGC steps need mibig_match_pct on EACH candidate cluster
        # (the natural shape of the bgc_mining skill output). Empty result is allowed.
        if "antismash" in (step.get("skill") or "").lower() or "bgc_mining" in (step.get("skill") or ""):
            res = step.get("result", {}) or {}
            if prov.get("simulated") is not True:
                clusters = res.get("candidate_clusters") or []
                if clusters and not all("mibig_match_pct" in c for c in clusters):
                    repairs.append(
                        f"step[{i}] (BGC mining) one or more candidate_clusters missing mibig_match_pct (rule 09)"
                    )
                if not clusters and "n_clusters_found" not in res:
                    repairs.append(f"step[{i}] (BGC mining) missing MIBiG cross-check evidence (rule 09)")

        # Rules 03, 04: Golden Gate steps need overhang_validation + internal_sites_count==0
        if step.get("skill") == "golden_gate_assembly":
            res = step.get("result", {}) or {}
            ov = res.get("overhang_validation") or {}
            if not ov.get("passed"):
                repairs.append(f"step[{i}] (golden_gate) overhang_validation.passed missing or false (rule 03)")
            if res.get("internal_sites_count", 1) != 0:
                repairs.append(f"step[{i}] (golden_gate) internal_sites_count != 0 (rule 04)")

        # Rule 08: OptKnock top KO sets must not contain ribosomal genes
        if step.get("skill") == "optknock_strain":
            res = step.get("result", {}) or {}
            for j, ko_set in enumerate(res.get("top_3_ko_sets", []) or []):
                if ko_set.get("ribosomal_hit"):
                    repairs.append(f"step[{i}] (optknock) top_3_ko_sets[{j}] hit ribosomal gene (rule 08)")
                for g in ko_set.get("genes", []):
                    if g in (res.get("essential_genes_audited_out") or []):
                        repairs.append(f"step[{i}] (optknock) top set has audited essential gene {g} (rule 08)")

    return {"passed": not repairs, "required_repairs": repairs,
            "notes": "execution reviewed" if not repairs else f"{len(repairs)} issue(s)"}


def review_reporting(report: dict, prior: dict | None = None) -> dict:
    repairs: list[str] = _validate_schema(report, "report.schema.json")

    repro = report.get("reproducibility", {}) or {}
    if not repro.get("shell_script") or len(repro["shell_script"]) < 10:
        repairs.append("rule: reproducibility.shell_script must be non-empty (≥10 chars) — '不允许的捷径' forbids omission")

    interp = report.get("interpretation", {}) or {}
    if "why_failed" not in interp:
        repairs.append("interpretation.why_failed missing (use ['No failures recorded'] if none)")

    # DOIs in references must come from prior retrieved_evidence
    cited_dois = {ref.get("doi") for ref in (report.get("references") or []) if ref.get("doi")}
    known_dois = set()
    for stage in ("scoping_plan", "design_plan", "execution_results"):
        if not prior or stage not in prior:
            continue
        ev = (prior[stage].get("retrieved_evidence") or {}).get("cases") or []
        for c in ev:
            if c.get("doi"):
                known_dois.add(c["doi"])
    invented = cited_dois - known_dois - {None}
    if invented:
        repairs.append(f"references contains DOIs not in retrieved_evidence: {sorted(invented)}")

    if not report.get("confidence"):
        repairs.append("missing 'confidence' label")

    return {"passed": not repairs, "required_repairs": repairs,
            "notes": "report reviewed" if not repairs else f"{len(repairs)} issue(s)"}


REVIEWERS = {
    "scoping": review_scoping,
    "design": review_design,
    "execution": review_execution,
    "reporting": review_reporting,
}


def review(stage: str, output: dict, prior: dict | None = None) -> dict:
    fn = REVIEWERS.get(stage)
    if not fn:
        return {"passed": False, "required_repairs": [f"unknown stage {stage!r}"], "notes": ""}
    if stage == "scoping":
        return fn(output)
    return fn(output, prior)
