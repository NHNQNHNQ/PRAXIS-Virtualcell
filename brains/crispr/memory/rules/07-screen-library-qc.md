---
rule_id: 07-screen-library-qc
rule_type: case_distilled
applies_to:
  edit_type: [pooled_crispr_screen_analysis]
  cell_context: ALL
evidence_cases: [crispr-006]
confidence: high
---

# Pooled screen library QC must precede hit-calling

A pooled CRISPR screen is only as good as the day-0 library distribution. Poorly-distributed libraries produce **artefactual hits** (sgRNAs that drop because they were absent at day 0, not because of biology).

**QC gates (all required):**
1. **Gini coefficient < 0.3** on day-0 counts (1 = max concentration; 0 = even distribution).
2. **Lorenz curve** plotted; clearly concave-up = good, near-diagonal = even.
3. **MOI ≤ 0.3** (multiplicity of infection) — higher MOI mixes sgRNAs in cells.
4. **≥ 200x cells per sgRNA** at infection — bottleneck below this.
5. **Day-0 + day-14+ time points** — single time point insufficient.
6. **≥ 2 biological replicates** for MAGeCK MLE β estimate.
7. **Control sgRNA normalization** preferred over median.
8. **DepMap CKE/NE benchmark** sanity: CKE should drop, NE should be flat.

**Action:** screen_analysis_mageck skill computes Gini + benchmark and BLOCKS hit-calling if any gate fails.
