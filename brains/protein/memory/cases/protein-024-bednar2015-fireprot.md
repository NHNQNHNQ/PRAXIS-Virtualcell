---
case_id: protein-024-bednar2015-fireprot
design_task: stabilization
target_pdb: 1CV2
target_uniprot: P21518
fold_class: alpha_beta
length_range: 100-400
tools: [FireProt, PyRosetta, Rosetta, MSA_consensus, evolutionary_information, statistical_potentials]
key_paper_doi: 10.1371/journal.pcbi.1004556
key_metrics:
  proteins_redesigned: "approx 10 enzyme cohort (haloalkane dehalogenases, others)"
  Tm_top_design: "+25 degC top observed (DhaA enzyme, multi-mutant)"
  activity_retention: "majority retained >70% WT activity"
  prediction_accuracy_vs_experimental_ddG: "approx 0.7 Spearman correlation on benchmark"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [stabilization, FireProt, PyRosetta, Rosetta, multi-point-mutant, dehalogenase, automated-engineering]
unverified_details:
  - "Tm gain +25 degC is for top variant in cohort, not average"
  - "Specific cohort enzyme selection variable; haloalkane dehalogenase is primary case"
---

# FireProt：能量 + 进化双轨 thermostab（Bednar et al. PLOS Comp Biol 2015）

## Background
- 起点：稳定化通常用 Rosetta ddG / PyRosetta cartesian_ddg，但单 method 假阳率高，~30-50% predicted stabilizing 实测无效或 destabilizing
- 目标：建立"能量计算 + 进化分析"双轨过滤 pipeline，组合多点突变；不仅识别稳定突变，还组合到一个变体上
- 应用：早期 SOTA 自动稳定化 pipeline；FireProt server 在工业酶工程中广泛使用；后续 PROSS 是其延伸+精化

## What I actually did（基于论文）
1. **能量轨道**：PyRosetta cartesian_ddg + Rosetta cartesian_ddg 单点突变，预测 ΔΔG
   - 双 method 共识（两者都说 stabilizing）才接受
2. **进化轨道**：MSA consensus 分析
   - 在自然界 MSA 中频率 > WT 5x 的位置 = "back-to-consensus"
   - Same residue type 在 thermophilic ortholog 出现 = "back-to-thermo"
3. **双轨交集**：能量 + 进化都 favor 的突变才进 candidate pool
4. **组合策略**：贪心 + 距离避免（突变间距 ≥ 8 Å 避免互相影响）+ 多点突变 ≤ 15
5. **Validation cohort**：~10 enzymes 跨 fold；典型代表 haloalkane dehalogenase DhaA, DbjA
6. **Wet lab**：基因合成 + BL21 表达 + DSF Tm + activity assay (specific to enzyme)
7. **结果**：top variants Tm +25°C；多数保留 >70% activity

## ★ 排除的位点/区域
- **Active site 残基（catalytic triad 等）**：明确 frozen（应用于酶 case）
- **Substrate-binding residues**：5 Å around substrate binding pose，不动
- **Cofactor-binding（NADH, FAD, metal）**：frozen
- **Disulfide bonds**：保留
- **PPI / dimer interface**：如果 quaternary structure 需要，frozen
- **Glycosylation 位点**：如果用真核 expression，frozen；BL21 expression 不需要
- **Buried H-bond network**：design 时 risk 高，case-by-case 评估；论文偏 conservative

## ★ 失败模式
- **Cooperative epistasis 破坏**：单点 ddG sum 不等于多点 ΔΔG ——~10% combined design 比 sum 预期低
- **Stability vs activity tradeoff**：~25% case 失去 >50% activity（与 PROSS 数据一致）
- **MSA 不足时 evolutionary track 退化**：< 50 homologs → 全靠能量预测，假阳率上升
- **同位置 ddG conflict**：PyRosetta 和 Rosetta 偶尔 disagree；论文丢弃这类
- **Aggregation 没建模**：少数 design Tm 升高但 SEC 上多聚——稳定 monomer ≠ 稳定 oligomer
- **Long-loop redesign 风险**：FireProt 偏向 helix/sheet 残基；loop 上 stabilizing 突变的 prediction 较差

## ★ 方法选择决策链
- **为什么 PyRosetta + Rosetta 双 method 共识 而非单一**：单 method 假阳 30-50%；双共识降到 ~10%
- **为什么 MSA consensus + thermo-ortholog 双进化轨**：MSA 反映"什么残基常见"，thermo-ortholog 反映"高温变体偏好"——两者捕获不同信号
- **为什么距离 ≥ 8 Å filter 多点突变**：避免突变间能量耦合（partial epistasis）；类似 Bremer 2013 推荐
- **为什么贪心 而非全枚举**：candidate pool 大（~30-100 stabilizing 突变）+ 多点全枚举 combinatorial blowup
- **为什么 BL21 + DSF**：throughput；后续 secondary 验证（CD, X-ray）只对 top variant
- **为什么 ~10 enzyme cohort**：generalization 验证 + 主流 industrial enzyme 覆盖

## ★ In silico vs in vitro 差距
- **In silico 通过 → 表达 OK**：~10 蛋白，全部表达
- **Tm 上升 ≥5°C**：~9/10 (~90%)
- **Activity retained >70%**：~7/10 (~70%)
- **同时 stability + activity OK**：~6/10 (~60%) **← 与 PROSS ~64% 接近**
- **Top variant Tm gain +20°C+**：~3/10 protein 达成，主要 DhaA 类 dehalogenase
- **vs case 023 (PROSS)**：FireProt 在 Tm gain 峰值高 (+25°C vs PROSS +12°C average)；PROSS 在 expression 提升更好
- **No standard pLDDT/iPTM**：传统 ddG-based pipeline，metric 是 Rosetta_ddG + PyRosetta ΔΔG + DSF Tm

## Lessons → seeds for rules
1. **能量 + 进化双轨过滤**：单 method 假阳率高；2-method 共识是稳定化设计的标准
2. **多点突变 distance ≥ 8 Å**：避免 epistasis 干扰
3. **Multi-method ddG voting** 是 rule 01 multi-model consensus 的早期 instance（双 ddG predictor）
4. **Stability/activity tradeoff 是 fundamental tension**：~30% case 失活 >50%——客户必须知情
5. **MSA 浅的蛋白 fall back to energy-only**：与 PROSS 教训一致
6. **DhaA 类 enzyme 是稳定化 sweet spot**：因为 active site 离 surface 远，design space 大
7. **PRAXIS implication**：mutation_effect_scan rule 01 强制 ≥2 predictors 直接源自这条原则；evolutionary signal (ESM-2 PLL 等) 应作为 ddG predictor 的 complement

## 数据指针
- 论文 + supp: https://doi.org/10.1371/journal.pcbi.1004556
- FireProt server: https://loschmidt.chemi.muni.cz/fireprotweb/
- 10 case cohort 数据 在 supp Tables
