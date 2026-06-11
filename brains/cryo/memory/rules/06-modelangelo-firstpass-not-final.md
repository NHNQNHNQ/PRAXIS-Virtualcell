---
rule_id: 06-modelangelo-firstpass-not-final
schema_version: 1
rule_type: case_distilled
applies_to:
  resolution_targets: ["2-3", "3-4"]
evidence_cases:
  - cryo-005-modelangelo-buildmodel
confidence: high
last_updated: 2026-04-29
---

## 规则
**ModelAngelo is a first-pass tool, not a final model.**

ModelAngelo accelerates ~80% of model building hours, but its output requires:
1. **Sequence FASTA input** (REQUIRED — without it, output is poly-Ala and downstream-useless).
2. **Phenix real_space_refine** afterwards.
3. **Coot manual fix** on every residue with confidence < 0.5.
4. **ISOLDE flexfit** on regions where the backbone tracing is dubious but density is decent.

ModelAngelo does NOT build:
- RNA / DNA (requires DRRAFTER / RNAforester / RNAComposer)
- Ligands / cofactors (manual placement)
- N-glycans (visible in maps but skipped by current weights)

## Reviewer block codes
- `MODELANGELO_NO_SEQUENCE` (skill-level invariant; the runner refuses to proceed)
- `CRYO_REVIEW_NO_MOLPROBITY` (chained: validation always required after build)
