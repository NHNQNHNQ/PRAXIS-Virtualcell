---
case_id: protein-018-bennett2023-deep-learning-binder-filter
design_task: de_novo_binder
target_pdb: 7K9I
target_uniprot: Q9NZQ7
fold_class: mini_protein_helical
length_range: 60-100
tools: [RFdiffusion, ProteinMPNN, AlphaFold2_initial_guess, ESMFold, PyRosetta]
key_paper_doi: 10.1038/s41467-023-38328-5
key_metrics:
  designs_screened: "thousands per target across 13 targets"
  in_silico_to_in_vitro_success_rate: "approx 6-23% across targets (vs 1-2% pre-DL filter)"
  best_KD_top: "single-digit nM on multiple targets (PD-L1, IL-7Rα, etc.)"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [binder, mini-protein, RFdiffusion, AF2-initial-guess, deep-learning-filter, multi-target]
unverified_details:
  - "Targets list paraphrased; full set in supp Table"
  - "Specific KD numbers vary by target; quoted single-digit nM is paper-claimed"
---

# Improving binder design with deep learning filters（Bennett et al. Nature Comm 2023）

## Background
- 起点：Watson 2023 RFdiffusion 论文（PRAXIS protein-002）建立了 RFdiff + MPNN + AF2 binder pipeline，但 in vitro 成功率 5-15%，多数 target 还在 1-2% 区间
- 目标：用 AF2 with initial guess 作为 in silico filter，对 RFdiffusion + ProteinMPNN 输出做 prediction-based 排序；提高 in vitro 转化率
- 应用：是 mini-binder 设计 SOTA pipeline 的核心 reference；后续多个工具继承这条 filter cascade

## What I actually did（基于论文）
1. **Targets**：13 个不同蛋白 target（包括 PD-L1, IL-7Rα, FGFR2, INSR, TrkA, TrkB, EGFR, IL-23R 等），每个 target 跑独立 pipeline
2. **RFdiffusion**：每 target ~1000-10000 backbone（视 target 难度）
3. **ProteinMPNN**：每 backbone 8 sequences，温度 0.1
4. **AF2 with initial guess**：把 RFdiff backbone 输入 AF2 作为 initial template hint，跑 monomer + multimer
5. **DL filter cascade**：
   - pLDDT_binder mean ≥ 80
   - pAE_interaction (interface PAE) ≤ 10
   - iPTM ≥ 0.6（multimer）
   - RMSD_initial_guess vs AF2 prediction < 1 Å（设计被 AF2 confirm 是同一 fold）
   - ProteinMPNN sequence recovery > 30%
6. **Top selection**：每 target 选 top 50-100 进 in vitro 实测
7. **Wet lab**：基因合成 → E.coli 表达 → SEC monomer → BLI 测亲和 → top hits 做 cryo-EM
8. **结果**：
   - Pipeline 平均 in vitro 转化率 6-23%（vs 老 pipeline 1-2%）
   - 多个 target 拿到 single-digit nM binder
   - Cryo-EM 验证多个设计 epitope 与设计意图一致

## ★ 排除的位点/区域
- **未 specified hotspot**：每 target 都明确手 / 文献定义 PPI hotspot 输入到 RFdiffusion ppi.hotspot_res
- **跨膜段 / 信号肽**：13 个 target 都用 ECD（去除 TM domain + signal peptide）
- **糖基化位点 + glycan**：避开（AF2 默认不建模糖基）
- **Disulfide bonds**：多数 target 含 disulfide，binder 设计中标 forbidden 不动 target SS
- **Conformational state mismatch**：apo-only 设计的 binder 常常和 holo 状态冲突——optimal 是 holo / pre-bound 状态作 RFdiff input

## ★ 失败模式
- **In silico 通过 → SEC 多聚** 仍然是主要 failure（~30%）
- **iPTM > 0.7 但实测亲和 > 1 μM**：~30% high-iPTM design 在 BLI 没结合或弱结合——AF2 false positive 仍然存在
- **目标间转化率差异大**：FGFR2, IL-23R 等 target 上 23%；EGFR 等仍 < 10%——target-specific 难度
- **Initial guess RMSD 严苛 filter 削弱多样性**：< 1 Å filter 砍掉 ~50% 候选；论文经验 1-1.5 Å 是 sweet spot
- **跨 paralog specificity 仍未解决**：未做 negative design 时 binder 可能交叉结合 PD-L2 / IL-7Rβ 等同源蛋白
- **In vitro confirmed binder → cellular function**：论文中 cellular activity 实验有限；多数 stop at biophysical binding

## ★ 方法选择决策链
- **为什么 AF2 with initial guess 而非 plain AF2**：plain AF2 from sequence 在 de novo binder 上 confidence 低；initial guess 把 RFdiff backbone 作为 strong prior
- **为什么 RMSD_initial_guess 是 filter 关键**：如果 AF2 把 backbone 推回到 RFdiff 设计的 fold，说明 sequence design 真的 encode 了 backbone；否则可能 fold 到 something else
- **为什么 5-metric joint filter 而非单 iPTM**：单 iPTM 假阳率高；joint 严苛但提高 in vitro hit rate 5-10x
- **为什么 13 个 target 而非更深一个 target**：generalization 验证——证明 pipeline 不是 target-specific
- **为什么不显式做 negative design**：deferred；本论文专注 binder positive；specificity 是 follow-up
- **为什么 ESMFold 也用**：作为快速 confidence check，比 AF2 快 10x；但 final ranking 还是 AF2

## ★ In silico vs in vitro 差距
- **跨 13 targets 平均 in vitro 转化率**：6-23%（依赖 target；mean ~12%）
- **vs case 002 (Watson 2023 PD-L1 5-15%)**：本论文上探到 23% 是 SOTA
- **vs case 011 (Cao 2020 LCB ~1%)**：DL filter 显著提高了 mini-binder 命中率
- **关键 driver**：AF2 initial guess 配合 RMSD filter 是核心
- **未解决**：~80% 通过 in silico filter 仍 in vitro 失败——mostly 表达 / SEC / 弱亲和
- **5-metric thresholds**：pLDDT≥80, pAE_int≤10, iPTM≥0.6, ddG<-30 REU, RMSD_initial<1Å + 满足全部 → 仍只 ~12% in vitro

## Lessons → seeds for rules
1. **AF2 with initial guess 是 binder pipeline 的关键**——不是 plain AF2，是 backbone-aware AF2
2. **RMSD_initial vs AF2 prediction < 1-1.5 Å** 是隐藏 filter，与 iPTM / pLDDT 同等重要
3. **DL filter 5-10x 提高 mini-binder in vitro hit rate**——~12% 是 2023 SOTA mean
4. **跨 target generalization 已证实**：但 target-specific 难度不可消除（FGFR2 23% vs EGFR < 10%）
5. **iPTM > 0.7 + AF2 confirmed fold** 仍非 binding 保证——AF2 false positive 30%
6. **Negative design 仍是开放问题**：specificity / paralog distinction 未充分解决
7. **PRAXIS implication**：predict_complex skill 在 de novo binder 路径上要 default-on AF2 initial guess + RMSD_initial filter；rule 02 (paired_msa) + RMSD_initial 共同 enforce

## 数据指针
- 论文 + supp: https://doi.org/10.1038/s41467-023-38328-5
- 13 target 的设计 + 选中 binder + cryo-EM PDB IDs 在 supp materials
- 后续 BindCraft (Pacesa 2024) 等工具直接继承这条 pipeline
