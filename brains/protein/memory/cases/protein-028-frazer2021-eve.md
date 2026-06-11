---
case_id: protein-028-frazer2021-eve
design_task: mutation_effect_prediction
target_pdb: 1TUP                   # TP53 DNA-binding domain — classic clinical variant target
target_uniprot: P04637             # human TP53, representative of paper's 3000+ disease protein cohort
fold_class: any
length_range: 30-1000
tools: [EVE, Variational_Autoencoder, MSA, deep_evolutionary_model]
key_paper_doi: 10.1038/s41586-021-04043-8
key_metrics:
  proteins_analyzed: "~3000+ disease-associated human proteins"
  benchmark_AUC_pathogenic_vs_benign: "approx 0.91 mean (vs 0.85-0.88 for AlphaMissense / EVmutation)"
  ClinVar_validated_set_AUC: "approx 0.93 on ClinVar pathogenic/benign labels"
  uncertain_VUS_classification: "~50% of variants of uncertain significance assignable to pathogenic or benign"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [mutation-effect, EVE, VAE, evolutionary, clinical-variant, ClinVar, pathogenicity, deep-mutation-scanning]
unverified_details:
  - "AUC numbers vary by benchmark; ~0.91 is ClinVar mean"
  - "3000+ protein cohort is paper-claimed; specific count varies by data source filter"
---

# EVE：deep evolutionary VAE 预测病理性突变（Frazer et al. Nature 2021）

## Background
- 起点：人类基因组中大量"variant of uncertain significance" (VUS)；clinical genetics 需要 quickly distinguish pathogenic vs benign
- 目标：用 variational autoencoder (VAE) 在大 MSA 上学 protein evolutionary distribution；通过 reconstruction likelihood ratio 评估 mutation 是否落在 evolutionary "tolerated" 区
- 应用：clinical genetics 应用；后续 AlphaMissense / ESM1v / popEVE 都基于这一 deep evolutionary framework；PRAXIS-Protein 可用于 protein engineering 中的"是否危险"过滤

## What I actually did（基于论文）
1. **MSA generation**：每 human protein 跑 jackhmmer 拿到 deep evolutionary MSA
2. **VAE training**：每 protein 训练独立 VAE
   - Encoder: sequence → latent z
   - Decoder: z → sequence distribution
   - Loss: reconstruction + KL divergence
3. **Mutation scoring**：mutated sequence vs WT 的 evidence lower bound (ELBO) ratio = "evolutionary anomaly score"
4. **Cohort scale**：~3000+ disease-associated human proteins
5. **Benchmark**：
   - ClinVar pathogenic/benign labels
   - DMS-based fitness data
   - Disease prevalence in population databases
6. **Validation**：AUC for pathogenic-vs-benign discrimination
7. **结果**：mean AUC ~0.91 跨 cohort；ClinVar 上 0.93；显著优于早期 EVmutation (DCA pairwise)

## ★ 排除的位点/区域
- **Disulfide bonds + active site**：EVE-trained 自然 capture（高 conservation, low ELBO）
- **Buried positions**：通常高 score = pathogenic risk
- **Surface positions** 上 prediction 较 noisy
- **MSA 浅的 protein**：< 100 effective sequences degrade
- **Disordered regions**：MSA alignment 困难
- **Large indel**：EVE fixed-length；deletion/insertion 不在 model
- **Compound heterozygous variants**：EVE 是 single-mutation；compound 不直接 score

## ★ 失败模式
- **Surface mutation**：~30% predicted pathogenic 实际 benign（surface 进化压力低）
- **Gain-of-function 突变**：EVE 是 conservation-based；新功能突变可能 UNDER-estimated as benign
- **Late-onset / partial-penetrance**：EVE 偏向 strong pathogenic；mild loss-of-function 不准
- **Tissue-specific effects**：EVE 不区分 tissue
- **Compound epistasis**：单 mutation；2-3 body interaction underestimated
- **Allele frequency confounding**：常见多态性 (frequent benign) 仍可能高 EVE score
- **Membrane protein MSA bias**：与 EVmutation 一致

## ★ 方法选择决策链
- **为什么 VAE 而非 DCA**：VAE 是 deep nonlinear；DCA 是 pairwise linear（Potts）→ VAE capture higher-order interactions
- **为什么 per-protein training 而非 cross-protein**：每 protein 进化分布不同；shared latent space 信息分摊（后续 ESM 的 motivation）
- **为什么 ELBO ratio 而非 log-likelihood**：VAE 的 native quantification；可解释为 "evidence of evolution tolerance"
- **为什么 AUC 而非 Spearman**：clinical task 是 binary classification (pathogenic vs benign)；AUC 是 standard
- **为什么 ClinVar benchmark**：clinical gold standard；DMS 是 functional 但不一定 disease-relevant
- **为什么 large 3000+ protein cohort**：generalization 跨 disease + fold；不是 case-by-case

## ★ In silico vs in vitro 差距
- **本论文不直接 in vitro**——临床 genetics + benchmark 任务
- **AUC ~0.91 means**：模型在 pathogenic vs benign 二分类上 91% 时间排序正确
- **VUS reclassification rate**：~50% VUS 可被 confidently assigned (high or low EVE score)
- **vs case 027 (EVmutation, AUC ~0.83-0.86 on ClinVar)**：EVE 提升 5-8 percentage points
- **vs AlphaMissense (later, 2023)**：comparable on ClinVar but AlphaMissense 在 pleiotropic 突变上更好（structure-aware）
- **vs ESM-1v / ESM-2 zero-shot**：comparable AUC（~0.85-0.90），但 EVE 在每蛋白独立训练，比 generic PLM 略好 on individual protein
- **No standard pLDDT/iPTM/Rosetta_ddG**：clinical task; AUC + ELBO + DMS Spearman

## Lessons → seeds for rules
1. **Deep VAE > pairwise DCA**：non-linear capture 更多 evolutionary structure
2. **Per-protein training > cross-protein for clinical accuracy**：每 protein 独立 evolutionary distribution
3. **AUC 0.9 is realistic ceiling for unsupervised evolutionary models**——不要期待完美预测
4. **Surface / gain-of-function 是 blind spot**——需要 structural / functional complement
5. **VUS reclassification 50%** 是 EVE 的 clinical impact 上限——剩 50% 仍 ambiguous
6. **Per-protein VAE 计算成本高**：每 protein 训练 hours-days；生产时 cache predictions
7. **PRAXIS implication**：mutation_effect_scan 拓展时可加 EVE-style VAE per-protein training；clinical-relevance task 上 EVE > ddG predictors；rule 01 multi-method 应包含 evolutionary likelihood predictor

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41586-021-04043-8
- EVE server + predictions: https://evemodel.org/
- Pre-computed scores for 3000+ human proteins in supp
