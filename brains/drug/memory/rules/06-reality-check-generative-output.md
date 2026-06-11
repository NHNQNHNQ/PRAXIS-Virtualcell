---
rule_id: 06-reality-check-generative-output
rule_type: case_distilled
applies_to: {target_class: ALL, modality: [small_mol_inhibitor, allosteric], project_phase: hit_id}
confidence: high
evidence_cases: [drug-002-reinvent-jak2-de-novo, drug-003-pocket2mol-sbdd]
schema_version: 2
---

# Rule 06: Reality-check every generative output

## Statement
Any compound produced by a generative model (REINVENT4, Pocket2Mol, MolGPT, TargetDiff, DiffSBDD, etc.) must pass three filters before being eligible as a "hit candidate":

1. **Re-dock validation** — `vina_gnina_dock` against the actual target structure
2. **ADMET multi-method** — `admet_multi` (ADMET-AI + SwissADME + pkCSM consensus)
3. **Retrosynthesis filter** — `aizynth_retrosynthesis` returns ≥ 1 route ≤ 6 steps with commercial start materials

A compound failing any of three is removed from the hit list with a logged reason.

## Why
Generative models optimize against their reward function — which is always a proxy for real drug-likeness. They produce strain-energy-violating structures (atom collisions, bad bond angles), molecules with macrocycles or rare heterocycles that aren't synthesizable, and molecules with predicted potency but ADMET red flags. Without reality check, the user sees plausible-looking SMILES that have zero chance of being made or tested.

## How to apply
- Reviewer at design stage blocks `compound_library` entries with `source: de_novo_generated` if `computational_pipeline.skill_ids` doesn't include all three of (`vina_gnina_dock`, `admet_multi`, `aizynth_retrosynthesis`).
- Reviewer at execution stage requires every `de_novo_generated` candidate carry `passed_qc: true` only if all three filters returned acceptable results.
