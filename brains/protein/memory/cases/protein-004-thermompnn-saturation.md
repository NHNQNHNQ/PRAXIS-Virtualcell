---
case_id: protein-004-thermompnn-saturation
design_task: mutation_effect_prediction
target_pdb: 1STN (Staphylococcal nuclease)
target_uniprot: P00644
fold_class: ob_fold
tools: [ThermoMPNN, ProteinMPNN zero-shot, ESM-2, PyRosetta, Rosetta cartesian_ddg]
key_paper_doi: 10.1101/2023.07.27.550881
status: validated
schema_version: 1
source: praxis_seed
extracted_at: 2026-04-29
---

# Staphylococcal nuclease：饱和突变 ΔΔG benchmark

## Background
SNase 是 ΔΔG 预测金标准 protein——文献有 ~3000 个实验测过的 ΔΔG（FireProt DB / ProTherm）。所有 ΔΔG 预测器都拿它 benchmark。能不能挑出"靠谱稳定突变"是核心 task。

## What I actually did
1. **Reference**：从 FireProt DB 拉 SNase 所有实验 ΔΔG 数据 (~600 mutant)
2. **饱和突变 in silico**：每个位点 19 个 mutant = 149 × 19 = 2831 mutations
3. **5 个预测器并跑**：
   - ThermoMPNN（专做 ΔΔG，performance 最好）
   - ProteinMPNN zero-shot（用 log-likelihood 差当 ΔΔG proxy）
   - ESM-2 650M zero-shot（masked LM log-likelihood 差）
   - PyRosetta cartesian_ddg（物理）
   - Rosetta cartesian_ddg（物理 + minimization）
4. **Spearman correlation 与实验**：ThermoMPNN ~0.65、Rosetta ~0.55、ProteinMPNN ~0.50、ESM-2 ~0.45、PyRosetta ~0.40（基于公开 benchmark）
5. **Recall@TopN**：要找 top 10 stabilizing mutations 实验确实 ΔΔG < -1，ThermoMPNN recall ~50%；二方法（ThermoMPNN + Rosetta）取交集 recall ~30% 但 precision ~80%
6. **Cost-aware combo**：先 ThermoMPNN 全 scan（秒级）→ top 100 用 Rosetta 精算（分钟级）→ top 10 用 PyRosetta 5x replica 验证

## ★ 排除/不做的事
- **只用 single predictor 给 lab 推荐**：单方法 precision 太低，lab 浪费时间合成失败 mutant
- **以 ΔΔG 绝对值排序而非 rank**：所有方法 RMSE 1+ kcal/mol，绝对值不可信；用 rank
- **不分 stabilizing vs destabilizing benchmark**：两类预测难度不同，stabilizing 难（少数派）
- **不考虑 buried vs exposed**：ThermoMPNN 在 buried position 表现远好于 exposed
- **忽略 multi-state**：active vs apo 形态稳定性不同；只用一个 PDB 训预测器是漏的

## ★ 失败模式
- **数据泄漏 benchmark**：ThermoMPNN 训练数据可能包含 SNase——self-benchmark 的 spearman 不可外推
- **Wild type position 影响**：某些 wild type 残基本身已"亚优"，所有 mutation 都 destabilize，预测器学不出
- **Position-specific success**：某 5 个位点占了所有方法 50% 错误率——active site / interface 周边
- **小 effect mutation（|ΔΔG| < 0.5）**：所有方法基本随机，noise 主导
- **Large ΔΔG 极值**（|ΔΔG| > 5）实验 outlier 多——蛋白可能完全 unfold，比较没意义

## Lessons → seeds for rules
1. **多方法 top-N 取交集**：ThermoMPNN ∩ Rosetta（不是 union），precision ↑ recall ↓
2. **Cost-aware tiered scan**：fast scan → expensive validate
3. **Rank-based 排序**而非 ΔΔG 绝对值
4. **Position context 报告**：buried/surface/active-site 分开报，因 predictor 在不同 context 表现差异大
5. **Large effect cutoff 谨慎**：推荐范围限 |ΔΔG| ≤ 3 kcal/mol——超出预测器训练分布
6. **Wild type baseline**：先报 WT 推测稳定性，再报 mutation 相对值
