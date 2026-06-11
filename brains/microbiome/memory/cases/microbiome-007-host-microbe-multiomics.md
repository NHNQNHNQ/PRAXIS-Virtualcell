---
case_id: microbiome-007-host-microbe-multiomics
task: host_microbiome_multiomics_integration
input_data: paired host RNA-seq + microbiome 16S + serum metabolomics
tools: [MOFA+, mixOmics, MaAsLin2, MIMOSA, NetCoMi]
key_paper_doi: 10.1126/science.aau5812
status: validated
microbiome_task: multiomics
sequencing_type: shotgun_short
sample_type: human_gut
reference_db: GTDB R220 + UniRef90 + KEGG
dataset_accession: PRJNA398089
biomass_estimate: high
---

# Host-microbe multi-omics 整合：IBD 研究范例

## Background
Host-microbe interaction 是 microbiome research 终极目标。Single-omics correlate microbe-disease；multi-omics integrate host transcriptome + microbiome + metabolome → mechanism。IBD（inflammatory bowel disease）研究 like HMP IBD 是经典 case。

## What I actually did
1. **Inputs paired**：每 sample 同时有 host RNA-seq counts + microbiome ASV table + serum / fecal metabolomics
2. **Per-omics QC + normalize**：
   - Host RNA: VST (variance stabilizing transform)
   - Microbiome: CLR (centered log-ratio) for compositionality
   - Metabolome: log + scale
3. **MOFA+**：unsupervised joint factor analysis → factor 解释跨 omics variance
4. **Per-factor 解读**：dominant features in each omics → biological story
5. **Mediation analysis**：microbe → metabolite → host transcript causal chain
6. **MIMOSA**：metabolite production by microbiome (predicted from metagenome) vs measured metabolite → identify microbe contributing
7. **Network inference**：correlation network across omics with permutation control
8. **Validation**：known biology (e.g., short-chain fatty acid producers ↔ butyrate metabolite ↔ host SCFA receptor expression)

## ★ 排除/不做的事
- **Per-omics independent analysis only**：integration is the value-add
- **CLR not applied to microbiome**：compositional bias confound integration
- **Single-method integration**：MOFA + mixOmics + MIMOSA cross-validate
- **Correlation = causation**：mediation / interventional study needed for true causal
- **Forget batch effect across omics**：DNA extraction / proteomics MS run 是 batch
- **Metabolite ID confidence ignored**：MS-derived metabolite ID confidence 等级（Level 1-4）

## ★ 失败模式
- **Inter-individual variability**：microbiome variability 跨 person > cross-condition
- **Time-lag effect**：microbe → metabolite → host effect delayed
- **Bidirectional causality**：host immune affects microbe, microbe affects host immune
- **Sample type heterogeneity**：fecal vs ileal vs colon microbiome 不同
- **Compositional bias persists**：CLR helps but doesn't eliminate
- **Sample size needed**：integration analysis needs n > 50 typically

## ★ Validation
- **Mock community + spike-in**: when feasible, spike known internal-standard organism + isotope-labeled metabolite into a subset of samples to track per-batch recovery (microbe + metabolite quantification both).
- **Negative control**: DNA extraction blank + reagent blank for shotgun arm; solvent + matrix blank for the metabolomics arm; processed identically to study samples. Run `decontam` on the microbiome side and explicit blank subtraction on the metabolomics side before integration.
- **Known biology check**: in IBD-vs-control cohorts, expect SCFA-producing genera (Faecalibacterium, Roseburia) reduced and Enterobacteriaceae expanded; concordant changes across 16S/shotgun + metabolomics + host transcriptomics serve as positive control.
- **Sensitivity analysis**: rerun MOFA+ with leave-one-omics-out to ensure no single layer dominates the latent factors.

## Lessons → seeds for rules
1. **Paired sample design** essential
2. **Per-omics correct normalization** (VST / CLR / log-scale)
3. **MOFA + mixOmics + MIMOSA** triangulation
4. **Mediation analysis** for causal chain
5. **Metabolite ID confidence Level 1-4** report
6. **Sample size ≥ 50** for integration
7. **Bidirectional causality** awareness
