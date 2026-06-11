---
case_id: crispr-003-base-editor-abe
schema_version: 1
edit_type: base_editing_a_to_g
target_gene: BCL11A
target_organism: hg38
cell_context: HSC
editing_system: ABE8e
delivery_method: mRNA_electroporation
tools:
- BE-Hive
- BEEP
- Be-Designer
- CRISPResso2 base editing mode
key_paper_doi: 10.1038/s41587-020-0414-6
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41587-020-0414-6
  citation: Richter MF et al. (2020) Nat Biotechnol 38:883-891 — ABE8e directed evolution
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- base_editing_a_to_g
- HSC
- ABE8e
- BCL11A
- HBB
- sickle_cell
- BE-Hive
delivery_method_list:
- mRNA_electroporation
- LNP+mRNA
---

# ABE8e 修 sickle cell：A→G 编辑的窗口设计

## Background
Sickle cell disease HBB E6V mutation = GAG→GTG（Glu→Val）。直接修 E6V 需要 T→A 编辑（CBE 方向）— 但难。Newman 2020 用 ABE 走另一条路：编辑 BCL11A 增强子 → BCL11A down → fetal HbF up → 弥补 mutant HbA。**BE 是 indel-free 编辑**，不切 dsDNA，安全 profile 更好。

## What I actually did
1. **Target choice**：BCL11A enhancer +58 region，GATA1 binding site 关键 A
2. **ABE 系统选**：ABE8e（最高活性 + 窄窗口 4-8）vs ABE7.10（早期，活性低）
3. **sgRNA 定位**：让目标 A 位于 protospacer 4-8 位（编辑窗口最高效区）
4. **Bystander mutation 预测**：BE-Hive 模型预测同窗口内其他 A 的编辑率
5. **Off-target categories**：
   - **Cas9 dependent**：常规 sgRNA off-target，CFD 评分
   - **Cas9 independent (deaminase off-target)**：ABE 的 TadA 在 RNA + ssDNA 上 off-target；ABE8e 比 ABE7.10 严重
   - **R-loop dependent**：靠 transient ssDNA 形成
6. **Editing efficiency goal**：HSC 中 ≥ 60% target allele edit，bystander < 5%
7. **Validation**：amplicon-seq with EditR / CRISPResso2 base editing mode；HbF 表达 flow cytometry

## ★ 排除/不做的事
- **ABE7.10 当 default**：活性 vs ABE8e 低 5-10×，临床场景不达 efficacy
- **Target A 不在 4-8 位**：< 4 或 > 8 编辑率暴跌
- **不查 bystander A**：意外编辑产生 missense；尤其 splicing site 附近
- **Cas9-independent off-target 不评估 with ABE 临床**：deaminase 在 transcriptome 编辑（hyperedit）是 BE 特有 risk
- **不用 BE-specific QC tool**：CRISPResso2 默认 indel mode，base 编辑被 miss
- **HSC 用 lentivirus delivery**：ABE 需高水平 RNP delivery；mRNA + LNP 是 SOTA

## ★ 失败模式
- **Window slip**：理想 4-8 但实际 cell type / chromatin 影响窗口位置
- **Bystander missense**：同窗口非 target A 编辑产生 unintended protein change
- **TadA off-target hyperediting**：mRNA 上 A→I（被 read 为 G）大规模错编，影响 transcriptome
- **Allelic bias**：双 allele edit rate 不同，单 allele heterozygous 输出
- **Editing in mature cells vs HSC**：HSC 编辑 ≠ in vivo erythroid lineage 表达
- **Long-term safety**：BE editor 长期表达可能累积 off-target；transient delivery（mRNA/RNP）必须

## Lessons → seeds for rules
1. **ABE/CBE 选最新代**：ABE8e/CBE4max vs early version 活性差 5-10×
2. **Target base 必须在 protospacer 4-8 窗口**：超出降效
3. **Bystander prediction 强制**（BE-Hive）：missense / splicing 影响评估
4. **Two off-target classes 都要查**：Cas9-dep（CFD）+ Cas9-indep（DNA/RNA 全转录组 deep seq）
5. **Delivery mode**：mRNA + LNP > lentivirus for safety
6. **CRISPResso2 base editing mode 必用**，不用 indel mode
