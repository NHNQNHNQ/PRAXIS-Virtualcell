---
case_id: NEG-AURORA-MAGE-A3-affinity-enhanced-tcr-titin
schema_version: 1
status: validated
source: praxis_seed_NEG
task: tcr_pmhc_complex_modeling
immuno_task: tcr_pmhc_complex_modeling
antigen_class: tumor_neoantigen
hla_class: HLA_I
hla_alleles: ["HLA-A*01:01"]
peptide_length_bin: "9"
disease_indication: cancer_melanoma
target_protein: MAGE-A3 (CT antigen)
target_protein_uniprot: ["P43357"]
tools: [structure-guided affinity maturation, retrospective TCRdock, retrospective ESM-IF self-similarity check]
key_paper_doi: 10.1182/blood-2013-03-490565
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, cross-reactivity, autoimmune_death, TCR-T, off-target, affinity-enhanced-TCR]
unverified_details: []
---

# NEG: Aurora MAGE-A3 affinity-enhanced TCR cross-reacted with cardiac TITIN → 2 patient deaths (Linette 2013 Blood)

## Background
Adaptimmune affinity-enhanced HLA-A*01:01 MAGE-A3 (EVDPIGHLY) TCR was advanced into a melanoma + multiple myeloma trial. **Both patients died of cardiogenic shock within 6 days** of T-cell infusion. Post-mortem: cardiac biopsies showed massive T-cell infiltration. Retrospective analysis showed the affinity-enhanced TCR cross-reacted with **TITIN ESDPIVAQY** (cardiac muscle), a 7-of-9 mismatch ignored at design time.

## What the trial actually did (the wrong way)
1. Took natural MAGE-A3 reactive TCR and structure-guided mutated CDR3 to enhance affinity (Kd → low nM)
2. Validated specificity against a 30-line cancer-cell-line panel — none expressed TITIN at testable level
3. Skipped: full proteome alanine-scan-style cross-reactivity panel; iPSC cardiomyocyte exposure assay
4. Skipped: structure-based off-target search across ALL human proteome 9-mers presented by HLA-A*01:01

## ★ 排除/不做的事 (anti-pattern)
- ❌ Affinity-enhanced TCR shipping without **comprehensive proteome-wide cross-reactivity scan**
- ❌ Single-tissue panel (cancer cell lines) as sole cross-reactivity validation
- ❌ Skipping iPSC-derived cardiomyocyte / hepatocyte / neuron specificity check before clinic
- ❌ Treating "binding affinity ↑" as monotonically good (higher Kd ≠ safer; specificity window collapses)

## ★ 失败模式 (anti-rule trigger)
- **Engineered TCR cross-reactivity to off-target self-protein expressed in vital tissue** (here: cardiac TITIN)
- **Affinity maturation collapsed specificity window** — more avid binding meant tolerance to more peptide-MHC mismatches
- **No requirement for orthogonal validation modalities** before clinic

## ★ 方法选择决策链 (what they should have done)
- TCRdock (Bradley 2024) on the post-mutation TCR + sliding window over UP000005640
- ESM-IF inverse-fold scoring of all 9-mers presented by A*01:01 vs the engineered TCR
- iPSC cardiomyocyte / hepatocyte cytotoxicity panel BEFORE clinical trial
- Cap affinity at "natural-TCR window" (Kd 1-100 µM) — NOT sub-nM

## ★ Validation
- Wet lab evidence: 2/2 patient deaths with cardiogenic shock + cardiac T-cell infiltration on autopsy
- Retrospective in vitro: re-stimulation panel showed engineered TCR potently killed iPSC cardiomyocytes (negative on parental TCR)

## Lessons → ANTI-RULES generated
- **anti-rule 1**: Engineered TCR (esp. affinity-enhanced) shipping without proteome-wide cross-reactivity panel + iPSC vital-tissue cytotoxicity → block
- **anti-rule 2**: Affinity-enhanced TCR with Kd < 1 µM without "specificity window" measurement → block
- **anti-rule 3**: Single-cell-line panel as sole specificity evidence for clinical TCR-T → block

## 数据指针
- Source: Linette GP et al. 2013, "Cardiovascular toxicity and titin cross-reactivity of affinity-enhanced T cells in myeloma and melanoma"
- Cross-reactive peptide: TITIN ESDPIVAQY at HLA-A*01:01
- Original target: MAGE-A3 EVDPIGHLY at HLA-A*01:01
- Sequence diff: 4 of 9 positions differ (E→E, V→S, D→D, P→P, I→I→V, G→A, H→Q, L→Y, Y→Y) — but TCR contact residues (P3, P5, P8) preserved
