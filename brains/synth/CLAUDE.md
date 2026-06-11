# PRAXIS-Synth — Agent Operating Manual

> **⚠ FIRST, READ [ENVIRONMENTS.md](./ENVIRONMENTS.md).** antiSMASH / iBioSim / RetroPath / BiG-SCAPE / DeepBGC are NOT installed on this host — skills return planning-only output. CrossRef + NCBI Web APIs work once `NCBI_EMAIL` + `CROSSREF_MAILTO` are set.

You are operating inside **PRAXIS-Synth**, a case-based-learning agent for synthetic biology. Your decisions are grounded in 10 real-literature cases (`memory/cases/`) plus 11 case-distilled rules (`memory/rules/`). The Reviewer gate will block any plan that violates the rules; treat the rules as load-bearing.

## Your brain (4-stage pipeline)

| Stage | Input | Output | Schema | Reviewer enforces |
|---|---|---|---|---|
| **Scoping** | `task.problem.{synth_task, host_organism, target_compound, scale, ...}` | `scoping_plan.json` | `schemas/scoping_plan.schema.json` | ≥3 candidate strategies for `pathway_design` / `bgc_mining`; every strategy cites a case_id or rule_id |
| **Design** | `scoping_plan` | `design_plan.json` | `schemas/design_plan.schema.json` | `excluded_designs` non-empty; pipeline ordering (`codon_optimize` before `fba_simulate`); `multi_objective: true` for FBA; OptKnock has essential-gene audit |
| **Execution** | `design_plan` | `execution_results.json` | `schemas/execution_results.schema.json` | Every step tagged `simulated/partial/full`; antiSMASH cross-checked vs MIBiG; Golden Gate has overhang-collision validator output |
| **Reporting** | `execution_results` | `report.json` + `outputs/report.md` | `schemas/report.schema.json` | `reproducibility.shell_script` non-empty; `interpretation.why_failed` array exists; DOIs from retrieved evidence |

Max **2 repair loops** per stage. If reviewer still fails after 2, output is frozen with `_warning` annotation.

## Your retrieval (8 channels)

```
synth_task        host_organism      target_compound   pathway_class
assembly_strategy scale              method_choice     text (BM25)
```

Pool routing: `same_task_same_host : same_task : same_host : cross = 5 : 2 : 1 : 1`. Cold-start at n=10 cases — `same_task_only` mode (full routing kicks in at n≥30).

Channel weights vary by stage — see `config/retrieval.yaml`.

## Hard rules (Reviewer rejects on violation)

| Rule | Source | When it fires |
|---|---|---|
| **01 multi-objective FBA** | cases 001, 009 | any `fba_simulate` or `optknock_strain` step |
| **02 codon-optimize mandatory** | cases 002, 004, 007 | host ≠ source organism in heterologous pathway |
| **03 overhang collision check** | case 003 | any `golden_gate_assembly` |
| **04 destroy internal restriction sites** | cases 003, 006 | parts contain BsaI/BsmBI/SapI sites |
| **05 ≥3 colony pick** | case 003 | any cloning protocol |
| **06 bistable parametric simulation** | case 005 | any toggle / bistable circuit |
| **07 flow cytometry, not bulk plate** | cases 005, 008 | bistable readout |
| **08 OptKnock essential-gene audit** | case 009 | any OptKnock call |
| **09 antiSMASH cross-check MIBiG** | case 010 | any BGC mining run |
| **10 biosensor specificity panel** | case 008 | any biosensor design |
| **11 P450 needs CPR partner** | case 002 | any pathway containing a P450 |

## Hard "不允许的捷径"

- ❌ MEMOTE not run on FBA model
- ❌ Single-objective FBA (must be multi-objective Pareto)
- ❌ Overhang collision not checked in Golden Gate
- ❌ Internal restriction site not destroyed
- ❌ Single colony pick (need ≥3)
- ❌ Bistable circuit without parametric simulation
- ❌ OptKnock targets essential gene (must audit + remove first)
- ❌ antiSMASH not cross-checked with MIBiG
- ❌ No `reproduce.sh`

## How to run

```bash
python scripts/engineer_synth.py \
    --synth-task pathway_design --host "E. coli" \
    --target-compound lycopene --scale fermenter

# or full pipeline:
python -m agents.orchestrator --task-file runs/inputs/task.json
```

## When a wetlab envelope arrives

`lims/filedrop_watcher.py --watch` validates JSON drops to `runs/{task_id}/wetlab_data/`. Then:

```bash
python -m agents.orchestrator --task-file runs/inputs/task.json --resume-from reporting
```

The Reporting agent merges `wetlab_data/_validated/*.json` into `execution.wetlab_results`.

## Honesty principles

- Every numerical result has `tool_provenance.{simulated|partial|full, version, wallclock_seconds, stderr_tail}`.
- If a binary is missing, the skill returns `passed_qc=false` and `simulated=true`. Do not silently fall through.
- DOIs cited in `report.references[]` MUST appear in some `retrieved_evidence.cases[]`. Do not invent citations.
- `confidence` label is always present: `cold_start | low | medium | high | domain_knowledge`.

## Files you frequently touch

- `memory/cases/synth-NNN-*.md` — the 10 seed cases (read-only at runtime).
- `memory/rules/*.md` — rules; reviewer reads these for stage checks.
- `agents/prompts/*.md` — your stage prompts.
- `runs/{task_id}/intermediates/{stage}.json` — per-stage outputs persisted for resume.
