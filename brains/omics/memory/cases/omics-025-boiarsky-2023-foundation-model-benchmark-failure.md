---
case_id: omics-025-boiarsky-2023-foundation-model-benchmark-failure
schema_version: 1
modality: scRNA_seq
study: "Boiarsky et al 2023, A deep dive into single-cell RNA sequencing foundation models"
public_accession: "(meta-analysis: scIB-bench + custom held-out cohorts vs Geneformer / scGPT / scFoundation)"
doi: 10.1101/2023.10.19.563100
organism: "Homo sapiens / Mus musculus (held-out test sets across both)"
tissue: "multi-tissue (immune / pancreas / lung / brain — held-out)"
study_design: meta_analysis_failure
assay_subtype: foundation_model_benchmark
cell_type_focus: [cross_tissue_failure_review, cell_type_classification, zero_shot_embedding]
tools: [Geneformer 30M, scGPT, scFoundation, scIB benchmark, sklearn baselines, PCA + logistic regression, Harmony]
method_choice: [foundation_model_critique, simple_baselines, domain_shift_evaluation, zero_shot_vs_finetune]
status: validated
validated: true
source: praxis_seed
case_class: failure_landscape
provenance:
  source_type: literature_failure_review
  doi: 10.1101/2023.10.19.563100
  extracted_at: 2026-05-01
tags: [failure_case, foundation_model, benchmark, zero_shot_failure, anti_pattern, fm_critique]
---

# Boiarsky 2023：scRNA foundation models 的"皇帝新衣"——基准评测的系统性失败

## Background
Boiarsky 等系统比较了 Geneformer / scGPT / scFoundation 等 2023 SOTA foundation model 与**简单 baseline (PCA + logistic regression / Harmony + KNN)** 在**held-out** 任务（cell type classification, batch correction, perturbation prediction）上的表现。**核心发现震撼整个 FM 社区**：很多场景下简单 baseline 与 FM 持平或更好；FM 在 domain shift（不同实验室 / 疾病状态 / 物种）下 zero-shot 性能崩塌。这是 case-based learning 中最重要的当代反面典型，直接对 case 023 (Geneformer success) 形成 counter-balance。

## What this paper actually did (and why it shocked the field)
1. 用 **scIB benchmark** + 自建 held-out 数据集（不同 lab / disease / cell line）
2. 对比 Geneformer / scGPT / scFoundation 各 mode：
   - **Zero-shot embedding** vs **PCA + Harmony**
   - **Fine-tune classifier** vs **logistic regression on PCA**
   - **In-silico KO / perturbation prediction** vs random
3. **关键发现**：
   - **Cell type classification F1**: PCA + LR 在 immune cell type 上达到 0.85；Geneformer fine-tune 0.83；zero-shot 0.71 → **复杂 FM 不一定打过 sklearn baseline**
   - **Domain shift**: 训练在 healthy donor，测试在 disease patient → FM zero-shot 性能 **drop 15-25%**；baseline drop ~5-10%
   - **跨物种 (human pretrain → mouse test)**: FM zero-shot 几乎与 random 持平（drop > 30%）
   - **Cell type embedding distance**: 多数 FM 不严格遵循 ontology 距离（CD4 与 dendritic cell 距离 < CD4 与 CD8 在某些 task）
   - **Perturbation prediction**: 当 perturbation 在 pretrain 未见过 → FM 预测与 random 不可区分
   - **Fine-tune 小数据 (< 1k cells/class)**: FM **inferior** 到 from-scratch baseline（catastrophic interference + 过拟合）

## ★ 排除/不做的事 (反面教材)
- **拿 FM zero-shot embedding 当 ground truth 做 cell type 注释**：在 disease/罕见 state 上直接错；至少 baseline + manual marker 双 verify
- **不做 baseline 对比直接发表 FM 应用 paper**：reviewer 标准已升级，要求 simple PCA + LR / Harmony 作为 floor baseline
- **跨物种 zero-shot 写 paper**：比 random baseline 难强，结果几乎肯定 unreliable
- **小队列 (< 1k cells/class) 上 fine-tune**：from-scratch baseline 通常更好；FM 的优势在大数据集
- **In-silico perturbation 当 mechanism 验证**：当 perturbation 不在 pretrain corpus 中，prediction 和 random 不可区分；wet-lab 仍然必须
- **Pretrain corpus check 跳过**：你 query 的 cell type / disease 状态如果不在 pretrain 中，zero-shot 信号是 hallucination
- **拿 single benchmark 的 leaderboard 当生产决策依据**：scGPT 在 immune benchmark 第一不代表 disease-specific task 也强

