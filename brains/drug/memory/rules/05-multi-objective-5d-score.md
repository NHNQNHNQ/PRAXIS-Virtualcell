---
rule_id: 05-multi-objective-5d-score
rule_type: case_distilled
applies_to: {target_class: ALL, modality: ALL, project_phase: [hit_id, hit_to_lead, lead_opt]}
confidence: high
evidence_cases: [drug-001-vina-egfr-screening, drug-002-reinvent-jak2-de-novo, drug-003-pocket2mol-sbdd, drug-004-admet-multi-parameter, drug-005-aizynth-retrosynthesis, drug-006-fbdd-vemurafenib, drug-007-protac-dbet1, drug-008-sotorasib-kras-covalent, drug-009-fep-relative-affinity, drug-010-imatinib-sar-bcr-abl]
schema_version: 2
---

# Rule 05: Five-dimensional scoring on every candidate (forced)

## Statement
Every compound that exits the execution stage must carry a 5-dimensional score block + composite + confidence label. This is enforced by `execution_results.schema.json` and gated by Reviewer.

The five dimensions:
1. **predicted_activity** — pIC50 / pKi from docking consensus + ML model
2. **selectivity_score** — fraction of off-target panel cleanly missed
3. **admet_score** — composite from hard endpoints (hERG/Ames/CYP3A4/DILI) + soft (logP/TPSA/MW)
4. **sa_score** — SAscore + AiZynthFinder route length
5. **novelty_score** — 1 − Tanimoto(nearest ChEMBL bioactive)

`composite_score = Σ weight_i × dim_i` with default weights {activity: 0.30, selectivity: 0.20, admet: 0.25, sa: 0.15, novelty: 0.10}.

`confidence_label ∈ {cold_start, low, medium, high, domain_knowledge}` — see `_default_bootstrap.md` for thresholds.

## Why
LLM agents will silently optimize for the loudest metric (usually pIC50). Forcing all five dimensions populated catches the "potency cliff at PK collapse" failure mode (drug-002 ruxolitinib analogues, drug-006 vemurafenib selectivity, drug-010 imatinib/nilotinib resistance trade).

## How to apply
- Schema `execution_results.schema.json` requires `scoring_5d` for every candidate; reviewer rejects partial fills.
- Hard stops in `admet_score.hard_stops_failed` cause auto-reject (rule 08).
- Lead-opt (`project_phase: lead_opt`) requires confidence_label ≥ `medium` to recommend wet-lab assays.
