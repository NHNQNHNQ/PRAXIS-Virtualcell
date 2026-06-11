---
case_id: immuno-001-mhci-netmhcpan
schema_version: 1
task: mhc_class_i_epitope_prediction
immuno_task: mhc_class_i_epitope_prediction
antigen_class: viral
hla_class: HLA_I
hla_alleles: ["HLA-A*02:01"]
peptide_length_bin: "9"
disease_indication: infection_sars_cov_2
target_protein: SARS-CoV-2 Spike (P0DTC2)
target_protein_uniprot: ["P0DTC2"]
target_hla: HLA-A*02:01
peptide_length: 9-mer (canonical class I)
tools: [NetMHCpan-4.1, MHCflurry-2, BigMHC, NetMHCstabpan, IEDB tools]
key_paper_doi: 10.4049/jimmunol.2000133
status: validated
source: praxis_seed
---

# MHC-I 9-mer epitope 预测：NetMHCpan + multi-method consensus

## Background
MHC class I 表位预测是 vaccine design / neoantigen 识别基础。NetMHCpan-4.1 是行业 baseline；MHCflurry-2 (open-source) + BigMHC (大模型) 是补充。**单方法 false discovery rate 高**，consensus 是临床推荐做法。

## What I actually did
1. **Input**：Spike protein 序列（1273 aa）切 9-mer sliding window → 1265 个候选 peptide
2. **NetMHCpan-4.1 跑**：每 peptide × HLA-A*02:01 → 输出 EL_rank (eluted ligand rank) + IC50
3. **Filter**：EL_rank ≤ 2.0（"strong binder"）+ IC50 ≤ 500 nM
4. **MHCflurry-2 平行**：per-allele model + presentation model → presentation score
5. **BigMHC**：transformer 大模型，PLM-based representation
6. **Consensus**：3 方法都 SB（strong binder）= high confidence；2/3 SB = medium
7. **NetMHCstabpan**：peptide-MHC 复合物 stability prediction，与 immunogenicity 相关
8. **IEDB cross-reference**：known SARS-CoV-2 epitopes 比对，验证 pipeline 召回 known
9. **Output**：top 20 epitope ranked by composite score + 已知 vs 新发现 标签

## ★ 排除/不做的事
- **单 method 给 final list**：NetMHCpan / MHCflurry / BigMHC 互不完全一致；single-method false call ~30%
- **不分 EL vs BA score**：EL (eluted ligand) trained on MS data 更接近 in vivo presentation；BA (binding affinity) 是体外 assay，预测 immunogenicity 弱
- **IC50 cutoff 太严**（< 50 nM）：错过 medium binder 但实际 immunogenic
- **Length 不限 9-mer**：class I 主要 8-11，9-mer 占多数；跨 length 一起 rank 不准
- **Population coverage 不评估**：单 HLA prediction 是少数群体；多 HLA 才有 vaccine 价值
- **Stability 不查**：高 binding 但 unstable peptide-MHC 不 immunogenic

## ★ 失败模式
- **HLA allele not in training data**：少见 HLA（如非洲特异 HLA-B*15:03）predictor 不准
- **Anchor residue convention error**：HLA-A*02:01 anchor at P2 (Leu) + P9 (Val/Leu)；anchor wrong score 高但实际不 bind
- **Glycosylated / phospho peptide**：modification 不在 model；in vivo 这些 peptide 数量少
- **Non-canonical length (8 / 11+)**：preditor 在长 peptide 上准度下降
- **Cross-reactive epitope**：peptide 在 multiple proteins 出现 → 自身免疫风险
- **Processing-dependent**：peptide proteasome 切割效率低 → high binder but 不 present；NetChop 评估 processing

## Lessons → seeds for rules
1. **Multi-method consensus 强制**（NetMHCpan + MHCflurry + BigMHC at least 2/3）
2. **EL_rank > BA score**：MS-trained 更准
3. **Length 分开 rank**：8/9/10/11 mer 分组
4. **Stability 必查**（NetMHCstabpan）
5. **Population coverage**：multi-HLA 评估
6. **Self-cross-reactivity**：vs human proteome BLAST 必步
7. **Processing prediction**（NetChop）补充
