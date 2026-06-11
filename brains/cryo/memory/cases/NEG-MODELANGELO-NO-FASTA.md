---
case_id: NEG-MODELANGELO-NO-FASTA
schema_version: 1
case_polarity: negative
sample_type: any
target_pdb: null
target_emdb: null
molecular_weight_kda: 200
symmetry_group: C1
resolution_target: "2-3"
resolution_achieved_a: 2.8
detector_type: K3
detergent_or_lipid: none
method_choice: [modelangelo_no_sequence]
tools: [ModelAngelo 1.0]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1038/s41586-024-07215-4"
  citation: "Jamali K, et al. ModelAngelo Nature 2024 — sequence input is described as required for assignment + per-residue confidence"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 9
veto_reason: "ModelAngelo run without sequence FASTA → output is poly-Ala backbone trace; no chain assignment, no per-residue confidence; downstream useless"
related_positive_cases: [cryo-005-modelangelo-buildmodel]
tags: [NEG, anti_pattern, modelangelo_no_fasta, polyalanine_only, no_sequence_assignment]
---

# NEG-MODELANGELO-NO-FASTA — ModelAngelo without sequence input

## Background (failure pattern)
ModelAngelo's per-residue confidence and chain assignment depend on the sequence FASTA input. Without it, the output is a poly-alanine backbone trace — geometrically reasonable but biologically useless: no side-chains assigned, no chain identity, downstream Phenix refinement has nothing to refine against.

## What was actually done (the wrong path)
1. Sharpened map → ModelAngelo invoked with `--map foo.mrc` only (no `--fasta`).
2. Output: poly-Ala mmCIF with backbone-only trace.
3. Phenix real_space_refine cannot proceed without side-chains.
4. ~3 days of manual Coot tracing to recover what would have taken seconds with the FASTA input.

## ★ Why this is forbidden
- The sequence FASTA is the cheapest input on the entire pipeline.
- Without it, every downstream tool (Phenix, Coot, validation) is partially blocked.
- The skill runner refuses to proceed (skill-level FAIL: `MODELANGELO_NO_SEQUENCE`).

## ★ Anti-rule mapping
**anti-rule 9**: ModelAngelo invocation without a non-empty sequence FASTA path → Reviewer veto + skill-level hard fail.

## Mitigation (rule 06-modelangelo-firstpass-not-final)
- Always provide multi-chain FASTA matching the complex composition.
- Verify chain count + length sum matches the expected map molecular weight.
