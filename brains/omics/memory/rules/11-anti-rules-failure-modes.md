---
rule_id: 11-anti-rules-failure-modes
rule_type: anti_rule
applies_to:
  modality: ALL
  study_design: ALL
  tissue_class: ALL
  task: ALL
evidence_cases:
  - case_id: omics-001-scrna-pbmc10k-canonical
  - case_id: omics-002-scrna-kang-ifnb-integration
  - case_id: omics-003-scrna-tabula-muris-multitech
  - case_id: omics-004-bulk-tcga-brca-deseq2
  - case_id: omics-005-scrna-tumor-malignant-id
  - case_id: omics-006-spatial-slideseq-cerebellum
  - case_id: omics-007-citeseq-bmnc-wnn
  - case_id: omics-008-mofa-cll-multiomics
  - case_id: omics-009-scatac-buenrostro-hematopoiesis
  - case_id: omics-010-bulk-airway-salmon-deseq2
confidence: high
status: active
created: 2026-04-29
---

# Anti-rules — auto-rejected patterns from 10 reference cases

These are **hard rejects**. The Reviewer gate must flag any of these and force
a repair round. Do not silence — only accept with explicit user `--override`
plus a written rationale recorded in provenance.

## Cross-modality (universal)
| Anti-rule | Detection | First-seen case |
|---|---|---|
| TPM/FPKM/CPM in DE NB model | first 100 row scan; non-integer or [0,1] floats | 004, 010 |
| `batch_key = condition` (when condition is biology) | YAML diff vs Scoping | 002, 003 |
| Single-tool annotation/integration/CNV/deconv | tool count in pipeline | 001, 002, 005, 006, 007 |
| Skip doublet detection | run-log absence | 001, 005, 007 |
| Single marker for cell-type call | per-cluster marker count | 001, 003, 007 |
| No `reproduce.sh` | post-run check | all |
| Reference version mismatch | provenance fingerprint compare | 010 |

## scRNA-seq specific
| Anti-rule | Reason | Case |
|---|---|---|
| Doublet detection AFTER normalization | HVG inherits doublet artifact | 001 |
| Flat 5% mito% across tissues | clears 30% of real PBMC mono | 001, 003 |
| HVG = 500 in atlas-scale | rare cell types (pDC < 0.5%) lost | 001 |
| Leiden res=0.1 single shot | misses CD4/CD8 sub-types | 001 |
| Cell-level Wilcoxon DE with replicates | pseudoreplication; Squair 2021 FDR 30-50% | 002, 005, 011 |
| Cross-platform naive concat | dropout patterns differ | 003 |
| Skip ambient RNA correction (SoupX/CellBender) in solid tissue | TCR/BCR/surfactant/acinar genes leak into all cells | 013 |
| Use single integration method as final | Luecken 2022 benchmark — over-correction or under-correction depending on method/task | 002, 012 |

## Bulk RNA-seq specific
| Anti-rule | Reason | Case |
|---|---|---|
| Drop `donor` from paired design | KLF15 LFC 5.8 → 2.3 | 010 |
| Skip `--gcBias --seqBias` in salmon | DE rank biased by GC content | 010 |
| Hard-set `--libType ISR/ISF` without check | half reads dropped silently | 010 |
| No MultiQC gate | 50% mapping pipeline still runs | 010 |
| Mix normal + tumor samples in subtype DE | dilutes signal | 004 |

## Spatial transcriptomics specific
| Anti-rule | Reason | Case |
|---|---|---|
| Treat bead as single cell + Leiden | mixture assumption broken | 006 |
| Deconvolve without paired scRNA reference | unmappable to biology | 006 |
| Cross-puck concat without batch | per-section batch drift | 006 |

## scATAC-seq specific
| Anti-rule | Reason | Case |
|---|---|---|
| PCA on raw scATAC counts | binary signal, low information | 009 |
| Use bulk ATAC peak set | misses rare cell-type peaks | 009 |
| Keep LSI component 1 | depth proxy, contaminates clusters | 009 |
| Per-peak DE (not motif level) | signal too sparse | 009 |
| Reuse mito% threshold | scATAC has no mito reads (nuclear prep) | 009 |

