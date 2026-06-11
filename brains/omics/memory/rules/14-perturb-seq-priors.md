---
rule_id: 14-perturb-seq-priors
rule_type: case_distilled
applies_to:
  modality: perturb_seq
  study_design: crispr_screen
  tissue_class: ALL
  task: [perturbation_phenotype, sgRNA_assignment, DE, clustering]
evidence_cases:
  - case_id: omics-014-replogle-2022-perturb-seq
    page_hint: "What I actually did + Lessons (perturbation is the unit)"
confidence: high
status: active
created: 2026-04-29
---

# Perturb-seq priors — perturbation is the unit, not the cell

## Statement
1. **Analysis unit shift**: in Perturb-seq, phenotype is per-perturbation
   (per-sgRNA), aggregated over cells. Cell-level DE is rarely the right
   inference target.
2. **sgRNA assignment must use Mixscape (or equivalent)**: raw `sgRNA UMI >
   threshold` confounds escapers (CRISPRi efficiency 70-90%) and lethal
   knockdowns.
3. **Multi-sgRNA cells (multiple integrations)** must be filtered out
   pre-analysis; MOI=1 is design-intent, ~30% is reality.
4. **Per-cell-line baseline**: do not directly compare perturbation effects
   across cell lines; compute per-line vs non-targeting control.
5. **Phenotype distance via energy distance / Wasserstein**, not marginal
   gene LFC: perturbations have multivariate signatures.
6. **Lethal sgRNA depletion** (CRISPRi knocks down → cells die → barcode
   under-represented): do depletion analysis over time before claiming
   "no phenotype".
7. **Cluster perturbations, not cells**: known-pathway sgRNAs should
   cluster together (validation: ribosome biogenesis sgRNAs cluster).

## Sanity anchors
- Non-targeting control sgRNA effect ≈ 0 (energy distance < 0.05). Otherwise
  → batch contamination or escaper-detection failure.
- Known pathway co-clustering: ribosome biogenesis (RPS3, RPL3, NOP56),
  proteasome (PSMA1-7, PSMB1-7), oxphos (NDUFA1-7) each cluster.

## Decision tree
```
Is this Perturb-seq?
├─ YES
│   → sgRNA assignment via Mixscape / MUSIC / scMAGeCK
│   → Filter multi-sgRNA cells
│   → Compute per-perturbation phenotype as mean / energy distance
│   → Cluster perturbations (not cells); validate via known pathways
│   → DE per-perturbation × cell-line: pseudobulk + DESeq2
│   → Lethal sgRNA flagged via depletion analysis (need timepoints)
└─ NO (regular scRNA) → rule 06 / 04 apply
```

## Anti-rules (auto-reject)
- Cell-level DE on Perturb-seq (treats sgRNA assignment as ignorable batch)
- Raw sgRNA UMI threshold without escaper detection
- Including multi-sgRNA cells in primary analysis
- Comparing perturbation strength directly across cell lines
- Skipping non-targeting control sanity check (control effect ≠ 0 → bad)
- < 30 cells per perturbation (insufficient power for phenotype call)

## Cold-start fallback
- Without Mixscape: Replogle's mixture-model proxy is acceptable; document
  in provenance.
- < 30 cells per perturbation: tag confidence: low; consider aggregating
  similar sgRNAs (multiple sgRNAs per gene).
- Single cell line: explicit `confidence: medium` (no cross-line validation).
