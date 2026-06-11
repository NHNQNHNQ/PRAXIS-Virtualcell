# fba-simulate

## Skill ID
`fba_simulate`

## What it does
fba_simulate — flux balance analysis with multi-objective Pareto + MEMOTE QC.

## Backends
COBRApy, Cameo, reframed

## Anti-shortcut enforcement
Enforces: rule 01.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/fba-simulate/run.py --help
```
