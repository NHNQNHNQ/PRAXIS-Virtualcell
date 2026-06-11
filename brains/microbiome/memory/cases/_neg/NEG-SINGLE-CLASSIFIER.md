---
case_id: NEG-SINGLE-CLASSIFIER
case_type: anti_pattern
microbiome_task: shotgun_taxonomy
failure_mode: Single-classifier shotgun calls produce 5-15% false positive species
maps_to_anti_rule: 2
maps_to_reviewer_block: MICROBIOME_REVIEW_SINGLE_CLASSIFIER
evidence_doi: 10.1186/s13059-019-1891-0
evidence_quote: "Single-method classification can introduce systematic biases; consensus across k-mer and marker-gene approaches reduces false positives."
status: validated_neg
schema_version: 2
---

# NEG-SINGLE-CLASSIFIER — Kraken2-only or MetaPhlAn-only shotgun call

## Pattern
Running **only** Kraken2 (k-mer based) **or only** MetaPhlAn (marker-gene based) on shotgun reads and reporting species-level abundance without cross-method consensus.

## Why it fails
- Kraken2 alone: over-calls related species (e.g. *E. coli* vs *Shigella* ~95% 16S identity → confused). 5-15% false positive rate.
- MetaPhlAn alone: misses species absent from its marker catalog (newly discovered taxa, lab strains)
- The two methods make different errors → intersection = high-confidence; union = candidate-only.
- Lu & Salzberg 2020 quantified this on synthetic + real metagenomes.

## Real failure example
A 2018 gut microbiome study used Kraken2 alone, reported *Shigella flexneri* as a marker of dysbiosis. Re-analysis with MetaPhlAn showed the Shigella reads were actually commensal *E. coli* misclassified by Kraken2's k-mer overlap. The clinical "biomarker" was an artifact.

## Anti-pattern detector
- `microbiome_task = shotgun_taxonomy`
- AND `design_plan.computational_pipeline.classifier_count < 2`
- OR (skill `shotgun_taxonomy` invoked but `consensus_species.tsv` not in outputs)

## Recovery
- Use `shotgun_taxonomy` (canonical Kraken2 + Bracken + MetaPhlAn4) or `shotgun_taxonomy_real` (bowtie2 + bwa dual aligner)
- Cite `microbiome-002-shotgun-kraken` + `02-dual-classifier-shotgun`
