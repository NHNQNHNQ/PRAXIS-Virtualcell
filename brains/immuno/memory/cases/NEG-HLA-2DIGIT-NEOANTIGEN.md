---
case_id: NEG-HLA-2DIGIT-NEOANTIGEN
schema_version: 1
status: validated
source: praxis_seed_NEG
task: tumor_neoantigen_identification
immuno_task: tumor_neoantigen_identification
antigen_class: tumor_neoantigen
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: "9"
disease_indication: cancer_melanoma
target_protein: tumor neoantigens
target_protein_uniprot: []
tools: [legacy 2-digit HLA typing, NetMHCpan with HLA-A02 (not A*02:01)]
key_paper_doi: 10.1126/scitranslmed.aaa3091
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, HLA-2-digit, neoantigen, allele-specificity]
unverified_details: []
---

# NEG: 2-digit HLA typing in early melanoma neoantigen vaccine pipelines blurred A*02:01 vs A*02:03 → wrong predictions (Carreno 2015 Sci & follow-ups)

## Background
Pre-2017 neoantigen pipelines often used 2-digit HLA (e.g., "A02") which conflates A*02:01, A*02:03, A*02:06, A*02:07 etc. — alleles with measurably different peptide-binding repertoires. Predictions made on 2-digit HLA → predicting for the wrong receptor → wrong peptides ranked.

## ★ 排除/不做的事
- ❌ 2-digit HLA in any MHC binding prediction (use 4-digit IMGT format)
- ❌ Equating "HLA-A02" with "HLA-A*02:01" (the most common A*02 allele in CEU but not in other populations)

## ★ 失败模式
- **Wrong predictions on HLA-A*02:03 / A*02:06 patients** because pipeline assumed A*02:01
- **Population bias** — 2-digit collapsing favors common Caucasian alleles, biases against East Asian (more A*02:06/07) and African populations

## ★ 方法选择决策链
- Always 4-digit IMGT format (HLA-A*02:01) — not 2-digit "HLA-A02"
- Type per-patient with ≥ 3 callers (rule 02) — OptiType + arcasHLA + HLA-LA consensus

## ★ Validation
- HLA-A*02:01 vs A*02:03: differ at residues 9 (Y/F) and 95 (V/L) → distinct binding pocket
- A*02:01 anchor preference: P2-Leu/Met/Val, P9-Val/Leu/Ile
- A*02:03 anchor preference: P2-Leu/Met, P9-Val (subtly different)

## Lessons → ANTI-RULES generated
- **anti-rule 13**: 2-digit HLA in MHC binding prediction → block (rule 02)
