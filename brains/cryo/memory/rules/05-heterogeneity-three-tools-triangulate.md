---
rule_id: 05-heterogeneity-three-tools-triangulate
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [heterogeneous_complex]
evidence_cases:
  - cryo-004-heterogeneity-3dclass
confidence: high
last_updated: 2026-04-29
---

## 规则
**Conformational/compositional heterogeneity MUST be probed with at least two of {discrete 3D class, 3DVA, cryoDRGN}.**

Each tool sees a different slice of the heterogeneity manifold. Discrete 3D classification recovers compositional sub-states; 3DVA captures linear conformational principal components; cryoDRGN explores the continuous nonlinear manifold. A single-tool answer is unreliable.

## Decision tree
1. Run 3D refine with K=1; if FSC under-shoots claim AND map shows local blurring → heterogeneity signal.
2. Run discrete RELION 3D class with K=3-5 first.
3. Run cryoSPARC 3DVA (3-5 PCs) on the same particles.
4. If both agree on the same dominant axis of motion → trust; otherwise run cryoDRGN as tie-breaker.

## Excluded actions
- Single-class refinement on a heterogeneous sample, reporting only the FSC.
- K > 10 on < 50k particles (each class < 5k = noisy).
- Treating the cryoDRGN movie as ground-truth biology rather than manifold smoothness.

## Reviewer block code
`CRYO_REVIEW_HETEROGENEITY_IGNORED`
