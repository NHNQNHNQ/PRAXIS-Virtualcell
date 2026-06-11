---
case_id: crispr-006-mageck-screen-analysis
schema_version: 1
edit_type: pooled_crispr_screen_analysis
target_gene: genome_wide
target_organism: hg38
cell_context: K562
editing_system: SpCas9
delivery_method: lentivirus
tools:
- MAGeCK MLE/RRA
- DrugZ
- BAGEL2
- CRISPhieRmix
- ScreenPro2
key_paper_doi: 10.1186/s13059-014-0554-4
status: validated
provenance:
  source_type: literature
  doi: 10.1186/s13059-014-0554-4
  citation: Li W et al. (2014) Genome Biol 15:554 — MAGeCK enables robust identification
    of essential genes from genome-scale CRISPR/Cas9 knockout screens
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- pooled_screen
- K562
- SpCas9
- MAGeCK
- DepMap
- Brunello
- GeCKO
- TKOv3
cell_context_list:
- K562
- MOLM13
- HCT116
---

# Pooled CRISPR screen 分析：MAGeCK 经典 pipeline

## Background
Pooled CRISPR screen 把 lentiviral library（~80k-100k sgRNA, 4-6 sgRNA/gene）转入 cell pool → 处理（化合物 / dropout / positive selection）→ NGS sgRNA counts → MAGeCK 找 hit gene。Tsherniak/Wang 等人在 K562/MOLM13 等 cell line 跑过 essential gene benchmark，是 screen pipeline 的 golden test。

## What I actually did
1. **Library QC**：sgRNA representation（reads per sgRNA distribution）+ Gini coefficient < 0.3 + lorenz curve 平
2. **Read counting**：MAGeCK `count` 模块 → fastq → counts table（sample × sgRNA）
3. **Normalize**：median 或 control sgRNA 归一化
4. **MAGeCK MLE 模型**（推荐）vs RRA：MLE 给 beta score（gene effect size），RRA 给 rank-based p-value
5. **DepMap-aware QC**：already-known essential gene（CKEs：core essential 100+）应富集 dropout top；non-essential（NEs：CRISPR null mutants）应 flat
6. **Hit calling**：MAGeCK p < 0.001 + |LFC| > 0.5 + ≥ 3 sgRNA 一致方向
7. **Pathway enrichment**：hit gene → MSigDB / Reactome（fgsea）
8. **Comparator screen**：control（DMSO）vs treatment（化合物）的 differential dropout = 化合物 mechanism

## ★ 排除/不做的事
- **Library distribution 不查 QC**：Gini > 0.5 表示 library biased，下游 hit calling 不可信
- **Single time point screen**：dropout 必须 day 0 (post-infection) + day 14-21 比较
- **Single biological replicate**：< 2 replicate 无 MLE estimate
- **不区分 essential vs synthetic lethal hit**：化合物 vs DMSO 才能找 SL；single arm 找 essential
- **MAGeCK 不用 control sgRNA**：non-targeting sgRNA 是关键 normalize anchor
- **不做 GO/pathway enrichment**：单 gene level hit list 难 interpret，pathway level 显示 mechanism

## ★ 失败模式
- **Library bottleneck**：< 200x cells per sgRNA 在 selection 阶段，sgRNA 丢失非生物学
- **Multiplicity of infection (MOI) 高**：MOI > 0.3 多个 sgRNA 同 cell，hit calling 错位；推荐 MOI 0.3
- **Gene with single sgRNA hit**：4-6 sgRNA 中只 1 显著 = 单 sgRNA 假阳；要求 ≥ 3 sgRNA consistent
- **Cell line-specific effects**：K562 essential ≠ HCT116 essential；hit 跨 cell line 验证
- **Off-target 在另一 essential gene**：sgRNA 数据 hit 看似 gene A 实际 off-target gene B
- **Dropout time too short**：3 day insufficient，slow-cycle gene dropout 看不到，需 14-21 day

## Lessons → seeds for rules
1. **Library QC first**：Gini coefficient + lorenz curve 必查
2. **MOI 0.3** + cell coverage 200x sgRNA 是 minimum
3. **MLE 给 effect size** + RRA 给 p-value，两个一起用
4. **DepMap CKE/NE benchmark** 是 screen QC 标尺（CKE 富集 dropout，NE 不富集）
5. **≥ 3 sgRNA consistent direction** for hit
6. **Control sgRNA normalization** 必用
7. **Pathway enrichment** 才能 interpret
