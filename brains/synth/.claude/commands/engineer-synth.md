---
name: engineer-synth
description: Run a synthetic biology task end-to-end through PRAXIS-Synth. One-shot wrapper around the synth-engineer subagent + the engineer_synth.py CLI.
allowed-tools: Bash(python:*), Read, Glob
---

Run a synth bio task through PRAXIS-Synth's 4-stage agent brain.

## Usage in chat

```
/engineer-synth pathway_design lycopene in E. coli at fermenter scale
/engineer-synth strain engineering of C. glutamicum for lysine industrial titer
/engineer-synth bgc_mining on Streptomyces sp. genome
/engineer-synth fba on iML1515
/engineer-synth golden gate plasmid assembly with 5 fragments
/engineer-synth biosensor for arabinose with 5 cross-reactants
```

## What this command does

1. Parses the user's natural-language task → maps to `synth_task ∈ {fba, pathway_design, plasmid_assembly, codon_opt, circuit, cell_free, biosensor, strain_engineering, bgc_mining}`.
2. Invokes `python /Volumes/T7/PRAXIS-Synth/scripts/engineer_synth.py` with extracted args.
3. Reports the Synthesis Recommendation (rules invoked, top cases, design library, validation plan, reproduce.sh).

## Behind the scenes

- Memory: 10 real-literature cases + 11 case-distilled rules + 9 task-overview landscape rules + 1 cold-start bootstrap.
- Retrieval: 8-channel RRF (k=60) with `(synth_task, host_organism)` pool routing.
- Pipeline: 4-stage orchestrator (Scoping → Design → Execution → Reporting) with deterministic Reviewer gate enforcing all 11 rules + 9 forbidden shortcuts.
- 10 skills with anti-shortcut enforcement: `fba_simulate / golden_gate_assembly / codon_optimize / heterologous_pathway_design / optknock_strain / circuit_simulate / dna_constraint_solve / cellfree_design / biosensor_design / bgc_mining`.

## Hard rules the agent will not violate

- Every DOI cited must come from CrossRef-verified retrieved cases (no invented citations).
- Every numerical claim must come from a real tool invocation with logged provenance (no fabricated numbers).
- `excluded_designs[]` is mandatory non-empty (rule from synthesis §III).
- All 9 "不允许的捷径" enforced (single-objective FBA / overhang collision / internal restriction site / single colony pick / bistable no-sweep / OptKnock essential KO / antiSMASH no MIBiG / no reproduce.sh).

If the task is outside synth bio, suggest routing to a sibling agent (PRAXIS-Enzyme / PRAXIS-Drug / PRAXIS-Protein / PRAXIS-MD).
