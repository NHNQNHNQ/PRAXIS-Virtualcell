---
rule_id: 10-af-cryoem-hybrid-flexfit
schema_version: 1
rule_type: case_distilled
applies_to:
  resolution_targets: ["2-3", "3-4", "4-6"]
evidence_cases:
  - cryo-008-af-cryoem-hybrid
confidence: high
last_updated: 2026-04-29
---

## 规则
**AF + cryoEM hybrid is the modern default for 3-4 Å maps; AF prediction must always be flexfit into the map (NOT used rigid).**

Pipeline:
1. AlphaFold3 (or ColabFold/ESMFold cross-check) predict all chains.
2. `phenix.dock_in_map` → initial rigid placement.
3. `chimerax fitmap` followed by ISOLDE flexfit (molecular dynamics).
4. Phenix `real_space_refine` to settle into density.
5. Validate (rule 07).
6. Per-residue source label EVERY position: `from_AF` | `from_map_remodel` | `disordered_low_plddt_low_density`.

## Excluded actions
- Reporting an AF model rigid-fit as the final structure (it's not — the map is the ground truth).
- Strong-fitting an AF segment with low pLDDT into ambiguous map density (double low-confidence is not biology).
- Ignoring AF-vs-map disagreement (it's an opportunity to characterize a conformational state, not noise).

## Reviewer block code
`CRYO_REVIEW_AF_NO_FLEXFIT`