## CITE-seq specific
| Anti-rule | Reason | Case |
|---|---|---|
| ADT log-normalize | ignores compositional structure | 007 |
| Skip isotype subtraction | per-cell antibody load bias | 007 |
| RNA-only doublet on CITE | CD3+CD19 doublets missed | 007 |
| `cbind` ADT into RNA matrix | scale dominance | 007 |

## Time-course specific (rule 13)
| Anti-rule | Reason | Case |
|---|---|---|
| `batch=stage` for development time-course | erases the development continuum | 015 |
| HVG cross-stage as intersection | misses stage-specific lineage markers | 015 |
| Single-seed trajectory inference | seed-sensitive, branches change | 015 |
| Treat trajectory as discrete clusters | continuous biology forced to discrete | 015 |

## Perturb-seq specific (rule 14)
| Anti-rule | Reason | Case |
|---|---|---|
| Cell-level DE on Perturb-seq | unit is perturbation, not cell | 014 |
| Raw sgRNA UMI threshold (no Mixscape) | 70-90% efficiency confounds escapers | 014 |
| Include multi-sgRNA (MOI > 1) cells | uninterpretable phenotype | 014 |
| Cross-cell-line perturbation comparison | lineage background not normalized | 014 |
| < 30 cells per perturbation | underpowered phenotype | 014 |

## Visium spatial specific (rule 07 extension)
| Anti-rule | Reason | Case |
|---|---|---|
| Standard Leiden (no spatial constraint) | misses tissue layer structure | 016 |
| Visium spot as single cell | each spot is 5-10 cell mixture | 016 |
| Cross-section concat without correction | section is independent batch | 016 |
| Layer marker as cell-type marker | SNAP25 is a layer marker, not a cell-type marker | 016 |

## Proteomics specific
| Anti-rule | Reason | Case |
|---|---|---|
| DDA + library-based search as default in 2021+ | DIA + DIA-NN is SOTA for plasma | 017 |
| Imputation before statistical test | violates assumptions; MSstats/limma model missing | 017 |
| Drop all proteins with any missing | major signal loss; > 50% missing is the cutoff | 017 |
| Skip per-run normalization (iRT) | inter-run drift dominates biology | 017 |

## Multi-omics MOFA specific
| Anti-rule | Reason | Case |
|---|---|---|
| Skip per-modality normalization | high-dim modality dominates | 008 |
| n_factors=50 default | phantom factors capture noise | 008 |
| Pre-impute before MOFA | introduces fake structure | 008 |
| Skip multi-seed reproducibility | factor unstable across seeds | 008 |

## ChIP-seq specific (rule 15)
| Anti-rule | Reason | Case |
|---|---|---|
| ChIP-seq without input control | enrichment uninterpretable | 018 |
| Replicate consistency = peak intersect (not IDR) | high false-positive rate | 018 |
| MACS2 narrow on H3K27me3 / H3K9me3 | misses broad domains | 018 |
| Skip ENCODE blacklist filter | repetitive region pseudo-enrichment | 018 |
| FRiP < 1% (narrow) / < 5% (broad) and continue | low-quality IP | 018 |
| Ignore antibody specificity validation | analysis cannot rescue bad antibody | 018 |

## Variant calling specific (rule 16)
| Anti-rule | Reason | Case |
|---|---|---|
| Single-sample calling then merge VCF | loses cross-sample power | 019 |
| Skip BQSR on Illumina data | systematic error propagates to calls | 019 |
| Hard filter on cohort ≥ 30 exomes | VQSR appropriate; hard filter loses recall | 019 |
| Mutect2 without PoN | technical artifacts called as somatic | 019 |
| Reference build mismatch (hg19 / hg38) | coordinate errors | 019 |
| Joint genotyping cross WGS+WES without recalibration | edge-of-coverage false calls | 019 |
| No GIAB / truth-set benchmark | sensitivity / precision unknown | 019 |

## RNA velocity specific (rule 17)
| Anti-rule | Reason | Case |
|---|---|---|
| Cellranger output only (no intron quant) | no spliced/unspliced matrix → no velocity | 020 |
| Steady-state model on transient state | reverse-direction arrows | 020 |
| Velocity as sole trajectory tool | rule 05 violation | 020 |
| Cell cycle confound un-regressed | cycle dominates direction | 020 |
| Cross-batch velocity merge | metabolism rate constants confound | 020 |
| Velocity on splicing-perturbed data | assumption broken | 020 |

