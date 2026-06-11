---
case_id: NEG-SINGLE-GUIDE-POLYPLOID
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 1
edit_type: knockout_indel
target_gene: any
target_organism: hg38
cell_context: HeLa
editing_system: SpCas9
delivery_method: lentivirus
tools: [SpCas9, CRISPOR, CRISPResso2]
key_paper_doi: 10.1038/nbt.3026
provenance:
  source_type: literature
  doi: 10.1038/nbt.3026
  citation: "Doench JG, Hartenian E, Graham DB, et al. Rational design of highly active sgRNAs for CRISPR-Cas9-mediated gene inactivation. Nat Biotechnol. 2014;32(12):1262-1267."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, single_guide, polyploid, mosaic_KO]
causal_tag: causal
---

# NEG-SINGLE-GUIDE-POLYPLOID — Single sgRNA in polyploid / aneuploid cell line

## What this NEG- case records
**Anti-pattern**: using a single sgRNA for KO in HeLa (3n), K562, U2OS, HCT116, MOLM13, Panc1 or any other polyploid/aneuploid cancer line, without dual-guide design or single-cell clone screening. The bulk population becomes a heterozygous mosaic and never reaches > 50% complete-KO.

## Where the failure mode was published
Doench 2014 (Nat Biotechnol) Fig 4 + multiple validation studies show single-sgRNA SpCas9 in HeLa/K562 produces ~30-50% indel allele but ≤ 20% homozygous-KO clones. HeLa karyotype is 70-90 chromosomes with TP53/CDKN2A loci typically tri-tetraploid → 3-4 alleles must each be cut + frameshifted independently.

## Mechanism — why it fails
1. SpCas9 cleavage rate per allele is ~80% in HeLa, but homozygous KO requires ALL N alleles in-frame indel.
2. With N=3 alleles and cleavage probability p=0.8, P(all-cut) = p^N = 0.51; with 50% in-frame indel (NHEJ produces 30-50% in-frame), P(all-frameshift) = (0.4)^3 ≈ 6%.
3. Bulk population is then a mosaic of single/double/triple-allele edits, dominated by partial KOs that retain partial function.
4. Compensatory upregulation (e.g., p63/p73 for TP53) further masks phenotype.

## Concrete numerics (from case-001 + Doench 2014)
- HeLa single-guide TP53 KO: ~5% homozygous knockout cells in bulk; 95% mosaic
- HeLa dual-guide (different exons) TP53 KO: ~40% homozygous via exon-deletion event
- Single-cell clone screening + amplicon-seq: only viable approach for clean homozygous bulk

## ★ Reviewer hard-stop
Any design plan that recommends a single sgRNA on `cell_context ∈ {HeLa, U2OS, K562, HCT116, MOLM13, Panc1}` without (a) explicit dual-guide design OR (b) single-cell clone sort plan must be vetoed. Required: ≥ 2 sgRNAs OR clonal screening protocol attached.

## Maps to anti-rule
**anti-rule #1**: Single sgRNA on polyploid/aneuploid cell line is forbidden. Required: dual-guide exon-spanning OR single-cell clone screen.

## Anti-retrieval keywords
single guide polyploid, single sgrna hela, single sgrna k562, mosaic ko, no dual guide, no single cell clone, polyploid bulk
