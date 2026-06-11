---
case_id: microbiome-004-humann-functional
task: functional_metagenomics
input_data: shotgun metagenomic reads
tools: [HUMAnN3 (formerly HUMAnN2), MetaCyc, KEGG ortholog, eggNOG, PICRUSt2 (16S-derived)]
key_paper_doi: 10.7554/eLife.65088
status: validated
microbiome_task: functional
sequencing_type: shotgun_short
sample_type: human_gut
reference_db: ChocoPhlAn v311 + UniRef90 201901b
dataset_accession: PRJNA398089
biomass_estimate: high
---

# HUMAnN3：metagenomics 功能 profile (KEGG / MetaCyc pathway)

## Background
Functional profile 比 taxonomy 更直接关联 host-microbe interaction。HUMAnN3 = 把 reads map 到 species-specific gene catalog → 推 KEGG ortholog (KO) + MetaCyc pathway abundance。**16S 替代**：PICRUSt2 用 16S taxonomy 推 function（lower accuracy）。

## What I actually did
1. **Input**：shotgun reads (paired)
2. **HUMAnN3 pipeline**：
   - Reads → MetaPhlAn taxonomy
   - Per-species gene catalog mapping (ChocoPhlAn DB)
   - Diamond BLAST for unmapped reads → UniRef90
   - Sum per KO / per MetaCyc reaction / per pathway
3. **Output formats**：
   - gene_families.tsv (UniRef90 per species)
   - pathabundance.tsv (MetaCyc pathway per species + community)
   - pathcoverage.tsv (% reactions present)
4. **Normalization**：CPM (copies per million), 不要 raw counts cross-sample compare
5. **Per-species vs community**：可以 attribute pathway to specific species
6. **Differential pathway analysis**：MaAsLin2 / ANCOM-BC2 on pathway abundance
7. **Cross-validation**：functional pathway consistency vs taxonomy (e.g., butyrate producers should correlate with butyrate pathway)

## ★ 排除/不做的事
- **PICRUSt2 当 functional 替代 shotgun**：accuracy 低 30-50%；only 16S have时
- **Raw count cross-sample**：normalize to CPM mandatory
- **Single annotation level**：KO + pathway + module 互补
- **Per-species pathway 跨 species 直接 sum without consideration**：合理 for community level，错 for species-specific
- **Forget unmapped reads**：unmapped fraction is signal too (novel function)
- **Pathway coverage vs abundance**：completeness vs concentration 不同 metric

## ★ 失败模式
- **Reference catalog 不全**：novel function 不在 ChocoPhlAn / UniRef90
- **Per-species attribution noise**：similar species share many genes，attribute uncertain
- **Pathway hierarchy collapse**：pathway 由多 reaction 组成，single missing reaction 致 pathway 不 covered
- **Compute time**：full HUMAnN3 几十 GB RAM, 数小时
- **Database version drift**：HUMAnN versions use different reference, 不可 cross-compare directly
- **Function ≠ activity**：基因 presence ≠ expression ≠ enzyme activity

## Lessons → seeds for rules
1. **HUMAnN3 > PICRUSt2** when shotgun available
2. **CPM normalization** for cross-sample
3. **KO + pathway dual analysis**
4. **Per-species attribution + community sum** parallel
5. **MaAsLin2 / ANCOM for differential**
6. **Database version log**
7. **Function != activity** caveat
