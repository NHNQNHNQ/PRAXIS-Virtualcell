---
case_id: NEG-SINGLE-BINNER
case_type: anti_pattern
microbiome_task: mag_assembly
failure_mode: Single-binner MAG recovery misses 20-40% of recoverable genomes
maps_to_anti_rule: 3
maps_to_reviewer_block: MICROBIOME_REVIEW_SINGLE_BINNER
evidence_doi: 10.1186/s40168-020-00990-y
evidence_quote: "Each binning algorithm uses different signals (composition vs coverage); consensus via DAS_Tool recovers 20-40% more high-quality MAGs than any single binner."
status: validated_neg
schema_version: 2
---

# NEG-SINGLE-BINNER — MetaBAT2-only or CONCOCT-only without DAS_Tool consensus

## Pattern
Running **only** MetaBAT2 (or CONCOCT, or MaxBin2) on a metagenome assembly without DAS_Tool consensus aggregation. Reporting MAGs from a single binner as final.

## Why it fails
- MetaBAT2 uses tetranucleotide composition + differential coverage
- CONCOCT uses Gaussian mixture on composition + coverage with different priors
- MaxBin2 uses single-copy gene markers + composition
- Each algorithm misses different genomes; ensemble recovers 20-40% more high-quality MAGs
- Without DAS_Tool consensus, you ship low-quality bins (chimeric / contaminated / fragmented)

## Real failure example
The UHGG (Almeida 2021) re-analysis ran MetaBAT2 alone on existing assemblies, recovered ~120k MAGs. Adding CONCOCT + MaxBin2 + DAS_Tool boosted to ~150k MAGs (+25%) and reduced contamination >5% rate from 18% → 4%.

## Anti-pattern detector
- `microbiome_task = mag_assembly`
- AND (`design_plan.computational_pipeline.binners.length < 2` OR DAS_Tool not in pipeline)
- AND CheckM2 not run (no quality gate)

## Recovery
- Use `mag_assembly_pipeline` (canonical: MEGAHIT + MetaBAT2 + CONCOCT + MaxBin2 + DAS_Tool + CheckM2 + GTDB-tk + dRep)
- Cite `microbiome-003-mag-assembly` + `03-multi-binner-consensus`
