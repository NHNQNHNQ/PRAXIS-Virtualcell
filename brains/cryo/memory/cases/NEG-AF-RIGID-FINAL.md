---
case_id: NEG-AF-RIGID-FINAL
schema_version: 1
case_polarity: negative
sample_type: any
target_pdb: null
target_emdb: null
molecular_weight_kda: 300
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 3.5
detector_type: K3
detergent_or_lipid: none
method_choice: [af_rigid_no_flexfit]
tools: [AlphaFold3]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1038/s41592-023-02087-4"
  citation: "Terwilliger TC, et al. AlphaFold predictions are valuable hypotheses and accelerate but do not replace experimental structure determination. Nat Methods 2024 — explicitly the paper warning against this anti-pattern"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 5
veto_reason: "AF prediction rigid-fit into cryoEM map, no flexfit (ChimeraX/ISOLDE), no per-residue source labels → publishes a model that is partly imagined where map disagrees"
related_positive_cases: [cryo-008-af-cryoem-hybrid]
tags: [NEG, anti_pattern, af_rigid_fit, no_flexfit, no_per_residue_source_label]
---

# NEG-AF-RIGID-FINAL — AlphaFold model published as the cryoEM model

## Background (failure pattern)
A 3.5 Å cryoEM map is collected. Instead of running AF prediction → dock_in_map → ChimeraX/ISOLDE flexfit → Phenix real_space_refine → per-residue source-label, the author rigid-fits the AF model into the map and publishes that. Where the map shows a different conformation, the published model is wrong; where the map is silent, the published model carries AF's confident-but-untested guess.

## What was actually done (the wrong path)
1. Map collected to 3.5 Å.
2. AF3 prediction generated.
3. `phenix.dock_in_map` to seat the AF model.
4. **Skipped** ChimeraX `fitmap` + ISOLDE flexfit.
5. **Skipped** per-residue source labeling (`from_AF` vs `from_map_remodel` vs `disordered`).
6. Phenix real_space_refine ONCE, deposited.

## ★ Why this is forbidden
- The map is the experimental ground truth; AF is a strong prior. Reversing this priority publishes an AF model dressed as a cryoEM model.
- Without per-residue source labels, downstream users cannot tell which residues were experimentally observed vs predicted.
- The 2024 Terwilliger paper exists precisely because this anti-pattern became common after AF2 release.

## ★ Anti-rule mapping
**anti-rule 5**: AF model used in af_cryoem_hybrid step but no flexfit logged AND/OR per-residue source labels missing → Reviewer veto.

## Mitigation (rule 10-af-cryoem-hybrid-flexfit)
- AF prediction → dock_in_map → ChimeraX `fitmap` → ISOLDE flexfit → Phenix real_space_refine.
- Every residue in the deposited model carries `source ∈ {from_AF, from_map_remodel, disordered_low_plddt_low_density}`.
- Flag AF-vs-map disagreement as biology (potential conformational state difference), not noise.
