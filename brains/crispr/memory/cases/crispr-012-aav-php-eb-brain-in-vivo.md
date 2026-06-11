---
case_id: crispr-012-aav-php-eb-brain-in-vivo
schema_version: 1
edit_type: in_vivo_gene_therapy
target_gene: any
target_organism: mm10
cell_context: in_vivo_organ
editing_system: SaCas9
delivery_method: AAV
tools:
- AAV-PHP.eB capsid
- single-AAV SaCas9
- tissue-specific Syn1 promoter
- RNA-seq for transduction quantification
- brain section IHC
key_paper_doi: 10.1038/nn.4593
status: validated
provenance:
  source_type: literature
  doi: 10.1038/nn.4593
  citation: Chan KY, Jang MJ, Yoo BB et al. (2017) Nat Neurosci 20:1172-1179 — Engineered
    AAVs for efficient noninvasive gene delivery to the central and peripheral nervous
    systems
  extracted_at: '2026-04-29'
  source: praxis_seed_v0.2
cell_context_list:
- in_vivo_organ
- neuron
- in_vivo_brain
editing_system_list:
- SaCas9
- SpCas9
- dCas9-VPR
delivery_method_list:
- AAV
- AAV9-PHP.eB
- AAV9-PHP.B
tags:
- in_vivo_gene_therapy
- brain
- AAV-PHP.eB
- BBB_crossing
- mouse_specific
- SaCas9
- Syn1_promoter
- intravenous
---

# AAV-PHP.eB — brain-wide CRISPR delivery via systemic injection

## Background
Standard AAV9 transduces brain at low efficiency (<5% neurons) when injected intravenously because the blood-brain barrier (BBB) blocks viral particles. **AAV-PHP.eB** (Chan 2017) is an engineered AAV9 capsid variant identified by directed evolution (CREATE selection) that crosses the BBB **~40× more efficiently** in C57BL/6J mice. A single tail-vein injection at 1×10¹² viral genomes per mouse transduces ~70% of NeuN+ neurons across cortex, striatum, cerebellum, and hippocampus — enabling **brain-wide CRISPR editing without stereotactic surgery**.

The huge caveat: PHP.eB efficiency is **mouse-strain-specific** (works great in C57BL/6, much weaker in BALB/c) and **does not translate to non-human primates or humans** (Liguore 2019 confirmed near-zero NHP transduction). PHP.eB is therefore a **research tool, not a clinical vector**.

## What I actually did
1. **Capsid choice**: AAV-PHP.eB (or earlier PHP.B) packaged with single-AAV SaCas9 cassette (4.2 kb fits in AAV's 4.7 kb cargo).
2. **Cargo**: U6-sgRNA + neuron-specific Syn1 promoter → SaCas9 + miniature polyA. Total ~4.5 kb.
3. **Dose**: 1-2 × 10¹² vg per adult mouse, IV (tail vein).
4. **Readout** (4-8 weeks post-injection): brain dissection → cortex/striatum/cerebellum/hippocampus IHC for HA-tagged SaCas9; amplicon-seq at target locus for indel rate; behavioral assays for functional KO.
5. **Typical efficiency**: ~70% NeuN+ cortical neurons SaCas9+; 30-60% indel at target locus per cell.
6. **Strain QC**: confirm C57BL/6J background; PHP.eB does NOT work in BALB/c, NOD/SCID, or many other strains.

## ★ 排除/不做的事
- **Using PHP.eB in non-C57BL/6 strains without pre-screen** — efficiency drops 10-100× in many other inbred strains.
- **Using PHP.eB in NHP/human translation studies** — does NOT cross primate BBB; revert to direct CNS injection (intracerebroventricular / intrathecal AAV9).
- **Single-AAV SpCas9 (4.2 kb CDS + sgRNA + promoter + polyA → 4.8 kb)** — exceeds AAV cargo limit; use SaCas9 (3.2 kb) or dual-AAV split.
- **CMV / CAG promoter for neuron-restricted KO** — drives expression in glia / endothelium too; use Syn1 (neuron) or GFAP (astrocyte) tissue-specific promoter.
- **AAV pre-existing NAb pre-screen for PHP.eB clinical** — irrelevant; PHP.eB is preclinical-only.
- **Long-term Cas9 expression assumed safe in brain** — adult neurons are post-mitotic, so editor accumulation persists; transient AAV expression is impossible without dilution.

## ★ 失败模式
- **Strain background drift** — colony C57BL/6J → C57BL/6N drift over generations; PHP.eB efficiency varies.
- **Astrocyte / oligodendrocyte off-target transduction** — Syn1 promoter helps but isn't perfectly neuron-restricted.
- **Peripheral organ transduction** — IV PHP.eB also lands in liver, heart, dorsal root ganglia (high); off-tissue editing unavoidable without local injection.
- **Immune response to bacterial Cas9** — chronic SaCas9 expression in CNS triggers low-grade microglial activation in some studies (Chew 2016).
- **Variable gene KO behavior in vivo** — neuronal KO lethality / circuit compensation can mask phenotype; needs orthogonal KO controls.
- **PHP.eB ↔ Ly6a receptor dependency** — efficiency depends on Ly6a expression; KO mice with Ly6a deficiency show no enhancement.

## Lessons → seeds for rules
1. **Brain-wide CRISPR via systemic AAV is mouse-only** — for NHP/human, use direct CNS injection (intracerebroventricular AAV9 or intrathecal AAVrh.10).
2. **Single-AAV SaCas9 + neuron-specific Syn1 promoter** is the canonical adult-mouse brain CRISPR cassette; SpCas9 requires dual-AAV split.
3. **C57BL/6J strain confirmation is mandatory** before assuming PHP.eB will work; pre-pilot in 2-3 mice with reporter cargo.
4. **Peripheral tissue editing is unavoidable** — IV PHP.eB transduces liver/heart/DRG; either accept off-tissue editing or switch to local injection.
5. **Long-term Cas9 expression in post-mitotic neurons** is a permanent state — once AAV transduces, editor cannot be diluted by cell division; transient delivery (mRNA / LNP) is the only safe option for clinical translation.
6. **Capsid receptor dependency** — PHP.eB requires Ly6a; future capsid engineering should screen for human-receptor analogs.
