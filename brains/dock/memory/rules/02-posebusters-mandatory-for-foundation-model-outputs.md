---
rule_id: 02-posebusters-mandatory-for-foundation-model-outputs
schema_version: 1
rule_type: case_distilled
confidence: high
applies_to:
  docking_types: [foundation_model_complex_prediction, antibody_antigen, peptide_protein, protein_nucleic_acid, protein_ligand]
  models: [AlphaFold3, AF3, Boltz-1, Boltz-2, Chai-1, RoseTTAFold-AA, RFAA]
evidence_cases:
  - dock-009-af3-boltz-as-docking      # AF3 / Boltz / Chai-1 PoseBusters benchmark (top-1 ≤ 2Å rate ~76% but ~50% PoseBusters fail)
  - dock-013-rfaa-protein-ligand       # RoseTTAFold-AA dedicated case (top-1 RMSD ~62%, PoseBusters ~68%)
distilled_at: 2026-04-30
---

# Rule 02: PoseBusters Check is Mandatory for Foundation Model Complex Outputs

**Confidence**: high (≥ 2 case-evidence + cross-architecture consistency: AF3/Boltz vs RFAA both show high RMSD-but-low-physical-validity profiles)

## Statement

For all foundation-model-based complex prediction tasks (AlphaFold3 / Boltz-1/2 /
Chai-1 / RoseTTAFold-AA), running the **PoseBusters physical sanity check on
every output pose is mandatory** before any downstream use. Reviewer must
block any execution_results that lacks `posebusters_check` when foundation-
model methods produced poses.

### Specific enforcement points

1. **Every foundation-model pose** (per seed, per model) must run through
   `pose_buster_validate` skill. Batch mode is acceptable
   (`pose_buster_validate --ligand-glob ...`).
2. **`posebusters_check` field is required in `execution_results`** when
   `chosen_methods` includes any of: `af3_complex_predict`,
   `protein_na_docking` (when using Boltz/AF3-NA mode),
   `flexpepdock_peptide` (when using AF-Multimer fallback for length > 20).
3. **`overall_pass_rate` thresholds**:
   - **`≥ 0.80`**: high confidence (all checks pass on most poses)
   - **`0.50–0.80`**: medium confidence; surface failed_checks in caveats
   - **`< 0.50`**: low confidence; report to user that physical validity is
     poor; consider re-prediction with more seeds OR fall back to traditional
     docking (Vina / GNINA)
4. **iPTM / pLDDT ≠ binding affinity (Kd)** must be explicitly declared in
   the report (case dock-009 lesson, also enforced in
   `af3_complex_predict/run.py` output `confidence_assessment.iptm_does_NOT_mean_KD`).
5. **Multi-method consensus when feasible**: AF3 + Boltz + RFAA 3-way agreement
   (top-1 pose RMSD < 2 Å between methods) → high confidence; divergent → flag.

## Why this is a high-confidence rule

### Evidence: dock-009 (AF3 / Boltz / Chai-1 benchmark)

- AF3 PoseBusters benchmark: **top-1 RMSD ≤ 2Å rate ~76%**, but only
  **~50% pass PoseBusters checks** (atom clash, bond lengths, valence)
- High-RMSD-pass with physical-fail is a **systematic foundation-model failure
  mode**: the model captures gross geometry but violates atom-level physics
- Boltz-1 + Chai-1 show similar profile (open-source replicates of AF3 architecture)
- Without PoseBusters: ~50% of "successful" AF3 poses are physically invalid →
  garbage downstream MD / FEP / lead optimization

### Evidence: dock-013 (RoseTTAFold-AA)

- RFAA top-1 RMSD ≤ 2Å rate **~62%** (lower than AF3) but PoseBusters pass
  rate **~68%** (higher than AF3) — different profile, **same lesson**:
  RMSD metric ≠ physical validity
- RFAA's slightly better PoseBusters comes from architectural differences
  (single-pass vs diffusion), but absolute pass rate (~68%) still leaves
  ~32% of "successful" poses physically invalid

### Cross-architecture consistency

Both AF3 (diffusion-based) and RFAA (single-architecture) show:
- **High top-1 RMSD success** (both > 60%) suggesting models learn pocket
  geometry
- **Lower physical-validity pass rate** (both < pass-rate-of-RMSD-success)
  suggesting they don't learn atom-level physics
- **Without PoseBusters check**, downstream pipelines treat all "RMSD-successful"
  poses as valid, propagating physical errors

This pattern is **architecture-agnostic and likely generalizes** to all
foundation-model complex predictors (Chai-1, future AF4, etc.).

## Boundary conditions (when this rule applies less strictly)

- **Internal benchmarks where physical validity is the metric**: PoseBusters
  pass rate IS the score being optimized; no need for separate check
- **AF3 used purely for protein structure prediction** (no ligand/NA in input):
  pose check focuses on intra-protein checks only (ramachandran, secondary
  structure), not full PoseBusters
- **Foundation-model output discarded immediately**: e.g., used only as MD
  starting pose for relaxation; relaxation handles physical issues

## Reviewer enforcement

In `agents/prompts/reviewer.md` execution-stage rules:

> For AF3/Boltz/Chai/RFAA outputs: `posebusters_check` non-null AND
> `posebusters_check.overall_pass_rate` reported (missing → BLOCK)

This rule is the formal high-confidence statement of that Reviewer check,
extending applicability beyond just AF3 to all foundation-model architectures.

## Interaction with rule_01 (covalent_docking)

Rule_01 enforces **covalent docking 不该用 vina_gnina_dock alone**.
Rule_02 enforces **foundation model output must run PoseBusters**.
**Combined**: a covalent inhibitor predicted via AF3/Boltz must:
- Use covalent-aware Boltz mode (CCD covalent ligand entry) OR fall back to
  `covalent_docking` skill
- AND run PoseBusters on output (rule_02)
Both rules apply orthogonally; not in conflict.

## Promotion path forward

Adding a 3rd evidence case (e.g., dock-021 if Chai-1 dedicated benchmark)
would push this rule's evidence to **3+ cross-architecture cases**, allowing
removal of "high confidence with 2 evidence + cross-architecture
consistency" caveat — pure ≥3-evidence-derived high-confidence rule.

Tracking known foundation-model failure modes (per case dock-009 list +
dock-013 list) suggests future rules:
- rule_03 candidate: "Train data leakage check for any pre-2021 PDB benchmark"
- rule_04 candidate: "Cofactor / metal / glycan explicit declaration when
  foundation model predicts complex"
