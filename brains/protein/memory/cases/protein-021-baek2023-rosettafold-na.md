---
case_id: protein-021-baek2023-rosettafold-na
design_task: complex_prediction
target_pdb: 7SVU                # CASP15 RNA target H1057, an RBP-RNA complex used in benchmark
target_uniprot: nan             # benchmark across many proteins, no single-target focus
fold_class: any
length_range: 30-500
tools: [RoseTTAFoldNA, RoseTTAFold, AlphaFold2_for_comparison, NMR, X-ray]
key_paper_doi: 10.1038/s41592-023-02086-5
key_metrics:
  benchmark_protein_RNA_DockQ_mean: "approx 0.4-0.5 on protein-RNA complex test set"
  benchmark_protein_DNA_DockQ_mean: "approx 0.5-0.6 on protein-DNA test"
  RNA_only_RMSD_top1: "approx 4-6 A on small RNA structure prediction"
  improved_over_AF2_unsuitable_for_NA: "AF2 not designed for NA — RFNA is significantly better on protein-NA mixed complexes"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [structure-prediction, protein-RNA, protein-DNA, RoseTTAFold, multi-modality, nucleic-acid]
unverified_details:
  - "Specific DockQ + RMSD ranges are approximate from paper benchmarks"
  - "Comparison with AF2 limited because AF2 was not trained on NA — unfair direct comparison"
---

# RoseTTAFoldNA：蛋白-核酸复合物预测（Baek et al. Nature Methods 2023）

## Background
- 起点：AF2 / RoseTTAFold 在蛋白上 SOTA，但都不是为 nucleic acid 设计
- 目标：扩展 RoseTTAFold 框架到 protein-DNA + protein-RNA + RNA-only 结构预测
- 应用：是 PRAXIS 在 nucleic acid binding protein design 中的关键能力前置——CRISPR Cas9, transcription factors, RNA-binding proteins 等

## What I actually did（基于论文）
1. **Architecture**：扩展 RoseTTAFold 的 SE3-equivariant transformer，加 nucleotide embedding（A/T/G/C/U + nucleotide bond geometry）
2. **Training data**：mixed dataset：
   - PDB protein-RNA complexes
   - PDB protein-DNA complexes
   - Pure RNA structures (SARS-CoV-2 RNA elements, ribozymes, etc.)
3. **Inference**：multi-chain 输入，protein 和 NA chain 都 token 化
4. **Benchmarks**：
   - Protein-RNA: CASP15 RNA targets + selected PDB
   - Protein-DNA: TF-DNA binding + chromatin-related complexes
   - RNA-only: small RNA structures (< 100 nt)
5. **Validation**：DockQ score for complexes，RMSD for RNA-only structures

## ★ 排除的位点/区域
- **大型 RNA (> 200 nt)**：训练 cover 有限；RNA folding 自身已是 hard，protein 周围长 RNA 累积错
- **Modified RNA bases (mRNA cap, m6A, pseudouridine)**：训练数据稀疏
- **DNA 偏 unusual structures (G-quadruplex, i-motif, Z-DNA)**：训练 cover 有限
- **Large RNP machines (ribosome, spliceosome)**：训练数据 PDB 中比例小
- **跨膜蛋白 + NA 复合物**：lipid environment 未建模
- **Multi-domain protein 上 multi-chain NA**：multi-domain RNA-binding 经常 cascading errors

## ★ 失败模式
- **DockQ 在 transient complexes 较低** (< 0.3)：低 affinity / dynamic protein-RNA 接触在 single-shot prediction 中难
- **RNA secondary structure 错预测**：在 protein 周围的 hairpin / pseudoknot 复杂；模型偏向 simpler base pairing
- **Large RNA RMSD > 10 Å**：长 RNA 预测累积错误
- **Confidence 在 NA 上 less calibrated**：pTM 在 NA-only 上 less reliable 比 protein
- **训练 leakage**：同 PDB family（RNA-binding domain 系列）在 train + test 出现 inflate metric
- **AF2 比对不公**：AF2 没在 NA 上训练；直接 compare 不 fair——RFNA 显著好但是 expected

## ★ 方法选择决策链
- **为什么扩 RoseTTAFold 而非全新架构**：SE3-equivariant transformer 已经 well-suited for graph-like biomolecules；只需加 NA atom node
- **为什么开源 (RFNA) vs 闭源 (AF3)**：RFNA 是 community 工具；AF3 weights 后来发布但限制 usage
- **为什么 mixed protein + RNA + DNA training**：单 modality model 在跨 modality 任务上失败
- **为什么 DockQ 是主要 metric for complexes**：DockQ 是 protein-protein docking 标准；扩到 protein-NA 是社区惯例
- **为什么不做 design (RFdiffusion-NA 是后续 work)**：本论文 focus on prediction；design 在 RFdiffusion-AA / NA 才扩展

## ★ In silico vs in vitro 差距
- **本论文是 prediction benchmark 论文，no in vitro data**
- **Protein-RNA DockQ ~0.4-0.5 mean**（acceptable threshold ~0.4 = "acceptable"，~0.5+ = "medium"，~0.7+ = "high"）
- **Protein-DNA 略高 (~0.5-0.6)**：DNA structure 比 RNA 简单
- **RNA-only RMSD ~4-6 Å**：RNA structure prediction 仍是 hard problem，比 protein folding 难
- **No standard pLDDT / iPTM / Rosetta_ddG**：本论文用 DockQ + RMSD + per-residue confidence
- **vs AF3 (Krishna 2024 RoseTTAFold-AA)**：AF3 在 NA 上训练更多，metric 略好，但 RFNA 是开源 baseline

## Lessons → seeds for rules
1. **Mixed modality training necessary**：单 modality 在跨 modality 任务上失败
2. **Protein-NA prediction 仍弱于 protein-only**：DockQ 0.4-0.5 vs protein-protein 0.7+
3. **Confidence less calibrated on NA**：pTM 在 NA 任务上 less reliable
4. **RNA secondary structure 预测不准** 是核心 bottleneck
5. **Modified RNA bases (m6A, cap) 缺训练数据**：未能预测
6. **AF2 on NA tasks 不公**：AF2 没在 NA 上训练
7. **PRAXIS implication**：predict_complex 拓展时要有 NA-aware variant；Boltz/Chai/AF3 在新 release 后会带来更准的 NA 复合物预测；当前 AF2 path 不适用 NA target

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41592-023-02000-z
- 代码 + 模型 weights: https://github.com/uw-ipd/RoseTTAFold2NA
- 后续 RFdiffusion-NA design tool: 同组 follow-up
