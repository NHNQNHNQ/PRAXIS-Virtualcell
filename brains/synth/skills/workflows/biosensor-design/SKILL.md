# biosensor-design

## Skill ID
`biosensor_design`

## What it does
biosensor_design — TF-promoter sensor design + dose-response + cross-reactant panel.

## Backends
Hill model, iBioSim, Cello

## Anti-shortcut enforcement
Enforces: rules 07, 10.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/biosensor-design/run.py --help
```
