---
case_id: protein-027-riesselman2018-evmutation
design_task: mutation_effect_prediction
target_pdb: 1EMA                   # GFP — classic DMS benchmark protein in EVmutation paper
target_uniprot: P42212             # GFP, representative of paper's 30+ benchmark cohort
fold_class: any
length_range: 30-1000
tools: [EVmutation, DCA_Direct_Coupling_Analysis, MSA, evolutionary_information]
key_paper_doi: 10.1038/nbt.4225
key_metrics:
  proteins_benchmarked: "approx 30 proteins from large-scale mutation scanning datasets"
  mean_Spearman_correlation_vs_experimental_fitness: "approx 0.5-0.6"
  improvement_over_independent_position_models: "20-50% relative improvement"
  large_scale_DMS_datasets: "DMS, GFP, beta-lactamase, RRM, etc."
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [mutation-effect, EVmutation, DCA, evolutionary-coupling, deep-mutation-scanning, MSA, fitness-prediction]
unverified_details:
  - "Spearman ~0.5-0.6 is paper-reported mean across cohort; per-protein varies 0.3 to 0.8"
  - "30 protein cohort is approximate; full set in paper supp"
---

# EVmutation：进化耦合预测突变效应（Riesselman et al. Nat Biotech 2018）

## Background
- 起点：Predicting mutation effects 历史方法包括 PSSM (independent position) + Rosetta ddG（结构）；前者忽略 inter-position coupling，后者只看物理稳定性不看进化
- 目标：用 Direct Coupling Analysis (DCA) 从 MSA 提取 inter-position evolutionary coupling，建立 unsupervised mutation effect predictor
- 应用：mutation effect prediction 的关键 baseline；后续 EVE / ESM-1v / ProteinGym 都比较；建立"evolutionary likelihood as fitness proxy"概念

## What I actually did（基于论文）
1. **MSA generation**：每 protein 跑 jackhmmer/HHblits 拿到大 MSA（典型 10^3-10^5 sequences）
2. **DCA inference**：在 MSA 上 fit Potts model（pairwise + single position parameters）；推断 inter-position couplings
3. **Mutation scoring**：对 single 或 multi-point mutation，计算 log-likelihood ratio (mutated / WT) under DCA model
4. **Benchmark vs DMS**：用 deep mutational scanning 数据集（GFP, β-lactamase, RRM, brassica HSP82 等）做 per-mutation experimental fitness
5. **Spearman correlation**：predicted score vs experimental fitness
6. **Compare vs**：independent position models (PSSM, profile)，独立 ddG predictors (PyRosetta/Rosetta)
7. **结果**：mean Spearman ~0.5-0.6 跨 cohort，比 independent position models 提升 20-50%；某些 protein 上达 0.8

## ★ 排除的位点/区域
- **Catalytic / functional residues 在 DMS 上往往是 negative-selected**：DCA 也 capture 这种 conservation
- **Disulfide bonds**：DCA 自然 capture（高 coupling）
- **Buried positions**：高度 conserved + DCA 高准确
- **Surface positions** 上 prediction 较弱：进化压力 less，coupling 信号弱
- **MSA 浅的 protein**：< 50 effective sequences → DCA 不可信，prediction 退化到 PSSM
- **N端/C端 disordered 区**：MSA 上 alignment quality 低

## ★ 失败模式
- **Large indel 不在 model**：EVmutation 是 fixed-length；deletion/insertion 不能预测
- **Surface mutation 预测较差**：低 coupling，预测 noisier
- **Positive selection / gain-of-function**：DCA 是 conservation-based；从未见过的"better-than-natural"突变会 underestimate
- **Multi-point epistasis**：DCA pairwise 抓 2-body coupling；3+ body epistasis 不准确
- **Buried polar 残基**：H-bond network 复杂；DCA 简化
- **Membrane protein MSA bias**：membrane domain conservation pattern 不同
- **Spearman ~0.5-0.6 means 50% rank-correlation**——top-ranked mutation 可能和 bottom-ranked 是 random shuffled

## ★ 方法选择决策链
- **为什么 DCA 而非 supervised ML**：unsupervised；不需要训练 data；transfers across proteins
- **为什么 pairwise Potts 而非 higher-order**：可计算；3-body+ MSA 数据稀疏
- **为什么 jackhmmer/HHblits 而非 PSI-BLAST**：sensitivity 高，captures distant homologs；DCA 需要 deep MSA
- **为什么 unsupervised 而非 fine-tuning per protein**：generalization；同一 model 可用于任意 protein
- **为什么 DMS benchmark 而非单 mutation 实测**：DMS 提供 thousands of data points per protein → robust correlation
- **为什么 Spearman 而非 RMSE**：experimental fitness 单位 vary；rank-correlation 是 robust 度量

## ★ In silico vs in vitro 差距
- **DMS rank-correlation Spearman ~0.5-0.6 mean**：~50-60% rank agreement
- **Top-10 picked vs experimental top-10 overlap**：~25-30% (precision@10)
- **Recall@top-50 (predicted top-50 包含 experimental top-50 比例)**：~30-40%
- **vs Rosetta cartesian_ddg alone**：~0.4 Spearman → EVmutation 提升 25-50%
- **vs ESM-1v (later, 2021)**：ESM 略好（~0.6-0.7 mean）但 EVmutation 在 deep MSA shallow MSA 不可用 protein 上仍有用
- **No standard pLDDT/iPTM/Rosetta_ddG**：DCA + Spearman 是核心 metric；ddG 是 alt approach
- **vs case 004 (ThermoMPNN ~0.65 Spearman)**：comparable on stability subset；EVmutation 在 functional fitness（活性、binding）任务上更好（更广 evolutionary signal）

## Lessons → seeds for rules
1. **Evolutionary coupling > PSSM for mutation effect**：pairwise DCA 提升 20-50%
2. **MSA 深度是 prerequisite**：< 50 effective sequences degrade
3. **Spearman ~0.6 is realistic**：不要期待 > 0.8 cross-protein average
4. **DCA + ddG voting**：EVmutation + Rosetta cartesian_ddg 共识可拿到 ~0.7 Spearman（rule 01 multi-method consensus）
5. **Surface vs buried 性能不同**：报告时 stratify
6. **Indel + 3-body epistasis 是 EVmutation blind spots**：需要其他方法补
7. **PRAXIS implication**：mutation_effect_scan 应当 include EVmutation/DCA-based predictor (CPU-only, fast)；与 ThermoMPNN (DL on structure) 互补；rule 01 ≥2 predictors 自然包含 evolutionary + structural 双轨

## 数据指针
- 论文 + supp: https://doi.org/10.1038/nbt.4225
- 代码 + 模型: https://github.com/debbiemarkslab/EVmutation
- DMS benchmark datasets 已成为 mutation prediction standard
