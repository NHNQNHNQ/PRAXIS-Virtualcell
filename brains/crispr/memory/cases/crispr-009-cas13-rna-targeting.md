---
case_id: crispr-009-cas13-rna-targeting
schema_version: 1
edit_type: rna_targeting
target_gene: KRAS
target_organism: hg38
cell_context: lung_cancer_cell_line
editing_system: RfxCas13d
delivery_method: lentivirus
tools:
- Cas13design
- RfxCas13d guide design tools
- REPAIR (Cas13 + ADAR)
- CIRTS
key_paper_doi: 10.1038/s41587-020-0456-9
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41587-020-0456-9
  citation: Wessels HH et al. (2020) Nat Biotechnol 38:722-727 — Cas13d guide design
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- rna_targeting
- RfxCas13d
- CasRx
- KRAS_mRNA
- G12D
- collateral_activity
delivery_method_list:
- lentivirus
- LNP+mRNA
- AAV
---

# Cas13 RNA targeting：mRNA 敲低与位点编辑

## Background
Cas13（type VI CRISPR）切 RNA 不切 DNA，**永久性低 + reversible + 可定位 mRNA isoform**。RfxCas13d (CasRx) 是高活性 + 紧凑 (930 aa) 变体。应用：(1) transient knockdown（vs siRNA）；(2) RNA editing（Cas13 + ADAR = REPAIR/RESCUE）；(3) live-cell RNA imaging。

## What I actually did
1. **Target mRNA region 选**：CDS（避 5'/3' UTR，效率低）+ 高 accessible region（low secondary structure，RNAfold predict）
2. **gRNA 长度**：Cas13d 22-30 nt，中间最佳
3. **Tile 策略**：transcript 上每 50 nt 一 gRNA → 选 top 5（accessibility + GC + 不 hit human transcriptome off-target）
4. **Cas13design 工具评估**：score 高 + flanking 序列优化（H/F/D etc.）
5. **Off-target on transcriptome**：Cas13 collateral activity（trans-cleavage）—— in mammalian cell **大幅减弱**（vs 体外），但仍是临床担心
6. **KRAS G12D specific knockdown**：design gRNA 跨 SNV 位点，让 mismatched WT 不被切（selectivity）
7. **Delivery**：mRNA + LNP（in vivo）/ lentivirus（in vitro）/ AAV（CasRx 紧凑可一 AAV pack）
8. **Validation**：qPCR + Western blot + RNA-seq（看 collateral / specificity）

## ★ 排除/不做的事
- **Cas13 当 DNA 编辑 tool**：concept 错误；Cas13 完全 RNA-only
- **Target mRNA 5'/3' UTR**：cleavage 效率低 vs CDS
- **Accessible region 不预测**：高 secondary structure 区 Cas13 access 差
- **Specificity 不评估 SNV-level**：KRAS G12D vs WT 区分需 gRNA 跨 SNV + mismatch tolerance
- **不查 collateral activity in target cell type**：Cas13 collateral 在某些 cell type 显著（神经元）
- **Stable Cas13 expression in vivo**：长期表达增 collateral risk；transient delivery preferred

## ★ 失败模式
- **Collateral cleavage**：Cas13 切 target 后非特异切 host RNA（in vitro 严重，in vivo 较轻但存在）
- **Off-target on transcriptome**：mismatch tolerance high；human transcriptome off-target panel 必跑
- **Knockdown not durable**：mRNA recycling，需 sustained Cas13 expression
- **Allele specificity 难达**：单 SNV 区分 WT/mutant 需 gRNA 精确设计 + mismatch position 关键
- **Cell type 表达异质性**：transient delivery 给不均一 knockdown，single-cell vs bulk 差大
- **Immune response in vivo**：bacterial protein triggers immunogenicity（如 SaCas9 但 Cas13 同样）

## Lessons → seeds for rules
1. **Target CDS 区**：避 UTR
2. **RNA accessibility predict**：RNAfold + tile strategy
3. **Collateral activity 评估** in target cell type
4. **Allele specificity** for SNV-targeting：gRNA 跨 SNV + mismatch position 关键
5. **Transient delivery (mRNA/LNP) preferred** for in vivo
6. **CasRx (RfxCas13d)** 紧凑 + 高活性 是 default for therapy