## ★ 失败模式 (论文记录的)
- **Cell line vs primary tissue 域偏移**：cancer cell line dominate 部分 pretrain corpora → primary tissue zero-shot 偏 cell-line-like state
- **Disease state under-represent**：罕见 disease (rare cancer subtype, autoimmune subtype) zero-shot embedding 集中到最近 healthy state，掩盖 disease signal
- **Embedding 不严格 ontology-faithful**：相同 cell type 跨 dataset 距离大于不同 cell type 内 distance（同 lab effect 主导）
- **Fine-tune metric overfit**：dev/test 按 cell split 而非 donor split，metric 虚高 10-20%
- **In-silico KO false negative on lethal genes**：如果 KO 基因不在 cell 的 top-2048 token，embedding shift = 0，看似"无 effect"实为 detection failure
- **Cross-batch dataset zero-shot drift**：相同 cell type 的 embedding 在不同 lab 数据集上差距 ≥ 不同 cell type 的差距
- **Pre-print → published 的 reanalysis 发现**：Geneformer 原 paper 的 cardiomyocyte regeneration KO prediction 部分 reanalysis 显示 effect size inflate（Boiarsky 等独立验证 1/3 prediction 不能复现）

## ★ 方法选择决策链 (Boiarsky 给出的)
```
准备用 foundation model?
├─ Step 1：先跑 baseline (PCA + LR + Harmony) 作为 floor
│   └─ 若 baseline 已 F1 > 0.85，FM 改善 < 3% 时不值
├─ Step 2：检查任务 vs pretrain 重合
│   ├─ Cell type / state 在 pretrain corpus 中表征 ≥ 1k cells → OK
│   ├─ 在 pretrain 中 < 100 cells → 高风险，必须 fine-tune adapter
│   └─ 完全未见 (rare disease, novel cell line) → FM 无优势
├─ Step 3：domain shift 检查
│   ├─ Same lab + same protocol → FM zero-shot 通常 OK
│   ├─ Cross lab → 需要 fine-tune
│   └─ Cross species → 必须 adapter / re-pretrain
├─ Step 4：split 严格度
│   ├─ Cell-level split → metric 不可信
│   ├─ Donor-level split → 标准
│   └─ Lab-level split (LOPO) → 最严格，揭示真泛化
└─ Step 5：报 baseline + FM 双 metric
    └─ 任何论文 / 报告都该 side-by-side
```

## ★ QC sanity check (known answer)
- Anchor (Boiarsky 2023 benchmarks)：
  - **PCA + Harmony + LR** 作为 floor，cell type F1 在 immune scIB benchmark > 0.80
  - **FM 必须 ≥ baseline + 3%** 才被视为有意义提升
  - **Domain shift drop**: FM zero-shot drop ≤ 15% 才合格；> 25% 视为 unsuitable
  - **Donor-split (not cell-split) F1** 应作 reportable metric；cell-split metric 视为 leakage
  - **Cross-species zero-shot < random baseline** → 必须用 adapter
- Pass criterion: FM > baseline by ≥ 3% F1 on the SPECIFIC user task + donor-split + domain-checked
- Fail criterion: FM ≈ baseline OR domain shift drop > 25% → 直接走 baseline pipeline，FM 没价值

## Lessons → seeds for rules
1. **Foundation model 必须 baseline + FM 双对比报告**（rule 23 候选 → 暂归 rule 11 anti-rule）— 单跑 FM 不可信
2. **Pretrain corpus check** 是 first sanity：不在 pretrain corpus 的 cell type / disease state，zero-shot 信号是 hallucination
3. **Donor-split 不 cell-split**（rule 23 候选）：cell-split metric overfit 10-20%
4. **Cross-species zero-shot 几乎一定不可信**：必须 adapter fine-tune
5. **Small data fine-tune 反而 inferior to from-scratch**：FM 的优势在大数据集；< 1k cells/class 别用
6. **In-silico perturbation 是 hypothesis 不是 mechanism**：wet-lab 验证仍然必须（与 case 023 一致）
7. **重要补充对 case 023**：Geneformer success 不是 universal — 适用窗口窄；任何 FM 应用必须先 baseline check