## Metabolomics specific (rule 18)
| Anti-rule | Reason | Case |
|---|---|---|
| Skip QC pool injections | injection drift invisible; cross-batch ruined | 021 |
| Skip isotope / adduct grouping | per-feature inflation; pathway map wrong | 021 |
| Mechanistic claim on Level 3 annotation | annotation tier not certified | 021 |
| Cross-mode (pos+neg) merge as features | m/z relationships incompatible | 021 |
| No internal standard spike-in | quantitative claims unreliable | 021 |
| m/z tolerance > 10 ppm on HRMS | wrong metabolite grouping | 021 |
| Cross-instrument data merge | mass accuracy + RT incompatible | 021 |

## Multimodal paired (10x Multiome / SHARE-seq) specific
| Anti-rule | Reason | Case |
|---|---|---|
| `cbind` RNA + ATAC matrix into single PCA | scale/distribution incompatible | 022 |
| Pooled-cell peak-gene linkage (cross cell type) | 30-50% false positive due to cell-type composition | 022 |
| ATAC QC using mito% | scATAC nuclear prep has no mito reads | 022 (echoes 009) |
| Single-modality cell pass-through | cell that fails ATAC QC must not enter analysis even if RNA is fine | 022 |
| RNA-only doublet on Multiome data | misses ATAC-only doublets; need AMULET + scrublet | 022 |
| chromVAR motif without GC-matched background | GC-rich/poor regions inflate motif activity | 022 |

## Foundation model (scGPT / Geneformer / scFoundation) specific
| Anti-rule | Reason | Case |
|---|---|---|
| log1p + scale before tokenize | rank-value encoding is the input; pre-normalize destroys signal | 023 |
| Fine-tune on < 1000 cells per class | foundation models overfit on small data; from-scratch baseline often beats them | 023, 025 |
| Cross-organism zero-shot without adapter | pretrain ~95% human; mouse zero-shot drops >30% F1 (Boiarsky) | 023, 025 |
| Cross-domain (lab/disease/state) zero-shot without baseline check | FM zero-shot drops 15-25% on domain shift; baseline ~5-10% | 025 |
| In-silico KO → mechanistic claim | transformer prediction is statistical pattern, not causal; Boiarsky reproduced 1/3 of Geneformer KO predictions | 023, 025 |
| Train/val split by cell (not donor) | leakage; same donor cells in both = inflated metrics 10-20% | 023, 025 |
| Use embedding as pseudotime ground truth | embedding ≠ trajectory; use rule 17 RNA velocity | 023 |
| Tokenize max_length=2048 default for rare-TF analysis | tail genes truncated; raise to 4096 if rare TFs are critical | 023 |
| Skip baseline (PCA + LR + Harmony) comparison | Boiarsky benchmark: baseline often matches/beats FM; no improvement <3% F1 = FM not worth it | 025 |
| Pretrain corpus check skipped | cell type / disease state not in pretrain → FM hallucinates | 025 |
| Single FM benchmark leaderboard → production | leaderboard rank ≠ disease-specific task performance | 025 |

## Experimental design / batch-effect specific (foundational)
| Anti-rule | Reason | Case |
|---|---|---|
| Nested design (1 batch = 1 condition) | batch and biology fully confounded; cannot be rescued post-hoc | 026 |
| < 2 batches per condition | minimum balanced/blocked design; underpowered confound estimation | 026 |
| Skip batch covariate in DE | hundreds-thousands of false-positive "DE genes" from capture/GEM batch | 026 |
| Cluster on uncorrected PCA | PC1 often = batch in scRNA; cluster = batch artifact, not cell type | 026 |
| Skip ERCC / equivalent technical control | technical noise unquantifiable; SNR estimate unreliable | 026 |
| No PC variance breakdown report (batch vs biology) | reader cannot judge confound severity | 026 |
| Cell number per batch imbalanced > 30% | low-N batches have inflated metric variance | 026 |
| 3-batch design as final cohort | educational minimum; production cohort recommended ≥ 5 batches | 026 |

