---
case_id: immuno-002-mhcii-long-peptide
schema_version: 1
task: mhc_class_ii_epitope_prediction
immuno_task: mhc_class_ii_epitope_prediction
antigen_class: bacterial
hla_class: HLA_II
hla_alleles: ["HLA-DRB1*15:01"]
peptide_length_bin: "13-15"
disease_indication: infection_tb
target_protein: M.tuberculosis Antigen 85B (P0A4V4)
target_protein_uniprot: ["P0A4V4"]
target_hla: HLA-DRB1*15:01 (DR2 representative)
peptide_length: 13-25 aa (variable)
tools: [NetMHCIIpan-4.3, MARIA, MixMHC2pred, MHCflurry-II, IEDB Tepitope]
key_paper_doi: 10.1093/nar/gkad380
status: validated
source: praxis_seed
---

# MHC-II epitope：长肽 + open binding cleft 难题

## Background
MHC class II（HLA-DR/DP/DQ）激活 CD4 T cell；表位 13-25 aa（vs class I 8-11）+ binding cleft 两端 open，core 9-mer 的位置不固定。**预测难度远超 class I**——register prediction（哪 9 aa 是 core）+ flanking 影响双重不确定。

## What I actually did
1. **Input**：Ag85B 序列 → sliding 15-mer (typical class II peptide length)
2. **NetMHCIIpan-4.3 跑**：每 15-mer × DRB1*15:01 → EL_rank + core_offset 预测
3. **Core 9-mer 识别**：每 15-mer 有 11 个可能 9-mer core，predictor 挑最 likely register
4. **Flanking residue 影响**：core 9-mer 外的 flanking aa 影响 binding；不在 score 但决定 immunogenicity
5. **MARIA / MixMHC2pred 平行**：deep learning 替代，跨 method consensus
6. **HLA-DR/DP/DQ 三 class 都查**：vaccine target 应跨多 class
7. **Promiscuous epitope**：能 bind 多个 HLA (≥ 3 个 alleles strong binding) → vaccine 优先候选
8. **Output**：top 10 promiscuous + per-HLA top 5

## ★ 排除/不做的事
- **当 class I 跑**：长 peptide + flexible register 完全不同 prediction problem
- **Single HLA-DR**：DP/DQ 也重要，覆盖完整 CD4 response
- **Core register 信任 single predictor**：NetMHCIIpan / MARIA / MixMHC2pred register prediction 经常不一致
- **Flanking residue 完全 ignore**：±2 aa 周围 aa 对 immunogenicity 影响 ~30%
- **15-mer 一刀切**：不同 length 的 same core peptide 可能 register 不同 → length-grid 评估
- **Promiscuous 不 filter human**：跨 multiple HLA bind = autoimmune 风险

## ★ 失败模式
- **Register ambiguity**：多个等可能 core，prediction 不确定
- **HLA-DQ 数据稀少**：DR 训练数据多，DQ predictor 准度低
- **Linker / flanking 经常错**：影响 affinity 预测
- **Cross-reactivity HLA-DR vs HLA-DRB3/4/5**：beta chain copy 可能 cross-bind
- **Asparagine deamidation 影响**：peptide aging in vivo 改变 affinity
- **Tissue-specific HLA expression**：epitope 预测假设 HLA 表达，实际 tissue dependent

## Lessons → seeds for rules
1. **NetMHCIIpan + MARIA + MixMHC2pred ≥ 2 consensus**
2. **HLA-DR/DP/DQ 三 class 都查**
3. **Core register multi-method 投票**
4. **Length grid**（13/15/18/21）评估
5. **Promiscuous epitope 优先 vaccine**（≥ 3 HLA SB）
6. **Self cross-reactivity check**（vs human proteome）
