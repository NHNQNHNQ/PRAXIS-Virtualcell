---
rule_id: 09-mutation-panel-lead-opt
rule_type: case_distilled
applies_to: {target_class: [kinase, gtpase, protease, polymerase], modality: [small_mol_inhibitor, covalent, allosteric], project_phase: [lead_opt, lead_opt_to_clinic]}
confidence: high
evidence_cases: [drug-010-imatinib-sar-bcr-abl]
schema_version: 2
---

# Rule 09: Mutation panel mandatory in lead-opt for resistance-prone targets

## Statement
For lead optimization on a target known to develop drug resistance (kinases, GTPases, proteases, polymerases), the design plan must include `mutation_panel_screen` against the clinically observed resistance mutations.

Minimum required panel for kinase targets:
- Gatekeeper mutation (e.g., ABL1 T315I, EGFR T790M, ALK L1196M)
- ATP-binding loop mutations
- C-helix / activation loop mutations

Pass criterion: lead candidates must retain affinity (`Δ docking score < 1.5 kcal/mol`) on all panel members, OR an explicit "resistance-targeted backup" series must be in the same project.

## Why
Imatinib → T315I resistance defined the BCR-ABL second-generation push (nilotinib, dasatinib, ponatinib). Designing a single lead without parallel resistance planning gives a 2-3 year clinical lifespan before resistance limits indication.

## How to apply
- Reviewer at design stage blocks lead-opt design plans whose `validation_plan.mutation_panel_required = false` for kinase / gtpase / protease / polymerase targets.
- Skill `mutation_panel_screen` runs PyRosetta cartesian_ddg for each mutation (antibody env), then `vina_gnina_dock` per mutated structure.
- Score difference > 1.5 kcal/mol on any single mutation is flagged; > 1.5 kcal/mol on ≥ 2 mutations downgrades the lead to "resistance-vulnerable" tag.