## Atlas-grade reference paper specific
| Anti-rule | Reason | Case |
|---|---|---|
| Single platform (10x only) for atlas | misses < 0.1% rare cell types (tuft, ionocyte) | 024 |
| Smart-seq2 + 10x naive concat | scale + dropout incompatible; need batch=platform | 024 |
| Lung mito% threshold ≤ 5 (PBMC default) | lung has high metabolic activity; ≤ 25 is correct | 024 (echoes 003) |
| Auto-cell-type-call without domain expert | rare cell types get merged into wrong cluster | 024 |
| < 30 cells in a candidate cell type cluster | underpowered; mark as review, not as cell type | 024 |
| Atlas paper without in-situ marker validation | spatial confirmation is publication-quality bar | 024 |
| Reference atlas without version lock in provenance | 2020 vs 2024 ontology differs; mapping inconsistency | 024 |
| Anatomical compartment confused at sampling | airway + alveoli mixed in one sample → unfixable | 024 |

## Trajectory inference specific (Saelens 2019 dynverse)
| Anti-rule | Reason | Case |
|---|---|---|
| Single trajectory tool as final | dynverse benchmark: 30-50% topology error rate per single tool | 027 |
| Linear-only tool (Wanderlust/Wishbone) on branching data | forces linear trajectory, missing multi-lineage biology | 027 |
| Cyclic data with non-cyclic-aware tool | cell cycle / circadian forced linear, missing cycle closure | 027 |
| Disconnected lineages forced into single tree (Monocle DDRTree) | builds artificial bridges between unrelated lineages | 027 |
| UMAP layout interpreted as trajectory | UMAP is dimensionality reduction, not lineage inference | 027 |
| Pseudotime treated as real time | latent ordering ≠ absolute time; needs explicit clarification | 027 |
| < 200 cells per branch + single seed | seed-sensitive, results not reproducible | 027 |
| Skip dynbenchmark reference for tool selection | rate-of-failure high without principled choice | 027 |

## Variant calling region difficulty (Krusche 2019 GIAB)
| Anti-rule | Reason | Case |
|---|---|---|
| Single global F1 reported (no region stratification) | misleads: 99% in easy region ≠ 99% in difficult region | 028 |
| Pharmacogenomics gene with standard caller | HLA/CYP2D6/KIR ~60% accuracy in segdup; need specialized | 028 |
| Long INDEL ≥ 50bp with small-variant caller | needs SV caller (Manta/GRIDSS), not GATK/DeepVariant | 028 |
| STR/VNTR with general caller | needs HipSTR / ExpansionHunter; general callers ~30% recall | 028 |
| Centromere/telomere variants reported | not callable; should be masked from output | 028 |
| Mitochondrial heteroplasmy with diploid caller | HC assumes diploid; needs mtDNA-specific (mitoSAlt) | 028 |
| GIAB truth set version not locked | v3.3 vs v4.2 not comparable; provenance must record | 028 |
| Trio data without mendelian violation check | violation rate > 1% suggests caller error | 028 |

## Cell cycle confound specific (Buettner 2015 / scLVM)
| Anti-rule | Reason | Case |
|---|---|---|
| Skip cell-cycle scoring as first-pass diagnostic | PC1 in dividing population is often cycle, not cell type | 029 |
| PC1/PC2 cluster called as cell type without cycle check | "hidden subpopulation" often = G1 / S / G2-M phases | 029 |
| Naive regress out all cycle genes in differentiating system | cycle exit IS biology (gastrulation/hematopoiesis); erases fate signal | 029 |
| Mouse cycle gene list applied to human data (or vice versa) | species-specific gene lists; mismatch = incomplete regression | 029 |
| Cancer scRNA without cycle-phase-specific regression | tumor cycle is biology AND confound; need phase-specific filter | 029 |
| Cross-batch integration without joint cycle + batch model | cycle phase imbalance per batch confounds with batch effect | 029 |
| Cluster cell-type-call when phase imbalance > 30% per cluster | call is dominated by cycle phase, not cell-state | 029 |

## How the Reviewer uses this
For each Design / Execution stage output, walk this list and flag any match in
`required_repairs`. Match = upstream agent emitted a configuration that hits
one of these anti-patterns.
