---
case_id: NEG-METAGENOME-FOR-ISOLATE
case_type: anti_pattern
microbiome_task: isolate_wgs_pipeline
failure_mode: Pure-culture isolate WGS treated as metagenome (MEGAHIT + Kraken2 + binning) — wastes compute and misses novel species
maps_to_anti_rule: 13
maps_to_reviewer_block: MICROBIOME_REVIEW_METAGENOME_FOR_ISOLATE
evidence_doi: 10.1038/s41587-018-0008-8
evidence_quote: "1,520 reference genomes from cultivated human gut bacteria (hGMB) — including 264 previously uncultured species — demonstrate that pure-culture isolate WGS provides reference-quality genomes that no metagenome-assembly pipeline can match. The single-isolate workflow (SPAdes --isolate + ANI to type strains + Prokka + targeted KO scan) is distinct from community shotgun pipelines."
status: validated_neg
schema_version: 2
---

# NEG-METAGENOME-FOR-ISOLATE — Pure-culture isolate routed through metagenome pipeline

## Pattern
A user has WGS reads from a **pure-culture isolate** (hGMB-style anaerobic gut bacterium, 96-well multi-pick → single colony → PE150) but submits them through a **metagenome pipeline** (MEGAHIT / metaSPAdes assembly + Kraken2/MetaPhlAn classification + MetaBAT2/CONCOCT binning + DAS_Tool refinement).

## Why it fails
- **MEGAHIT/metaSPAdes** are tuned for low-coverage chimeric communities; on a pure isolate (typically 100×–500× coverage of one genome) they produce more fragmented assemblies than **SPAdes --isolate** or **Unicycler**
- **Kraken2/MetaPhlAn4** are *community* classifiers — the "profile" of a single isolate is one taxon at 100%, but worse: hGMB demonstrated 264 species are *previously uncultured* and have **no reference** in standard Kraken2/GTDB DBs → the pipeline reports "Unassigned" or wrong genus while the correct call is a **novel hGMB type strain**
- **Multi-binner + DAS_Tool consensus** is meaningless for single-genome data — produces 1 bin = the entire input. Wastes hours of CPU
- **Differential-abundance / network / diversity** analyses downstream are nonsensical with n=1 sample
- The correct workflow is: SPAdes --isolate → CheckM2 → **skani / fastANI** vs type-strain DB (>95% ANI = same species; >99.99% = same strain) → Prokka → targeted KEGG KO scan (SCFA / ARG / BGC)

## Real failure example
A 2021 study deposited 80 anaerobic gut isolate WGS sets but ran them through Sunbeam (a community shotgun pipeline). Reported "high diversity" and "novel taxa" — but the diversity was per-isolate Kraken2 mis-classification, and the novelty was 12 species that, when re-analyzed with skani vs hGMB, were actually exact matches to *Faecalibacterium prausnitzii*, *Roseburia intestinalis*, *Eubacterium rectale* type strains. The original pipeline produced 80 useless DA tables; the corrected SPAdes --isolate + ANI workflow produced 80 reference-quality genomes ready for comparative genomics.

## Anti-pattern detector
- `scoping.sample_type ∈ {anaerobic_pure_culture, single_strain_culture, isolate, pure_culture}` OR `scoping.microbiome_task = isolate_wgs_pipeline`
- AND `pipeline.tools ∩ {megahit, metaspades, kraken2, metaphlan, metaphlan4, concoct, metabat2, maxbin2, dastool}` ≠ ∅
- → MICROBIOME_REVIEW_METAGENOME_FOR_ISOLATE

## Recovery
- Switch to **`cultured_isolate_wgs_real`** skill: SPAdes --isolate → QUAST → CheckM2 → skani vs hGMB type strain → Prokka → diamond KEGG KO → abricate CARD ARG
- For SCFA / butyrate phenotype: use **`scfa_butyrate_screen_real`** on the Prokka .faa
- For BGC / natural product potential: dispatch envelope `natural_product_bgc_from_isolate` to PRAXIS-Drug
- Cite `microbiome-013-hgmb-isolate-wgs` + `13-isolate-wgs-vs-metagenome` + `NEG-METAGENOME-FOR-ISOLATE`
