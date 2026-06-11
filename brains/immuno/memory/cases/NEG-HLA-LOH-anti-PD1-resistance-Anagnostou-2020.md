---
case_id: NEG-HLA-LOH-anti-PD1-resistance-Anagnostou-2020
schema_version: 1
status: validated
source: praxis_seed_NEG
task: tumor_neoantigen_identification
immuno_task: tumor_neoantigen_identification
antigen_class: tumor_neoantigen
hla_class: HLA_I
hla_alleles: []
peptide_length_bin: "9-10"
disease_indication: cancer_lung_NSCLC
target_protein: tumor neoantigens
target_protein_uniprot: []
tools: [pVACseq, NetMHCpan, MHCflurry, MISSED LOHHLA on the lost-allele clones]
key_paper_doi: 10.1158/2159-8290.CD-19-1230
extracted_at: 2026-05-02
tags: [NEG, anti-rule, failure_mode_anchor, HLA-LOH, tumor-escape, anti-PD1-resistance, neoantigen-vaccine-failure]
unverified_details: []
---

# NEG: NSCLC neoantigen pipeline missed HLA LOH → predicted neoantigens that tumor could not present → anti-PD1 resistance (Anagnostou 2020 Cancer Discov)

## Background
Anagnostou et al. profiled longitudinal tumor + plasma in NSCLC patients on anti-PD-1. **~30% of acquired-resistance tumors had loss of heterozygosity at HLA Class I** (LOHHLA-detected). Neoantigen pipelines that did NOT integrate LOHHLA called peptides restricted to the LOST HLA allele as "high-confidence vaccine candidates" → those peptides were never actually presented in the resistant tumor → vaccine targets useless. This case formalizes why rule 02 (HLA LOH check mandatory in tumor neoantigen pipelines) exists.

## What earlier pipelines did wrong (the wrong way)
1. Took baseline tumor exome + RNA-seq + 4-digit HLA typing
2. Predicted neoantigens for ALL 6 HLA-I alleles (assumed all alleles intact)
3. Did NOT run LOHHLA on the tumor BAM
4. Ranked by EL_rank + CCF + RNA_VAF
5. Top picks for vaccine were on the lost HLA allele (e.g., HLA-B*07:02 lost in tumor → all B*07:02 neoantigens irrelevant)

## ★ 排除/不做的事 (anti-pattern)
- ❌ Tumor neoantigen pipeline without LOHHLA pre-filter
- ❌ Treating all 6 HLA-I alleles as equally available in tumor
- ❌ Picking vaccine candidates without per-allele LOH status check
- ❌ Static germline HLA typing in evolving tumor without re-typing post-resistance

## ★ 失败模式 (anti-rule trigger)
- **Neoantigens predicted on LOST HLA allele** → tumor can't present → vaccine target ineffective
- **Anti-PD-1 resistance via HLA LOH** = ~30% of acquired-resistance NSCLC; B2M loss is another ~10%
- **Subclonal HLA LOH** also exists — partial allele loss in some tumor cells but not others; complicates clonal CCF interpretation

## ★ 方法选择决策链 (what they should have done)
- LOHHLA (McGranahan et al 2017) on tumor + matched normal BAM → per-allele LOH status
- Drop neoantigens whose restricting HLA is lost or has LOH score > threshold
- For acquired-resistance setting: re-type HLA from progressing tumor sample (not just germline)
- Report LOH status per neoantigen as first-class field in output

## ★ Validation
- Anagnostou 2020 Cancer Discov: ~30% of anti-PD-1-resistant NSCLC tumors have HLA LOH; ~10% have B2M loss
- McGranahan 2017 Cell: HLA LOH is recurrent across pan-cancer (PMID 29155345)
- Practical impact: any neoantigen vaccine without LOH check will rank ~30% lost-allele peptides as top candidates → wasted clinical trial slots

## Lessons → ANTI-RULES generated
- **anti-rule 10**: Tumor neoantigen pipeline (esp. for vaccine design) without LOHHLA step → block (rule 02)
- **anti-rule 11**: Acquired-resistance setting using only germline HLA without re-typing tumor → block

## 数据指针
- Source: Anagnostou V et al. 2020, "Integrative tumor and immune cell multi-omic analyses predict response to immune checkpoint blockade in melanoma and NSCLC"
- Foundational: McGranahan N et al. 2017, "Allele-specific HLA loss and immune escape in lung cancer evolution"
- Tool: LOHHLA https://bitbucket.org/mcgranahanlab/lohhla
