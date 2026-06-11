---
case_id: NEG-CLASS-I-ONLY-FOR-CD4-VACCINE
schema_version: 1
status: validated
source: praxis_seed_NEG
task: mrna_vaccine_sequence_design
immuno_task: mrna_vaccine_sequence_design
antigen_class: viral
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: "9"
disease_indication: infection_general
target_protein: any vaccine antigen
target_protein_uniprot: []
tools: [Class I-only epitope optimization, ignored CD4 T-cell help requirement]
key_paper_doi: 10.1038/s41541-021-00309-4
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, vaccine-design, CD4-T-help, Class-II-balance]
unverified_details: []
---

# NEG: Vaccine designed only for Class I (CD8) without Class II (CD4 help) → poor antibody response + short-lived CD8 memory

## Background
CD8 T-cell vaccines designed by maximizing Class I epitope coverage but ignoring Class II → no CD4 T-cell help. Without CD4 help, CD8 memory is short-lived and B-cell antibody response is weak. Field standard: include both Class I and Class II epitopes (or ensure antigen has natural Class II epitopes).

## ★ 排除/不做的事
- ❌ Vaccine design that scores ONLY Class I epitopes
- ❌ Removing Class II epitopes during codon optimization (some optimizers do this)
- ❌ Single-allele vaccine without population-coverage Class II panel

## ★ 失败模式
- **Short-lived CD8 memory** without CD4 T-cell help (CD4 cytokines + CD40L on activated B cells essential)
- **Weak antibody response** because B cells need T-helper signals
- **Population coverage gap** when vaccine focuses only on dominant A*02:01 (Class I)

## ★ 方法选择决策链
- Always score both Class I (CD8) and Class II (CD4) epitopes (rule 03)
- Population-coverage HLA panel (≥ 80%)
- Cross-agent: PRAXIS-Drug for adjuvant (TLR agonist) to boost CD4 help

## Lessons → ANTI-RULES generated
- **anti-rule 22**: Vaccine candidate without Class II (CD4 help) coverage → block / warn
