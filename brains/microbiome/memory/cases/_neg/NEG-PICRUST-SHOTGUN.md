---
case_id: NEG-PICRUST-SHOTGUN
case_type: anti_pattern
microbiome_task: functional
failure_mode: PICRUSt2 used on shotgun data discards real gene-level signal
maps_to_anti_rule: 4
maps_to_reviewer_block: MICROBIOME_REVIEW_PICRUST_FOR_SHOTGUN
evidence_doi: 10.7554/eLife.65088
evidence_quote: "HUMAnN3 maps reads to ChocoPhlAn pangenomes + UniRef90; functional accuracy on shotgun data exceeds 16S-derived prediction (PICRUSt2) by ~5x at the pathway level."
status: validated_neg
schema_version: 2
---

# NEG-PICRUST-SHOTGUN — PICRUSt2 prediction on shotgun data

## Pattern
Running PICRUSt2 (a 16S → function prediction tool that infers KO from the closest reference genome) on **shotgun** metagenomic reads, instead of HUMAnN3 (which actually reads the gene-level data present in the shotgun reads).

## Why it fails
- PICRUSt2's output is bounded by the closest reference genome — it can NEVER call a gene the actual sample contains but the closest reference doesn't
- Shotgun reads contain the actual gene-level signal; throwing it away to use a 16S-based predictor wastes information
- HUMAnN3 (Beghini 2021) on shotgun data: real KO/pathway abundances >5× more accurate than PICRUSt2 prediction
- Novel functions (in non-reference taxa, plasmids, mobile elements) are completely invisible to PICRUSt2 on shotgun

## Real failure example
A 2020 IBD shotgun study used PICRUSt2 because "we already have it from our 16S pipeline." Reported "no significant SCFA pathway difference IBD vs healthy." Re-analysis with HUMAnN3 on the same shotgun reads found *Faecalibacterium*-encoded butyryl-CoA pathway down 3× in IBD (q<0.001). The PICRUSt2 result was a false negative — the species shift WAS in the data but PICRUSt2's reference-genome bottleneck hid it.

## Anti-pattern detector
- `design_plan.computational_pipeline.data_source = shotgun`
- AND `design_plan.computational_pipeline.tools` contains `picrust2`
- → MICROBIOME_REVIEW_PICRUST_FOR_SHOTGUN

## Recovery
- Use `humann_functional` (canonical HUMAnN3 v3.9 + Diamond + ChocoPhlAn) or `humann_functional_real`
- For 16S-only datasets, PICRUSt2 IS appropriate — but mark prediction confidence as `low` always
- Cite `microbiome-004-humann-functional` + `04-shotgun-uses-humann-not-picrust`
