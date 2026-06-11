---
case_id: NEG-MEMBRANE-NO-STABILIZER
schema_version: 1
case_polarity: negative
sample_type: membrane_protein_complex
target_pdb: null
target_emdb: null
molecular_weight_kda: 40
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: null
detector_type: K3
detergent_or_lipid: DDM
method_choice: [ddm_only_no_stabilizer]
tools: [RELION 5, cryoSPARC v4]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1038/s41586-018-0235-7"
  citation: "Koehl A, et al. Structure of the mu-opioid receptor-Gi protein complex. Nature 2018 — establishes scFv16 as a standard GPCR-G stabilizer; absence of any stabilizer is the failure pattern this NEG- case captures"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 4
veto_reason: "40 kDa GPCR alone in DDM micelle, no fusion partner / scFv / mini-G / nanobody → microscope failure rate near 100%; below cryoEM size cutoff"
related_positive_cases: [cryo-002-membrane-protein-gpcr]
tags: [NEG, anti_pattern, GPCR_alone, no_stabilizer, DDM_only, microscope_failure]
---

# NEG-MEMBRANE-NO-STABILIZER — 40 kDa GPCR alone in DDM, microscope-failed

## Background (failure pattern)
A pure 40 kDa GPCR is solubilized in DDM detergent and frozen on grids. The detergent micelle (~80 kDa equivalent in apparent mass) dominates the projection signal. Particles cannot be aligned; the reconstruction stalls at low resolution and ambiguous orientation.

## What was actually done (the wrong path)
1. Receptor expression + DDM solubilization (no fusion partner, no scFv, no mini-G, no nanobody).
2. Grid screen → particles visible but featureless.
3. ~10k movies collected.
4. 2D classify shows mostly micelle-only blobs; 3D ab-initio fails to converge.
5. Six months of microscope time wasted before pivoting to a scFv16-stabilized prep.

## ★ Why this is forbidden
- 40 kDa is below the cryoEM size cutoff for SNR-driven alignment.
- DDM micelles add ~80 kDa of low-information signal that the picker / aligner cannot distinguish from the receptor.
- Fusion partners (BRIL, mini-Gs/i, T4 lysozyme) and antibody fragments (scFv16, nanobody) are STANDARD for GPCR cryoEM precisely because of this.

## ★ Anti-rule mapping
**anti-rule 4**: membrane protein < 200 kDa AND no stabilizer (fusion / scFv / mini-G / nanobody / nanodisc / amphipol) listed in design plan → Reviewer veto.

## Mitigation (rule 03-membrane-stabilizer-required)
- See rule 03 for the stabilizer decision matrix.
- Below 100 kDa membrane protein: stabilizer is mandatory; pure-detergent prep should be REJECTED at scoping.
