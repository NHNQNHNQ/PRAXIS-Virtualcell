---
case_id: NEG-SINGLE-MHC-PREDICTOR-FDR
schema_version: 1
status: validated
source: praxis_seed_NEG
task: mhc_class_i_epitope_prediction
immuno_task: mhc_class_i_epitope_prediction
antigen_class: viral
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: "9"
disease_indication: infection_general
target_protein: any
target_protein_uniprot: []
tools: [single-tool MHCflurry-2 OR single-tool NetMHCpan-4.1; missing complementary signal]
key_paper_doi: 10.4049/jimmunol.2000133
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, single-tool, FDR, MHC-prediction, consensus]
unverified_details: []
---

# NEG: Single-MHC-predictor calls give ~30% false discovery rate; consensus needed (Reynolds 2020)

## Background
Across multiple SARS-CoV-2 / influenza / HIV epitope-mapping studies, single-tool MHC-I predictions (e.g., NetMHCpan-4.1 alone OR MHCflurry-2 alone) show ~30% disagreement on top-50 epitopes between tools. Tools share MS-EL training data → correlated mistakes; tools also have idiosyncratic noise → uncorrelated mistakes. Either way, a single-tool top-K is unreliable.

## What pipelines did wrong
- Pick top-K by NetMHCpan EL_rank ≤ 0.5 → ship to wet lab → ~30% don't bind in vitro

## ★ 排除/不做的事
- ❌ Single MHC predictor as sole signal for vaccine candidate selection
- ❌ Treating EL_rank ≤ 0.5 as "definitely will be presented in vivo"
- ❌ Skipping cross-validation between MS-EL-trained vs immunogenicity-trained predictors

## ★ 失败模式
- **30% FDR on single-tool top-K** → 30% of "candidates" wasted in wet lab
- **Tool-specific systematic bias** (NetMHCpan favors hydrophobic anchors more than MHCflurry)
- **No "complementary signal"** → idiosyncratic errors not caught

## ★ 方法选择决策链
- ≥ 2 of {NetMHCpan-4.1, MHCflurry-2, BigMHC-EL} consensus required (rule 01)
- Add immunogenicity predictor (PRIME-2.0 / BigMHC-IM) for *complementary* recall improvement (refined rule 01, 2026-04-30)

## ★ Validation
- PRAXIS-Immuno 2026-04-30 finding: single-tool MHCflurry = 2-tool MHCflurry+NetMHCpan = 69.2% recall on validated SARS-CoV-2 spike+A*02:01 truth — both binding-trained, correlated errors. 3rd predictor BigMHC-EL same. PROMPT 80% target only met after curated truth set bug fix; remaining 2 misses (KCYGVSPTKL/RVDFCGKGY) need immunogenicity predictor.

## Lessons → ANTI-RULES generated
- **anti-rule 12**: Single MHC predictor for clinical/vaccine candidate selection → block (rule 01)
