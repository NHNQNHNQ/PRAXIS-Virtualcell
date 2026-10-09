# Scientific capability and validation scope

This historical capability audit distinguishes executable software paths from scientific
validation. The current framework is described in the
[preprint](https://arxiv.org/abs/2609.29221v1). Numerical experiments must be interpreted
within their exact dataset, predictor, environment, and evidence scope.

## Biological modules

| Module | Recorded implementation scope |
|---|---|
| M1: membrane system | Rule-based advisory annotations |
| M2: genetic hub | Mock local fixtures and separately provisioned GEARS/scGPT predictors |
| M3: mitochondrial energy metabolism | GEM/FBA and pathway scoring; secondary for growth/flux |
| M4: cytoplasmic metabolism | Cobra FBA and pathway scoring |
| M5: biosynthetic network | Rule-based advisory annotations |
| M6: cytoskeletal framework | Spatial-niche integration limitations |
| M7: stress processor | Restricted state scoring and drug embedding paths |
| M8: degradation machinery | Rule-based advisory annotations and species mismatch checks |

Historical engine coverage concerned four families (M2/M3/M4/M7), with external assets
required for M2. It did not establish eight independently validated predictive models.
Multiple module entries describe routing and advisory context; they do not establish
independent predictor fan-out or a merged evidence chain.

## Audit findings

- The message schema and deterministic offline tests were exercised.
- Provenance checks verified required fields and per-call identities; they did not measure
  a general missingness rate or establish cross-version tamper resistance.
- Repeated execution compared artifacts for the same request. This is narrower than replay
  from an exported trace bundle.
- The historical negative corpus recorded zero unsafe acceptances across 92 cases.
  This scoped result is not a universal false-acceptance rate.
- No representative corpus established a single-module success rate, an unsupported-request
  abstention rate, or a prompt-injection bypass rate.
- The cross-module gate checks internal module-plan consistency. Independent-result conflict
  detection was unsupported in this audit.
- The narrative checks did not establish zero unsupported LLM claims in general. Interpretation
  remains bounded by structured artifacts and the deterministic verdict.
- The 16 end-to-end cases represent 14 distinct requests; duplicate requests test different assertions.

Historical external tests exercised GEARS, scGPT donor equivalence (absolute tolerance 1e-6),
and the Norman mean baseline. Donor workflow, container, and end-to-end predictor provenance
checks had separate incomplete entries. These records do not certify an arbitrary current
checkpoint, environment, or product promotion.

See the retained case tables and [reproducibility guide](../../docs/REPRODUCIBILITY.md).
Missing, unsupported, or unvalidated capability must preserve structured abstention.
