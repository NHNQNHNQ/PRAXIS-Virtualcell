---
case_id: NEG-AFFINITY-MATURED-ANTIBODY-NO-IMMUNOGENICITY-CHECK
schema_version: 1
status: validated
source: praxis_seed_NEG
task: bcr_repertoire_lineage_analysis
immuno_task: bcr_repertoire_lineage_analysis
antigen_class: viral
hla_class: HLA_II
hla_alleles: []
peptide_length_bin: "13-25"
disease_indication: biologic_therapeutic
target_protein: therapeutic antibody candidate
target_protein_uniprot: []
tools: [computational antibody affinity maturation, missed T-cell epitope (immunogenicity) check]
key_paper_doi: 10.1080/19420862.2017.1334032
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, antibody-immunogenicity, anti-drug-antibodies, T-cell-epitope, deimmunization]
unverified_details: []
---

# NEG: Affinity-matured therapeutic antibody without T-cell epitope check → ADA response (anti-drug antibodies) (Jawa 2017 mAbs)

## Background
Affinity-matured antibody candidates (humanized scFvs, framework-grafted CDRs) often introduce novel CD4-T-cell epitopes in their CDR or FR regions. Without a T-cell epitope (Class II) check, these candidates can elicit anti-drug antibody (ADA) responses in patients → loss of efficacy + infusion reactions. The field standard is "deimmunization" — predict T-cell epitopes, mutate to remove, validate by ex vivo T-cell assay.

## ★ 排除/不做的事
- ❌ Therapeutic antibody candidate selection without HLA-II T-cell epitope screen
- ❌ Treating "humanized" as automatically "non-immunogenic"
- ❌ Skipping ex vivo MHC-II tetramer assay before clinical trial

## ★ 失败模式
- **Novel Class II epitope in CDR/FR → ADA response → drug failure**
- **Engineered residue introduces motif binding to common HLA-DRB1*01:01/*15:01**
- **Loss-of-efficacy in 5-30% of patients** depending on affinity-maturation strategy

## ★ 方法选择决策链
- NetMHCIIpan / MARIA on the antibody Fv sequence vs population-coverage HLA-II panel
- Mutate flagged epitopes (deimmunization) — preserve binding via constraint
- Ex vivo HLA-II tetramer assay on top candidates
- Cross-agent handoff: PRAXIS-Protein for binding-preserving mutations

## Lessons → ANTI-RULES generated
- **anti-rule 21**: Therapeutic antibody candidate without HLA-II T-cell epitope screen → block (immunogenicity / ADA risk)
