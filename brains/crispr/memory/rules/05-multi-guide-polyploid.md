---
rule_id: 05-multi-guide-polyploid
rule_type: case_distilled
applies_to:
  edit_type: [knockout_indel, multiplex_knockout]
  cell_context: [HeLa, U2OS, K562, MOLM13, HCT116, Panc1]
evidence_cases: [crispr-001, crispr-005]
confidence: high
---

# Polyploid / aneuploid cell lines need ≥2 guides OR single-cell clone

Single-guide KO in polyploid cells (HeLa = 3n; many cancer lines aneuploid) yields **<50% complete-KO** in the bulk population — a heterozygous mosaic dominates.

**Mitigation options:**
1. **Dual-guide** spanning a critical exon → exon excision (one event KOs all alleles).
2. **Single-cell clone screening** + Western/amplicon-seq to confirm full KO before phenotyping.
3. **Single-cell sort** + bulk validation of the homozygous KO clones.

**Action:** sgrna_design_score skill emits a polyploid warning whenever cell ∈ POLYPLOID_CELLS; design_plan must include `excluded_guides[]` for single-guide-only when polyploid.
