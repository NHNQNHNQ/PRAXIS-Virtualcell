---
rule_id: 01-symmetry-imposition
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [soluble_oligomer, virus_capsid]
  symmetry_groups: [C2, C3, C4, C5, C6, C7, D2, D3, D4, T, O, I]
evidence_cases:
  - cryo-001-apoferritin-reference
confidence: high
last_updated: 2026-04-29
---

## 规则
**High-symmetry samples MUST impose the corresponding point group during 3D refinement.**

For an O-symmetric sample (e.g. apoferritin), an asymmetric refinement requires roughly 24× as many particles to reach the same resolution. Imposing O symmetry effectively multiplies signal per-particle by the order of the group.

## Decision tree
1. Identify symmetry from biology (oligomeric state) and 2D-class diagnostics (rotational averaging).
2. If point group ∈ {Cn≥2, Dn, T, O, I}: set `refinement.symmetry_imposed = <group>`.
3. If symmetry is uncertain: run a C1 ab-initio first; verify with overlay against the symmetrized reconstruction.

## Excluded actions
- Running C1 refinement on a known O-symmetric sample (wastes ~24× particle budget).
- Forcing symmetry on a sample with broken symmetry (will smear genuine asymmetry).

## Reviewer block code
`CRYO_REVIEW_NO_SYM_IMPOSED`
