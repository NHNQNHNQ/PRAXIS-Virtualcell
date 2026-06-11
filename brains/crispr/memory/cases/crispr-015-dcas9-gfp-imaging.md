---
case_id: crispr-015-dcas9-gfp-imaging
schema_version: 1
edit_type: crispr_imaging
target_gene: any
target_organism: hg38
cell_context: U2OS
editing_system: dCas9-GFP
delivery_method: lentivirus
tools:
- dCas9-GFP fusion (or dCas9-mRuby for multicolor)
- MS2-PP7 sgRNA scaffold for signal amplification
- live-cell confocal microscopy
- telomere repeat sgRNA
key_paper_doi: 10.1016/j.cell.2013.12.001
status: validated
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2013.12.001
  citation: Chen B, Gilbert LA, Cimini BA et al. (2013) Cell 155:1479-1491 — Dynamic
    imaging of genomic loci in living human cells by an optimized CRISPR/Cas system
  extracted_at: '2026-04-29'
  source: praxis_seed_v0.2
cell_context_list:
- U2OS
- HeLa
- RPE-1
editing_system_list:
- dCas9-GFP
- dCas9-mRuby
- MS2-MCP-GFP
tags:
- crispr_imaging
- U2OS
- dCas9-GFP
- live_cell
- telomere
- MUC4
- repeat_loci
- signal_amplification
---

# dCas9-GFP — live-cell imaging of genomic loci

## Background
Pre-CRISPR genomic locus imaging required either FISH (fixed cells) or TALE-array probes (laborious, single-locus). **Chen 2013** (Huang/Lim labs) showed that a **catalytically dead Cas9 (dCas9) fused to EGFP** can be programmed by sgRNA to bind any genomic locus and produce a **live-cell fluorescent dot** that tracks chromosomal dynamics in real time. The killer application: live imaging of **repeat-rich loci** (telomeres ~3-10 kb of TTAGGG; centromeres; MUC4) requires only one sgRNA but produces bright signal because hundreds of dCas9-GFP molecules bind the array.

For **unique single-locus loci**, one sgRNA = one molecule = no signal; the workaround is **arrays of 30-70 sgRNAs** tiled across a 1-2 kb non-repetitive region. This is the conceptual foundation of CASFISH and later CRISPR-Sirius / SuperRA imaging methods.

## What I actually did
1. **dCas9 construct**: dSpCas9 (D10A + H840A double mutant) fused to EGFP at C-terminus, optionally with a nuclear localization signal (NLS).
2. **sgRNA design for repeat loci**: single sgRNA matching the repeat unit (e.g., telomere TTAGGG → sgRNA "GGGTTAGGGTTAGGGTTAGG"); one sgRNA recruits hundreds of dCas9-GFP to the repeat array.
3. **sgRNA design for unique loci**: 30-70 sgRNAs tiled across a 1.5-3 kb region; pooled cloning into the cell + co-expression with dCas9-GFP.
4. **Cell line**: U2OS (good for cytoplasm-to-nucleus signal contrast; flat morphology); HeLa or RPE-1 also used.
5. **Delivery**: lentivirus for stable expression; doxycycline-inducible for tunable expression (too much dCas9-GFP washes out the signal).
6. **Imaging**: spinning-disk confocal, 60-100×, live cells in CO2-controlled stage; z-stacks for 3D tracking; time-series for chromosomal dynamics.
7. **Result**: clear puncta corresponding to ~3-7 telomere ends per nucleus; track over hours; quantify telomere clustering, motion.

## ★ 排除/不做的事
- **Single sgRNA at unique non-repetitive locus** — single dCas9-GFP molecule = below imaging threshold; need ≥30 tiled sgRNAs.
- **Targeting essential / actively transcribed regions for imaging** — dCas9 binding interferes with transcription; choose intergenic or 3' UTR regions.
- **High dCas9-GFP overexpression** — saturates the nucleus with diffuse green signal; lose contrast. Tune to lowest possible expression with detectable signal.
- **Treating dCas9 binding as biologically inert** — it can transiently impede transcription, replication; observed phenotype may be off-target rather than imaging artifact.
- **Long-term dCas9-GFP expression in proliferating cells** — chromosomal binding may slow replication or cause site-specific instability over many divisions.
- **Trying to image a single chromatin locus with CMV-promoter dCas9-GFP** — CMV is too strong; use Tet-inducible or weaker promoter (EF1a / Ubc).

## ★ 失败模式
- **Diffuse nuclear signal (no puncta)** — usually too much dCas9-GFP expression; reduce promoter strength or doxycycline dose.
- **Punctum disappears during mitosis** — dCas9 dissociates from condensed chromatin; signal returns in interphase.
- **Off-target binding to similar sequences** — long sgRNA-protospacer matches at unintended loci create spurious puncta; use tiled-array specificity.
- **Locus-pair distance affected by imaging** — heavy dCas9-GFP labeling can artificially cluster homologous regions through GFP dimerization; use monomeric GFP variant (mEGFP) to mitigate.
- **Inability to image small loci (<1 kb)** — signal too weak; minimum locus size for tiled array is ~1.5 kb.
- **Cell-type variation** — cells with low chromatin accessibility (heterochromatic clones) show poor binding; use accessible cell lines (U2OS, RPE-1) for development.

## Lessons → seeds for rules
1. **Repeat-rich loci (telomere, centromere) need only 1 sgRNA**; unique loci need ≥30 tiled sgRNAs.
2. **Use catalytically dead dCas9** (D10A + H840A) — never live Cas9 for imaging.
3. **Tunable expression (Tet-inducible) is critical** — over-expressed dCas9-GFP gives diffuse background.
4. **Monomeric GFP variants (mEGFP)** prevent artifactual locus clustering via fluorophore dimerization.
5. **U2OS / HeLa / RPE-1** are the standard imaging cell lines (flat morphology, accessible chromatin).
6. **dCas9-GFP is not transcriptionally inert** — observed phenotypes may reflect dCas9 binding interference rather than pure imaging; use orthogonal controls (e.g., scrambled sgRNA arrays).
7. **For multi-color**: dCas9-mRuby + dCas9-GFP with orthogonal sgRNA scaffolds (e.g., MS2-PP7 system) enables 2-locus simultaneous imaging.
