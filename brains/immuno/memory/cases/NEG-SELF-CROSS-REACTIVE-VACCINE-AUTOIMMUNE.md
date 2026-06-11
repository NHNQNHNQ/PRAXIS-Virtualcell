---
case_id: NEG-SELF-CROSS-REACTIVE-VACCINE-AUTOIMMUNE
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
target_protein: any antigen
target_protein_uniprot: []
tools: [naive epitope picker without proteome BLAST, missed self cross-reactivity]
key_paper_doi: 10.1146/annurev-immunol-042617-053405
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, molecular-mimicry, autoimmune, central-tolerance, self-cross-reactivity]
unverified_details: []
---

# NEG: Vaccine epitope cross-reactive with human self-protein → autoimmune risk / central-tolerance breach

## Background
Multiple post-vaccination autoimmune sequelae (e.g., narcolepsy after H1N1 Pandemrix, GBS/transverse myelitis cases after various vaccines) have been linked to **molecular mimicry**: vaccine antigen contains a peptide with high identity to a self-protein → CD8/CD4 T cells primed against vaccine peptide cross-react with self → autoimmunity. The 2009 Pandemrix narcolepsy case is the most famous: Pandemrix (but not Focetria) contained a sequence with HLA-DQB1*06:02-restricted homology to hypocretin receptor.

## ★ 排除/不做的事
- ❌ Vaccine antigen design without per-peptide BLAST vs UP000005640 human proteome
- ❌ Promoting peptides with > 80% identity over 8 contiguous aa to a human protein
- ❌ Skipping HLA-DQB1*06:02 specifically when designing flu vaccines (narcolepsy risk)

## ★ 失败模式
- **High-similarity vaccine peptide → self protein cross-reaction → autoimmunity**
- **Central-tolerance breach** in genetically susceptible (HLA-DQB1*06:02 homozygous for narcolepsy)

## ★ 方法选择决策链
- BLASTp every promoted vaccine peptide vs UP000005640 (rule 04)
- Threshold: > 80% identity over 8 contiguous aa flagged
- Special-case: known narcolepsy / GBS-associated HLA alleles get tighter threshold

## ★ Validation
- Pandemrix narcolepsy: ~1300 confirmed cases in EU 2009-2010, OR ~5-10x baseline
- Mechanism: cross-reactivity between H1N1 nucleoprotein and human hypocretin (orexin) receptor 2

## Lessons → ANTI-RULES generated
- **anti-rule 14**: Vaccine epitope without proteome-wide BLAST → block (rule 04)
