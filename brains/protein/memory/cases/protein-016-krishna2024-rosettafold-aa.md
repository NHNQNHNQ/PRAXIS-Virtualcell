---
case_id: protein-016-krishna2024-rosettafold-aa
design_task: all_atom_prediction
target_pdb: nan
target_uniprot: nan
fold_class: any
length_range: 30-1000
tools: [RoseTTAFold-AA, RFdiffusion-AA, ProteinMPNN, Chai-1_or_AF3_for_comparison]
key_paper_doi: 10.1126/science.adl2528
key_metrics:
  validation_targets: "predicted protein-ligand, protein-DNA, protein-RNA, protein-metal complexes"
  benchmark_PDBbind_DockQ: "approx 0.4 mean DockQ on protein-protein subset (improved over AF-Multimer baseline)"
  ligand_RMSD_top1: "approx 2 A on small molecule docking benchmark (PDBbind)"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [structure-prediction, all-atom, ligand-binding, RNA-DNA, RoseTTAFold, multi-modality]
unverified_details:
  - "DockQ + RMSD numbers are approximate from paper benchmarks; specific subset breakdown in supp"
  - "Comparison with AF3 / Chai-1 may not be fully apples-to-apples (different test sets)"
---

# RoseTTAFold All-Atom：蛋白 + 小分子 + 核酸 + 金属统一预测（Krishna et al. Science 2024）

## Background
- 起点：AF2 / RoseTTAFold 只预测蛋白；AF3 (2024) 是首个 unified all-atom 模型，但闭源；RoseTTAFold-AA 是开源的 all-atom 同期工作
- 目标：扩展 RoseTTAFold 到 all-atom（含小分子 ligand、DNA、RNA、metal cofactor）；同时支持 design（RFdiffusion-AA）
- 应用：drug-target 复合物预测（PRAXIS-Drug 上游）；enzyme + cofactor 设计；nucleotide-binding protein 设计

## What I actually did（基于论文）
1. **All-atom representation**：扩展 RoseTTAFold 的 graph representation，不仅蛋白 backbone + sidechain，还包括：
   - 小分子（SMILES → atom graph）
   - DNA / RNA（核苷酸基团）
   - 金属离子（点 + 配位 geometry）
2. **Training**：mixed dataset 包括 PDBbind (protein-ligand)、PDB protein-RNA、PDB protein-DNA、metalloprotein
3. **Inference**：multi-chain + ligand 输入 → 端到端结构预测
4. **Benchmarks**：
   - PDBbind 蛋白-小分子 docking RMSD
   - PDB-RNA 复合物 prediction
   - 金属配位 geometry
5. **Design extension (RFdiffusion-AA)**：扩展 RFdiffusion 让其在小分子 / DNA 周围 design protein backbone（"motif scaffolding around ligand"）
6. **Validation**：多个 benchmark 比 AF-Multimer / 早期 docking 工具好，比 AF3 略低（同期）

## ★ 排除的位点/区域
- **大型 ligand（> 100 atoms）**：训练数据稀疏；预测 unreliable
- **多 ligand 复合物（> 3 ligands）**：训练 cover 有限，预测稳定性差
- **罕见 metal 离子（Sn, Hg 等）**：训练数据不足；常见金属（Mg, Zn, Fe, Ca, Cu）预测好
- **修饰过的核酸（mRNA cap、N6-methyladenosine 等）**：训练时未充分覆盖
- **大型 RNA（> 200 nt）**：folding 自身已是 hard problem，protein-RNA 复合物预测 cascading errors
- **跨膜蛋白复合物**：lipid bilayer 未建模

