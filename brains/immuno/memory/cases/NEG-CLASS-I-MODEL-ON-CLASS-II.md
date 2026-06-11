---
case_id: NEG-CLASS-I-MODEL-ON-CLASS-II
schema_version: 1
status: validated
source: praxis_seed_NEG
task: mhc_class_ii_epitope_prediction
immuno_task: mhc_class_ii_epitope_prediction
antigen_class: viral
hla_class: HLA_II
hla_alleles: []
peptide_length_bin: "13-15"
disease_indication: infection_general
target_protein: any
target_protein_uniprot: []
tools: [NetMHCpan-4.1 (Class I model) erroneously applied to 13-25mer Class II input]
key_paper_doi: 10.1093/nar/gkad380
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, class-mismatch, MHC-II, register-prediction]
unverified_details: []
---

# NEG: NetMHCpan-4.1 (Class I model) applied to 13-25mer → wrong predictions (cross-class confusion)

## Background
NetMHCpan-4.1 is trained for HLA Class I peptide-binding (8-11 mer, closed-end groove). HLA Class II uses an open-end groove that accepts 13-25 mer with variable register. Applying Class I models to Class II input → systematic mis-prediction of binding + register.

## ★ 排除/不做的事
- ❌ NetMHCpan (Class I) on > 11 mer / Class II HLA
- ❌ NetMHCIIpan (Class II) on < 13 mer / Class I HLA
- ❌ Treating peptide_length_bin as cosmetic (must drive pipeline routing)

## ★ 失败模式
- **Class I model on Class II peptide** → no register prediction, wrong anchor, garbage rank
- **MHC restriction misassignment** in TCR-pMHC modeling

## ★ 方法选择决策链
- Class I → NetMHCpan family (NetMHCpan, MHCflurry, BigMHC)
- Class II → NetMHCIIpan family (NetMHCIIpan, MARIA, MixMHC2pred)
- Reviewer hard-block on cross-class application (rule 03)

## Lessons → ANTI-RULES generated
- **anti-rule 15**: Cross-class predictor application (Class I model on Class II input or vice versa) → block (rule 03)
