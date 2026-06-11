---
rule_id: 17-rna-velocity-priors
rule_type: case_distilled
applies_to:
  modality: [scRNA_seq]
  study_design: [time_course, reference_atlas, cohort_lineage]
  tissue_class: ALL
  task: [trajectory, velocity, latent_time, transient_state]
evidence_cases:
  - case_id: omics-020-bergen-2020-scvelo-rna-velocity
    page_hint: "Dynamical model + transient state + sanity anchors"
  - case_id: omics-015-pijuan-sala-2019-gastrulation-time-course
    page_hint: "trajectory inference companion case"
confidence: high
status: active
created: 2026-04-29
---

# RNA velocity priors (scVelo dynamical model grade)

## Statement
1. **Spliced + unspliced double matrix required** — must be quantified at
   alignment stage (alevin-fry / kb_python / velocyto). Cellranger output
   alone = no velocity.
2. **Dynamical model is default** (Bergen 2020); steady-state only for large
   + steady-state cohorts.
3. **Cell cycle gene confounding** — must be regressed out or velocity
   restricted to non-cycling cells; otherwise cycle direction dominates.
4. **Velocity ≠ ground-truth trajectory** — cross-validate with PAGA /
   Palantir / known terminal states. Single tool is rule 05 violation.
5. **Per-batch fit** — kinetic rate constants confound with batch.
6. **Latent time more stable than diffusion pseudotime** — use it for
   per-cell ordering; mark branch points as ambiguous.
7. **Driver gene via rank_velocity_genes** — not by velocity magnitude
   (which is noisy).

## Decision tree
```
Need RNA velocity?
├─ Trajectory data (development / differentiation / activation) → YES
├─ Steady-state atlas (healthy adult) → SKIP (no biological meaning)
├─ Drug perturbation affecting splicing → DO NOT USE (assumption broken)
└─ Cell cycle dominant → regress cycle genes first, then velocity

Quantification?
├─ Need to redo from fastq → alevin-fry --rad (fastest, scVelo 0.3 recommended)
├─ Can recompute from BAM → velocyto (slower but stable)
└─ Already have Cellranger output only → STOP, must rerun quant

Velocity model?
├─ Default → dynamical
├─ Cell count > 50k AND want speed → stochastic (legacy)
└─ Transient state focus (rapid lineage commitment) → dynamical mandatory
```

## Sanity anchors
- Pancreas (case 020): endocrine progenitor → α/β/δ/ε direction consistent;
  latent_time monotonic to mature; β cell at terminal_states.
- Erythroid lineage: GATA1+ → mature RBC direction.

## Cold-start fallback
- If only 3' Cellranger output exists → recommend rerun with alevin-fry
  before attempting velocity.
- Cell count per lineage < 200 → confidence: low; statistics unstable.
- Cell cycle confound suspected → run with + without cycle regression,
  compare.

## Linked anti-rule sections (rule 11)
RNA-velocity-specific: steady-state model on transient state, velocity as
sole trajectory evidence, cross-batch velocity comparison, velocity on
splicing-perturbed data.
