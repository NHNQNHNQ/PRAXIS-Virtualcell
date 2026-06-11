---
case_id: NEG-GENERIC-PPDOCK-FOR-TCR
schema_version: 1
status: validated
source: praxis_seed_NEG
task: tcr_pmhc_complex_modeling
immuno_task: tcr_pmhc_complex_modeling
antigen_class: viral
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: "9"
disease_indication: infection_general
target_protein: TCR-pMHC complex
target_protein_uniprot: []
tools: [HADDOCK, ClusPro, PatchDock; generic protein-protein dockers without TCR-pMHC geometric prior]
key_paper_doi: 10.1038/s41587-023-01989-0
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, TCR-pMHC, generic-PP-docker, geometric-prior]
unverified_details: []
---

# NEG: Generic PP-dockers (HADDOCK / ClusPro / PatchDock) on TCR-pMHC give wrong topology (Bradley 2024 Nat Biotechnol)

## Background
Generic protein-protein dockers (HADDOCK, ClusPro, PatchDock, ZDOCK) lack the TCR-pMHC geometric prior: TCR Vα/Vβ should sit *diagonally* across the pMHC groove with CDR3α/β over the peptide center. Without this prior, generic dockers explore physically implausible orientations and rank them by surface complementarity → wrong top-1 in ~70% of test cases. TCRdock (Bradley 2024) uses TCR-pMHC-specific structural template + AlphaFold2 with restricted MSA → ~10x better top-1 RMSD.

## ★ 排除/不做的事
- ❌ HADDOCK / ClusPro / PatchDock / ZDOCK as primary TCR-pMHC docker
- ❌ Generic AF-Multimer without paired TCR-pMHC MSA + geometric template

## ★ 失败模式
- **Wrong TCR docking topology** (e.g., reversed Vα/Vβ orientation, CDR3 not over peptide)
- **Top-1 RMSD > 5 Å vs crystal** in ~70% of test set
- **No MHC restriction class enforcement** → Class II TCR docked on Class I pMHC

## ★ 方法选择决策链
- TCRdock (Bradley 2024) for TCR-pMHC primary
- AF-Multimer with custom TCR-pMHC paired MSA as orthogonal validation (multi-seed)
- TCRen / ESM-IF as scoring auxiliaries
- Multi-seed ≥ 5 mandatory (rule 05)

## Lessons → ANTI-RULES generated
- **anti-rule 16**: Generic PP-docker (HADDOCK/ClusPro/PatchDock/ZDOCK) for TCR-pMHC modeling → block (rule 05)
