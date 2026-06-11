# golden-gate-assembly

## Skill ID
`golden_gate_assembly`

## What it does
golden_gate_assembly — Type-IIs Golden Gate / MoClo plan with mandatory
overhang collision check + internal-site scan (rules 03, 04).

## Backends
Biopython.Restriction, pydna, j5

## Anti-shortcut enforcement
Enforces: rules 03, 04.

## Sanity test
See `tests/test_sanity.py` and `tests/test_phase2_skills.py`.

## Negative tests (counter-examples)
See `tests/test_negative_skills.py`.

## CLI
```
python skills/workflows/golden-gate-assembly/run.py --help
```
