---
case_id: NEG-Z-NORM-NO-PLATE
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 3
task: high_content_screening_hit_identification
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 384well
channel_count: 4
dataset_accession: null
antibodies_rrid: []
software_versions:
  scipy: ">=1.11"
tools: [raw z-score, scipy.stats.zscore, no plate normalization, no B-score, no SSMD]
key_paper_doi: 10.1177/1087057103258285
provenance:
  source_type: literature
  doi: 10.1177/1087057103258285
  citation: "Brideau C, Gunter B, Pikounis B, Liaw A. Improved statistical methods for hit selection in high-throughput screening. J Biomol Screen. 2003;8(6):634-647. (defines B-score; quantifies how raw Z fails on edge-effect plates)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, raw_z_score, no_plate_normalization, no_b_score, edge_effect, hcs]
causal_tag: causal
---

# NEG-Z-NORM-NO-PLATE — Raw Z-score plate analysis without B-score / SSMD

## What this NEG- case records
**Anti-pattern**: scoring HCS hits using `(x - mean) / std` of all wells on a plate, without first removing row/column edge effects via median-polish (B-score) or applying SSMD with separate negative + positive control populations.

## Where the failure mode was published
Brideau 2003 J Biomol Screen — the canonical B-score paper — quantifies that raw Z on a plate with row/column edge effects (typical for 384-well + 1-3 % evaporation gradient) inflates false-positive rate at edges by 5-10×. The paper explicitly recommends median-polish first.

## Mechanism — why it fails
- 384-well plates have a 5-10 % intensity gradient from edges to center (evaporation, temperature, dispenser path).
- Raw Z-score uses the plate's global mean + SD, which aliases the edge effect into the test statistic.
- Wells at the edge get systematically high or low Z without any biology behind it.

## Concrete numerics (from PRAXIS-Cell `cell-002` validated_run on synthetic edge-effect plate)
- Raw-Z recall on planted hits: **0.81**
- B-score recall on same plate: **0.94**
- B-score recovers 13 pp recall by removing the edge gradient
- SSMD with positive-control population: -3.44 (clean separation), DMSO median z ≈ 0

## ★ Reviewer hard-stop
Any HCS design plan that lists raw Z-score (or `scipy.stats.zscore`) as the only normalization, on a plate format ≥ 96-well, must be vetoed. Required: median-polish B-score OR per-plate DMSO median+MAD robustize OR SSMD with explicit positive-control population.

## Maps to anti-rule
**anti-rule #3**: Raw plate-level Z-score without B-score / SSMD on HCS data is forbidden. Required: median-polish B-score or per-plate DMSO median+MAD.

## Anti-retrieval keywords
raw z-score plate, scipy zscore, no plate normalization, no b-score, no ssmd, no median polish, edge effect ignore
