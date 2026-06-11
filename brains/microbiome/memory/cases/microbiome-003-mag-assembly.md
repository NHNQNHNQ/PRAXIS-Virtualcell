---
case_id: microbiome-003-mag-assembly
task: metagenomic_assembled_genome_recovery
input_data: shotgun metagenomic reads (≥ 50 GB sequencing for complex sample)
tools: [MEGAHIT, metaSPAdes, MetaBAT2, CONCOCT, MaxBin2, DAS_Tool, CheckM2, GTDB-tk]
key_paper_doi: 10.1186/s40168-020-00990-y
status: validated
microbiome_task: mag_assembly
sequencing_type: shotgun_short
sample_type: mock_community
reference_db: GTDB R220
dataset_accession: PRJNA316126
biomass_estimate: high
---

# MAG 装配：从 metagenome 拿 species-level genome

## Background
MAGs (Metagenome-Assembled Genomes) = 从 metagenome 中 binning + recover 单 species genome。**适合**：novel species 发现、functional annotation per genome、horizontal gene transfer 分析。Pipeline：assemble → bin → quality check → taxonomy。

## What I actually did
1. **Assembly**：MEGAHIT (fast) 或 metaSPAdes (sensitive) → contigs
2. **Mapping**：reads back to contigs (bowtie2) → coverage per contig
3. **Binning**：
   - **MetaBAT2**：tetranucleotide composition + coverage
   - **CONCOCT**：similar
   - **MaxBin2**：marker gene-based
   - **DAS_Tool**：consensus from multiple binners → best bins
4. **Quality (CheckM2)**：completeness > 50% + contamination < 5% = medium quality MAG; > 90 / < 5 = high quality
5. **Taxonomy (GTDB-tk)**：classify MAGs to GTDB taxonomy → identify novel species (no close DB match)
6. **dRep dereplication**：100s of MAGs → cluster at 95% ANI → species-level representatives
7. **Functional annotation**：Prokka + Pfam + KEGG per MAG
8. **Output**：dereplicated MAG set + quality metrics + taxonomy + function

## ★ 排除/不做的事
- **Single binner only**：DAS_Tool consensus 给 best bins
- **Low completeness (< 50%) MAGs trust as genome**：incomplete genome misleads functional analysis
- **Skip dereplication**：跨 sample 同 MAG 多次出现，unique species count 错
- **Single sample MAG**：cross-sample assembly + binning recovers more species
- **CheckM v1**：CheckM2 ML-based 准且快
- **Forget viruses / fungi**：specific pipelines (VirSorter / EukRep)

## ★ 失败模式
- **Low coverage species miss**：rare species 不够 reads to assemble
- **Strain heterogeneity 混 binning**：multiple strain of same species → fragmented bins
- **Mobile genetic elements (plasmid / phage)** miss-binned
- **Assembly fragmentation**：highly diverse / repeat-rich samples → many short contigs
- **rRNA gene assembly**：highly conserved rRNA genes 不 assemble well in MAGs
- **Compute resources**：50 GB metagenome assembly 100+ GB RAM, days

## Lessons → seeds for rules
1. **MEGAHIT for fast / metaSPAdes for high quality**
2. **Multi-binner + DAS_Tool consensus**
3. **CheckM2** for quality
4. **GTDB-tk for taxonomy**
5. **dRep dereplicate** before downstream
6. **Cross-sample assembly** for low abundance
7. **Compute / RAM planning** essential
