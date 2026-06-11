---
case_id: protein-014-hosseinzadeh2017-macrocycle-topologies
design_task: cyclic_peptide_topology_sampling
target_pdb: nan
target_uniprot: nan
fold_class: cyclic_macrocycle
length_range: 7-14
tools: [Rosetta, GenKIC, NMR]
key_paper_doi: 10.1126/science.aap7577
key_metrics:
  topologies_sampled: "approx 200000 candidate cyclic peptide topologies"
  designs_synthesized: "30+ representative designs"
  NMR_validated_to_design: "20+ designs fold to design within ensemble RMSD"
  novel_topologies_observed: "trefoil knots, ABBA hairpins, novel beta-turn motifs"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [cyclic-peptide, macrocycle, topology-enumeration, GenKIC, NMR-validated, comprehensive-sampling]
unverified_details:
  - "Exact count of NMR-validated designs varies by stringency definition; paper claims ~80% of selected designs match NMR"
  - "topologies count is order-of-magnitude reading from supplementary tables"
---

# Comprehensive cyclic peptide topology design（Hosseinzadeh et al. Science 2017）

## Background
- 起点：Bhardwaj 2016 证明了"de novo cyclic peptide design 可行"，但只覆盖 12 个 specific design。空间是否包含更多 topology 待探索
- 目标：系统性 enumerate 7-14 aa cyclic peptide 的所有可能 backbone topology——不只是 helix-turn-helix，还包括 beta-turns, novel cross-strand H-bond, 甚至 trefoil 拓扑
- 应用：建立 cyclic peptide design 的 topology library——为后续 binder + drug design 提供 diverse scaffold pool

## What I actually did（基于论文）
1. **Topology enumeration**：穷举 7-14 aa cyclic peptide 的可能 secondary structure abstraction：
   - 双 hairpin 拓扑（ABBA）
   - 单 hairpin + helix 段
   - 全 helix 短片段
   - Trefoil（带 disulfide bridge）
   - 含 beta-turn motif (i,i+3 H-bond) 的混合
2. **Backbone sampling**：每个 topology 跑 ~10^4 GenKIC closure，得到几何上合法的 backbone 池
3. **Sequence design + scoring**：fixed-bb FastDesign + Rosetta talaris score function
4. **Funnel filter**：每个 design 跑 ab initio 折叠，要求 design backbone 是 lowest-energy basin
5. **Total**：~200,000 candidate topology + sequence combinations 通过 funnel filter
6. **Selection**：~30+ representative designs 选作 in vitro validation
7. **Synthesis + NMR**：固相合成 → 头尾 / 二硫闭合 → 2D NMR → 计算 NMR ensemble vs design model RMSD
8. **结果**：~80% NMR fold to design conformation；发现 trefoil 拓扑（之前没在天然 cyclic peptide 见过）+ 多个 novel beta-turn motif

## ★ 排除的位点/区域
- **未在 funnel basin 的 sequence**：~95% 通过 sequence design 但不通过 funnel test 的 design 直接 discard
- **几何上不闭合的 backbone**：GenKIC 输入约束自动 enforce
- **Pro / Gly 在 helix 中间**：除非论文明确测试 disrupting 效果，否则 helix 段 Pro 排除
- **Cys 不在 disulfide 配对位置**：自由 Cys 可能 disulfide-mediated dimerize; 总是配对使用
- **All-D 的 sequence 在天然环境**：本论文以 L+D 混合为主；纯 D 设计在 in vivo 验证少
- **Topology 中含 knot 的若不能用 disulfide 强制**：knot 拓扑没有 SS 几乎不可能正确 fold

## ★ 失败模式
- **NMR 显示多 conformation populated**：~20% NMR-tested 设计有多构象 ensemble；这些被归类 "partial fold"
- **Knot topology 合成失败**：trefoil 拓扑的合成产率非常低（< 10%），需要分步合成 + SS 形成 + 纯化
- **Beta-turn 相关 H-bond 未形成**：部分 beta-turn design NMR 显示 turn 角度对 fold 但 H-bond pattern 与设计不一致
- **温度稳定性 < helix-only**：含 beta-turn 的多数 Tm < 80°C（vs all-helix Tm > 95°C）；topology 越复杂越 entropy 不稳
- **Sequence 多样性受限**：design 必须在 funnel 最低位，limit 了氨基酸 diversity；一些 topology 只能用很少 sequence
- **Solubility variation**：含 hydrophobic 内核的 topology 在水中聚集 ~10%

## ★ 方法选择决策链
- **为什么 enumerate topology 而非 random sample**：topology pool 是 finite + tractable；随机采样大概率 collapse 到几个 dominant fold
- **为什么 Rosetta 而非 deep-learning（如 RFdiffusion）**：2017 年 deep-learning structure design 还未成熟；Rosetta 是 baseline
- **为什么 ~30 designs 而非更多 in vitro**：合成 cost + NMR 时间——选 representative 而非 exhaustive
- **为什么 NMR > X-ray**：cyclic peptide 难晶体；NMR 唯一可达
- **为什么 funnel test 必须**：fold-only 任务在 cyclic peptide 上 critical；没有 funnel test 的 design 大概率多 conformation

## ★ In silico vs in vitro 差距
- **No pLDDT / iPTM / pAE 等 AF metric**：2017 paper，AF2 还未出现；用 Rosetta talaris score + ab initio funnel 作为质量代理
- **Rosetta_ddG 不适用**：cyclic peptide fold-only 任务，没有 interface
- **后续 cyclic peptide binder 工作（Bhardwaj 2022, Wu 2023）才引入 AF / Rosetta_ddG 双重评估**
- **设计候选数**：200,000 in silico → ~30 selected → ~24 NMR-validated to design (~80%)
- **比 Bhardwaj 2016 (100% 12/12)**：本论文 topology 多样性更高，转化率略降但仍极高 vs mini-binder
- **合成产率**：复杂 topology 平均 ~20-30% 产率（vs simple cyclo-peptide 50%）
- **稳定性谱**：all-helix 设计 Tm > 95°C；含 beta-turn 设计 Tm 70-90°C；trefoil 设计 Tm 60-80°C
- **Conformation purity**：NMR ensemble RMSD 平均 < 1.5 Å vs design model（top decile < 0.5 Å）
- **No functional binding tested in this paper**——topology library，不针对 target；因此没有 binder 转化率 metric

## Lessons → seeds for rules
1. **Topology enumeration > random sampling**：cyclic peptide design 的搜索空间已经足够小，systematic 优于 stochastic
2. **Funnel test 是 cyclic peptide design 的 gold standard**：design backbone 必须是 lowest energy basin
3. **Helix-only 最稳定，topology 越复杂 Tm 越低**——drug development 注意 stability/diversity tradeoff
4. **80% NMR validation rate at ~200k → ~30 → ~24** 是当前 cyclic peptide design 的实际 yield
5. **Trefoil / 新颖 topology 需要 SS bridge enforcement**——纯 head-to-tail 难达成
6. **Solubility 是 cyclic peptide 的 hidden constraint**：表面残基设计要 explicit 极性
7. **本论文不涉及 binder**——cyclic peptide binder 是后续工作（Bhardwaj 2022 / Wu 2023）

## 数据指针
- 论文 + supp: https://doi.org/10.1126/science.aap7577
- 设计 + NMR 结构 → supp materials
- Topology library：作为后续 cyclic peptide design 的 reference scaffold pool
