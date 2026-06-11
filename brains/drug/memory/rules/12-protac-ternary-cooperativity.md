---
rule_id: 12-protac-ternary-cooperativity
rule_type: case_distilled
applies_to: {target_class: ALL, modality: [protac, molecular_glue], project_phase: ALL}
confidence: high
evidence_cases: [drug-007-protac-dbet1]
schema_version: 2
---

# Rule 12: PROTAC needs ternary complex modeling, not single-target docking

## Statement
A PROTAC molecule has three components — target warhead, linker, E3-ligase ligand. Designing it as if it were a single inhibitor (just the warhead) misses ternary geometry, cooperativity α, and the hook effect.

Required design pipeline:
1. Identify warhead, linker, and E3 ligand (CRBN / VHL / IAP / MDM2 are common)
2. Model **ternary complex** (target-PROTAC-E3) — `protac_ternary` skill
3. Compute **cooperativity α = K_d(binary) / K_d(ternary)**; α > 1 means ternary is more stable than binary (productive)
4. Test ≥ 5 linker lengths (PEG vs alkyl vs rigid)
5. Warn on **hook effect**: at high PROTAC concentration, binary complexes outcompete ternary, killing degradation (bell-shape dose-response)

Track: DC50, Dmax, ternary stability, cell penetration (MW typically 700-900 → permeability is bottleneck).

## Why
dBET1 (drug-007) is the founding case: JQ1 + thalidomide-derivative + PEG linker. PROTAC science split from inhibitor design because the binding event is catalytic (PROTAC is recycled), not stoichiometric. Linker length > 5 atoms is typical; pure PEG often loses cell permeability.

## How to apply
- Reviewer at design stage blocks pipelines that route PROTAC through `vina_gnina_dock` instead of `protac_ternary`.
- Reviewer warns when linker explicitly all-PEG without alkyl/rigid alternatives in `compound_library`.
- Reporting stage requires `cooperativity_alpha` field on every PROTAC candidate.
