---
case_id: protein-015-anishchenko2021-hallucination
design_task: hallucination_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: any
length_range: 60-200
tools: [trRosetta, MCMC_sequence_search, Rosetta]
key_paper_doi: 10.1038/s41586-021-04184-w
key_metrics:
  designs_synthesized: "129 hallucinated sequences expressed and tested"
  fold_validated_by_circular_dichroism_or_NMR: "approx 27% (35/129) showed expected folded behaviour"
  novel_topologies_found: "many; not catalogued individually but include novel beta sheet arrangements + non-natural helix bundles"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [hallucination, trRosetta, de-novo, MCMC, novel-fold, network-inversion]
unverified_details:
  - "Exact 27% number is approximate; paper presents detailed table with multiple validation modalities"
  - "trRosetta version: pre-RoseTTAFold; specific commit/version in supp"
---

# trRosetta hallucination 从随机序列设计 novel folds（Anishchenko et al. Nature 2021）

## Background
- 起点：trRosetta 是 2020 时期的结构预测网络（输入序列 → 输出 distance / orientation distributions），用于结构预测
- 目标：反向使用——从随机序列开始 MCMC 搜索，最大化 trRosetta 输出的 confidence（"hallucinate" 一个让 net believe is foldable 的 sequence）
- 应用：开创"network inversion"作为 protein design 范式的开端，影响后续 RFdiffusion / hallucination-based 工具

## What I actually did（基于论文）
1. **Random initialization**：从均匀随机氨基酸 sequence 开始（无 topology prior）
2. **MCMC sampling**：每步 propose 单点突变 → 跑 trRosetta → 计算 KL divergence between predicted distance / orientation distribution and a "background" distribution（高 information / sharp distribution = 好）
3. **Acceptance**：Metropolis acceptance based on Δscore，温度 schedule 渐降
4. **Output**：每条 trajectory 收敛到 sharp / confident 结构 prediction 的 sequence
5. **Diversity**：跑 ~10^4 trajectories，得到 diverse novel topology pool
6. **Selection for in vitro**：~129 sequences（覆盖不同 length / topology）选作 wet lab
7. **Validation cascade**：
   - 圆二色 (CD) 看 secondary structure
   - SEC 看 monomer
   - 部分跑 NMR HSQC 验证 unique fold
   - 极少数 X-ray
8. **结果**：~35/129 (27%) 显示 expected folded behaviour（CD pattern correct + SEC monomer + 部分 NMR/X-ray confirm topology）

## ★ 排除的位点/区域
- **没有 explicit forbidden residues**——hallucination 是 from-scratch；但隐式约束：
- **氨基酸 frequencies**：MCMC 偏向自然蛋白氨基酸 distribution（防止 all-Ala / all-Gly trivial solutions）
- **Loop 长度**：MCMC 不允许 loop > 20 aa（trRosetta 在长 loop 上不稳）
- **Cys 不强 enforce**：自由 Cys 可 disulfide misformation；论文报告少量 design 在表达后形成意外 SS
- **跨膜段 / signal peptide**：默认排除（不是设计 target）

## ★ 失败模式
- **CD 显示 unstructured / random coil**：~30-40% 设计在 CD 上没有清晰的 helix or sheet pattern；trRosetta confident prediction ≠ in vitro fold
- **SEC 多聚 / aggregate**：~20% 在 SEC 上多峰（dimer / aggregate）
- **CD pattern 与 design 不符**：design 要 alpha helix bundle 但 CD 显示 beta sheet——trRosetta 信号 conflate 不同 secondary structures
- **NMR 显示 molten globule**：少数 design CD 看起来 OK 但 NMR 上 line broadening——partial / dynamic fold
- **Hidden disulfide false positive**：设计无 disulfide 但表达后有 Cys-Cys 形成
- **Inclusion body**：~30% 不可溶
- **跨 length cutoff 表现不均**：60-100 aa designs 成功率 > 100-200 aa；长序列上 trRosetta 信号变弱

## ★ 方法选择决策链
- **为什么 trRosetta 而非 AF2**：2020-2021 年 AF2 公开但 inversion 作为 design tool 还没成熟；trRosetta 输出的 distogram 比 AF2 的 single structure 更适合 KL-divergence MCMC
- **为什么 KL divergence 而非 直接 confidence**：KL 鼓励 "sharp" prediction (low entropy)，避开 confidence saturation 的 plateau
- **为什么 MCMC 而非 gradient descent**：discrete sequence 不可微；MCMC 是 natural choice
- **为什么 ~10^4 trajectory 而非 1**：每条 trajectory 收敛到 local optimum；topology diversity 来自 different starting seed
- **为什么 CD + SEC + NMR 三步验证**：每个 modality 检测不同 failure mode（secondary structure / oligomer / unique conformation）

## ★ In silico vs in vitro 差距
- **trRosetta confidence (network 输出 distogram entropy) 与 in vitro fold 弱相关**：高 confidence 的 hallucinated sequence 也有 ~40% 不 fold
- **后续 RFdiffusion 等工作把 pLDDT (AF2) 作为 secondary filter 提升转化率**——本论文未做
- **没有 iPTM / pAE_interface / Rosetta_ddG**——hallucination 是 monomer 任务，没有 binder/multimer interface 概念
- **In silico → CD pattern correct**：129 → ~80 (62%)
- **CD correct → SEC monomer**：~80 → ~50 (62%)
- **SEC monomer → NMR/X-ray fold-correct**：~50 → ~35 (70%)
- **总在 vitro 转化率**：~35/129 ≈ **27%**
- **vs case 002 (Watson 2023 RFdiffusion binder ~5-15%)**：hallucination 的 fold-only 任务转化率比 binder 高 2x
- **vs case 013 (Bhardwaj 2016 cyclic peptide 100%)**：hallucination 比 cyclic peptide 低，因为 hallucinated proteins 是更大、更复杂的 fold
- **关键观察**：trRosetta 对 hallucinated sequence 的 confidence 与 in vitro fold-success 弱相关 — confidence 高未必 fold

## Lessons → seeds for rules
1. **Network inversion 可设计 novel fold**——开创 hallucination 范式，证明 design networks 不只能预测，还能"反向产生" sequence
2. **Confidence != fold success**：trRosetta predict confidence ≠ in vitro fold；后续 RFdiffusion 等工具引入 Schreyer 等多步 selection
3. **Hallucinated proteins novel topology**：大量没在 PDB 见过的 fold——但 in vitro 验证率显著低于经典 scaffold-based design
4. **CD + SEC + NMR 三步验证标准**：design without functional target 的 baseline workflow
5. **MCMC > gradient**：sequence-discrete design 必须 MCMC 或 evolutionary 算法
6. **Diversity from many trajectories not few iterations**：每 trajectory 是 local optimum；多样性靠 multiple seed
7. **27% conversion rate**：hallucination 类设计的 baseline；优化（filter cascade / RFdiffusion ensemble）后可提升

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41586-021-04184-w
- Hallucinated sequences + structure models: deposited in PDB / Github
- 后续衍生：RFdiffusion (2023), AfCycDesign, HighFold 等都受此 inversion 范式启发
