---
skill_id: cas13_grna_design
description: RfxCas13d (CasRx) gRNA design for mRNA targeting — tile 22-30 nt gRNA every 50 nt over CDS (UTR penalized); RNAfold accessibility predict; Cas13design flanking H/F/D scoring; transcriptome BLAST for off-target; SNV-allele specificity (gRNA across SNV); collateral activity warning in target cell type. Transient delivery preferred.
inputs:
  - mrna_seq: full mRNA (with optional 5'UTR/CDS/3'UTR annotation)
  - cds_start, cds_end: 0-indexed CDS bounds (else assume entire mrna_seq is CDS)
  - target_snv: optional 0-indexed position of SNV for allele-specific design
  - cell_context: lung_cancer / neuron / etc.
outputs:
  - tiled_grnas: list of {position, sequence, gc, accessibility_score, cas13_score, off_target_count}
  - allele_specific_grnas: if target_snv provided, gRNAs that span SNV with mismatch position central
  - delivery_recommendation: mRNA+LNP / AAV (single CasRx fits) / lentivirus
  - collateral_risk: HIGH for neurons / MED otherwise
  - blocked_use: Cas13 attempted as DNA editor → block
sanity_check: KRAS mRNA mock — tile gRNA in CDS only (UTR skipped), top hits have GC 30-70%, collateral warning emitted
reference_case: crispr-009-cas13-rna-targeting
---

## 输出契约

```json
{
  "skill_id": "cas13_grna_design",
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
