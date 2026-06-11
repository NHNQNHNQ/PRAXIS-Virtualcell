---
case_id: microbiome-008-cooccurrence-network
task: microbial_cooccurrence_network
input_data: ASV abundance across 100+ samples
tools: [SparCC, SPIEC-EASI, NetCoMi, FlashWeave]
key_paper_doi: 10.1371/journal.pcbi.1002687
status: validated
microbiome_task: network
sequencing_type: 16S
sample_type: human_gut
reference_db: null
dataset_accession: null
biomass_estimate: high
---

# Co-occurrence network：keystone species + microbial interaction inference

## Background
Microbial co-occurrence network 推 species 间 (positive 共生 / negative 拮抗) interaction。**陷阱**：compositionality 让 standard Pearson 大量 spurious correlation。SparCC / SPIEC-EASI 是 compositionality-aware。

## What I actually did
1. **Input**：ASV count table, 100+ samples (sufficient for correlation)
2. **Filter**：prevalence > 20% sample, abundance > 0.01% mean
3. **SparCC**：Sparse Correlations for Compositional data，iterative log-ratio transform
4. **SPIEC-EASI**：sparse inverse covariance via lasso，partial correlation (controls indirect)
5. **Bootstrapping**：100 bootstrap replicates → edge confidence
6. **Network construction**：edges with |correlation| > 0.3 + bootstrap support > 80% + adj p < 0.05
7. **Topology**：degree centrality, betweenness → keystone species (high centrality + connectivity)
8. **Module detection**：Louvain / Leiden → community of co-occurring species
9. **Visualization**：Cytoscape / igraph

## ★ 排除/不做的事
- **Pearson on raw count**：compositionality 假阳率 > 50%
- **Single method**：SparCC + SPIEC-EASI + FlashWeave triangulate
- **No bootstrap confidence**：single estimate noise
- **Edge threshold too liberal (|r| > 0.1)**：random correlations dominate
- **Forget sample size requirement**：< 50 sample correlation noisy
- **Static network without time / condition**：dynamic interactions 更生物 meaningful

## ★ 失败模式
- **Spurious correlation in compositional data**：even compositionality-aware tools 不完美
- **Indirect correlations**：A → B and A → C 让 B-C 也 correlate
- **Differential abundance confound**：condition shift 让所有 species correlate
- **Bias from rare species**：low abundance highly variable correlation
- **Cross-domain interaction miss**：bacteria-fungi 经常 co-occur 但 single-domain analysis 漏
- **Causality vs correlation**：edge ≠ direct interaction (intervention needed for causal)

## Lessons → seeds for rules
1. **Compositionality-aware methods** (SparCC / SPIEC-EASI / FlashWeave)
2. **≥ 50 samples** for stable correlation
3. **Bootstrap confidence** mandatory
4. **Multi-method consensus**
5. **Filter edge threshold + adj p**
6. **Cross-domain (fungi + bacteria)** combined network
7. **Causal inference caveat** for any inferred interaction
