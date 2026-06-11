---
case_id: NEG-COPY-NUMBER-IGNORED
case_type: anti_pattern
microbiome_task: amplicon_16s
failure_mode: 16S read counts treated as cell counts despite 1–15× rRNA operon copy-number variation across taxa
maps_to_anti_rule: 11
maps_to_reviewer_block: MICROBIOME_REVIEW_COPY_NUMBER_IGNORED
evidence_doi: 10.1093/femsre/fuy016
evidence_quote: "Bacterial 16S rRNA gene copy number varies from 1 (Mycoplasma, most Bifidobacterium) to ≥15 (Bacillus, Clostridium, some Enterobacteriaceae). Treating raw read counts as proportional to cell counts overestimates high-copy-number taxa by up to 15× and biases all downstream alpha-diversity, beta-diversity, and abundance comparisons."
status: validated_neg
schema_version: 2
---

# NEG-COPY-NUMBER-IGNORED — 16S read counts treated as cell counts

## Pattern
Treating 16S amplicon read counts (or relative abundances) as if they directly equal cell-count abundance, without applying rrnDB or PICRUSt2's `add_descriptions.py --copy_number` correction. Especially common when comparing across phyla with very different copy numbers (Firmicutes ~6, Actinobacteria ~3, Proteobacteria ~5, *Bifidobacterium* ~2).

## Why it fails
- 16S copy number varies 1–15× across bacteria (Stoddard 2015, rrnDB)
- A *Clostridium difficile* (12 copies) cell contributes 12× more 16S reads than a *Bifidobacterium longum* (2 copies) cell at the same biomass
- Without copy-number correction, "*Clostridium* up 6×" might mean "no biomass change, just more rRNA per cell"
- Affects alpha-diversity (Shannon overweights high-copy taxa), beta-diversity (UniFrac branch lengths skew), and DA (false hits proportional to ratio of copy numbers)
- shotgun does NOT have this problem (each cell = 1 genome ~= proportional read recruitment)

## Real failure example
A 2019 dietary intervention 16S study reported "high-fiber diet doubled *Lachnoclostridium* abundance (q=0.001)." After rrnDB copy-number correction (*Lachnoclostridium* has 7–9 copies), the corrected effect was 1.2× (q=0.18) — non-significant. The "doubling" was explained by a small subpopulation shift toward higher-copy strains, NOT by biomass increase. The corrected interpretation (no significant increase) was the right one.

## Anti-pattern detector
- `design_plan.computational_pipeline.amplicon_target` ∈ {`16S`, `16S_V3V4`, `16S_V4`}
- AND `design_plan.computational_pipeline.copy_number_correction` is missing OR set to `false` / `none`
- AND `design_plan.computational_pipeline.task` ∈ {`alpha_diversity`, `beta_diversity`, `differential_abundance`, `quantitative_comparison`}
- → MICROBIOME_REVIEW_COPY_NUMBER_IGNORED

## Recovery
- Apply rrnDB copy-number normalization (download `rrnDB-5.8_pantaxa_stats_NCBI.tsv`) BEFORE quantitative comparison, OR
- Use PICRUSt2's `metagenome_pipeline.py` which divides by predicted copy number internally, OR
- Switch to shotgun (no copy-number bias)
- ALWAYS report copy-number assumption in methods + label inferences as "16S-relative" not "cell-count" if uncorrected
- Cite `microbiome-011-copy-number` + `NEG-COPY-NUMBER-IGNORED`
