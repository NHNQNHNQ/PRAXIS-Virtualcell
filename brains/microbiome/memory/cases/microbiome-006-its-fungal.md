---
case_id: microbiome-006-its-fungal
task: fungal_amplicon_its
input_data: ITS1 / ITS2 amplicon Illumina reads
target_organism: human gut / soil mycobiome
tools: [QIIME2, DADA2, UNITE database, ITSx, ITSxpress, FUNGuild]
key_paper_doi: 10.1186/s40168-020-00818-9
status: validated
microbiome_task: amplicon_its
sequencing_type: ITS
sample_type: soil
reference_db: UNITE 10.0
dataset_accession: null
biomass_estimate: low
---

# ITS amplicon：真菌组分析（不同于 16S 细菌）

## Background
真菌 ITS (Internal Transcribed Spacer) 是 fungal 标准 marker（vs 细菌 16S）。**ITS 特殊**：(1) length variable (200-600 bp) → trimming + filtering 不同；(2) UNITE reference DB 而非 SILVA；(3) FUNGuild functional grouping (saprotroph/pathogen/symbiont)；(4) low fungal biomass + 真菌 reads 在 stool 较稀。

## What I actually did
1. **Read QC + primer removal**：ITS1F + ITS2 primers
2. **ITSxpress**：extract ITS1 region (variable length, removes flanking 18S/5.8S)
3. **DADA2 with length filtering removed**（因 ITS variable length）
4. **Taxonomy**：QIIME2 classify-sklearn vs UNITE reference
5. **FUNGuild**：annotate fungal lifestyle/guild (saprotroph, plant pathogen, animal pathogen, mycorrhizal)
6. **Diversity**：Shannon, Simpson；fungal richness usually lower than bacterial
7. **Bias considerations**：ITS copy number varies across fungi (10-100×)
8. **Cross-validation**：18S as marker（some studies）OR shotgun for fungal community

## ★ 排除/不做的事
- **Use SILVA for fungi**：错；UNITE only
- **DADA2 with strict length filter**：ITS variable length, will lose true sequences
- **16S DADA2 parameters directly**：truncation 不同
- **Trust species level**：ITS species resolution 在某些 genera 弱
- **Skip ITS region extraction**：flanking conserved 18S 在 reads 中混淆 taxonomy
- **Forget functional guild**：community taxonomic 不直接给 ecological function

## ★ 失败模式
- **Low fungal biomass**：human gut stool fungal < 1% reads → noise
- **Primer bias**：ITS primer pair 偏向某些 phyla
- **Copy number variation**：fungi ITS copies 10-100x 跨 species → relative abundance 偏
- **Reference DB gap**：UNITE 比 SILVA 小，novel fungi miss
- **Yeast vs filamentous bias**：DNA extraction efficiency 不同
- **Cross-domain primer specificity**：偶 amplify plant DNA (host)

## ★ Validation
- **Mock community**: known synthetic fungal communities (e.g., 12-species mock from Bakker 2018) — recovered ≥80% at genus level confirms pipeline.
- **Negative control**: DNA extraction blank + reagent blank are mandatory for soil and any low-biomass mycobiome (stool fungi <1% reads). Apply `decontam` (prevalence-based) to remove kit contaminants before analysis. Without blanks, soil mycobiome analyses are uninterpretable.
- **Known biology check**: confirm expected dominant phyla for the biome (e.g., Ascomycota + Basidiomycota dominate most soil and gut samples).

## Lessons → seeds for rules
1. **UNITE reference for ITS**
2. **ITSxpress** for ITS region extraction
3. **No strict length filter** in DADA2
4. **FUNGuild functional annotation**
5. **Genus-level safer than species** for fungi
6. **Fungal-specific extraction** (mechanical lysis stronger needed)
7. **Co-amplification check** (host plant)
