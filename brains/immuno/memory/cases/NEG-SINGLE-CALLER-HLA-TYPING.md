---
case_id: NEG-SINGLE-CALLER-HLA-TYPING
schema_version: 1
status: validated
source: praxis_seed_NEG
task: hla_typing_from_rnaseq
immuno_task: hla_typing_from_rnaseq
antigen_class: n/a
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: n/a
disease_indication: cancer_general
target_protein: HLA loci
target_protein_uniprot: []
tools: [single-caller HLA typing (e.g., OptiType only), no consensus check]
key_paper_doi: 10.1186/s13073-018-0560-3
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, single-caller, HLA-typing, rare-allele-dropout]
unverified_details: []
---

# NEG: Single-caller HLA typing from RNA-seq has 5-10% error rate; rare alleles miscalled (Lee 2018 Genome Med)

## Background
HLA typing from RNA-seq with a single caller (OptiType / arcasHLA / HLA-LA / seq2HLA / xHLA / Polysolver) achieves only ~92-95% 4-digit accuracy on average, with worse performance on rare alleles (frequency < 0.001 in IMGT/HLA), HLA-Cw alleles, and class II loci. Multi-caller consensus (≥ 2/3 of 3 callers) brings 4-digit accuracy to > 95%.

## ★ 排除/不做的事
- ❌ Single-caller HLA typing as input to neoantigen pipeline
- ❌ Treating OptiType output as ground truth without confirmation
- ❌ Skipping consensus check on rare alleles or low-coverage loci

## ★ 失败模式
- **5-10% wrong allele calls on common alleles**, > 20% on rare alleles
- **Wrong allele → wrong neoantigen predictions** → wrong vaccine candidates
- **HLA-Cw and HLA-DPB1 disproportionately error-prone**

## ★ 方法选择决策链
- ≥ 3 callers (OptiType + arcasHLA + HLA-LA), require ≥ 2/3 consensus
- For rare alleles, add seq2HLA / xHLA as 4th
- Confirm by PCR-SBT for clinical use

## Lessons → ANTI-RULES generated
- **anti-rule 17**: Single-caller HLA typing from RNA-seq into clinical-grade neoantigen pipeline → block (rule 02 / 05)
