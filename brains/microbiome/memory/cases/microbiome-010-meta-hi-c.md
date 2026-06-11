---
case_id: microbiome-010-meta-hi-c
task: meta_hi_c_proximity_ligation
input_data: shotgun metagenomics + Meta3C / proxiMeta proximity ligation reads
tools: [bin3C, MetaCC, ProxiMeta (commercial Phase Genomics), HiC-Pro]
key_paper_doi: 10.1038/s41587-021-01057-5
status: validated
microbiome_task: hi_c
sequencing_type: hi_c
sample_type: mock_community
reference_db: GTDB R220
dataset_accession: PRJNA413092
biomass_estimate: high
---

# Meta Hi-C：proximity ligation 改善 binning + plasmid-host linking

## Background
Standard MAG binning 难以 resolve close-related strains + 难以 attribute plasmid/phage to host。Meta Hi-C / Meta3C = proximity ligation in metagenome 让 same-cell DNA 物理 link → resolve 同 cell co-localized DNA。**显著提升 binning quality + 找 plasmid-host interaction**。

## What I actually did
1. **Sample prep**：shotgun + parallel Meta Hi-C library
2. **Standard MAG pipeline first**：assembly + standard binning (MetaBAT2 etc.)
3. **Hi-C alignment**：Hi-C reads → assembled contigs (bowtie2 paired-end mapping)
4. **bin3C / MetaCC**：use Hi-C contact matrix to refine MAG bins → 同 cell contigs cluster together
5. **Plasmid-host linking**：plasmid contigs 与 chromosome contigs 共 cell → Hi-C contact map
6. **Phage-host linking**：similar approach for prophage / lytic phage host
7. **Quality**：CheckM2 quality should improve vs standard binning
8. **Validation**：known plasmid-host pair (e.g., E.coli K-12 plasmid F) recovered

## ★ 排除/不做的事
- **Standard MAG binning when Hi-C 可用**：information loss
- **Hi-C library prep error not QC'd**：bad ligation efficiency 让 Hi-C signal weak
- **Restriction enzyme choice 不 considered**：DpnII vs Sau3AI vs HindIII 不同 GC bias
- **Skip standard binning step**：bin3C uses standard bins as input
- **Sample size insufficient for plasmid linking**：rare plasmids need more reads
- **Cross-sample Hi-C 直接 compare**：每 sample 独立处理

## ★ 失败模式
- **Low Hi-C signal**：ligation efficiency varies, low signal samples 不能 use
- **Restriction enzyme bias**：GC-bias 让某些 region under-represented
- **Strain heterogeneity 仍 challenge**：same species different strains 难分
- **Computational complexity**：Hi-C matrix 大
- **Spurious contacts**：ligation noise 让 cross-cell contact apparent
- **Specialized library prep**：not all sample 有 Hi-C library, 与 standard metagenome incompatible

## ★ Validation
- **Mock community**: 5–10 known genomes mixed in known proportions, processed through both standard shotgun and Hi-C library prep. Pass criterion: ≥80% of input genomes recovered as high-quality MAGs (>90% completeness, <5% contamination), AND Hi-C-augmented bins assign each plasmid to its correct host genome.
- **Negative control / library QC**: Hi-C library prep itself acts as a control surface — ligation efficiency QC (cis/trans contact ratio) flags low-signal libraries. For DNA extraction, an extraction blank is still required since contaminating reads can produce spurious Hi-C contacts. ProxiMeta / bin3C ship with a noise model that explicitly down-weights low-confidence contact edges.
- **Cross-validation**: compare Hi-C bins against MetaBAT2/CONCOCT/MaxBin2 + DAS_Tool consensus; high Jaccard overlap on the high-quality MAGs validates pipeline; major divergence on novel bins should be flagged for manual inspection.

## Lessons → seeds for rules
1. **Hi-C augmented binning > standard alone**
2. **bin3C / MetaCC** for MAG refinement
3. **Plasmid-host linking** unique advantage
4. **Library QC** mandatory (ligation efficiency)
5. **Restriction enzyme choice** report
6. **Sample-by-sample independent** processing
7. **Cross-validation with standard bins**
