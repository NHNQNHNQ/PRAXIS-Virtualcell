---
case_id: vcell-001-bootstrap
schema_version: 1
task: perturbation_response_prediction
input_data: scRNA-seq baseline + perturbation spec
image_modality: null
sample_dimension: null
cell_type: generic
assay_format: null
channel_count: null
dataset_accession: null
antibodies_rrid: []
software_versions: {}
tools: [Coordinator, ExperienceQuery, EvalAgent]
key_paper_doi: null
provenance:
  source_type: bootstrap
  doi: null
  citation: "PRAXIS-virtualcell bootstrap seed (no literature)."
  extracted_at: 2026-06-11
  extraction_confidence: low
  unverified_details: ["placeholder case; replaced by real perturbation cases in Week 3/5"]
tags: [bootstrap, placeholder, virtualcell]
status: draft
---

# Bootstrap case

This draft seeds the VirtualCell brain so that retrieval and loading have a
minimal structured record. It is not a literature case or a measured benchmark.

The associated rule in `memory/rules/_default_bootstrap.md` requires traceable
benchmark comparisons, species applicability checks, marked simulation outputs,
and honest abstention reporting. Scientific evaluation records are maintained
separately in `reports/science` and the reproducibility guide.
