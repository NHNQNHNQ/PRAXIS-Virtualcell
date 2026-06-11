---
skill_id: sge_library_design
description: Saturation genome editing (SGE) library design — per-codon 19-substitution + stop + silent control ssODN library. HAP1 cell line preferred (haploid); cut site < 30 nt from target codon; HDR enhancer (NU7441/Scr7); ≥3 replicates, ≥14-day selection; MaveDB-format export.
inputs:
  - target_seq: target DNA region (must include open reading frame portion)
  - frame_offset: 0/1/2 — codon-frame offset of target_seq[0]
  - codon_range: (start_codon, end_codon) — codons to saturate (1-indexed)
  - cell_context: HAP1 (recommended) | HEK293 | other
outputs:
  - oligo_pool: list of {variant_id, codon_position, mutation, oligo_sequence (70-100 nt), homology_arms_lr, anchor_type}
  - sgrna_anchors: each with cut site within 30 nt of any covered codon
  - controls: stop-codon and synonymous-only oligos (for QC anchors)
  - cell_line_warning: diploid → analysis complexity
  - hdr_enhancer_recommendation: NU7441 / Scr7 / RAD51 stim
  - mavedb_export_template: tsv format for MaveDB submission
sanity_check: BRCA1 RING-domain mock — library has stop + synonymous controls + ≥19 substitutions per codon; HAP1 OK warning; HDR enhancer recommended
reference_case: crispr-007-saturation-mutagenesis
---

## Don't

- ❌ Diploid cell line (analysis complicated by hetero/homo allele states).
- ❌ HDR efficiency unboosted (default <5% in HAP1).
- ❌ Library without silent control (no neutral baseline).
- ❌ Single replicate (variant noise too high).
- ❌ Selection < 14 days (insufficient fitness drift).

## 输出契约

```json
{
  "skill_id": "sge_library_design",
  "n_guides": 0,
  "guides_csv": "",
  "best_guide": {
    "seq": "",
    "cfd_score": 0.0,
    "mit_score": 0.0
  },
  "diagnostics": {
    "brain": "crispr",
    "archetype": "crispr"
  }
}
```