## ★ 失败模式
- **小分子 binding pose RMSD > 4 Å**：~30% PDBbind 测试 case 在 top1 上不对；rescoring (top5) 可救约一半
- **金属配位 geometry 不准**：tetrahedral vs octahedral 偶尔混淆——尤其 transition metal
- **RNA secondary structure 错预测**：在 protein 周围的 RNA 长 hairpin / pseudoknot 易错
- **Multi-domain protein-protein 与 ligand 同时预测**：single-stage 推理时 protein-protein interface 与 ligand binding pose 互相干扰
- **训练 leakage**：同 protein-ligand pair 在 train + test set 出现过会 inflate metric——supp 报告 leakage-aware split 的 metric 较低
- **Confidence calibration**：pTM 在 ligand 上 less calibrated 比 在 protein 上

## ★ 方法选择决策链
- **为什么 RoseTTAFold 基础 + atom extension 而非 from scratch**：RoseTTAFold 的 SE3-equivariant transformer 已经是 SOTA； atom node 可加入而不重训
- **为什么 unified network 而非 stage-wise（先预测 protein 再 dock ligand）**：stage-wise 让 protein folding 不知 ligand 存在，错失 induced fit；unified 让 ligand inform protein conformation
- **为什么开源（vs AF3 闭源）**：AF3 weights 不开放；RoseTTAFold-AA 的开源是为了 community 使用 + design extension
- **为什么 RFdiffusion-AA 是 follow-up**：先要预测 (RoseTTAFold-AA)，再有反向设计 (RFdiffusion-AA)
- **为什么对 small mol / RNA 都同一 representation**：通用性；但确实在某些 modality 上不如 specialized models（如 RNA folding 上不如 RhoFold）

## ★ In silico vs in vitro 差距
- **本论文不直接做 in vitro**——是 prediction benchmark 论文，不是 design + experiment paper
- **Benchmark vs experimental ground truth (PDB structures)**：
  - 蛋白-小分子 docking RMSD ~2 Å (top1)
  - 蛋白-蛋白复合物 DockQ ~0.4 average + pLDDT > 80 on subset
  - 金属配位 geometry ~80% correct
  - iPTM 在 protein-protein subset 显示与 DockQ 中等相关；但 ligand-pTM less calibrated
  - ΔΔG metric 不直接 report（这是 prediction 论文非 design 论文）；Rosetta_ddG 在 follow-up RFdiffusion-AA 论文出现
  - SAP score 同样在 follow-up
- **比较 AF3 / Chai-1**：略低，但开源；后续 design 应用（RFdiffusion-AA）证实工程可用性
- **为后续设计设定 baseline**：用 RoseTTAFold-AA 预测 → RFdiffusion-AA 设计 → ProteinMPNN 序列 → 表达验证；类似 PRAXIS-Protein 的 binder pipeline + ligand awareness

## Lessons → seeds for rules
1. **Unified all-atom model > stage-wise**：ligand 影响 protein conformation 必须 jointly predict
2. **Open source vs closed**：AF3 weights 闭源限制 community 使用；RoseTTAFold-AA 开源激发更多 derivative work
3. **Multi-modality benchmark 必要**：蛋白-蛋白、蛋白-小分子、蛋白-RNA、蛋白-金属各自分开 metric，不能 conflate
4. **Confidence less calibrated on ligand**：pTM 在 ligand binding 上 less reliable 提示符号
5. **Leakage-aware split** 很重要：train-test 之间 ligand / protein 没共享才 fair
6. **PRAXIS 启发**：predict_complex skill 应当在 future 拓展到 ligand / cofactor（目前只支持 protein-protein）；wire RFdiffusion-AA 作为 alt backbone
7. **AF3 comparison disclaimer**：当前 PRAXIS predict_complex 目录有 Boltz-1 + Chai-1 (AF3-equivalent)；RoseTTAFold-AA 是另一选项，可在 rule 01 multi-model consensus 中加入

## 数据指针
- 论文 + supp: https://doi.org/10.1126/science.adl2528
- 代码 + 模型 weights: https://github.com/baker-laboratory/RoseTTAFold-All-Atom
- RFdiffusion-AA 后续 paper: separate publication
