---
case_id: NEG-HER2-CART-FIRST-PATIENT-DEATH-MORGAN-2010
schema_version: 1
status: validated
source: praxis_seed_NEG
task: car_target_selection_safety
immuno_task: car_target_selection_safety
antigen_class: tumor_neoantigen
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: cancer_colon
target_protein: ERBB2 (HER2)
target_protein_uniprot: ["P04626"]
tools: [trastuzumab-derived scFv, third-generation CD28-4-1BB-CD3ζ CAR]
key_paper_doi: 10.1038/mt.2010.24
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, on-target-off-tumor, CAR-T, patient-death, target-selection, normal-tissue-expression]
unverified_details: []
---

# NEG: First HER2 CAR-T patient died from on-target off-tumor pulmonary toxicity (Morgan 2010 Mol Ther)

## Background
NCI Phase 1 trial of HER2-CAR-T (trastuzumab scFv + CD28-4-1BB-CD3ζ third-gen design) in metastatic colorectal cancer with HER2+ pulmonary metastases. **First patient died within 5 days** of single 10^10 cell infusion. Autopsy: massive pulmonary infiltrate + cytokine storm. Cause: low-level normal HER2 expression on lung epithelium → CAR-T attacked normal lung.

## What the trial actually did (the wrong way)
1. Picked HER2 because of trastuzumab precedent (validated tumor target)
2. Validated tumor expression by IHC on patient biopsy (~3+ HER2 staining)
3. Skipped: comprehensive normal-tissue expression panel (DepMap was not yet public; HPA was nascent)
4. Skipped: affinity de-tuning (used trastuzumab-derived scFv at Kd ~5 nM — extremely high affinity)
5. Did NOT account for pulmonary epithelial low-level HER2 (~10x below tumor) which is sufficient for sub-nM CAR engagement

## ★ 排除/不做的事 (anti-pattern)
- ❌ CAR target selection based on tumor IHC alone (no normal tissue panel)
- ❌ Trastuzumab-affinity scFv (Kd ~5 nM) on a target with documented low normal expression → predictable on-target off-tumor
- ❌ First-in-human dose at 10^10 cells without dose escalation
- ❌ No pulmonary tissue cytotoxicity check on patient-derived CAR-T

## ★ 失败模式 (anti-rule trigger)
- **CAR-T against target with low-level normal essential-tissue expression** (HER2 on lung epithelium ~10x lower than tumor but well above the sub-nM CAR engagement threshold)
- **High-affinity scFv inappropriate for non-tumor-restricted target** (affinity de-tuning required)
- **Single-source expression validation** (patient IHC only; missed broader normal landscape)

## ★ 方法选择决策链 (what they should have done)
- Multi-source normal expression panel: DepMap (cell lines) + GTEx (tissue bulk) + HPA (IHC) + TabulaSapiens (sc-RNA-seq) — minimum 4 sources
- Affinity-tuning: low-affinity 4D5-derived scFv variants (Kd 100 nM-1 µM) for "differential expression discrimination"
- iPSC pulmonary epithelial cytotoxicity panel
- Logic-gated CAR (e.g., AND-gate with tumor-restricted second antigen)
- Cap first dose at 10^7 cells with strict dose escalation

## ★ Validation
- Wet lab evidence: 1/1 first patient died of cytokine storm + pulmonary failure in 5 days
- Retrospective: low-level normal HER2 in lung epithelium confirmed by IHC + GTEx (years later)
- Subsequent HER2 CAR-T trials use de-tuned scFv (Sun et al 2014, Liu et al 2015) — no pulmonary toxicity

## Lessons → ANTI-RULES generated
- **anti-rule 4**: CAR target with tumor-IHC-only validation (no multi-source normal expression) → block
- **anti-rule 5**: High-affinity scFv (Kd < 10 nM) for target with documented low normal expression in essential tissue → block; require affinity de-tuning
- **anti-rule 6**: First-in-human CAR-T at >10^8 cells without dose escalation → block

## 数据指针
- Source: Morgan RA et al. 2010, "Case report of a serious adverse event following the administration of T cells transduced with a chimeric antigen receptor recognizing ERBB2"
- Patient: 39 yo F, metastatic colorectal cancer, HER2+ lung mets
- Cell dose: 10^10 cells single infusion
- Time to death: 5 days
- This case rewrote the CAR-T target selection field — see rule 07 (multi-source CAR target expression)
