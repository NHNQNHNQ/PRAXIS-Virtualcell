---
case_id: NEG-PEARSON-ONLY
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 4
task: marker_colocalization_quantification
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: dish
channel_count: 2
dataset_accession: null
antibodies_rrid: []
software_versions:
  scikit-image: ">=0.22"
tools: [Pearson r alone, scipy.stats.pearsonr, no Manders, no Costes randomization]
key_paper_doi: 10.1111/j.1365-2818.2006.01706.x
provenance:
  source_type: literature
  doi: 10.1111/j.1365-2818.2006.01706.x
  citation: "Bolte S, Cordelières FP. A guided tour into subcellular colocalization analysis in light microscopy. J Microsc. 2006;224(3):213-232. (defines multi-method consensus standard; shows Pearson alone misleading)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, pearson_only, no_manders, no_costes, no_consensus, colocalization]
causal_tag: causal
---

# NEG-PEARSON-ONLY — Pearson correlation alone for colocalization

## What this NEG- case records
**Anti-pattern**: reporting Pearson r as the single colocalization metric for a 2-channel fluorescence image, without also reporting Manders coefficients (M1, M2) AND Costes block-shuffle randomization p-value.

## Where the failure mode was published
Bolte 2006 J Microsc — the canonical colocalization methodology paper — shows that Pearson alone has 3 well-known failure modes: (1) high background masks true colocalization (low r despite real co-occupancy); (2) high Pearson with negative-correlation patches misleading; (3) no statistical control for spatial null.

## Mechanism — why each single metric fails
- **Pearson r**: pixel-pair linear correlation; insensitive to fraction of overlap, sensitive to background.
- **Manders M1, M2**: fraction of channel-A pixels that overlap channel-B-positive pixels (and vice versa); correctly captures partial overlap, but vulnerable to thresholding choice.
- **Costes block-shuffle randomization**: randomizes pixel blocks to compute the spatial null; provides p-value rejecting "could have occurred by chance".

The 3-method consensus is the field standard precisely because no single metric is robust on all 3 failure modes simultaneously.

## Concrete numerics (from PRAXIS-Cell `cell-005` validated_run)
On synthetic high-coloc 2-channel image:
- Pearson 0.89 (high correlation)
- Manders M1 0.71 / M2 0.68 (partial-overlap quantification)
- Costes p = 0.005 (significant vs spatial null)
On random control image: Pearson 0.0, Manders ≈ 0, Costes p > 0.5 — all 3 agree on null.

## ★ Reviewer hard-stop
Any colocalization design plan that reports only Pearson r (no Manders M1/M2, no Costes randomization) for a publication-bound result must be vetoed. Required: 3-method consensus.

## Maps to anti-rule
**anti-rule #4**: Pearson alone for colocalization is forbidden. Required: Pearson + Manders + Costes block-shuffle.

## Anti-retrieval keywords
pearson only, single colocalization metric, no manders, no costes, no randomization, no consensus, scipy pearsonr alone
