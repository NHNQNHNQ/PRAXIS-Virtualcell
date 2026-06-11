---
rule_id: 10-synthesis-filter-sa-aizynth
rule_type: case_distilled
applies_to: {target_class: ALL, modality: [small_mol_inhibitor, agonist, allosteric, covalent], project_phase: ALL}
confidence: high
evidence_cases: [drug-002-reinvent-jak2-de-novo, drug-005-aizynth-retrosynthesis]
schema_version: 2
---

# Rule 10: Triple synthesis filter — SAscore + AiZynth + commercial start materials

## Statement
Every candidate must pass three synthesis filters in series:
1. **SAscore** ≤ 4.5 (Ertl & Schuffenhauer 2009)
2. **AiZynthFinder** returns at least one route ≤ 6 steps
3. **Commercial start materials** — at least 80% of starting reagents available from eMolecules / Enamine BB / Sigma

Top-N reporting includes the route length and the start materials list.

## Why
SAscore is fast but blind to macrocycles, atropisomers, late-stage diversification. AiZynthFinder catches feasibility but can return long synthetic plans. Commercial-availability check catches the "rare reagent" failure mode (drug-005 imatinib teaches industrial 5-7 steps; drug-002 generative produced ≥ 8-step molecules with rare heterocycles).

## How to apply
- Skill `aizynth_retrosynthesis` (P0) returns `routes[]` with `length`, `score`, `commercial_start_materials`.
- Reviewer at reporting stage requires every Top-N candidate to carry a `synth_route` block with `n_steps ≤ 6` AND `commercial_start_materials` non-empty.
- Compounds failing synthesis filters are moved to `excluded_compounds_section` with reason "synthesis_infeasible".
