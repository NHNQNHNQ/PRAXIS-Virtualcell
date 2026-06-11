---
case_id: NEG-CLUSTER-NO-ANCHOR
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 7
task: phenotype_landscape_clustering
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: U2OS
assay_format: 384well
channel_count: 6
dataset_accession: null
antibodies_rrid: []
software_versions:
  scanpy: ">=1.10"
  hdbscan: ">=0.8"
tools: [Leiden cluster, HDBSCAN, no reference compound, no MoA anchor, no LINCS lookup]
key_paper_doi: 10.1038/nprot.2016.105
provenance:
  source_type: literature
  doi: 10.1038/nprot.2016.105
  citation: "Bray M-A et al. Cell Painting, a high-content image-based assay for morphological profiling using multiplexed fluorescent dyes. Nat Protoc. 2016;11(9):1757-1774. (defines reference compound anchor protocol; shows clusters are uninterpretable without anchors)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, cluster_no_anchor, no_reference, no_moa, no_lincs, phenotype_landscape]
causal_tag: causal
---

# NEG-CLUSTER-NO-ANCHOR — Phenotype cluster without reference compound MoA anchor

## What this NEG- case records
**Anti-pattern**: running Leiden / HDBSCAN / KMeans on a Cell Painting compound × feature matrix and reporting the cluster IDs as the result, without first including known-MoA reference compounds (e.g., taxol = microtubule, latrunculin = actin, MG132 = proteasome) as cluster anchors.

## Where the failure mode was published
Bray 2016 Nat Protoc — the canonical Cell Painting protocol — explicitly requires reference compound inclusion as a per-plate control. Without anchors, cluster IDs (cluster 0, cluster 1, …) carry no biological meaning and downstream MoA hypothesis testing is ungrounded.

## Mechanism — why it fails
- Cluster algorithms produce arbitrary integer labels.
- Without anchors, "cluster 3 contains compound X" has no actionable meaning — you don't know if cluster 3 is microtubule disruptors, actin disruptors, or generic-cytotoxic.
- Including known-MoA compounds as anchors lets you call: "cluster 3 = microtubule MoA because taxol + epothilone B + nocodazole all fall in it".
- Without anchors, every screen needs full re-annotation; with anchors, MoA hypotheses transfer across plates.

## Concrete numerics (from PRAXIS-Cell cell-010 validated_run)
- Synthetic 800 compounds × 1500 features × 5 known MoAs (microtubule, DNA-damage, kinase-inhib, ER-stress, DMSO).
- With reference anchor: held-out MoA matching 5/5 = 100 % (cluster centroid of training MoA-labelled compounds → predict held-out compound's MoA via nearest centroid).
- Without anchor: cluster IDs are 0..4 but no biological label; MoA matching is impossible (un-anchored cluster ID is useless).

## ★ Reviewer hard-stop
Any phenotype landscape / Cell Painting design plan that lists Leiden / HDBSCAN / KMeans output cluster IDs as the deliverable, without reference compound anchors, must be vetoed. Required: ≥ 3 known-MoA reference compounds per plate AND post-hoc cluster → MoA assignment via nearest-anchor centroid.

## Maps to anti-rule
**anti-rule #7**: Phenotype clustering without reference MoA compound anchor is forbidden. Required: ≥ 3 reference compounds + nearest-anchor MoA assignment.

## Anti-retrieval keywords
cluster no anchor, no reference compound, no moa lookup, no lincs, raw cluster id, leiden alone, hdbscan alone
