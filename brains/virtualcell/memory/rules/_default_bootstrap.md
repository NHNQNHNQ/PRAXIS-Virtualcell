---
rule_id: _default_bootstrap
schema_version: 1
scope: bootstrap
applies_to:
  perturbation_type: ALL
  species: ALL
  task: ALL
evidence_cases: [vcell-001]
confidence: medium
rule_type: cross_task_priors
provenance:
  source_type: synthesis
  source_path: synthesis/virtualcell-bootstrap.md
  extracted_at: 2026-06-11
---

# VirtualCell bootstrap priors

Apply these priors when no more specific validated rule has been retrieved.

1. Support performance claims with explicit benchmark and baseline comparisons.
2. Check species and task applicability before transferring a predictor.
3. Mark simulated outputs and keep them separate from experimental records.
4. Report abstention benefits and limitations without exaggerating their size.

Give recommendations a confidence level (`cold_start`, `low`, `medium`, or
`high`) and identify their supporting cases, rules, or benchmark evidence.
