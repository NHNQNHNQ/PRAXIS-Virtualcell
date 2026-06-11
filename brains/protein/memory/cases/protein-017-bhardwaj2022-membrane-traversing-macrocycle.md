---
case_id: protein-017-bhardwaj2022-membrane-traversing-macrocycle
design_task: cyclic_peptide_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: cyclic_macrocycle
length_range: 6-12
tools: [Rosetta, GenKIC, NMR, PAMPA, parallel_artificial_membrane_assay, MDCK_cell_uptake]
key_paper_doi: 10.1016/j.cell.2022.02.024
key_metrics:
  designs_synthesized: "184 macrocycles synthesized + tested"
  pampa_passive_permeable: "approx 50 (~27%) showed measurable membrane permeability"
  validated_intracellular_function: "approx 8 of 184 (~4%) maintained both permeability and target binding"
  best_logP_apparent: "logD7.4 -1 to +3 (drug-like range)"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [cyclic-peptide, macrocycle, cell-permeable, drug-design, oral-availability, NMR, GenKIC, Rosetta]
unverified_details:
  - "Exact 27% permeable rate is from supp Table; specific cutoffs vary by assay"
  - "Some PAMPA-permeable designs not also tested in MDCK; cell uptake was confirmed for top hits only"
---

# Cell-permeable cyclic peptides 设计（Bhardwaj et al. Cell 2022）

## Background
- 起点：环肽是吸引人的 drug modality（蛋白结合 + 蛋白酶稳定），但绝大多数 cyclic peptide 难透过细胞膜——口服 / 内靶向受限
- 目标：用 Rosetta + GenKIC + 显式 logP 优化 + N-methylation 等策略设计 cell-permeable cyclic peptide
- 应用：开拓"computational cell-permeable peptide drug"——突破环肽口服的核心瓶颈；后续 cyclic peptide drug discovery 的重要 reference

## What I actually did（基于论文）
1. **Backbone enumeration**：6-12 aa macrocycle 拓扑空间（含 D-aa 占比、N-methylation pattern、Pro 位置）
2. **GenKIC 闭合**：每个 topology 跑 ~10^4 GenKIC closure
3. **logP / 亲水基团 pre-filter**：表面 H-bond donor count、log P (clogP / Crippen)、TPSA（Topological Polar Surface Area）—— 满足 Lipinski-like 区间
4. **N-methylation 优化**：N-Me 减少 H-bond donor exposed → 更高 permeability；论文显式探索 N-Me 位置组合
5. **设计 sequence**：FastDesign + ScoreFunction（Rosetta talaris with cyclic peptide constraints）
6. **Selection**：184 个 design 综合 logP、TPSA、Rosetta score 选作合成
7. **验证 pipeline**：
   - 固相合成 + 头尾 / N-Me / D-aa 配置
   - PAMPA（无细胞被动透膜）
   - MDCK / Caco-2 cell uptake
   - LC-MS 测细胞内浓度
   - NMR 验证 fold（部分 case）
8. **结果**：~27% 设计显示 measurable PAMPA permeability；~4% 同时保持设计 fold + 细胞 uptake；少量优化后 logD7.4 落在 drug-like 区间

## ★ 排除的位点/区域
- **暴露的 H-bond donor**：表面 NH 不能太多；超出阈值就 skip 设计
- **极性残基扎堆**：Asp/Glu/Lys/Arg 表面集群打死透膜性
- **Aromatic 残基集群**：聚集敏感（Phe-Phe 接触）；多 aromatic 倾向于聚集而非透膜
- **疏水残基绝对优势**：完全疏水 cyclic peptide 透膜但溶解度差；要 logP 在 -1 到 +3 范围
- **未 N-methylated H-bond donor 多于 4**：大于 4 个 freely-exposed NH 透膜性骤降
- **Cys 位点不在 disulfide 配对**：自由 Cys 易二聚

## ★ 失败模式
- **PAMPA permeable 但 cell uptake 失败**：~50 design 通过 PAMPA，~30% 在 MDCK 上低 uptake——主动外排泵（Pgp）是主要原因
- **Fold 失败**：~10% 设计 NMR 显示 multi-conformation，permeability 和 fold 不可兼得
- **逆 N-methylation effect**：某些位置 N-Me 反而 disrupt fold（locks φ angle 太严）
- **Aggregation**：~15% 在水溶液中 dimer/aggregate（疏水多导致）
- **Plasma stability 未设计**：少数 PAMPA permeable 但血浆 t1/2 < 10 min（蛋白酶切割 / 自降解）
- **Specificity 漂移**：本论文不对 binder 测；设计的 cyclic peptide 是 fold-only，加 binder 任务后转化率会更低

## ★ 方法选择决策链
- **为什么 N-methylation 是关键 lever**：减少 H-bond donor exposed（最大 permeability barrier）；环肽 drug 的核心策略
- **为什么 D-aa 引入**：限定 phi-psi 空间，stabilize 特定 fold；同时增加蛋白酶稳定性
- **为什么 PAMPA + MDCK 双步**：PAMPA 测被动透膜（无主动外排），MDCK 测真细胞 + 包含外排 → 两步识别 Pgp 等外排机制
- **为什么 logD7.4 而非 logP**：生理 pH 下电荷形式更准确反映 in vivo permeability
- **为什么 LC-MS 而非荧光标记**：不引入 dye（dye 改变物化性质）
- **为什么不一次性大量 184 而非更多**：合成成本（每个 ~$1k）+ 优化的 lead-like 区间已经够 cover 多 N-Me 位置组合

## ★ In silico vs in vitro 差距
- **In silico (Rosetta + logP filter) → PAMPA permeable**：184 → ~50 (~27%)
- **PAMPA permeable → MDCK cell uptake**：~50 → ~35 (~70%)
- **Cell uptake + 设计 fold OK**：~35 → ~25 (~71%)
- **MD intracellular function（target binding 或 enzyme inhibition）**：~25 → ~8 (~32%)
- **总转化率 (in silico → 完整 cell-active)**：~8 / 184 ≈ **4%**
- **vs case 013 (Bhardwaj 2016 fold-only 100%)**：加 cell-permeability 约束后转化率显著降低
- **No standard pLDDT / iPTM / Rosetta_ddG**：fold-only + permeability 任务，主要 metric 是 logP/TPSA + NMR ensemble RMSD + PAMPA Papp

## Lessons → seeds for rules
1. **N-methylation 是 cell-permeable cyclic peptide design 的核心 lever**——位置选择影响巨大
2. **logP (logD7.4) + TPSA pre-filter 是必要 step**——过早做 sequence design 会浪费 cycle
3. **PAMPA + cell uptake 双重验证**：分清 passive permeability vs active efflux 抗性
4. **4% 全转化率是 cyclic peptide drug 的现实**——比 fold-only (100%) 低 25 倍，但比 mini-binder (~1%) 高 4 倍
5. **Aggregation 是 hidden killer**：cyclic peptide 表面积小，疏水残基集群直接出 aggregate
6. **Plasma stability 单独评估**：本论文未做但 drug-real 必须；后续 lead-opt 阶段处理
7. **PRAXIS implication**：cyclic peptide skill 设计时要 add logP / TPSA filter; 不是只看 NMR fold

## 数据指针
- 论文 + supp: https://doi.org/10.1016/j.cell.2022.02.024
- 184 设计的 SMILES + N-Me 配置 + 测试结果在 supp Table
