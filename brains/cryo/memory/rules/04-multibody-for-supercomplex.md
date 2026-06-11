---
rule_id: 04-multibody-for-supercomplex
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [membrane_protein_complex, supercomplex, ribonucleoprotein, large_complex]
  molecular_weight_kda_above: 300
evidence_cases:
  - cryo-002-membrane-protein-gpcr
  - cryo-003-supercomplex-ribosome
confidence: high
last_updated: 2026-04-29
---

## 规则
**Large multi-domain complexes MUST use multibody refinement (RELION) or local refinement (cryoSPARC).**

Inter-body relative motion is the #1 limiter of full-rigid refinement on big complexes. Splitting the consensus map into ≥ 2 rigid bodies with independent alignment recovers 0.3–1.0 Å per body.

## Decision tree
1. Inspect local resolution map of the consensus reconstruction.
2. If ≥ 2 regions show local resolution worse than overall by ≥ 0.5 Å → multibody candidate.
3. Split bodies along physical hinges (TM bundle vs G-protein, 60S vs 40S, head vs body, etc.).
4. Each body needs a soft-edge mask (≥ 6 voxels) and ≥ 30k particles for stable alignment.

## Excluded actions
- Running rigid full refinement and reporting "this is what cryoEM can do" (it isn't).
- Using > 4 bodies on a < 1 MDa complex (over-fragmentation, each body under-particled).

## Reviewer block code
`CRYO_REVIEW_NO_MULTIBODY_ON_LARGE_COMPLEX` (soft check; warns when > 500 kDa flexible complex skips multibody).
