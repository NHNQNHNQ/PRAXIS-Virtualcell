---
case_id: microbiome-009-strain-tracking
task: strain_level_tracking
input_data: longitudinal shotgun metagenomics from same individual
tools: [StrainPhlAn4, inStrain, midas2, PanPhlAn3]
key_paper_doi: 10.1038/s41587-021-01070-8
status: validated
microbiome_task: strain
sequencing_type: shotgun_short
sample_type: human_gut
reference_db: GTDB R220 (strain-level)
dataset_accession: null
biomass_estimate: high
---

# Strain-level tracking：细菌 stability + transmission

## Background
Species-level analysis 隐藏 strain heterogeneity——同 species 可有多 strain，functionally 重要差异（e.g., E.coli K-12 vs O157:H7）。**Strain tracking** = 通过 SNV 模式区分 strain，跨 sample 跟踪同一 strain。Mother-infant transmission / IBD persistence / FMT engraftment 是经典 application。

## What I actually did
1. **Per-sample shotgun reads → strain profile**：StrainPhlAn4 用 marker gene SNV
2. **Per-strain phylogeny**：跨 sample / individual / time 同 strain 形成 phylogeny
3. **Strain identity criterion**：< 0.1% SNV difference = same strain
4. **Mother-infant transmission**：婴儿 strain 与 mother strain phylogenetic close = vertical transmission
5. **FMT engraftment**：donor strain 在 recipient 中 detect = engraftment
6. **inStrain alternative**：deeper SNV-level analysis, popANI calculation
7. **Coverage requirement**：> 5x mapped to species genome 才能 reliable strain call
8. **Output**：strain phylogeny tree + transmission inference

## ★ 排除/不做的事
- **Species level when strain matters**：FMT efficacy / pathogen track 必须 strain level
- **Insufficient coverage (< 5x)**：strain call unreliable
- **Cross-individual same strain claim without phylogeny**：close abundance ≠ same strain
- **Single-marker gene tracking**：multiple markers needed for confidence
- **Forget time-zero**：longitudinal needs baseline
- **Skip recombination consideration**：HGT / recombination 让 phylogeny 复杂

## ★ 失败模式
- **Multi-strain coexistence in same sample**：obscure individual strain detection
- **Reference strain bias**：StrainPhlAn 比对 known strains，novel strain miss
- **Coverage uneven**：rare species low coverage 失败
- **Strain definition ambiguity**：how many SNV = different strain？
- **Plasmid transfer**：plasmid 跨 strain 让 strain ID 不稳
- **Bottleneck effects**：transmission 后 single founder dominate，多样性 loss

## Lessons → seeds for rules
1. **StrainPhlAn4 + inStrain dual method**
2. **≥ 5x coverage** per species for strain call
3. **Strain identity threshold defined explicitly**
4. **Multi-marker gene support**
5. **Time series + baseline**
6. **Plasmid / recombination caveat**
7. **Reference DB choice** affects result
